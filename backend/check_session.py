"""Check if a specific session is stored in Firestore."""

import os
import sys
import io
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

try:
    from google.cloud import firestore
except ImportError:
    print("[ERROR] google-cloud-firestore not installed!")
    exit(1)

# Session ID from your test
SESSION_ID = "1aac8291-8868-477f-bc0e-2b1ef7a207d0"

print("Checking Firestore for stored session...")
print("=" * 60)

try:
    db = firestore.Client()
    print("[OK] Firestore client connected\n")
except Exception as e:
    print(f"[ERROR] Failed to connect: {e}")
    print("\nCheck:")
    print("1. GOOGLE_APPLICATION_CREDENTIALS is set in .env")
    print("2. Service account key file exists")
    exit(1)

# Check specific session
print(f"Looking for session: {SESSION_ID}")
print("-" * 60)

try:
    doc_ref = db.collection("prep_sessions").document(SESSION_ID)
    doc = doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        print("[SUCCESS] Session found in Firestore!\n")
        print(f"Session ID: {data.get('id', 'N/A')}")
        print(f"Created: {data.get('created_at', 'N/A')}")
        print(f"Patient Name: {data.get('patient_info', {}).get('name', 'N/A')}")
        print(f"Patient Age: {data.get('patient_info', {}).get('age', 'N/A')}")
        print(f"Summary: {data.get('ai_summary', 'N/A')[:100]}...")
        print(f"Questions: {len(data.get('followup_data', {}).get('questions', []))}")
        print(f"Answers: {len(data.get('followup_data', {}).get('answers', []))}")
        print(f"Has Final HTML: {'final_output_html' in data}")
        print(f"Consent: {data.get('consentToStore', False)}")
        print("\n" + "=" * 60)
        print("[VERIFIED] Data is stored in Firestore!")
        print("=" * 60)
    else:
        print("[NOT FOUND] Session not found in Firestore")
        print("\nPossible reasons:")
        print("1. Firestore API not enabled")
        print("2. Database not created")
        print("3. Storage failed (check backend logs)")
        print("\nCheck backend logs for errors when calling API")
        
except Exception as e:
    error_msg = str(e)
    print(f"[ERROR] {error_msg}")
    
    if "SERVICE_DISABLED" in error_msg or "403" in error_msg:
        print("\n[ACTION REQUIRED] Firestore API needs to be enabled!")
        print("Enable here:")
        print("https://console.developers.google.com/apis/api/firestore.googleapis.com/overview?project=round-rain-478416-s4")
    elif "not found" in error_msg.lower():
        print("\n[ACTION REQUIRED] Firestore database needs to be created!")
        print("Create here:")
        print("https://console.cloud.google.com/firestore")

print("\n" + "=" * 60)
print("View in Google Cloud Console:")
print(f"https://console.cloud.google.com/firestore/data/prep_sessions/{SESSION_ID}")
print("=" * 60)

