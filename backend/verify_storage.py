"""Quick script to verify if data is stored in Firestore."""

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

# Initialize Firestore
try:
    db = firestore.Client()
    print("[OK] Firestore client connected\n")
except Exception as e:
    print(f"[ERROR] Failed to connect: {e}")
    exit(1)

# Check for specific session
session_id = input("Enter session ID to check (or press Enter to list all): ").strip()

if session_id:
    # Check specific session
    print(f"\nChecking session: {session_id}")
    print("=" * 60)
    
    try:
        doc_ref = db.collection("prep_sessions").document(session_id)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            print(f"[SUCCESS] Session found!\n")
            print(f"Session ID: {data.get('id', 'N/A')}")
            print(f"Created: {data.get('created_at', 'N/A')}")
            print(f"Patient: {data.get('patient_info', {}).get('name', 'N/A')}")
            print(f"Summary: {data.get('ai_summary', 'N/A')[:80]}...")
            print(f"Questions: {len(data.get('followup_data', {}).get('questions', []))}")
            print(f"Answers: {len(data.get('followup_data', {}).get('answers', []))}")
            print(f"Has Final HTML: {'final_output_html' in data}")
            print(f"Consent: {data.get('consentToStore', False)}")
        else:
            print(f"[NOT FOUND] Session {session_id} not found in Firestore")
            print("\nPossible reasons:")
            print("1. Firestore API not enabled")
            print("2. Database not created")
            print("3. consent was false when calling API")
            print("4. Storage failed silently")
    except Exception as e:
        print(f"[ERROR] {e}")
else:
    # List all sessions
    print("Listing all sessions in Firestore...")
    print("=" * 60)
    
    try:
        sessions = db.collection("prep_sessions").stream()
        sessions_list = list(sessions)
        
        if not sessions_list:
            print("[INFO] No sessions found in Firestore!")
            print("\nThis means:")
            print("- Either no data has been stored yet")
            print("- Or Firestore API/database is not set up")
        else:
            print(f"\n[SUCCESS] Found {len(sessions_list)} session(s):\n")
            for i, doc in enumerate(sessions_list, 1):
                data = doc.to_dict()
                print(f"{i}. Session ID: {doc.id}")
                print(f"   Patient: {data.get('patient_info', {}).get('name', 'N/A')}")
                print(f"   Created: {data.get('created_at', 'N/A')}")
                print(f"   Has Answers: {len(data.get('followup_data', {}).get('answers', [])) > 0}")
                print()
    except Exception as e:
        print(f"[ERROR] {e}")
        print("\nCheck:")
        print("1. Firestore API enabled: https://console.developers.google.com/apis/api/firestore.googleapis.com/overview?project=round-rain-478416-s4")
        print("2. Database created: https://console.cloud.google.com/firestore")

print("\n" + "=" * 60)
print("View in Google Cloud Console:")
print("https://console.cloud.google.com/firestore/data/prep_sessions")
print("=" * 60)

