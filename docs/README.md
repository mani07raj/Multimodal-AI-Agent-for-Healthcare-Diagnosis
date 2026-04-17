# Project Documentation

Simple documentation for the AI Medical Assistant project.

**Quick Start**: See [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md) for overview

## Overview

This project is an AI-powered medical diagnosis assistant that:
- Analyzes medical images
- Transcribes patient voice descriptions
- Generates diagnosis and treatment recommendations
- Stores patient history
- Allows chat with AI doctor

## Main Files

1. **gradio_app.py** - The web interface (main file to run)
2. **brain_of_the_doctor.py** - Image analysis and LLM client
3. **voice_of_the_patient.py** - Audio to text conversion
4. **voice_of_the_doctor.py** - Text to speech conversion
5. **app/api_local.py** - Main processing functions
6. **app/services/** - Helper modules:
   - `fusion_service.py` - Combines image and audio data
   - `confidence_service.py` - Calculates confidence scores
   - `history_service.py` - Stores and retrieves patient history

## How It Works

1. User uploads image and/or records audio
2. Audio is converted to text (Whisper API)
3. Image is analyzed (Groq Vision API)
4. Both are combined and sent to LLM for diagnosis
5. Results are displayed and saved to database
6. User can chat with AI doctor for follow-up questions

## Setup

1. Install Python dependencies: `pip install -r requirements.txt`
2. Set up `.env` file with `GROQ_API_KEY=your_key`
3. Run: `python gradio_app.py`
4. Open browser to `http://127.0.0.1:7860`

## Technologies Used

- Python 3.x
- Gradio (web interface)
- Groq API (LLM, Vision, Whisper)
- SQLite (patient history)
- ElevenLabs/gTTS (text-to-speech)

## Notes

- The app works with or without LLM (has fallback keyword matching)
- Patient history is stored in `patient_history.db`
- All APIs require valid keys in `.env` file
