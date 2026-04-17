# Project Summary

## What This Project Does

An AI medical assistant that helps diagnose medical conditions by:
- Analyzing medical images
- Understanding patient voice descriptions
- Providing diagnosis and treatment recommendations
- Storing patient history
- Answering follow-up questions

## Key Features

1. **Image Analysis** - Upload medical images, AI analyzes them
2. **Voice Input** - Record symptoms, converted to text automatically
3. **AI Diagnosis** - Combines image and audio to generate diagnosis
4. **Treatment Plan** - Gets recommended medications and care instructions
5. **Patient History** - Stores visits, can view past diagnoses
6. **Chat Interface** - Ask follow-up questions to the AI doctor

## Technologies

- **Python** - Main programming language
- **Gradio** - Web interface framework
- **Groq API** - For LLM, vision, and speech-to-text
- **SQLite** - Database for patient history
- **ElevenLabs/gTTS** - Text-to-speech

## File Structure

```
gradio_app.py              # Main UI (run this file)
brain_of_the_doctor.py      # Image analysis + LLM
voice_of_the_patient.py     # Audio to text
voice_of_the_doctor.py      # Text to speech
app/
  api_local.py             # Main processing
  services/
    fusion_service.py      # Combines data
    confidence_service.py   # Calculates confidence
    history_service.py     # Database operations
```

## Quick Start

1. Install: `pip install -r requirements.txt`
2. Setup: Create `.env` with `GROQ_API_KEY=your_key`
3. Run: `python gradio_app.py`
4. Open: `http://127.0.0.1:7860`

## How It Works

1. User provides audio/image input
2. Audio → Text (Whisper)
3. Image → Analysis (Vision API)
4. Both → LLM for diagnosis
5. Results displayed and saved
6. User can chat for questions

## Notes

- Works offline with keyword matching (no LLM needed)
- Patient history improves accuracy for repeat visits
- All data stored locally in SQLite database

