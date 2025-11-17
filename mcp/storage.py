
from google.cloud import storage
import os

def upload_pdf(bucket_name: str, blob_name: str, data: bytes) -> str:
    """Uploads a PDF to Google Cloud Storage and returns its public URL."""
    # TODO: Implement actual GCS upload. Ensure GOOGLE_APPLICATION_CREDENTIALS is set.
    # For local development, this will be a mock.
    print(f"Uploading {blob_name} to bucket {bucket_name} (mock)")
    # Mocking a public URL
    return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
