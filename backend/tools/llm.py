"""LLM wrapper module.

Currently returns mocked responses so the application can run locally without
Gemini credentials. Replace `call_gemini` implementation with Vertex AI /
Gemini API calls before deploying.
"""

from __future__ import annotations

import random


def call_gemini(prompt: str, mode: str = "suggest") -> dict:
    """Call Gemini (mock implementation)."""
    if mode == "suggest":
        return {
            "summary": "Mock summary: mild headache and nausea for 2 days.",
            "followupQuestions": [
                {"id": "q1", "label": "When did the symptoms start?", "type": "text"},
                {
                    "id": "q2",
                    "label": "Rate the pain from 1-10",
                    "type": "scale",
                    "min": 1,
                    "max": 10,
                },
                {
                    "id": "q3",
                    "label": "Any fever or vomiting?",
                    "type": "choice",
                    "options": ["Yes", "No"],
                },
            ],
        }

    if mode == "generate":
        sample_html = """
        <html><body>
        <h2>Doctor Appointment Prep Sheet</h2>
        <p>This is a mock prep sheet for preview purposes.</p>
        </body></html>
        """
        sample_text = "Doctor Appointment Prep Sheet (mock) - review symptoms and questions."
        return {
            "prep_sheet_html": sample_html,
            "prep_sheet_text": sample_text,
        }

    # Default fallback
    return {"content": "mock response", "token": random.randint(1, 1000)}


# TODO: Replace with real Gemini call, e.g.:
# from vertexai.generative_models import GenerativeModel
# def call_gemini(prompt: str, mode: str = "suggest") -> dict:
#     model = GenerativeModel("gemini-1.5-flash")
#     response = model.generate_content(prompt)
#     return parse_response(response.text)


