# Imports
import os
import re
from datetime import datetime
from dotenv import load_dotenv
from django.shortcuts import render
import spacy
from dateparser.search import search_dates

from .models import Message, Patient
from .neo4j_driver import Neo4jDriver

# LangChain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.prompts import PromptTemplate

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(override=True)

# Global Variables and Initializations
GEMINI_API_KEY = os.getenv("LLM_API_KEY")
logger.info(f"GEMINI_API_KEY: {GEMINI_API_KEY}")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

# Initialize the NLP model
nlp = spacy.load('en_core_web_sm')

# Initialize the Neo4j driver
neo4j_driver = Neo4jDriver("bolt://localhost:7687", "neo4j", "dtxplus2024")  # Update with your credentials

# View Function
def chat_view(request):
    messages = Message.objects.all().order_by('timestamp')
    patient = Patient.objects.first()
    request_output = None
    entities = None

    if request.method == 'POST':
        user_message = request.POST.get('message')
        if user_message:
            Message.objects.create(sender='patient', text=user_message)
            bot_response, request_output, entities = process_bot_response(user_message, patient)
            Message.objects.create(sender='bot', text=bot_response)

        context = {
            'messages': Message.objects.all().order_by('timestamp'),
            'patient': patient,
            'request_output': request_output,
            'entities': entities,
        }
        return render(request, 'chat/chat.html', context)

    context = {
        'messages': messages,
        'patient': patient,
        'request_output': request_output,
        'entities': entities,
    }
    return render(request, 'chat/chat.html', context)

# Helper Functions
def process_bot_response(user_message, patient):
    # Check if the message is health-related
    if not is_health_related(user_message):
        return "I'm sorry, but I can only assist with health-related questions.", None, None

    # Preprocess the message
    preprocessed_message = preprocess_message(user_message)

    # Generate messages for the AI model
    messages = generate_prompt(preprocessed_message, patient)

    # Get response from the AI model
    bot_response = get_gemini_response(messages)

    # Extract entities from the user's message
    entities = extract_entities_with_llm(preprocessed_message)
    if entities:
        neo4j_driver.save_entities(f"{patient.first_name} {patient.last_name}", entities)

    # Detect appointment or treatment requests
    output_message = None
    if is_appointment_request(preprocessed_message) or is_treatment_request(preprocessed_message):
        # Extract relevant information
        requested_time = extract_requested_time(preprocessed_message)
        if requested_time != 'unspecified time':
            output_message = (
                f"Patient {patient.first_name} {patient.last_name} is requesting an appointment change "
                f"from {patient.next_appointment.strftime('%Y-%m-%d %H:%M')} to {requested_time}."
            )
        elif 'medication' in entities:
            output_message = (
                f"Patient {patient.first_name} {patient.last_name} is requesting a change in medication: "
                f"{entities.get('medication')}."
            )
        else:
            output_message = f"Patient {patient.first_name} {patient.last_name} has made a request: {user_message}"

    # Debugging statements
    logger.debug(f"User message: {user_message}")
    logger.debug(f"Preprocessed message: {preprocessed_message}")
    logger.debug(f"Entities extracted: {entities}")
    logger.debug(f"Bot response before processing: {bot_response}")

    return bot_response, output_message, entities

def contains_disallowed_content(text):
    disallowed_keywords = ['illegal', 'violent', 'hate', 'explicit', 'politics', 'religion', 'offensive']
    return any(word in text.lower() for word in disallowed_keywords)

def is_health_related(message):
    # Keywords related to disallowed topics
    disallowed_keywords = ['politics', 'religion', 'violence', 'illegal', 'hate', 'explicit', 'offensive']
    message_lower = message.lower()

    if any(word in message_lower for word in disallowed_keywords):
        return False

    # Keywords related to health topics
    health_keywords = [
        'health', 'medication', 'medicine', 'drug', 'appointment', 'doctor', 'pain', 'treatment',
        'diet', 'symptom', 'exercise', 'nutrition', 'therapy', 'diagnosis',
        'wellness', 'prescription', 'illness', 'injury', 'recovery', 'surgery',
        'pill', 'dosage', 'take', 'taking', 'tablet', 'capsule', 'twice a day', 'once a day', 'morning', 'evening'
    ]

    # If message contains health-related keywords, return True
    is_related = any(word in message_lower for word in health_keywords)
    logger.debug(f"Is health-related: {is_related}, Message: '{message}'")
    return is_related

def is_appointment_request(message):
    appointment_keywords = ['appointment', 'reschedule', 'schedule', 'cancel', 'change', 'move']
    return any(word in message.lower() for word in appointment_keywords)

def is_treatment_request(message):
    treatment_keywords = ['medication', 'treatment', 'dosage', 'prescription', 'therapy', 'change medicine']
    return any(word in message.lower() for word in treatment_keywords)

def preprocess_message(message):
    # Replace ordinal numbers with cardinal numbers (e.g., '1st' -> '1')
    message = re.sub(r'\b(\d+)(st|nd|rd|th)\b', r'\1', message)
    return message

def extract_requested_time(message):
    # Preprocess the message to handle ordinals
    message = preprocess_message(message)
    current_date = datetime.now()
    settings = {
        'PREFER_DATES_FROM': 'future',
        'RELATIVE_BASE': current_date,
        'DATE_ORDER': 'MDY',  # Adjust based on your locale ('MDY' or 'DMY')
    }
    results = search_dates(message, settings=settings)
    # Debug print to check what dateparser returns
    logger.debug(f"Dateparser Results: {results}")
    if results:
        extracted_date = results[0][1]
        return extracted_date.strftime('%Y-%m-%d %H:%M')
    else:
        return 'unspecified time'

def format_patient_knowledge(knowledge):
    knowledge_items = [f"{key}: {value}" for key, value in knowledge.items()]
    return "; ".join(knowledge_items)

def generate_prompt(user_message, patient):
    # Retrieve knowledge about the patient from the knowledge graph
    patient_knowledge = neo4j_driver.get_patient_knowledge(f"{patient.first_name} {patient.last_name}")
    # Format the knowledge into a string
    patient_knowledge_text = format_patient_knowledge(patient_knowledge)

    # Define system message with patient's context
    system_message = (
        f"You are HealthBot, a friendly and empathetic health assistant chatbot. "
        f"You are assisting {patient.first_name} {patient.last_name}, who has {patient.medical_condition}. "
        f"Medication regimen: {patient.medication_regimen}. "
        f"Additional patient information: {patient_knowledge_text}. "
        "Provide clear, supportive responses to their questions. "
        "If the patient requests to change an appointment or treatment, respond with "
        f"'I will convey your request to Dr. {patient.doctor_name}.' "
        "Do not mention any limitations or inability to assist. "
        "Use simple language and a conversational tone."
    )

    # Initialize messages list
    messages = [{'role': 'system', 'content': system_message}]
    total_tokens = len(system_message.split())
    max_tokens = 500  # Adjust based on the model's limits

    # Get recent messages
    recent_messages = Message.objects.all().order_by('-timestamp')[:5]

    # Add messages until token limit is reached
    for msg in reversed(recent_messages):
        role = 'user' if msg.sender == 'patient' else 'assistant'
        content = msg.text
        content_tokens = len(content.split())
        if total_tokens + content_tokens > max_tokens:
            break
        messages.append({'role': role, 'content': content})
        total_tokens += content_tokens

    # Add the current user message
    messages.append({'role': 'user', 'content': user_message})

    return messages

def get_gemini_response(messages):
    # Prepare the messages in the format expected by LangChain
    lc_messages = []

    for msg in messages:
        if msg['role'] == 'system':
            lc_messages.append(SystemMessage(content=msg['content']))
        elif msg['role'] == 'user':
            lc_messages.append(HumanMessage(content=msg['content']))
        elif msg['role'] == 'assistant':
            lc_messages.append(AIMessage(content=msg['content']))
    logger.debug(f"Messages sent to LLM: {lc_messages}")

    try:
        # Initialize the ChatGoogleGenerativeAI model
        chat = ChatGoogleGenerativeAI(
            model='gemini-1.5-flash',
            temperature=0.6,
            top_p=0.8,
            top_k=40,
            google_api_key=GEMINI_API_KEY,
        )

        # Get the response
        response = chat(lc_messages)
        bot_reply = response.content
        logger.debug(f"LLM response: {bot_reply}")

        # Perform safety check
        if contains_disallowed_content(bot_reply):
            return "I'm sorry, but I can't assist with that request."
        return bot_reply.strip()

    except Exception as e:
        # Log the error for debugging
        logger.error(f"API Request failed: {e}")
        return "Sorry, I'm having trouble responding right now."

def extract_entities_with_llm(message):
    response_schemas = [
        ResponseSchema(name="medication", description="Name of the medication mentioned by the patient"),
        ResponseSchema(name="frequency", description="Frequency of medication intake"),
        ResponseSchema(name="date", description="Date mentioned in the message"),
        ResponseSchema(name="time", description="Time mentioned in the message"),
        ResponseSchema(name="symptom", description="Symptom mentioned by the patient"),
        ResponseSchema(name="diet", description="Diet mentioned by the patient"),
        # Add more schemas as needed
    ]

    output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
    format_instructions = output_parser.get_format_instructions()

    prompt = PromptTemplate(
        template=(
            "You are an assistant that extracts relevant health-related information from patient messages. "
            "Only extract information related to medications, symptoms, dates, times, and present it in the specified JSON format.\n"
            "{format_instructions}\n\nMessage: {message}\n"
        ),
        input_variables=["message"],
        partial_variables={"format_instructions": format_instructions}
    )

    _input = prompt.format_prompt(message=message)
    llm = ChatGoogleGenerativeAI(
        model='gemini-1.5-flash',
        temperature=0,
        google_api_key=GEMINI_API_KEY,
    )

    try:
        response = llm([HumanMessage(content=_input.to_string())])
        logger.debug(f"LLM entity extraction response: {response.content}")
        entities = output_parser.parse(response.content)
    except Exception as e:
        logger.error(f"Error parsing entities: {e}")
        entities = {}

    return entities
