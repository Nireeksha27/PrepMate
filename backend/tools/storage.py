"""Google Cloud Storage helper utilities."""

from __future__ import annotations

try:
    from google.cloud import storage  # type: ignore
except Exception:  # pragma: no cover
    storage = None


def upload_pdf(bucket_name: str, blob_name: str, data: bytes) -> str | None:
    """Upload PDF bytes to GCS and return the public URL."""
    if storage is None:
        raise RuntimeError("google-cloud-storage is not installed.")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data, content_type="application/pdf")
    blob.make_public()
    return blob.public_url


