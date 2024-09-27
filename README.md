# PATIENT CHAT APPLICATION

## Overview

This Django application allows a patient to interact with an AI bot regarding their health and care plan. The AI bot is designed to handle health-related conversations, detect patient requests for changes to their treatment or appointments, and filter out irrelevant or sensitive topics.

## Table of Contents

- [Features](#features)
- [Bonus Features](#bonus-features)
- [Assumptions](#assumptions)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [Running the Application](#running-the-application)
- [Usage Instructions](#usage-instructions)
- [Explanation of Features](#explanation-of-features)
- [Conclusion](#conclusion)

## Features

- **Patient Profile**: A predefined patient with attributes such as First Name, Last Name, Date of Birth, Phone Number, Email, Medical Condition, Medication Regimen, Last Appointment DateTime, Next Appointment DateTime, and Doctor's Name.

- **Chat Interface**:
  - User-friendly chat box.
  - Displays conversation history with date and time stamps for each interaction.

- **AI Bot Functionality**:
  - Responds only to health-related topics.
    - General health and lifestyle inquiries.
    - Questions about the patient's medical condition, medication regimen, diet, etc.
  - Filters out and ignores any unrelated, sensitive, or controversial topics.
  - Manages long conversations while optimizing memory usage.

- **Appointment and Treatment Requests**:
  - Detects when the patient requests to modify their appointment or treatment.
    - Example: “Can we reschedule the appointment to next Friday at 3 PM?”
  - Responds with: “I will convey your request to Dr. [Doctor's Name].”
  - Outputs a message next to the chat box for review by the patient, summarizing the request.

- **Entity Extraction**:
  - Extracts key entities from the conversation.
    - Example: From “I am taking lisinopril twice a day”, it extracts `{medication: lisinopril, frequency: twice a day}`.
  - Stores extracted entities in a knowledge graph for use in subsequent conversations.

## Bonus Features

- **Knowledge Graph Integration**:
  - Integrates a Neo4j Knowledge Graph to dynamically query additional data about the patient.
  - Retrieves information like lab tests, doctor notes, weight, vital signs, and medications.

- **Conversation Summaries and Medical Insights**:
  - Generates live conversation summaries.
  - Extracts medical insights from ongoing conversations.

- **LLM Agnostic Design**:
  - Allows different language models to be easily swapped out by setting environment variables.
  - Utilizes LangChain for LLM and Retrieval-Augmented Generation (RAG).

## Assumptions

- **Single Patient**:
  - The application is designed for one patient (no authentication/authorization needed).
  - Patient data is either hardcoded or stored in a database table with one entry.

- **Health-Focused**:
  - The AI bot focuses solely on health-related topics.
  - Filters out unrelated, sensitive, or controversial topics.

- **Environment Variables**:
  - API keys and model names are set using environment variables for flexibility.

## Prerequisites

- **Python**: Version 3.7 or higher.
- **Django**: Version 3.x or higher.
- **PostgreSQL**: For the database.
- **Neo4j**: knowledge graph feature.
- **Gemini API Key**: For the LLM model.
- **LangChain and LangChain-Google-GenAI**: For language model integration.

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/patient-chat-application.git
cd patient-chat-application 
```

### 2. Create a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate 
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in the root directory.

Add the following variables:

```bash
LLM_API_KEY=your_gemini_api_key
LLM_MODEL_NAME=gemini-1.5-flash  # Or your desired model name
```
Replace your_gemini_api_key with your actual Gemini API key obtained from AI Studio.

### 5. Configure Database Settings

In `settings.py`, update the `DATABASES` configuration with your PostgreSQL credentials.

```bash
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'patient_chat_db',
        'USER': 'patient',
        'PASSWORD': 'dtxplus2024',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",} } }
```

### 6. Configure Neo4j Settings

In `neo4j_driver.py`, update the Neo4j connection details.

```bash
self.driver = GraphDatabase.driver(
    "bolt://localhost:7687", auth=("neo4j", "your_neo4j_password")
)
```

### 7. Run Migrations

```bash
python patient_chat/manage.py makemigrations
python patient_chat/manage.py migrate
```

### 8. Populate the Database

Use the Django admin panel or create a script to add the patient data to the database. Ensure there is at least one Patient entry in the database.

## Running the Application

### 1. Start the Django Development Server
   ```bash
   python patient_chat/manage.py runserver
   ```

### 2. Access the Application
Open your web browser and navigate to [http://localhost:8000/](http://localhost:8000/).

## Usage Instructions

### Interacting with the Chat Bot
- **Start a Conversation:** Type your health-related messages into the chat box.
- **Ask Health Questions:** Inquire about your medical condition, medication regimen, diet, etc.
- **Request Appointment Changes:** For example, “Can we reschedule the appointment to next Friday at 3 PM?”

### Viewing Responses
- **AI Bot Replies:** The bot will respond to your queries in a friendly and empathetic manner.
- **Request Confirmation:** If you request an appointment or treatment change, the bot will confirm by saying, “I will convey your request to Dr. [Doctor's Name].”
- **Request Summary:** A summary of your request will be displayed next to the chat box for your review.

### Understanding Conversation Summaries
- **Live Summaries:** The application provides live summaries of the conversation, highlighting key points.
- **Medical Insights:** Important medical insights extracted from the conversation are displayed for your reference.

## Explanation of Features

### Patient Profile
- The application uses a predefined patient profile for simplicity.
- Patient attributes are utilized by the AI bot to provide personalized responses.

### AI Bot Functionality
- **Health-Related Focus:** The bot is programmed to engage only in health-related conversations.
- **Sensitive Topics Filtering:** Automatically filters out any unrelated or sensitive topics to maintain professionalism.
- **Memory Optimization:** Manages long conversations efficiently without losing important information.

### Appointment and Treatment Requests
- **Detection:** The bot detects phrases indicating a request to change appointments or treatments.
- **Response:** Confirms the request and assures the patient that it will be conveyed to the doctor.
- **Request Output:** Generates a concise summary of the request for patient review.

### Entity Extraction
- Utilizes language models to extract key entities from the conversation.
- Extracted entities (e.g., medications, symptoms) are stored in a knowledge graph for future reference.

### Knowledge Graph Integration
- **Neo4j Database:** Stores patient data and extracted entities.
- **Dynamic Queries:** The AI bot can retrieve additional patient information during the conversation.

## Conversation Summaries and Medical Insights
- Provides real-time summaries to help the patient keep track of the discussion.
- Highlights important medical information for better understanding and decision-making.

## Conclusion
This Patient Chat Application serves as a functional prototype that meets the specified requirements. It allows for seamless interaction between a patient and an AI bot, focusing on health-related conversations while efficiently managing requests and information.

