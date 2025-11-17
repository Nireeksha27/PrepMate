import os

import pdfkit

def html_to_pdf_bytes(html: str) -> bytes:
    """Converts HTML string to PDF bytes using pdfkit."""
    # TODO: Ensure wkhtmltopdf is installed and accessible in the environment.
    # For Cloud Run, this will be handled in the Dockerfile.
    return pdfkit.from_string(html, False)
