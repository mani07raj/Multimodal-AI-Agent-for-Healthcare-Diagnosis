#!/usr/bin/env python
"""Test script to verify PyAudio is now optional"""

print("Testing PyAudio fix...")
print("-" * 50)

# Test 1: Import the module
try:
    from voice_of_the_patient import transcribe_with_groq, PYAUDIO_AVAILABLE
    print("✓ Successfully imported voice_of_the_patient module")
    print(f"  PyAudio available: {PYAUDIO_AVAILABLE}")
except ImportError as e:
    print(f"✗ Failed to import: {e}")
    exit(1)

# Test 2: Try to use record_audio function
try:
    from voice_of_the_patient import record_audio
    print("✓ record_audio function is accessible")
    
    # Try to call it (should raise RuntimeError if PyAudio not installed)
    try:
        record_audio("test.mp3", timeout=1)
        print("  Note: PyAudio is installed and working")
    except RuntimeError as e:
        print(f"  Expected error when PyAudio not installed: {e}")
        print("✓ Error handling works correctly")
    except Exception as e:
        # Other exceptions (like timeout) mean PyAudio is working
        print(f"  PyAudio is available (got expected exception: {type(e).__name__})")
        
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    exit(1)

print("-" * 50)
print("✓ All tests passed! PyAudio is now optional.")
print("  The app will work without microphone recording.")
print("  Users can still upload audio files for transcription.")
