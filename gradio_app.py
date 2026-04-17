
# if you dont use pipenv uncomment the following:
from dotenv import load_dotenv
load_dotenv(override=True)

import os

import gradio as gr

from app import api_local
from app.services.history_service import get_patient_history
from brain_of_the_doctor import GroqLLMClient
from voice_of_the_doctor import text_to_speech_with_elevenlabs
from voice_of_the_patient import PYAUDIO_AVAILABLE


def _get_llm_client():
    """Create LLM client if API key is available, otherwise return None."""
    try:
        # Reload environment to ensure latest API key
        load_dotenv(override=True)
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key and api_key != "your_groq_api_key_here" and api_key.strip():
            print(f"Creating LLM client with API key (length: {len(api_key)})")
            return GroqLLMClient(api_key=api_key)
        else:
            print("Warning: GROQ_API_KEY not found or invalid. Using fallback mode.")
    except Exception as e:
        print(f"Could not create LLM client: {e}. Using fallback mode.")
        import traceback
        traceback.print_exc()
    return None


def _clean_text_for_speech(text):
    """Remove punctuation and formatting that would sound unprofessional when spoken."""
    if not text:
        return ""
    
    import re
    
    # Preserve "Step 1", "Step 2" etc. by temporarily replacing them
    step_pattern = r'(Step\s+\d+)'
    steps = re.findall(step_pattern, text, re.IGNORECASE)
    step_placeholders = {}
    for i, step in enumerate(steps):
        placeholder = f"__STEP_{i}__"
        step_placeholders[placeholder] = step
        text = text.replace(step, placeholder)
    
    # Replace common punctuation that TTS might speak
    text = text.replace(" - ", ", ")  # Replace dashes with commas
    text = text.replace("—", ", ")  # Replace em dashes
    text = text.replace("–", ", ")  # Replace en dashes
    text = text.replace("\n", ". ")  # Replace newlines with periods
    text = text.replace(":", ". ")  # Replace colons with periods
    text = text.replace(";", ". ")  # Replace semicolons with periods
    
    # Remove bullet points and list markers (but preserve step numbers)
    text = text.replace("•", "")
    # Remove standalone dashes (but keep "Step 1 -" patterns)
    text = re.sub(r'\s+-\s+', ' ', text)  # Simple dash removal
    text = text.replace("* ", "")
    
    # Clean up multiple spaces and periods
    text = re.sub(r'\.{2,}', '.', text)  # Multiple periods to single
    text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single
    text = re.sub(r'\.\s*\.', '.', text)  # Period followed by period
    
    # Remove parentheses content that might be spoken (but preserve medical terms in parentheses)
    # Only remove if it's not a medical term (like dosage or medical abbreviation)
    text = re.sub(r'\([^)]*\)', '', text)
    
    # Clean up common patterns that sound bad
    text = text.replace("LIKELY CONDITION:", "Based on what I see, the likely condition is")
    text = text.replace("CARE INSTRUCTIONS:", "Here's what you should do")
    text = text.replace("WARNING SIGNS — SEEK CARE IF:", "Please seek immediate care if you notice")
    text = text.replace("SPECIAL PRECAUTIONS:", "Also keep in mind")
    
    # Restore step numbers
    for placeholder, step in step_placeholders.items():
        text = text.replace(placeholder, step)
    
    return text.strip()


def _format_doctor_text(fusion_result, action_result):
    """Compose a concise, patient‑facing text answer."""
    if not fusion_result:
        return "I could not generate an assessment from the information provided."

    diag = fusion_result.get("preliminary_diagnosis", "")
    plan = fusion_result.get("recommended_treatment", "")
    safety = fusion_result.get("safety_notes", "")
    triage = action_result.get("triage_action", "monitor_closely_and_seek_care_if_worse")

    # Format text naturally
    text = f"{diag}. {plan} "
    if safety:
        text += f"Also important: {safety} "
    text += f"My overall recommendation is to {triage.replace('_', ' ')}."

    return text


def submit_callback(audio_filepath, image_filepath, patient_id, patient_name, age, sex, 
                    date_of_birth, phone_no, address, session_state):
    # Try to use LLM if available, otherwise use fallback
    llm_client = _get_llm_client()
    
    result = api_local.submit_record(
        audio_filepath=audio_filepath,
        image_filepath=image_filepath,
        patient_id=patient_id or None,
        llm_client=llm_client,  # Use LLM if available
        patient_name=patient_name or None,
        age=age or None,
        sex=sex or None,
        phone_no=phone_no or None,
        address=address or None,
        date_of_birth=date_of_birth or None,
    )

    transcript = result["transcript"]
    fusion_result = result["fusion_result"]
    action_result = result["action_result"]

    doctor_text = _format_doctor_text(fusion_result, action_result)
    treatment = fusion_result.get("recommended_treatment", "")
    medicine = ", ".join(fusion_result.get("medicine_constituents", []))
    safety_notes = fusion_result.get("safety_notes", "")

    # Update session state for chatbot conversation
    new_state = result["session_state"]
    
    # Store initial assessment in session state for chatbot context
    new_state["initial_assessment"] = {
        "diagnosis": fusion_result.get("preliminary_diagnosis", ""),
        "treatment": fusion_result.get("recommended_treatment", ""),
        "medicine": fusion_result.get("medicine_constituents", []),
        "safety": fusion_result.get("safety_notes", ""),
        "reasoning": fusion_result.get("reasoning", ""),
        "image_summary": new_state.get("image_summary", ""),
        "transcript": transcript,
    }
    
    # Initialize chat history with initial doctor greeting
    initial_greeting = (
        f"Hello! I've completed my initial assessment of your case.\n\n"
        f"**Diagnosis:** {fusion_result.get('preliminary_diagnosis', 'Assessment completed')}\n\n"
        f"I've prepared a treatment plan for you. You can see the details in the assessment results on the left.\n\n"
        f"Feel free to ask me any questions about:\n"
        f"• Your diagnosis and what it means\n"
        f"• How to follow the treatment plan\n"
        f"• Your medications and how to use them\n"
        f"• What symptoms to watch for\n"
        f"• When to seek additional care\n\n"
        f"How can I help you today?"
    )
    new_state["chat_history"] = [
        {"role": "assistant", "content": initial_greeting}
    ]

    # Prepare voice output - clean text first to avoid speaking punctuation
    audio_output_path = None
    try:
        if doctor_text and doctor_text.strip():
            cleaned_text = _clean_text_for_speech(doctor_text)
            if cleaned_text and cleaned_text.strip():
                import os
                # Use absolute path to ensure file is accessible
                # Create file in current working directory
                audio_file = os.path.join(os.getcwd(), "final.mp3")
                print(f"Generating voice output for text length: {len(cleaned_text)}")
                print(f"Text preview: {cleaned_text[:100]}...")
                print(f"Audio file path: {audio_file}")
                
                audio_output_path = text_to_speech_with_elevenlabs(
                    input_text=cleaned_text, output_filepath=audio_file
                )
                
                if audio_output_path:
                    # Check if file exists and has content
                    if os.path.exists(audio_output_path):
                        file_size = os.path.getsize(audio_output_path)
                        print(f"Voice output generated successfully: {audio_output_path} (size: {file_size} bytes)")
                        if file_size == 0:
                            print("Warning: Audio file is empty (0 bytes)")
                            audio_output_path = None
                    else:
                        print(f"Warning: Audio file not found at: {audio_output_path}")
                        audio_output_path = None
                else:
                    print("Warning: text_to_speech_with_elevenlabs returned None")
            else:
                print("Warning: Cleaned text is empty")
        else:
            print("Warning: Doctor text is empty, skipping voice generation")
    except Exception as e:
        print(f"Error generating voice output: {e}")
        import traceback
        traceback.print_exc()
        audio_output_path = None
    
    # Ensure we return a valid file path or None
    if audio_output_path:
        if not os.path.exists(audio_output_path):
            print(f"Warning: Audio file does not exist: {audio_output_path}")
            audio_output_path = None
        else:
            file_size = os.path.getsize(audio_output_path)
            if file_size == 0:
                print(f"Warning: Audio file is empty (0 bytes): {audio_output_path}")
                audio_output_path = None
            else:
                print(f"Audio file ready: {audio_output_path} ({file_size} bytes)")

    return (
        transcript,
        doctor_text,
        treatment,
        medicine,
        safety_notes,
        action_result.get("final_confidence", 0.0),
        action_result.get("triage_action", ""),
        new_state["chat_history"],  # Return chat history for chatbot
        audio_output_path,
        new_state,
    )


def chat_callback(message, chat_history, session_state):
    """Handle real-time chat with the doctor."""
    if not message or not message.strip():
        return chat_history, session_state
    chat_history = chat_history or []
    
    if not session_state or not session_state.get("initial_assessment"):
        # No initial assessment yet, ask user to submit first
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": "Please first submit your medical image and/or audio description for analysis."})
        return chat_history, session_state
    
    # Get LLM client for chatbot responses
    llm_client = _get_llm_client()
    
    # Build context from initial assessment and conversation history
    initial = session_state["initial_assessment"]
    
    # Build conversation history string
    conversation_context = ""
    if len(chat_history) > 1:  # More than just the initial greeting
        conversation_context = "\n\nPREVIOUS CONVERSATION:\n"
        for msg in chat_history[:-2]:  # Exclude current message pair
            if msg.get("role") == "user":
                conversation_context += f"Patient: {msg.get('content', '')}\n"
            elif msg.get("role") == "assistant":
                conversation_context += f"Doctor: {msg.get('content', '')}\n\n"
    
    context = f"""You are a highly experienced, board-certified medical doctor with expertise across ALL medical specialties - 
    you are a master physician, surgeon, dentist, gynecologist, cardiologist, neurologist, dermatologist, ophthalmologist, 
    orthopedic surgeon, pediatrician, psychiatrist, and expert in ALL medical fields including Ayurveda and traditional medicine. 
    You ARE the doctor providing direct medical care to this patient.
    
    CRITICAL: You do NOT refer patients to other doctors or specialists unless it is a true life-threatening emergency 
    requiring immediate in-person intervention (like cardiac arrest, severe trauma, loss of consciousness). For all other 
    conditions, you provide direct diagnosis and treatment yourself - you are capable of treating conditions across ALL specialties.

INITIAL ASSESSMENT CONTEXT:
- Diagnosis: {initial.get('diagnosis', 'Not specified')}
- Treatment Plan: {initial.get('treatment', 'Not specified')}
- Medicine Constituents: {', '.join(initial.get('medicine', []))}
- Safety Notes: {initial.get('safety', 'Not specified')}
- Clinical Reasoning: {initial.get('reasoning', 'Not specified')}
- Image Findings: {initial.get('image_summary', 'No image provided')}
- Patient's Initial Description: {initial.get('transcript', 'No description provided')}
{conversation_context}
PATIENT'S CURRENT QUESTION:
{message}

INSTRUCTIONS:
1. Answer the patient's question based on the initial assessment context and conversation history above
2. Provide clear, professional medical guidance that is specific to their condition
3. Be empathetic, warm, and reassuring - speak as a caring doctor would in a real consultation
4. Reference the initial diagnosis and treatment plan when relevant
5. If asked about medications, explain how to use them properly, dosages, and what to expect
6. If asked about symptoms, relate them to the initial assessment and explain what they mean
7. If the question indicates a true life-threatening emergency (cardiac arrest, severe trauma, loss of consciousness), 
   recommend immediate emergency care. For all other conditions, provide direct treatment yourself - do NOT refer to other doctors
8. Keep responses concise but comprehensive (typically 2-5 sentences)
9. Use natural, conversational language - write as if you are SPEAKING directly to the patient
10. DO NOT use bullet points, dashes, colons, or formatting that sounds mechanical - write in flowing sentences
11. If you don't have enough information, ask clarifying questions to provide better treatment - you are the doctor
12. Maintain continuity with previous conversation if relevant
13. Apply your comprehensive knowledge from all medical specialties (surgery, medicine, dentistry, gynecology, ophthalmology, Ayurveda, etc.)
14. REMEMBER: You ARE the doctor - provide treatment directly, don't tell them to see another doctor

Respond naturally as a real doctor would speak in a consultation - warm, professional, clear, and conversational. 
Write in complete sentences that flow naturally, as if you are speaking directly to the patient:"""

    # Generate doctor's response
    doctor_response = ""
    if llm_client:
        try:
            doctor_response = llm_client.generate(context)
            # Clean up response if it's wrapped in JSON
            if doctor_response.startswith('{'):
                import json
                try:
                    parsed = json.loads(doctor_response)
                    doctor_response = parsed.get("response", parsed.get("answer", doctor_response))
                except:
                    pass
        except Exception as e:
            print(f"Error generating chat response: {e}")
            doctor_response = "I apologize, but I'm having trouble processing your question right now. Please try rephrasing it or consult with a healthcare provider in person if this is urgent."
    else:
        # Fallback response without LLM
        doctor_response = f"Based on your initial assessment showing {initial.get('diagnosis', 'your condition')}, I'd recommend following the treatment plan provided. For specific questions about your condition, please consult with a healthcare provider in person for the most accurate guidance."
    
    # Update chat history
    chat_history.append({"role": "user", "content": message})
    chat_history.append({"role": "assistant", "content": doctor_response})
    session_state["chat_history"] = chat_history
    
    return chat_history, session_state


def load_history_callback(patient_id):
    """Load and format patient history for display."""
    if not patient_id or not patient_id.strip():
        return "Please enter a Patient ID to view history."
    
    try:
        visits = get_patient_history(patient_id.strip(), limit=50)
        
        if not visits:
            return f"No history found for Patient ID: {patient_id.strip()}"
        
        # Format history as markdown
        history_text = f"# 📋 Patient History: {patient_id.strip()}\n\n"
        history_text += f"**Total Visits:** {len(visits)}\n\n"
        history_text += "---\n\n"
        
        for i, visit in enumerate(visits, 1):
            fusion = visit.get("fusion_result", {})
            timestamp = visit.get("timestamp", "Unknown date")
            transcript = visit.get("transcript", "No description provided")
            image_summary = visit.get("image_summary", "No image analysis")
            
            # Truncate long image summaries
            if len(image_summary) > 300:
                image_summary = image_summary[:300] + "..."
            
            # Get patient details
            patient_name = visit.get("patient_name", "")
            age = visit.get("age", "")
            sex = visit.get("sex", "")
            phone_no = visit.get("phone_no", "")
            address = visit.get("address", "")
            date_of_birth = visit.get("date_of_birth", "")
            diagnosis = visit.get("diagnosis", "") or fusion.get("preliminary_diagnosis", "No diagnosis available")
            
            treatment = fusion.get("recommended_treatment", "No treatment plan available")
            medications = fusion.get("medicine_constituents", [])
            safety_notes = fusion.get("safety_notes", "No safety notes")
            reasoning = fusion.get("reasoning", "No clinical reasoning available")
            confidence = fusion.get("confidence", 0.0)
            
            history_text += f"## 🏥 Visit #{i} - {timestamp}\n\n"
            
            # Add patient details if available
            if patient_name or age or sex:
                history_text += f"### 👤 Patient Information\n"
                if patient_name:
                    history_text += f"**Name:** {patient_name}\n"
                if age:
                    history_text += f"**Age:** {age}\n"
                if sex:
                    history_text += f"**Sex:** {sex}\n"
                if date_of_birth:
                    history_text += f"**Date of Birth:** {date_of_birth}\n"
                if phone_no:
                    history_text += f"**Phone:** {phone_no}\n"
                if address:
                    history_text += f"**Address:** {address}\n"
                history_text += "\n"
            
            history_text += f"### 📝 Diagnosis\n{diagnosis}\n\n"
            history_text += f"### 🗣️ Patient Description\n{transcript}\n\n"
            history_text += f"### 📷 Image Analysis\n{image_summary}\n\n"
            history_text += f"### 💊 Treatment Plan\n{treatment}\n\n"
            
            if medications:
                history_text += f"### 🧪 Medications\n"
                for med in medications:
                    history_text += f"- {med}\n"
                history_text += "\n"
            
            if safety_notes:
                history_text += f"### ⚠️ Safety Notes\n{safety_notes}\n\n"
            
            if reasoning:
                history_text += f"### 🧠 Clinical Reasoning\n{reasoning}\n\n"
            
            history_text += f"**Confidence Score:** {confidence:.2f}\n\n"
            history_text += "---\n\n"
        
        return history_text
    except Exception as e:
        return f"Error loading history: {str(e)}"


def view_history_for_patient(pid):
    """Switch to history tab and load history for the given patient ID."""
    if pid and pid.strip():
        history_text = load_history_callback(pid.strip())
        # Return tab index 1 (second tab, which is history)
        return gr.update(selected=1), pid.strip(), history_text
    return gr.update(selected=1), "", "Please enter a Patient ID first."


with gr.Blocks(title="AI Doctor with Vision and Voice") as iface:
    state = gr.State({})

    gr.Markdown("## 🏥 AI Doctor with Vision, Voice, and Real-Time Chat")

    with gr.Tabs() as main_tabs:
        with gr.Tab("🔍 Analysis", id="analysis"):
            with gr.Row():
                with gr.Column(scale=1):
                    audio_input = gr.Audio(
                        sources=["microphone", "upload"],
                        type="filepath",
                        label="🎤 Record Your Voice"
                    )
                    image_input = gr.Image(
                        type="filepath", label="📷 Upload Medical Image (optional)"
                    )
                    gr.Markdown("### 👤 Patient Information")
                    patient_id = gr.Textbox(
                        label="Patient ID",
                        placeholder="e.g. patient123",
                    )
                    patient_name = gr.Textbox(
                        label="Patient Name",
                        placeholder="Enter patient's full name",
                    )
                    with gr.Row():
                        age = gr.Textbox(
                            label="Age",
                            placeholder="e.g. 35",
                            scale=1,
                        )
                        sex = gr.Dropdown(
                            label="Sex",
                            choices=["Male", "Female", "Other"],
                            scale=1,
                        )
                    date_of_birth = gr.Textbox(
                        label="Date of Birth",
                        placeholder="YYYY-MM-DD",
                    )
                    phone_no = gr.Textbox(
                        label="Phone Number",
                        placeholder="e.g. +1234567890",
                    )
                    address = gr.Textbox(
                        label="Address",
                        placeholder="Enter patient's address",
                        lines=2,
                    )
                    submit_btn = gr.Button("🔍 Analyze", variant="primary")
                    view_history_btn = gr.Button("📋 View History", variant="secondary", scale=1)
                    
                    gr.Markdown("### 📋 Initial Assessment Results")
                    transcript_out = gr.Textbox(label="🗣️ Speech to Text", lines=2)
                    doctor_out = gr.Textbox(label="👨‍⚕️ Doctor's Overall Response", lines=3)
                    treatment_out = gr.Textbox(label="💊 Treatment Plan", lines=4)
                    medicine_out = gr.Textbox(label="🧪 Medicine Constituents", lines=3)
                    safety_out = gr.Textbox(label="⚠️ Safety Notes", lines=3)
                    confidence_out = gr.Slider(
                        0,
                        1,
                        value=0,
                        step=0.01,
                        label="Model Confidence (combined)",
                        interactive=False,
                    )
                    triage_out = gr.Textbox(label="Triage Suggestion", interactive=False)
                    voice_out = gr.Audio(label="🔊 Doctor's Voice Response")
                
                with gr.Column(scale=1):
                    gr.Markdown("### 💬 Chat with Your Doctor")
                    chatbot = gr.Chatbot(
                        label="Real-Time Doctor Consultation",
                        height=500,
                        show_label=True,
                        type="messages",
                    )
                    chat_input = gr.Textbox(
                        label="Type your question here",
                        placeholder="Ask me anything about your condition, treatment, medications, or symptoms...",
                        lines=2,
                    )
                    chat_btn = gr.Button("💬 Send Message", variant="primary")
        
        with gr.Tab("📋 Patient History", id="history"):
            gr.Markdown("### 📊 View Patient Diagnosis History")
            history_patient_id = gr.Textbox(
                label="Patient ID",
                placeholder="Enter Patient ID to view history (e.g. patient123)",
            )
            load_history_btn = gr.Button("🔍 Load History", variant="primary")
            history_display = gr.Markdown(
                value="Enter a Patient ID and click 'Load History' to view past visits.",
                label="Patient History"
            )
            
            # Load history on button click
            load_history_btn.click(
                fn=load_history_callback,
                inputs=[history_patient_id],
                outputs=[history_display],
            )
            
            # Load history on Enter key
            history_patient_id.submit(
                fn=load_history_callback,
                inputs=[history_patient_id],
                outputs=[history_display],
            )

    # Submit button - initial assessment
    submit_btn.click(
        fn=submit_callback,
        inputs=[audio_input, image_input, patient_id, patient_name, age, sex, 
                date_of_birth, phone_no, address, state],
    outputs=[
            transcript_out,
            doctor_out,
            treatment_out,
            medicine_out,
            safety_out,
            confidence_out,
            triage_out,
            chatbot,  # Update chatbot with initial greeting
            voice_out,
            state,
        ],
    )
    
    # Chat button - real-time conversation
    chat_btn.click(
        fn=chat_callback,
        inputs=[chat_input, chatbot, state],
        outputs=[chatbot, state],
    ).then(
        lambda: "",  # Clear input after sending
        outputs=[chat_input],
    )
    
    # Allow Enter key to send message
    chat_input.submit(
        fn=chat_callback,
        inputs=[chat_input, chatbot, state],
        outputs=[chatbot, state],
    ).then(
        lambda: "",  # Clear input after sending
        outputs=[chat_input],
    )
    
    # View History button - switch to history tab
    view_history_btn.click(
        fn=view_history_for_patient,
        inputs=[patient_id],
        outputs=[main_tabs, history_patient_id, history_display],
    )

def launch_app(server_name="127.0.0.1", server_port=7860, debug=True):
    iface.launch(
        debug=debug,
        show_error=True,
        server_name=server_name,
        server_port=server_port,
        max_threads=10,
    )


if __name__ == "__main__":
    launch_app()

#http://127.0.0.1:7860

# now this is similar to above code only. just that clear button is removed and now doctor voice can also be played in UI itself along with attachment file is generated. 
'''
import os
import gradio as gr

from brain_of_the_doctor import encode_image, analyze_image_with_query
from voice_of_the_patient import transcribe_with_groq
from voice_of_the_doctor import text_to_speech_with_gtts, text_to_speech_with_elevenlabs

system_prompt = """You have to act as a professional doctor, i know you are not but this is for learning purpose. 
            What's in this image?. Do you find anything wrong with it medically? 
            If you make a differential, suggest some remedies for them. Donot add any numbers or special characters in 
            your response. Your response should be in one long paragraph. Also always answer as if you are answering to a real person.
            Donot say 'In the image I see' but say 'With what I see, I think you have ....'
            Dont respond as an AI model in markdown, your answer should mimic that of an actual doctor not an AI bot, 
            Keep your answer concise (max 2 sentences). No preamble, start your answer right away please"""

def process_inputs(audio_filepath, image_filepath):
    # Debug: Check if audio is captured
    print(f"Audio file received: {audio_filepath}")
    print(f"Image file received: {image_filepath}")
    
    # Handle audio input
    if audio_filepath is None:
        speech_to_text_output = "No audio recorded"
    else:
        try:
            speech_to_text_output = transcribe_with_groq(
                GROQ_API_KEY=os.environ.get("GROQ_API_KEY"), 
                audio_filepath=audio_filepath,
                stt_model="whisper-large-v3"
            )
        except Exception as e:
            speech_to_text_output = f"Error in transcription: {str(e)}"

    # Handle the image input
    if image_filepath:
        try:
            doctor_response = analyze_image_with_query(
                query=system_prompt + speech_to_text_output, 
                encoded_image=encode_image(image_filepath), 
                model="meta-llama/llama-4-scout-17b-16e-instruct"
            )
        except Exception as e:
            doctor_response = f"Error in image analysis: {str(e)}"
    else:
        doctor_response = "No image provided for me to analyze"

    # Generate voice response
    try:
        audio_output_path = "final_response.mp3"
        text_to_speech_with_elevenlabs(
            input_text=doctor_response, 
            output_filepath=audio_output_path
        )
        voice_of_doctor = audio_output_path
    except Exception as e:
        voice_of_doctor = None
        print(f"Error in TTS: {str(e)}")

    return speech_to_text_output, doctor_response, voice_of_doctor

# Create the interface
iface = gr.Interface(
    fn=process_inputs,
    inputs=[
        gr.Audio(
            sources=["microphone", "upload"],
            type="filepath",
            format="wav",
            label="🎤 Record Your Voice"
        ),
        gr.Image(
            type="filepath",
            label="📷 Upload Medical Image"
        )
    ],
    outputs=[
        gr.Textbox(label="🗣️ Speech to Text"),
        gr.Textbox(label="👨‍⚕️ Doctor's Response"),
        gr.Audio(label="🔊 Doctor's Voice Response")
    ],
    title="🏥 AI Doctor with Vision and Voice",
    description="Record your voice and upload an image for medical analysis"
)

iface.launch(debug=True)
'''




#Generated by claude. where in 
'''Separated recording from processing - Audio recording is now independent
Added explicit submit button - Processing only happens when you click "Analyze"
Added max_threads=10 - Allows concurrent operations
Removed automatic processing - Audio recording won't trigger processing

The root cause was likely that your original gr.Interface was trying to process the audio immediately when it was recorded, causing the server to be busy and interfering with the recording process.
Alternative quick fix for your original code:
Change your gr.Interface to process only on submit, not on input change:'''


'''
import os
import gradio as gr
from concurrent.futures import ThreadPoolExecutor
import threading

from brain_of_the_doctor import encode_image, analyze_image_with_query
from voice_of_the_patient import transcribe_with_groq
from voice_of_the_doctor import text_to_speech_with_gtts, text_to_speech_with_elevenlabs

system_prompt = """You have to act as a professional doctor, i know you are not but this is for learning purpose. 
            What's in this image?. Do you find anything wrong with it medically? 
            If you make a differential, suggest some remedies for them. Donot add any numbers or special characters in 
            your response. Your response should be in one long paragraph. Also always answer as if you are answering to a real person.
            Donot say 'In the image I see' but say 'With what I see, I think you have ....'
            Dont respond as an AI model in markdown, your answer should mimic that of an actual doctor not an AI bot, 
            Keep your answer concise (max 2 sentences). No preamble, start your answer right away please"""

def process_inputs(audio_filepath, image_filepath):
    # Debug: Check if audio is captured
    print(f"Audio file received: {audio_filepath}")
    print(f"Image file received: {image_filepath}")
    
    # Handle audio input
    if audio_filepath is None:
        speech_to_text_output = "No audio recorded"
    else:
        try:
            speech_to_text_output = transcribe_with_groq(
                GROQ_API_KEY=os.environ.get("GROQ_API_KEY"), 
                audio_filepath=audio_filepath,
                stt_model="whisper-large-v3"
            )
        except Exception as e:
            speech_to_text_output = f"Error in transcription: {str(e)}"

    # Handle the image input
    if image_filepath:
        try:
            doctor_response = analyze_image_with_query(
                query=system_prompt + speech_to_text_output, 
                encoded_image=encode_image(image_filepath), 
                model="meta-llama/llama-4-scout-17b-16e-instruct"
            )
        except Exception as e:
            doctor_response = f"Error in image analysis: {str(e)}"
    else:
        doctor_response = "No image provided for me to analyze"

    # Generate voice response
    try:
        audio_output_path = "final_response.mp3"
        text_to_speech_with_elevenlabs(
            input_text=doctor_response, 
            output_filepath=audio_output_path
        )
        voice_of_doctor = audio_output_path
    except Exception as e:
        voice_of_doctor = None
        print(f"Error in TTS: {str(e)}")

    return speech_to_text_output, doctor_response, voice_of_doctor

# Create interface with separated recording and processing
with gr.Blocks(title="AI Doctor with Vision and Voice") as iface:
    gr.Markdown("# 🏥 AI Doctor with Vision and Voice")
    gr.Markdown("Record your voice and upload an image for medical analysis")
    
    with gr.Row():
        with gr.Column():
            # Audio recording - separated from processing
            audio_input = gr.Audio(
                sources=["microphone", "upload"],
                type="filepath",
                label="🎤 Record Your Voice"
            )
            
            image_input = gr.Image(
                type="filepath",
                label="📷 Upload Medical Image"
            )
            
            # Separate submit button
            submit_btn = gr.Button("🔍 Analyze", variant="primary")
        
        with gr.Column():
            speech_output = gr.Textbox(label="🗣️ Speech to Text")
            doctor_output = gr.Textbox(label="👨‍⚕️ Doctor's Response")
            voice_output = gr.Audio(label="🔊 Doctor's Voice Response")
    
    # Only process when submit is clicked, not when audio changes
    submit_btn.click(
        fn=process_inputs,
        inputs=[audio_input, image_input],
        outputs=[speech_output, doctor_output, voice_output]
    )

# Launch with specific settings to avoid blocking
iface.launch(
    debug=True,
    show_error=True,
    server_name="127.0.0.1",
    server_port=7860,
    max_threads=10  # Allow multiple concurrent requests
)
iface = gr.Interface(
    fn=process_inputs,
    inputs=[
        gr.Audio(
            sources=["microphone", "upload"],
            type="filepath",
            format="wav",
            label="🎤 Record Your Voice"
        ),
        gr.Image(
            type="filepath",
            label="📷 Upload Medical Image"
        )
    ],
    outputs=[
        gr.Textbox(label="🗣️ Speech to Text"),
        gr.Textbox(label="👨‍⚕️ Doctor's Response"),
        gr.Audio(label="🔊 Doctor's Voice Response")
    ],
    live=False,
    title="🏥 AI Doctor with Vision and Voice",
    description="Record your voice and upload an image for medical analysis"
)

iface.launch(debug=True)
'''
