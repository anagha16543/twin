"""
ai-service/app/utils/privacy_utils.py

PII sanitization utilities for NBA Accreditation AI service.

These functions sanitize a COPY of faculty data before sending to the LLM.
The original data must NOT be mutated so that deterministic calculations
remain unaffected by sanitization.

SENSITIVE_FACULTY_KEYS contains the set of field names whose values must
never be forwarded to the language model.
"""

from __future__ import annotations

from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Sensitive field names — values are stripped before LLM calls
# ---------------------------------------------------------------------------

SENSITIVE_FACULTY_KEYS: frozenset[str] = frozenset({
    "phone",
    "mobile",
    "phone_number",
    "contact_number",
    "personal_email",
    "email",
    "home_email",
    "address",
    "residential_address",
    "home_address",
    "pan",
    "aadhaar",
    "ssn",
    "national_id",
    "dob",
    "date_of_birth",
    "blood_group",
    "salary_in_hand",
    "bank_account",
})


def sanitize_faculty_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a shallow copy of a single faculty record with all PII fields removed.

    The original dict is NOT mutated.
    """
    return {
        key: value
        for key, value in record.items()
        if key not in SENSITIVE_FACULTY_KEYS
    }


def sanitize_faculty_data(faculty_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Return a new list of sanitized faculty records.

    Each record is a shallow copy with PII fields stripped.
    The original list and its dicts are NOT mutated.
    """
    return [sanitize_faculty_record(record) for record in faculty_records]
