# AI Medical Assistant Project

A simple medical diagnosis app that uses AI to analyze medical images and patient audio descriptions. Built with Python, Gradio, and Groq API.

## Features
- Upload medical images for analysis
- Record voice descriptions of symptoms
- Get AI-powered diagnosis and treatment recommendations
- View patient history
- Chat with the AI doctor for follow-up questions

## Table of Contents

1. [Installing FFmpeg and PortAudio](#installing-ffmpeg-and-portaudio)
   - [macOS](#macos)
   - [Linux](#linux)
   - [Windows](#windows)
2. [Setting Up a Python Virtual Environment](#setting-up-a-python-virtual-environment)
   - [Using Pipenv](#using-pipenv)
   - [Using pip and venv](#using-pip-and-venv)
   - [Using Conda](#using-conda)
3. [Running the application](#project-phases-and-python-commands)

## Installing FFmpeg and PortAudio

### macOS

1. **Install Homebrew** (if not already installed):

   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Install FFmpeg and PortAudio:**

   ```bash
   brew install ffmpeg portaudio
   ```


### Linux
For Debian-based distributions (e.g., Ubuntu):

1. **Update the package list**

```
sudo apt update
```

2. **Install FFmpeg and PortAudio:**
```
sudo apt install ffmpeg portaudio19-dev
```

### Windows

#### Download FFmpeg:
1. Visit the official FFmpeg download page: [FFmpeg Downloads](https://ffmpeg.org/download.html)
2. Navigate to the Windows builds section and download the latest static build.

#### Extract and Set Up FFmpeg:
1. Extract the downloaded ZIP file to a folder (e.g., `C:\ffmpeg`).
2. Add the `bin` directory to your system's PATH:
   - Search for "Environment Variables" in the Start menu.
   - Click on "Edit the system environment variables."
   - In the System Properties window, click on "Environment Variables."
   - Under "System variables," select the "Path" variable and click "Edit."
   - Click "New" and add the path to the `bin` directory (e.g., `C:\ffmpeg\bin`).
   - Click "OK" to apply the changes.

#### Install PortAudio:
1. Download the PortAudio binaries from the official website: [PortAudio Downloads](http://www.portaudio.com/download.html)
2. Follow the installation instructions provided on the website.

---

## Setting Up a Python Virtual Environment

### Using Pipenv
1. **Install Pipenv (if not already installed):**  
```
pip install pipenv
```

2. **Install Dependencies with Pipenv:** 

```
pipenv install
```

3. **Activate the Virtual Environment:** 

```
pipenv shell
```

---

### Using `pip` and `venv`
#### Create a Virtual Environment:
```
python -m venv venv
```

#### Activate the Virtual Environment:
**macOS/Linux:**
```
source venv/bin/activate
```

**Windows:**
```
venv\Scripts\activate
```

#### Install Dependencies:
```
pip install -r requirements.txt
```

---

### Using Conda
#### Create a Conda Environment:
```
conda create --name myenv python=3.11
```

#### Activate the Conda Environment:
```
conda activate myenv
```

#### Install Dependencies:
```
pip install -r requirements.txt
```


# Project Phases and Python Commands

## Phase 1: Brain of the doctor
```
python brain_of_the_doctor.py
```

## Phase 2: Voice of the patient
```
python voice_of_the_patient.py
```

## Phase 3: Voice of the doctor
```
python voice_of_the_doctor.py
```

## Phase 4: Setup Gradio UI
```
python gradio_app.py
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the project root (same folder as `gradio_app.py`):
   - Copy `.env.example` to `.env` (or create a new file named `.env`)
   - Add your API keys in this format (NO quotes, NO spaces around =):
   ```
   GROQ_API_KEY=gsk_your_actual_key_here
   ELEVENLABS_API_KEY=your_elevenlabs_key_here
   ```

**Note**: 
- Get your Groq API key from: https://console.groq.com/
- ElevenLabs API key is optional (app will use free gTTS if not provided)
- If you see "401 Unauthorized" errors, run `python check_env.py` to verify keys are loaded
- Make sure `.env` file is in the project root, not in a subfolder

4. Run the app:
```bash
python gradio_app.py
```

The app will open in your browser at `http://127.0.0.1:7860`

## How It Works

1. **Audio Input**: Records patient voice and converts to text using Groq Whisper
2. **Image Analysis**: Analyzes medical images using Groq Vision API
3. **Diagnosis**: Combines audio and image data to generate diagnosis using LLM
4. **History**: Stores patient visits in SQLite database
5. **Chat**: Allows follow-up questions with the AI doctor

## Project Structure

- `gradio_app.py` - Main UI application
- `brain_of_the_doctor.py` - Image analysis and LLM client
- `voice_of_the_patient.py` - Audio transcription
- `voice_of_the_doctor.py` - Text-to-speech
- `app/api_local.py` - Main processing functions
- `app/services/` - Fusion, confidence, and history services


