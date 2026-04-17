"""
Confidence calculation and triage decisions.
Calculates how confident we are in the diagnosis and suggests next steps.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional


def _get_threshold(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, default))
    except (TypeError, ValueError):
        value = default
    return max(0.0, min(1.0, value))


def compute_action(
    fusion_conf: float,
    image_conf: Optional[float],
    transcript_conf: Optional[float],
    fused_findings: Optional[Dict[str, Any]],
    conflict_flag: bool = False,
    severity: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate final confidence score and decide what action to recommend.
    Uses LLM-provided severity (low/moderate/high/emergency) as the primary signal
    for triage, with confidence as a numeric indicator.
    """
    low_th = _get_threshold("FUSION_CONFIDENCE_LOW", 0.55)
    high_th = _get_threshold("FUSION_CONFIDENCE_HIGH", 0.8)

    # Normalise sub-confidences
    def _norm(c: Optional[float]) -> float:
        if c is None:
            return fusion_conf
        try:
            v = float(c)
        except (TypeError, ValueError):
            return fusion_conf
        if v > 1.0:
            v = v / 100.0
        return max(0.0, min(1.0, v))

    img_c = _norm(image_conf)
    txt_c = _norm(transcript_conf)

    # Weighted average: fusion_conf (from LLM) carries most weight
    final_conf = round((fusion_conf * 0.6 + img_c * 0.2 + txt_c * 0.2), 2)
    final_conf = max(0.0, min(1.0, final_conf))

    # Use LLM severity as the primary triage driver if available
    if severity == "emergency":
        triage_action = "seek_emergency_care_immediately"
    elif severity == "high":
        triage_action = "recommend_in_person_review"
    elif severity == "moderate":
        triage_action = "monitor_closely_and_seek_care_if_worse"
    elif severity == "low":
        triage_action = "self_care_and_routine_followup"
    else:
        # Fallback: derive triage from numeric confidence
        if final_conf >= high_th and not conflict_flag:
            triage_action = "self_care_and_routine_followup"
        elif final_conf >= low_th:
            triage_action = "monitor_closely_and_seek_care_if_worse"
        else:
            triage_action = "recommend_in_person_review"

    print(f"[TRIAGE] severity={severity!r} → triage={triage_action}, final_confidence={final_conf}")

    return {
        "final_confidence": final_conf,
        "triage_action": triage_action,
    }


