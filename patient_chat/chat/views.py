# Imports
import os
import re
from datetime import datetime
from dotenv import load_dotenv
from django.shortcuts import render
from dateparser.search import search_dates

from .models import Message, Patient, PatientRequest
from .neo4j_driver import Neo4jDriver

# LangChain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv(override=True)

# Global Variables and Initializations
GEMINI_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gemini-1.5-flash")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

# Initialize the Neo4j driver
neo4j_driver = Neo4jDriver("bolt://localhost:7687", "neo4j", "dtxplus2024")  # Update with your credentials

# View Function
def chat_view(request):
    messages = Message.objects.all().order_by('timestamp')
    patient = Patient.objects.first()
    neo4j_driver.save_patient_data(patient)
    request_output = None
    entities = None
    conversation_summary = None
    medical_insights = None

    if request.method == 'POST':
        user_message = request.POST.get('message')
        if user_message:
            Message.objects.create(sender='patient', text=user_message)
            bot_response, request_output, entities, conversation_summary, medical_insights = process_bot_response(
                user_message, patient)
            Message.objects.create(sender='bot', text=bot_response)

        context = {
            'messages': Message.objects.all().order_by('timestamp'),
            'patient': patient,
            'request_output': request_output,
            'entities': entities,
            'conversation_summary': conversation_summary,
            'medical_insights': medical_insights,
        }
        return render(request, 'chat/chat.html', context)

    context = {
        'messages': messages,
        'patient': patient,
        'request_output': request_output,
        'entities': entities,
        'conversation_summary': conversation_summary,
        'medical_insights': medical_insights,
    }
    return render(request, 'chat/chat.html', context)

# Helper Functions
def process_bot_response(user_message, patient):
    # Check if the message is health-related
    if not is_health_related(user_message):
        return "I'm sorry, but I can only assist with health-related questions.", None, None, None, None

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

    # Generate conversation summary and medical insights
    conversation_summary, medical_insights = generate_summary_and_insights(patient)

    # Initialize output_message
    output_message = None

    # Check if it's an appointment request
    if is_appointment_request(preprocessed_message):
        # Extract requested time for appointment change
        requested_time = extract_requested_time(preprocessed_message)
        if requested_time != 'unspecified time':
            output_message = (
                f"Patient {patient.first_name} {patient.last_name} is requesting an appointment change "
                f"from {patient.next_appointment.strftime('%Y-%m-%d %H:%M')} to {requested_time}."
            )
            # Save the appointment change request to the database
            PatientRequest.objects.create(
                patient=patient,
                request_type='appointment',
                details=f"Change from {patient.next_appointment.strftime('%Y-%m-%d %H:%M')} to {requested_time}",
            )
        else:
            output_message = (
                f"Patient {patient.first_name} {patient.last_name} has made an appointment request: {user_message}"
            )
            # Save the appointment request to the database
            PatientRequest.objects.create(
                patient=patient,
                request_type='appointment',
                details=user_message,
            )
    # Check if it's a treatment request
    elif is_treatment_request(preprocessed_message):
        if 'medication' in entities:
            medication = entities.get('medication')
            output_message = (
                f"Patient {patient.first_name} {patient.last_name} is requesting a change in medication: "
                f"{medication}."
            )
            # Save the medication change request to the database
            PatientRequest.objects.create(
                patient=patient,
                request_type='medication',
                details=f"Change medication to {medication}",
            )
        else:
            output_message = (
                f"Patient {patient.first_name} {patient.last_name} has made a treatment request: {user_message}"
            )
            # Save the treatment request to the database
            PatientRequest.objects.create(
                patient=patient,
                request_type='medication',
                details=user_message,
            )
    else:
        output_message = None

    return bot_response, output_message, entities, conversation_summary, medical_insights

def contains_disallowed_content(text):
    disallowed_keywords = [
        'illegal', 'violent', 'hate', 'explicit', 'politics', 'religion', 'offensive'
    ]
    return any(word in text.lower() for word in disallowed_keywords)

def is_health_related(message):
    disallowed_keywords = [
        'politics', 'religion', 'violence', 'illegal', 'hate', 'explicit', 'offensive'
    ]
    message_lower = message.lower()

    if any(word in message_lower for word in disallowed_keywords):
        return False

    health_keywords = [
        'health', 'medication', 'medicine', 'drug', 'appointment', 'doctor', 'pain',
        'treatment', 'diet', 'symptom', 'exercise', 'nutrition', 'therapy', 'diagnosis',
        'wellness', 'prescription', 'illness', 'injury', 'recovery', 'surgery', 'pill',
        'dosage', 'take', 'taking', 'tablet', 'capsule', 'twice a day', 'once a day',
        'morning', 'evening', 'lab tests', 'doctor notes', 'weight', 'vital signs',
        'medications'
    ]

    return any(word in message_lower for word in health_keywords)

def is_appointment_request(message):
    message_lower = message.lower()
    appointment_actions = ['reschedule', 'schedule', 'cancel', 'change', 'move', 'book']
    return 'appointment' in message_lower and any(
        action in message_lower for action in appointment_actions
    )

def is_treatment_request(message):
    treatment_keywords = [
        'medication', 'change medication', 'new medication', 'dosage', 'prescription',
        'therapy', 'change medicine', 'adjust medication'
    ]
    return any(phrase in message.lower() for phrase in treatment_keywords)

def preprocess_message(message):
    # Replace ordinal numbers with cardinal numbers (e.g., '1st' -> '1')
    return re.sub(r'\b(\d+)(st|nd|rd|th)\b', r'\1', message)

def extract_requested_time(message):
    message = message.lower()
    import re
    from dateutil.relativedelta import relativedelta, MO, TU, WE, TH, FR, SA, SU

    day_pattern = r'(next|this)?\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)'
    time_pattern = r'at\s*(\d{1,2}(?::\d{2})?\s*(am|pm)?)'

    day_match = re.search(day_pattern, message)
    time_match = re.search(time_pattern, message)

    weekdays = {
        'monday': MO, 'tuesday': TU, 'wednesday': WE, 'thursday': TH,
        'friday': FR, 'saturday': SA, 'sunday': SU
    }

    if day_match:
        day_modifier = day_match.group(1)
        day_name = day_match.group(2)
        current_date = datetime.now()
        if day_modifier == 'next':
            appointment_date = current_date + relativedelta(weekday=weekdays[day_name](+1))
        else:
            appointment_date = current_date + relativedelta(weekday=weekdays[day_name](+0))
            if appointment_date < current_date:
                appointment_date += relativedelta(weeks=1)
    else:
        appointment_date = None

    if time_match:
        time_str = time_match.group(1)
        from dateutil import parser
        appointment_time = parser.parse(time_str).time()
    else:
        appointment_time = None

    if appointment_date and appointment_time:
        appointment_datetime = datetime.combine(appointment_date.date(), appointment_time)
        return appointment_datetime.strftime('%Y-%m-%d %H:%M')
    elif appointment_date:
        return appointment_date.strftime('%Y-%m-%d')
    else:
        return 'unspecified time'

def format_patient_knowledge(knowledge):
    knowledge_items = []
    for key, value in knowledge.items():
        if value:
            if isinstance(value, list):
                filtered_values = [str(v) for v in value if v is not None]
                value_str = ', '.join(filtered_values) if filtered_values else ''
            else:
                value_str = str(value)
            if value_str:
                knowledge_items.append(f"{key.replace('_', ' ').title()}: {value_str}")
    return "; ".join(knowledge_items)

def generate_prompt(user_message, patient):
    patient_knowledge = neo4j_driver.get_patient_knowledge(f"{patient.first_name} {patient.last_name}")
    patient_knowledge_text = format_patient_knowledge(patient_knowledge)

    system_message = (
        f"You are HealthBot, a friendly and empathetic health assistant chatbot. "
        f"You are assisting {patient.first_name} {patient.last_name}. "
        f"Patient information: {patient_knowledge_text}. "
        "Provide clear, supportive responses to their questions. "
        "If the patient requests to change an appointment or treatment, respond with "
        f"'I will convey your request to Dr. {patient.doctor_name}.' "
        "Do not mention any limitations or inability to assist. "
        "Use simple language and a conversational tone."
    )

    messages = [{'role': 'system', 'content': system_message}]
    total_tokens = len(system_message.split())
    max_tokens = 500

    recent_messages = Message.objects.all().order_by('-timestamp')[:5]

    for msg in reversed(recent_messages):
        role = 'user' if msg.sender == 'patient' else 'assistant'
        content = msg.text
        content_tokens = len(content.split())
        if total_tokens + content_tokens > max_tokens:
            break
        messages.append({'role': role, 'content': content})
        total_tokens += content_tokens

    messages.append({'role': 'user', 'content': user_message})
    return messages

def get_gemini_response(messages):
    lc_messages = []

    for msg in messages:
        if msg['role'] == 'system':
            lc_messages.append(SystemMessage(content=msg['content']))
        elif msg['role'] == 'user':
            lc_messages.append(HumanMessage(content=msg['content']))
        elif msg['role'] == 'assistant':
            lc_messages.append(AIMessage(content=msg['content']))

    try:
        chat = ChatGoogleGenerativeAI(
            model=LLM_MODEL_NAME,
            temperature=0.6,
            top_p=0.8,
            top_k=40,
            google_api_key=GEMINI_API_KEY,
        )
        response = chat(lc_messages)
        bot_reply = response.content

        if contains_disallowed_content(bot_reply):
            return "I'm sorry, but I can't assist with that request."
        return bot_reply.strip()

    except Exception:
        return "Sorry, I'm having trouble responding right now."

def extract_entities_with_llm(message):
    response_schemas = [
        ResponseSchema(name="medication", description="Name of the medication mentioned by the patient"),
        ResponseSchema(name="frequency", description="Frequency of medication intake"),
        ResponseSchema(name="date", description="Date mentioned in the message"),
        ResponseSchema(name="time", description="Time mentioned in the message"),
        ResponseSchema(name="symptom", description="Symptom mentioned by the patient"),
        ResponseSchema(name="diet", description="Diet mentioned by the patient"),
        ResponseSchema(name="lab_test", description="Lab test mentioned by the patient"),
        ResponseSchema(name="vital_sign", description="Vital sign mentioned by the patient"),
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
        model=LLM_MODEL_NAME,
        temperature=0,
        google_api_key=GEMINI_API_KEY,
    )

    try:
        response = llm([HumanMessage(content=_input.to_string())])
        entities = output_parser.parse(response.content)
    except Exception:
        entities = {}

    return entities

# def generate_summary_and_insights(patient):
#     recent_messages = Message.objects.all().order_by('-timestamp')[:10]
#     recent_messages = reversed(recent_messages)

#     conversation_history = ""
#     for msg in recent_messages:
#         sender = "Patient" if msg.sender == 'patient' else "Bot"
#         conversation_history += f"{sender}: {msg.text}\n"

#     response_schemas = [
#         ResponseSchema(name="summary", description="A brief summary of the conversation."),
#         ResponseSchema(name="medical_insights", description="Any medical insights or important information mentioned."),
#     ]

#     output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
#     format_instructions = output_parser.get_format_instructions()

#     prompt = (
#         "You are a medical assistant helping to summarize a conversation and extract medical insights.\n\n"
#         "Conversation:\n"
#         f"{conversation_history}\n"
#         "Please provide your response in the following JSON format:\n"
#         f"{format_instructions}"
#     )

#     try:
#         llm = ChatGoogleGenerativeAI(
#             model=LLM_MODEL_NAME,
#             temperature=0,
#             google_api_key=GEMINI_API_KEY,
#         )
#         response = llm([HumanMessage(content=prompt)])
#         output = response.content.strip()

#         parsed_output = output_parser.parse(output)
#         conversation_summary = parsed_output.get('summary', 'Could not generate summary.')
#         medical_insights = parsed_output.get('medical_insights', 'Could not extract medical insights.')

#     except Exception:
#         conversation_summary = "Error generating summary."
#         medical_insights = "Error extracting medical insights."

#     return conversation_summary, medical_insights
