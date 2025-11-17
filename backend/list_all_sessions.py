"""List all sessions stored in Firestore."""

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

print("Listing all sessions in Firestore...")
print("=" * 60)

try:
    db = firestore.Client()
    print("[OK] Firestore client connected\n")
    
    # Get all documents
    sessions = db.collection("prep_sessions").stream()
    sessions_list = list(sessions)
    
    if not sessions_list:
        print("[INFO] No sessions found in Firestore!")
        print("\nThis means:")
        print("1. Either no data has been stored yet")
        print("2. Or storage failed silently (check backend logs)")
        print("\nCheck your backend server logs for errors like:")
        print("  WARNING: Failed to create Firestore session: ...")
        print("  WARNING: Failed to update Firestore session: ...")
    else:
        print(f"[SUCCESS] Found {len(sessions_list)} session(s):\n")
        for i, doc in enumerate(sessions_list, 1):
            data = doc.to_dict()
            print(f"{i}. Document ID: {doc.id}")
            print(f"   Session ID: {data.get('id', 'N/A')}")
            print(f"   Patient: {data.get('patient_info', {}).get('name', 'N/A')}")
            print(f"   Created: {data.get('created_at', 'N/A')}")
            print(f"   Questions: {len(data.get('followup_data', {}).get('questions', []))}")
            print(f"   Answers: {len(data.get('followup_data', {}).get('answers', []))}")
            print(f"   Has Final HTML: {'final_output_html' in data}")
            print(f"   Consent: {data.get('consentToStore', False)}")
            print()
        
except Exception as e:
    error_msg = str(e)
    print(f"[ERROR] {error_msg}")
    
    if "SERVICE_DISABLED" in error_msg:
        print("\n[ACTION REQUIRED] Firestore API needs to be enabled!")
    elif "not found" in error_msg.lower():
        print("\n[ACTION REQUIRED] Firestore database needs to be created!")

print("\n" + "=" * 60)
print("View in Google Cloud Console:")
print("https://console.cloud.google.com/firestore/data/prep_sessions")
print("=" * 60)

