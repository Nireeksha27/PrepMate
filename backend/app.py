"""FastAPI backend for PrepMate with ADK Agent and MCP integration.

This backend provides REST API endpoints that use:
- Google ADK Agent with Gemini as the brain
- MCP Server for Firestore operations
"""

import base64
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from agent import get_agent
from tools import db, pdf, storage

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PrepMate API",
    description="AI-powered doctor visit preparation assistant",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
GCS_BUCKET = os.environ.get("GCS_BUCKET_NAME")

# Get agent instance
agent = get_agent()


# Pydantic models for request/response
class PatientInfo(BaseModel):
    name: str
    age: int = Field(..., ge=1, le=120)
    gender: str
    allergies: str
    medications: str


class SuggestRequest(BaseModel):
    patient_info: PatientInfo
    symptom_description: str
    language: str = "en"
    consent: bool = False
    session_id: Optional[str] = None


class SuggestResponse(BaseModel):
    session_id: str
    summary: str
    questions: list


class FollowupAnswer(BaseModel):
    id: str
    label: str
    answer: str


class GenerateRequest(BaseModel):
    session_id: str
    patient_info: PatientInfo
    summary: str
    answers: list[FollowupAnswer]
    language: str = "en"
    consent: bool = False


class GenerateResponse(BaseModel):
    session_id: str
    prep_sheet_html: str
    prep_sheet_text: str
    pdf_url: Optional[str] = None
    pdf_base64: Optional[str] = None


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "PrepMate API"}


@app.post("/suggest", response_model=SuggestResponse)
async def suggest_followups(request: SuggestRequest):
    """Generate AI summary and follow-up questions.
    
    This endpoint:
    1. Takes patient info and symptom description
    2. Calls ADK Agent with Gemini to generate summary and questions
    3. Optionally stores in Firestore via MCP if consent is given
    """
    
    # Validate inputs
    if not request.symptom_description.strip():
        raise HTTPException(status_code=400, detail="symptom_description is required")
    
    # Generate session ID
    session_id = request.session_id or str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat() + "Z"
    
    try:
        # Call ADK Agent to generate summary and questions
        result = await agent.suggest_followups(
            patient_info=request.patient_info.dict(),
            symptom_description=request.symptom_description,
            language=request.language
        )
        
        summary = result.get("summary", "")
        questions = result.get("questions", [])
        
        # Store in Firestore via MCP if consent given
        if request.consent:
            db.create_session(
                doc_id=session_id,  # Fixed: was session_id, should be doc_id
                document={
                    "id": session_id,
                    "created_at": created_at,
                    "patient_info": request.patient_info.dict(),
                    "language_code": request.language,
                    "initial_input_text": request.symptom_description,
                    "ai_summary": summary,
                    "followup_data": {
                        "questions": questions,
                        "answers": []
                    },
                    "consentToStore": True
                }
            )
        
        return SuggestResponse(
            session_id=session_id,
            summary=summary,
            questions=questions
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating suggestions: {str(e)}")


@app.post("/generate", response_model=GenerateResponse)
async def generate_prep_sheet(request: GenerateRequest):
    """Generate final prep sheet with HTML and PDF.
    
    This endpoint:
    1. Takes summary, answers, and patient info
    2. Calls ADK Agent with Gemini to generate final prep sheet
    3. Generates PDF using pdfkit
    4. Optionally uploads to GCS and updates Firestore via MCP
    """
    
    # Validate inputs
    if not request.summary.strip():
        raise HTTPException(status_code=400, detail="summary is required")
    
    try:
        # Call ADK Agent to generate prep sheet
        result = await agent.generate_prep_sheet(
            summary=request.summary,
            followup_answers=[answer.dict() for answer in request.answers],
            patient_info=request.patient_info.dict(),
            language=request.language
        )
        
        prep_html = result.get("prep_sheet_html", "<p>No data</p>")
        prep_text = result.get("prep_sheet_text", "")
        
        # Generate PDF
        pdf_bytes = None
        pdf_url = None
        try:
            pdf_bytes = pdf.html_to_pdf_bytes(prep_html)
            
            # Upload to GCS if bucket configured
            if GCS_BUCKET and pdf_bytes:
                pdf_url = storage.upload_pdf(
                    GCS_BUCKET, 
                    f"prep-sheets/{request.session_id}.pdf", 
                    pdf_bytes
                )
        except Exception as exc:
            logger.warning(f"PDF generation failed: {exc}")
        
        # Update Firestore via MCP if consent given
        if request.consent:
            db.update_session_answers(
                session_id=request.session_id,
                answers=[answer.dict() for answer in request.answers],
                final_html=prep_html,
                pdf_url=pdf_url
            )
        
        # Prepare response
        response = GenerateResponse(
            session_id=request.session_id,
            prep_sheet_html=prep_html,
            prep_sheet_text=prep_text,
            pdf_url=pdf_url
        )
        
        if pdf_bytes:
            response.pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating prep sheet: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "service": "PrepMate API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "suggest": "/suggest",
            "generate": "/generate"
        },
        "architecture": {
            "framework": "FastAPI",
            "agent": "Google ADK with Gemini",
            "tools": "MCP Server (Firestore)",
            "database": "Google Firestore",
            "storage": "Google Cloud Storage"
        }
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
