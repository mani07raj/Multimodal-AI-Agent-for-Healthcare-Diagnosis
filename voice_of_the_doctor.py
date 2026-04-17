"""
Text-to-speech functionality for the medical AI agent.
Supports ElevenLabs (premium), gTTS (free online), and pyttsx3 (offline fallback).
"""

import os
from dotenv import load_dotenv
from gtts import gTTS

# Load environment variables
load_dotenv(override=True)

try:
    from elevenlabs.client import ElevenLabs
except ImportError:
    ElevenLabs = None

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    pyttsx3 = None

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")


def text_to_speech_with_pyttsx3(input_text, output_filepath):
    """
    Generate speech using pyttsx3 (offline TTS).
    Works without internet connection. Saves as .wav since pyttsx3 doesn't support mp3.
    """
    try:
        # pyttsx3 only supports wav - use a .wav path
        wav_filepath = output_filepath.replace(".mp3", ".wav")
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)  # Speed of speech
        engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
        
        # Save to file
        engine.save_to_file(input_text, wav_filepath)
        engine.runAndWait()
        engine.stop()
        
        # Verify file was created
        if os.path.exists(wav_filepath) and os.path.getsize(wav_filepath) > 0:
            return wav_filepath
        return None
    except Exception as e:
        print(f"pyttsx3 failed: {e}")
        return None


def text_to_speech_with_gtts(input_text, output_filepath):
    """
    Generate speech using gTTS (Google Text-to-Speech).
    Free, no API key required.
    """
    language = "en"
    audioobj = gTTS(
        text=input_text,
        lang=language,
        slow=False
    )
    audioobj.save(output_filepath)
    return output_filepath


def text_to_speech_with_elevenlabs(input_text, output_filepath):
    """
    Generate speech using ElevenLabs, fallback to gTTS if API key is missing.
    Returns the output filepath for Gradio to use.
    """
    if not input_text or not input_text.strip():
        print("Warning: Empty text provided for TTS")
        return None
    
    # Try ElevenLabs first if API key is available
    if ELEVENLABS_API_KEY and ELEVENLABS_API_KEY != "your_elevenlabs_api_key_here" and ELEVENLABS_API_KEY.strip():
        if ElevenLabs is None:
            print("ElevenLabs library not installed. Falling back to gTTS...")
        else:
            try:
                client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
                
                # Use the new text_to_speech.convert() method
                audio = client.text_to_speech.convert(
                    voice_id="UzYWd2rD2PPFPjXRG3Ul",  # Aria voice ID
                    output_format="mp3_22050_32",
                    text=input_text,
                    model_id="eleven_turbo_v2"
                )
                
                # Save the audio using chunks
                with open(output_filepath, "wb") as f:
                    for chunk in audio:
                        f.write(chunk)
                
                print(f"Successfully generated audio with ElevenLabs: {output_filepath}")
                return output_filepath
            except Exception as e:
                print(f"ElevenLabs TTS failed: {e}. Falling back to gTTS...")
    
    # Fallback to gTTS (free, no API key needed) - with timeout to avoid hanging
    try:
        print("Using gTTS for text-to-speech...")
        language = "en"
        import threading

        result_holder = [None]
        error_holder = [None]

        def _run_gtts():
            try:
                audioobj = gTTS(text=input_text, lang=language, slow=False)
                audioobj.save(output_filepath)
                result_holder[0] = output_filepath
            except Exception as ex:
                error_holder[0] = ex

        t = threading.Thread(target=_run_gtts, daemon=True)
        t.start()
        t.join(timeout=20)  # Give gTTS max 20 seconds

        if t.is_alive():
            print("gTTS timed out after 20s. Falling back to offline TTS...")
        elif error_holder[0]:
            print(f"gTTS failed: {error_holder[0]}")
        elif result_holder[0] and os.path.exists(result_holder[0]) and os.path.getsize(result_holder[0]) > 0:
            print(f"Successfully generated audio with gTTS: {result_holder[0]}")
            return result_holder[0]
        else:
            print("gTTS failed: Audio file not created or empty")
    except Exception as e:
        print(f"gTTS failed: {e}")
        
    # Final fallback to pyttsx3 (offline)
    if PYTTSX3_AVAILABLE:
        try:
            print("Using pyttsx3 for offline text-to-speech...")
            result = text_to_speech_with_pyttsx3(input_text, output_filepath)
            if result:
                print(f"Successfully generated audio with pyttsx3: {output_filepath}")
                return result
        except Exception as e:
            print(f"pyttsx3 also failed: {e}")
    
    print("All TTS methods failed. No audio will be generated.")
    return None
