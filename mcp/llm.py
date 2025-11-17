import os

def call_gemini(prompt: str) -> str:
    """Placeholder for Gemini API call."""
    # TODO: Replace with actual Vertex AI client and Gemini API call.
    # Ensure safety guardrails and 'not medical advice' text are included.

    # Mocking Gemini response for local development
    if "suggest" in prompt.lower():
        return "Summary: This is a mock summary of your symptoms.\nQuestions: What makes it worse?_input|How long have you had this?_input|Any other symptoms?_input"
    elif "prep sheet" in prompt.lower():
        return "<p>This is a mock prep sheet generated from your inputs.</p>"
    return "Mock Gemini response."
