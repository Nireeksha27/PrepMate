"""HTML-to-PDF helpers."""

from __future__ import annotations

import pdfkit  # type: ignore


def html_to_pdf_bytes(html: str) -> bytes:
    """Convert HTML string to PDF bytes."""
    return pdfkit.from_string(html, False)


