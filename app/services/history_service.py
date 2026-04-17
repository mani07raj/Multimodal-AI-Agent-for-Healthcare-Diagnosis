"""
Patient history storage using SQLite database.
Saves visit records and can retrieve past diagnoses for a patient.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional


DB_PATH = Path(os.getenv("PATIENT_HISTORY_DB", "patient_history.db"))


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT,
            patient_name TEXT,
            age TEXT,
            sex TEXT,
            phone_no TEXT,
            address TEXT,
            date_of_birth TEXT,
            disease TEXT,
            diagnosis TEXT,
            timestamp TEXT,
            transcript TEXT,
            image_summary TEXT,
            fusion_result_json TEXT
        )
        """
    )
    # Add new columns to existing table if they don't exist
    try:
        conn.execute("ALTER TABLE visits ADD COLUMN patient_name TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE visits ADD COLUMN age TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE visits ADD COLUMN sex TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE visits ADD COLUMN phone_no TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE visits ADD COLUMN address TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE visits ADD COLUMN date_of_birth TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE visits ADD COLUMN disease TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE visits ADD COLUMN diagnosis TEXT")
    except sqlite3.OperationalError:
        pass
    return conn


def save_visit(
    patient_id: Optional[str],
    transcript: str,
    image_summary: str,
    fusion_result: Dict[str, Any],
    timestamp: str,
    patient_name: Optional[str] = None,
    age: Optional[str] = None,
    sex: Optional[str] = None,
    phone_no: Optional[str] = None,
    address: Optional[str] = None,
    date_of_birth: Optional[str] = None,
) -> None:
    """Save a patient visit to the database with patient details."""
    conn = _get_conn()
    
    # Extract diagnosis from fusion_result
    diagnosis = fusion_result.get("preliminary_diagnosis", "") if fusion_result else ""
    
    with conn:
        conn.execute(
            """
            INSERT INTO visits (
                patient_id, patient_name, age, sex, phone_no, address, date_of_birth,
                disease, diagnosis, timestamp, transcript, image_summary, fusion_result_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                patient_id or "anonymous",
                patient_name or "",
                age or "",
                sex or "",
                phone_no or "",
                address or "",
                date_of_birth or "",
                diagnosis,  # Store diagnosis separately for easy access
                diagnosis,  # Same as disease for now
                timestamp,
                transcript or "",
                image_summary or "",
                json.dumps(fusion_result or {}),
            ),
        )
    conn.close()


def get_history_summary(patient_id: Optional[str]) -> str:
    """Get a short summary of patient's previous visits (last 3 visits)."""
    conn = _get_conn()
    try:
        cur = conn.execute(
            """
            SELECT fusion_result_json, timestamp
            FROM visits
            WHERE patient_id = ?
            ORDER BY id DESC
            LIMIT 3
            """,
            (patient_id or "anonymous",),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return "No significant prior history is recorded for this patient."

    diagnoses = []
    for fusion_json, ts in rows:
        try:
            data = json.loads(fusion_json or "{}")
        except json.JSONDecodeError:
            data = {}
        diag = data.get("preliminary_diagnosis") or "unspecified issue"
        diagnoses.append(f"{diag} ({ts})")

    summary = "; ".join(diagnoses)
    return f"Previous visits suggest: {summary}"


def get_patient_history(patient_id: Optional[str], limit: int = 50) -> list[Dict[str, Any]]:
    """
    Get all visit records for a patient.
    Returns list with visit details: patient info, diagnosis, treatment, medications, etc.
    """
    conn = _get_conn()
    try:
        cur = conn.execute(
            """
            SELECT id, patient_id, patient_name, age, sex, phone_no, address, date_of_birth,
                   disease, diagnosis, timestamp, transcript, image_summary, fusion_result_json
            FROM visits
            WHERE patient_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (patient_id or "anonymous", limit),
        )
        rows = cur.fetchall()
    finally:
        conn.close()
    
    visits = []
    for row in rows:
        (visit_id, pid, patient_name, age, sex, phone_no, address, date_of_birth,
         disease, diagnosis, timestamp, transcript, image_summary, fusion_json) = row
        try:
            fusion_result = json.loads(fusion_json or "{}")
        except json.JSONDecodeError:
            fusion_result = {}
        
        visits.append({
            "id": visit_id,
            "patient_id": pid,
            "patient_name": patient_name or "",
            "age": age or "",
            "sex": sex or "",
            "phone_no": phone_no or "",
            "address": address or "",
            "date_of_birth": date_of_birth or "",
            "disease": disease or "",
            "diagnosis": diagnosis or "",
            "timestamp": timestamp,
            "transcript": transcript or "",
            "image_summary": image_summary or "",
            "fusion_result": fusion_result,
        })
    
    return visits


