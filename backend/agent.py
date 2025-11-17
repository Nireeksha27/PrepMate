"""Google ADK Agent with Gemini brain and MCP tools.

This module sets up the ADK agent that orchestrates:
- Gemini as the LLM brain
- MCP Firestore server as tools
"""

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
import google.generativeai as genai
from jinja2 import Environment, FileSystemLoader

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Gemini client
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("Gemini API configured successfully")
else:
    logger.warning("GEMINI_API_KEY not set. Agent will use mock responses.")


class PrepMateAgent:
    """ADK-style agent for PrepMate using Gemini and MCP tools."""
    
    def __init__(self):
        self.model_name = "gemini-2.5-flash"  # Stable, fast, free-tier model
        self.tools = self._setup_tools()
        # Setup Jinja2 for prompt templates
        self.prompt_env = Environment(
            loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "prompts")),
            autoescape=False
        )
    
    def _setup_tools(self) -> list:
        """Setup MCP tools for the agent."""
        return [
            {
                "name": "create_prep_session",
                "description": "Create a new prep session document in Firestore with initial patient info, symptom summary, and follow-up questions",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Unique session ID (UUID)"
                        },
                        "created_at": {
                            "type": "string",
                            "description": "ISO 8601 timestamp"
                        },
                        "initial_input_text": {
                            "type": "string",
                            "description": "User's original symptom description"
                        },
                        "ai_summary": {
                            "type": "string",
                            "description": "AI-generated symptom summary"
                        },
                        "followup_questions": {
                            "type": "array",
                            "description": "List of follow-up questions"
                        },
                        "patient_info": {
                            "type": "object",
                            "description": "Patient information"
                        },
                        "language_code": {
                            "type": "string",
                            "description": "Language code"
                        }
                    },
                    "required": ["session_id", "created_at", "initial_input_text", "ai_summary", "followup_questions", "patient_info", "language_code"]
                }
            },
            {
                "name": "update_prep_session",
                "description": "Update a prep session with follow-up answers and final HTML output",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "answers": {"type": "array"},
                        "final_output_html": {"type": "string"},
                        "pdf_url": {"type": "string"}
                    },
                    "required": ["session_id", "answers", "final_output_html"]
                }
            }
        ]
    
    async def suggest_followups(
        self, 
        patient_info: dict,
        symptom_description: str,
        language: str
    ) -> dict:
        """Generate symptom summary and follow-up questions.
        
        Args:
            patient_info: Patient details (name, age, gender, allergies, medications)
            symptom_description: User's symptom description
            language: Language code (en, hi, kn)
        
        Returns:
            dict with 'summary' and 'questions' keys
        """
        
        # Render prompt using Jinja2
        template = self.prompt_env.get_template("suggest.txt")
        prompt = template.render(
            patient_info=json.dumps(patient_info, ensure_ascii=False),
            symptom_description=symptom_description,
            language=language
        )
        
        # Mock response if no API key
        if not GEMINI_API_KEY:
            logger.warning("Using mock Gemini response")
            return {
                "summary": "Mock summary: mild headache and nausea for 2 days.",
                "questions": [
                    {"id": "q1", "label": "When did the symptoms start?", "type": "text"},
                    {"id": "q2", "label": "Rate the pain from 1-10", "type": "scale", "min": 1, "max": 10},
                    {"id": "q3", "label": "Any fever or vomiting?", "type": "choice", "options": ["Yes", "No"]}
                ]
            }
        
        try:
            # Call Gemini
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    response_mime_type="application/json"
                )
            )
            
            result = json.loads(response.text)
            
            # Normalize the response format
            return {
                "summary": result.get("summary", ""),
                "questions": result.get("followupQuestions", result.get("questions", []))
            }
        
        except Exception as e:
            logger.error(f"Error calling Gemini: {e}")
            raise
    
    async def generate_prep_sheet(
        self,
        summary: str,
        followup_answers: list,
        patient_info: dict,
        language: str
    ) -> dict:
        """Generate final prep sheet HTML and text.
        
        Args:
            summary: AI-generated symptom summary
            followup_answers: User's answers to follow-up questions
            patient_info: Patient details
            language: Language code
        
        Returns:
            dict with 'prep_sheet_html' and 'prep_sheet_text' keys
        """
        
        # Render prompt using Jinja2
        template = self.prompt_env.get_template("generate.txt")
        prompt = template.render(
            summary=summary,
            followup_answers=json.dumps(followup_answers, ensure_ascii=False),
            patient_info=json.dumps(patient_info, ensure_ascii=False),
            language=language
        )
        
        # Mock response if no API key
        if not GEMINI_API_KEY:
            logger.warning("Using mock Gemini response")
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
                
                <div class="section">
                    <h2>Questions to Ask Your Doctor</h2>
                    <ul>
                        <li>What could be causing these symptoms?</li>
                        <li>Do I need any tests?</li>
                        <li>What treatment options are available?</li>
                    </ul>
                </div>
                
                <div class="section">
                    <h2>Safety Note</h2>
                    <p>If you experience severe symptoms, chest pain, difficulty breathing, or other emergency signs, seek immediate medical attention.</p>
                </div>
            </body>
            </html>
            """
            
            return {
                "prep_sheet_html": mock_html,
                "prep_sheet_text": "Doctor Appointment Prep Sheet (mock) - review symptoms and questions."
            }
        
        try:
            # Call Gemini
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    response_mime_type="application/json"
                )
            )
            
            result = json.loads(response.text)
            
            return {
                "prep_sheet_html": result.get("prep_sheet_html", "<p>No data</p>"),
                "prep_sheet_text": result.get("prep_sheet_text", "")
            }
        
        except Exception as e:
            logger.error(f"Error calling Gemini: {e}")
            raise


# Global agent instance
agent = PrepMateAgent()


def get_agent() -> PrepMateAgent:
    """Get the global agent instance."""
    return agent

