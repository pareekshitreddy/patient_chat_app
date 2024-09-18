from django.shortcuts import render, redirect
from .models import Message, Patient
from django.utils import timezone

def chat_view(request):
    messages = Message.objects.all().order_by('timestamp')
    patient = Patient.objects.first()
    request_output = None

    if request.method == 'POST':
        if user_message := request.POST.get('message'):
            Message.objects.create(sender='patient', text=user_message)
            bot_response = process_bot_response(user_message, patient)
            Message.objects.create(sender='bot', text=bot_response)

            # Check if it's an appointment request
            if is_appointment_request(user_message):
                requested_time = extract_requested_time(user_message)
                request_output = f"Patient {patient.first_name} {patient.last_name} is requesting an appointment change to {requested_time}."

        context = {
            'messages': messages,
            'patient': patient,
            'request_output': request_output,
        }
        return render(request, 'chat/chat.html', context)

    context = {
        'messages': messages,
        'patient': patient,
    }
    return render(request, 'chat/chat.html', context)


import requests

GEMINI_API_KEY = 'AIzaSyAwzpBRwIN4CdNj1l9SiJ-msrZxB3Uwu1c'  # Will delete it once the project is done

def process_bot_response(user_message, patient):
    # Filter the message
    if not is_health_related(user_message):
        return "I'm sorry, but I can only assist with health-related questions."

    # Check for appointment or treatment requests
    if is_appointment_request(user_message):
        requested_time = extract_requested_time(user_message)
        output_message = f"Patient {patient.first_name} {patient.last_name} is requesting an appointment change to {requested_time}."
        # You can handle the output_message as needed
        return f"I will convey your request to Dr. {patient.doctor_name}."

    # Generate messages for the API
    messages = generate_prompt(user_message, patient)

    # Get the response from the Gemini model
    bot_response = get_gemini_response(messages)

    return bot_response


def is_health_related(message):
    # Simple keyword check (can be enhanced)
    health_keywords = ['health', 'medication', 'appointment', 'doctor', 'pain', 'treatment', 'diet']
    return any(word in message.lower() for word in health_keywords)

def is_appointment_request(message):
    appointment_keywords = ['appointment', 'reschedule', 'schedule', 'cancel']
    return any(word in message.lower() for word in appointment_keywords)

def extract_requested_time(message):
    # Simple extraction (can be enhanced with NLP libraries)
    # For now, we'll just return the whole message
    return message

def generate_prompt(user_message, patient):
    # System message to define the assistant's behavior
    system_message = (
        f"You are HealthBot, a friendly and empathetic health assistant chatbot. "
        f"You are assisting {patient.first_name}, who has {patient.medical_condition}. "
        "Provide clear, supportive responses to their health-related questions. "
        "Use simple language and a conversational tone."
    )

    # Fetch the last few messages for context
    recent_messages = Message.objects.all().order_by('-timestamp')[:5]
    conversation_history = []
    for msg in reversed(recent_messages):
        role = 'user' if msg.sender == 'patient' else 'assistant'
        conversation_history.append({'role': role, 'content': msg.text})

    # Add the current user message
    conversation_history.append({'role': 'user', 'content': user_message})

    return [{'role': 'system', 'content': system_message}] + conversation_history



def get_gemini_response(messages):
    url = 'https://api.gemini.com/v1/chat/completions'  # Replace with the correct endpoint
    headers = {
        'Authorization': f'Bearer {GEMINI_API_KEY}',
        'Content-Type': 'application/json',
    }
    data = {
    'model': 'gemini-chat-1',  # Use the correct model name
    'messages': messages,
    'temperature': 0.6,  # Lower values for more focused responses
    'max_tokens': 200,   # Adjust as needed
    'n': 1,
    'stop': None,
}

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        bot_reply = response.json()['choices'][0]['message']['content']
        # Perform safety check
        if contains_disallowed_content(bot_reply):
            return "I'm sorry, but I can't assist with that request."
        return bot_reply.strip()
    except requests.exceptions.RequestException as e:
        # Log the error for debugging
        print(f"API Request failed: {e}")
        return "Sorry, I'm having trouble responding right now."


import spacy

nlp = spacy.load('en_core_web_sm')

def extract_entities(message):
    doc = nlp(message)
    return {ent.label_: ent.text for ent in doc.ents}

def contains_disallowed_content(text):
    # Simple keyword-based check
    disallowed_keywords = ['illegal', 'violent', 'hate', 'explicit']
    return any(word in text.lower() for word in disallowed_keywords)

