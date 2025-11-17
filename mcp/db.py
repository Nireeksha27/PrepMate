
from google.cloud import firestore
import os

db = None

def get_firestore_client():
    global db
    if db is None:
        # TODO: Initialize Firestore client. Use service account credentials in production.
        # For local development, ensure GOOGLE_APPLICATION_CREDENTIALS environment variable is set.
        db = firestore.Client()
    return db

def create_session(doc_id: str, doc: dict):
    db_client = get_firestore_client()
    # TODO: Redact sensitive PII from logs before writing to Firestore.
    print(f"Creating session {doc_id} with data: {doc}") # Example log, redact PII
    db_client.collection("prep_sessions").document(doc_id).set(doc)

def update_session_answers(doc_id: str, answers: dict, final_html: str, pdf_url: str | None = None):
    db_client = get_firestore_client()
    # TODO: Redact sensitive PII from logs before writing to Firestore.
    print(f"Updating session {doc_id} with answers: {answers}") # Example log, redact PII
    db_client.collection("prep_sessions").document(doc_id).update({
        "followup_data.answers": answers,
        "final_output_html": final_html,
        "pdf_url": pdf_url,
        "updated_at": firestore.SERVER_TIMESTAMP
    })
