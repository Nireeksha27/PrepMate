"""Google ADK Agent implementation for PrepMate.

This module uses Google ADK (Agent Development Kit) framework to create agents that:
- Use Gemini as the LLM brain
- Have Firestore tools for data storage
- Follow ADK framework patterns
"""

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from google.adk.agents import Agent
from jinja2 import Environment, FileSystemLoader

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get API key (ADK uses GOOGLE_API_KEY)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY/GOOGLE_API_KEY not set. Agent will use mock responses.")

# Setup Jinja2 for prompt templates
prompt_env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "prompts")),
    autoescape=False
)


# Firestore tools as functions (ADK uses function tools)
def create_prep_session(
    session_id: str,
    created_at: str,
    initial_input_text: str,
    ai_summary: str,
    followup_questions: list,
    patient_info: dict,
    language_code: str
) -> dict:
    """Create a new prep session document in Firestore.
    
    Args:
        session_id: Unique session ID (UUID)
        created_at: ISO 8601 timestamp
        initial_input_text: User's original symptom description
        ai_summary: AI-generated symptom summary
        followup_questions: List of follow-up questions
        patient_info: Patient information dict
        language_code: Language code (en, hi, kn)
    
    Returns:
        dict with success status
    """
    try:
        from tools import db
        db.create_session(
            doc_id=session_id,
            document={
                "id": session_id,
                "created_at": created_at,
                "patient_info": patient_info,
                "language_code": language_code,
                "initial_input_text": initial_input_text,
                "ai_summary": ai_summary,
                "followup_data": {
                    "questions": followup_questions,
                    "answers": []
                },
                "consentToStore": True
            }
        )
        return {"status": "success", "session_id": session_id, "message": "Session created in Firestore"}
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        return {"status": "error", "error": str(e)}


def update_prep_session(
    session_id: str,
    answers: list,
    final_output_html: str,
    pdf_url: str = None
) -> dict:
    """Update a prep session with answers and final HTML output.
    
    Args:
        session_id: Session ID to update
        answers: List of answer dicts
        final_output_html: Final prep sheet HTML
        pdf_url: Optional PDF URL
    
    Returns:
        dict with success status
    """
    try:
        from tools import db
        db.update_session_answers(
            session_id=session_id,
            answers=answers,
            final_html=final_output_html,
            pdf_url=pdf_url
        )
        return {"status": "success", "session_id": session_id, "message": "Session updated in Firestore"}
    except Exception as e:
        logger.error(f"Failed to update session: {e}")
        return {"status": "error", "error": str(e)}


# Create ADK agents
def create_suggest_agent() -> Agent:
    """Create ADK agent for generating symptom summaries and questions."""
    
    instruction = """You are a helpful assistant that helps patients prepare for doctor visits.
You analyze symptom descriptions and generate:
1. A concise 1-sentence summary
2. Up to 5 clarifying follow-up questions

You are NOT a doctor and must NOT provide diagnoses or medical advice.
Only include pregnancy-related questions if symptoms clearly require it.
Keep questions concise and prefer yes/no or short-answer formats.

You must respond with valid JSON in this exact format:
{
  "summary": "<1 sentence summary>",
  "followupQuestions": [
    {"id": "q1", "label": "<question text>", "type": "text|choice|scale", "options": [], "min": 1, "max": 10}
  ]
}"""
    
    return Agent(
        model='gemini-2.5-flash',
        name='suggest_agent',
        description='Generates symptom summaries and follow-up questions for doctor visits',
        instruction=instruction,
        tools=[create_prep_session],  # Tool available to agent
    )


def create_generate_agent() -> Agent:
    """Create ADK agent for generating final prep sheets."""
    
    instruction = """You are a helpful assistant that creates Doctor Appointment Prep Sheets.
You generate structured HTML prep sheets with:
- Patient information
- Symptom summary
- Doctor questionnaire
- Things to bring
- Conversation starter
- Safety reminders

You are NOT a doctor and must NOT provide medical advice or diagnosis.
Always include a disclaimer: "This is a communication aid, not medical advice."
Include red-flag guidance for when to seek urgent care (general terms only).

You must respond with valid JSON in this exact format:
{
  "prep_sheet_html": "<clean HTML with sections>",
  "prep_sheet_text": "<plain text version>"
}"""
    
    return Agent(
        model='gemini-2.5-flash',
        name='generate_agent',
        description='Generates final doctor appointment prep sheets',
        instruction=instruction,
        tools=[update_prep_session],  # Tool available to agent
    )


# Global agent instances
suggest_agent = create_suggest_agent()
generate_agent = create_generate_agent()


class PrepMateAgent:
    """Wrapper class for ADK agents to maintain API compatibility."""
    
    async def suggest_followups(
        self,
        patient_info: dict,
        symptom_description: str,
        language: str
    ) -> dict:
        """Generate symptom summary and follow-up questions using ADK agent."""
        
        # Render prompt template
        template = prompt_env.get_template("suggest.txt")
        user_prompt = template.render(
            patient_info=json.dumps(patient_info, ensure_ascii=False),
            symptom_description=symptom_description,
            language=language
        )
        
        # Mock response if no API key
        if not GEMINI_API_KEY:
            logger.warning("Using mock response (no API key)")
            return {
                "summary": "Mock summary: mild headache and nausea for 2 days.",
                "questions": [
                    {"id": "q1", "label": "When did the symptoms start?", "type": "text"},
                    {"id": "q2", "label": "Rate the pain from 1-10", "type": "scale", "min": 1, "max": 10},
                    {"id": "q3", "label": "Any fever or vomiting?", "type": "choice", "options": ["Yes", "No"]}
                ]
            }
        
        try:
            # Use direct Gemini API with structured output (ADK integration simplified)
            # ADK's run_async requires InvocationContext which is complex for our use case
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Use the agent's instruction as system prompt
            system_instruction = suggest_agent.canonical_instruction if hasattr(suggest_agent, 'canonical_instruction') else ""
            full_prompt = f"{system_instruction}\n\n{user_prompt}" if system_instruction else user_prompt
            
            gemini_response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    response_mime_type="application/json"
                )
            )
            result = json.loads(gemini_response.text)
            
            return {
                "summary": result.get("summary", ""),
                "questions": result.get("followupQuestions", result.get("questions", []))
            }
        
        except Exception as e:
            logger.error(f"Error in suggest_followups: {e}")
            raise
    
    async def generate_prep_sheet(
        self,
        summary: str,
        followup_answers: list,
        patient_info: dict,
        language: str
    ) -> dict:
        """Generate final prep sheet using ADK agent."""
        
        # Render prompt template
        template = prompt_env.get_template("generate.txt")
        user_prompt = template.render(
            summary=summary,
            followup_answers=json.dumps(followup_answers, ensure_ascii=False),
            patient_info=json.dumps(patient_info, ensure_ascii=False),
            language=language
        )
        
        # Mock response if no API key
        if not GEMINI_API_KEY:
            logger.warning("Using mock response (no API key)")
            mock_html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #2c3e50; }}
                    .section {{ margin: 20px 0; }}
                </style>
            </head>
            <body>
                <h1>Doctor Appointment Prep Sheet</h1>
                <p><em>This is a communication aid, not medical advice.</em></p>
                
                <div class="section">
                    <h2>Patient Information</h2>
                    <p><strong>Name:</strong> {patient_info.get('name', 'N/A')}</p>
                    <p><strong>Age:</strong> {patient_info.get('age', 'N/A')}</p>
                    <p><strong>Gender:</strong> {patient_info.get('gender', 'N/A')}</p>
                    <p><strong>Allergies:</strong> {patient_info.get('allergies', 'N/A')}</p>
                    <p><strong>Medications:</strong> {patient_info.get('medications', 'N/A')}</p>
                </div>
                
                <div class="section">
                    <h2>Symptom Summary</h2>
                    <p>{summary}</p>
                </div>
            </body>
            </html>
            """
            
            return {
                "prep_sheet_html": mock_html,
                "prep_sheet_text": "Doctor Appointment Prep Sheet (mock) - review symptoms and questions."
            }
        
        try:
            # Use direct Gemini API with structured output (ADK integration simplified)
            # ADK's run_async requires InvocationContext which is complex for our use case
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Use the agent's instruction as system prompt
            system_instruction = generate_agent.canonical_instruction if hasattr(generate_agent, 'canonical_instruction') else ""
            full_prompt = f"{system_instruction}\n\n{user_prompt}" if system_instruction else user_prompt
            
            gemini_response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    response_mime_type="application/json"
                )
            )
            result = json.loads(gemini_response.text)
            
            return {
                "prep_sheet_html": result.get("prep_sheet_html", "<p>No data</p>"),
                "prep_sheet_text": result.get("prep_sheet_text", "")
            }
        
        except Exception as e:
            logger.error(f"Error in generate_prep_sheet: {e}")
            raise


# Global agent instance (for backward compatibility)
agent = PrepMateAgent()


def get_agent() -> PrepMateAgent:
    """Get the global agent instance."""
    return agent
