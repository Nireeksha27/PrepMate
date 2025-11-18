"""Firestore helper functions."""

from __future__ import annotations

import logging
from typing import Any

try:
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    firestore = None

_CLIENT = None


def _client():
    global _CLIENT
    if _CLIENT is None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore is not installed.")
        _CLIENT = firestore.Client()
    return _CLIENT


def create_session(doc_id: str, document: dict[str, Any]) -> None:
    """Create a prep session document."""
    try:
        _client().collection("prep_sessions").document(doc_id).set(document)
    except Exception as exc:  # pragma: no cover
        logging.warning("Failed to create Firestore session: %s", exc)


def update_session_answers(
    session_id: str, answers: list[dict[str, Any]], final_html: str, pdf_url: str | None
) -> None:
    """Update session with answers and final output."""
    try:
        doc_ref = _client().collection("prep_sessions").document(session_id)
        doc = doc_ref.get()
        
        if doc.exists:
            # Document exists, update it
            doc_ref.update(
                {
                    "followup_data.answers": answers,
                    "final_output_html": final_html,
                    "pdf_url": pdf_url,
                }
            )
        else:
            # Document doesn't exist, create it with minimal data
            logging.warning(f"Session {session_id} not found, creating new document")
            doc_ref.set(
                {
                    "id": session_id,
                    "followup_data": {"answers": answers},
                    "final_output_html": final_html,
                    "pdf_url": pdf_url,
                    "consentToStore": True,
                },
                merge=True
            )
    except Exception as exc:  # pragma: no cover
        logging.warning("Failed to update Firestore session: %s", exc)


