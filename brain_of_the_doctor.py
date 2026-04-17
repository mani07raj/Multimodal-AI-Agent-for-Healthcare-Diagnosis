# if you dont use pipenv uncomment the following:
from dotenv import load_dotenv
load_dotenv()

"""
Main medical assessment module.
Handles image analysis with Groq vision API and combines everything for diagnosis.
"""

import base64
import os
from datetime import datetime
from typing import Any, Dict, Optional

try:
    # Optional – the app can run without Groq installed.
    from groq import Groq  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Groq = None

from app.services.fusion_service import fuse
from app.services.confidence_service import compute_action
from app.services.history_service import get_history_summary, save_visit


# Reload environment to ensure API key is loaded
load_dotenv(override=True)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")


class GroqLLMClient:
    """Wrapper for Groq API to generate medical diagnoses."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "meta-llama/llama-4-scout-17b-16e-instruct"):
        """Initialize Groq client with API key and model name."""
        if Groq is None:
            raise ValueError("Groq library is not installed")
        
        self.api_key = api_key or GROQ_API_KEY
        if not self.api_key or not self.api_key.strip():
            raise ValueError("GROQ_API_KEY must be set. Please check your .env file and ensure the key is valid.")
        
        self.client = Groq(api_key=self.api_key)
        self.model = model
    
    def generate(self, prompt: str) -> str:
        """Send prompt to Groq API and return JSON response."""
        try:
            # Try with JSON mode first (if supported by model)
            try:
                chat_completion = self.client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a medical expert. Always respond with valid JSON only, no markdown, no code blocks, just pure JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    model=self.model,
                    temperature=0.3,  # Lower temperature for more consistent, accurate responses
                    response_format={"type": "json_object"}  # Force JSON output
                )
            except Exception:
                # Fallback if JSON mode not supported
                chat_completion = self.client.chat.completions.create(
    messages=[
                        {
                            "role": "system",
                            "content": "You are a medical expert. CRITICAL: Respond ONLY with valid JSON. No markdown, no code blocks, no explanations before or after. Just pure JSON starting with { and ending with }."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    model=self.model,
                    temperature=0.3,
                )
            
            response = chat_completion.choices[0].message.content
            
            # Clean up response - remove markdown code blocks if present
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]  # Remove ```json
            if response.startswith("```"):
                response = response[3:]   # Remove ```
            if response.endswith("```"):
                response = response[:-3]  # Remove trailing ```
            response = response.strip()
            
            return response
        except Exception as e:
            raise Exception(f"Groq LLM generation failed: {str(e)}")


def encode_image(image_path: str) -> str:
    """Convert an image file to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


# --- Legacy single‑shot image + text analysis ---------------------------------

QUERY_DEFAULT = "Is there something wrong with my face?"
MODEL_DEFAULT = "meta-llama/llama-4-scout-17b-16e-instruct"  # Llama 4 Scout on Groq


def analyze_image_with_query(query: str, model: str, encoded_image: str) -> str:
    """
    Backwards‑compatible Groq multimodal call.

    If Groq is not available this falls back to a short deterministic message so
    that imports and simple runs do not fail when offline.
    """
    if Groq is None:
        return "Image analysis model is not configured; using offline fallback description only."

    api_key = GROQ_API_KEY
    if not api_key or api_key == "your_groq_api_key_here" or api_key == "":
        raise ValueError("GROQ_API_KEY must be set in environment or .env file")
    
    client = Groq(api_key=api_key)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": query},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"},
                },
            ],
        }
    ]
    chat_completion = client.chat.completions.create(messages=messages, model=model)
    return chat_completion.choices[0].message.content


# --- New fused multimodal assessment -----------------------------------------

def get_multimodal_assessment(
    image_summary: str,
    image_conf: float,
    transcript: str,
    transcript_conf: float,
    patient_id: Optional[str] = None,
    llm_client: Optional[Any] = None,
    patient_name: Optional[str] = None,
    age: Optional[str] = None,
    sex: Optional[str] = None,
    phone_no: Optional[str] = None,
    address: Optional[str] = None,
    date_of_birth: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Main function that combines everything: gets history, creates diagnosis, 
    calculates confidence, and saves the visit.
    """
    history_summary = get_history_summary(patient_id)

    fusion_result = fuse(
        image_summary=image_summary,
        image_conf=image_conf,
        transcript=transcript,
        transcript_conf=transcript_conf,
        history_summary=history_summary,
        llm_client=llm_client,
    )

    action_result = compute_action(
        fusion_conf=fusion_result.get("fusion_confidence", 0.5),
        image_conf=image_conf,
        transcript_conf=transcript_conf,
        fused_findings=fusion_result.get("simple_findings"),
        conflict_flag=False,
        severity=fusion_result.get("severity"),
    )

    # Persist visit including any raw LLM output for auditing.
    save_visit(
        patient_id=patient_id,
        transcript=transcript,
        image_summary=image_summary,
        fusion_result=fusion_result,
        timestamp=datetime.utcnow().isoformat(timespec="seconds"),
        patient_name=patient_name,
        age=age,
        sex=sex,
        phone_no=phone_no,
        address=address,
        date_of_birth=date_of_birth,
    )

    return {
        "fusion_result": fusion_result,
        "action_result": action_result,
        "history_summary": history_summary,
    }

