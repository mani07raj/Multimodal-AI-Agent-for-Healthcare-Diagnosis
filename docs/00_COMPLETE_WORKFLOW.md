# Complete Workflow - AI Medical Assistant

Simple explanation of how the project works.

## Overview

This is an AI medical diagnosis app that:
- Takes audio recordings from patients
- Analyzes medical images
- Uses AI to generate diagnosis and treatment
- Stores patient history
- Allows chat with AI doctor

## How It Works (Simple Flow)

```
1. User uploads image and/or records audio
   ↓
2. Audio → Text (Whisper API)
   Image → Analysis (Vision API)
   ↓
3. Combine both → Send to LLM
   ↓
4. Get diagnosis, treatment, medications
   ↓
5. Display results + Save to database
   ↓
6. User can chat for follow-up questions
```

## Main Components

### 1. gradio_app.py
- The web interface
- Handles user input (audio, image)
- Displays results
- Manages chat functionality

### 2. app/api_local.py
- Main processing function `submit_record()`
- Calls audio transcription
- Calls image analysis
- Combines everything

### 3. brain_of_the_doctor.py
- Image analysis using Groq Vision API
- LLM client for diagnosis
- Main function: `get_multimodal_assessment()`

### 4. voice_of_the_patient.py
- Converts audio to text
- Uses Groq Whisper API

### 5. voice_of_the_doctor.py
- Converts text to speech
- Uses ElevenLabs or gTTS

### 6. app/services/
- **fusion_service.py**: Combines image + audio data
- **confidence_service.py**: Calculates confidence score
- **history_service.py**: Saves and retrieves patient visits

## Step-by-Step Process

### Step 1: User Input
- User records audio describing symptoms
- User uploads medical image (optional)
- User enters Patient ID (optional)

### Step 2: Processing
1. Audio is transcribed to text
2. Image is analyzed (if provided)
3. Previous history is retrieved (if Patient ID given)

### Step 3: Diagnosis
- All data is combined
- Sent to LLM (or uses keyword matching if no LLM)
- Gets diagnosis, treatment plan, medications

### Step 4: Output
- Results displayed in UI
- Audio response generated
- Visit saved to database

### Step 5: Chat
- User can ask follow-up questions
- AI responds based on initial diagnosis

## Database

- Uses SQLite (`patient_history.db`)
- Stores: patient_id, timestamp, transcript, image_summary, diagnosis
- Can retrieve history for same patient

## API Keys Needed

- `GROQ_API_KEY` - For LLM, Vision, and Whisper
- `ELEVENLABS_API_KEY` - For text-to-speech (optional)

## Running the App

```bash
python gradio_app.py
```

Then open browser to `http://127.0.0.1:7860`

## Notes

- Works without LLM (uses simple keyword matching as fallback)
- Patient history helps improve diagnosis for repeat visits
- All processing happens locally (except API calls)
