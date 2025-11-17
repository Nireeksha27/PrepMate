"""MCP Server for Firestore operations.

This MCP server exposes tools for creating and updating PrepMate sessions in Firestore.
"""

import json
import logging
from typing import Any

from google.cloud import firestore
from mcp.server import Server
from mcp.types import Tool, TextContent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Firestore client
try:
    db = firestore.Client()
    logger.info("Firestore client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Firestore: {e}")
    db = None


# Create MCP server instance
mcp_server = Server("firestore-prepmate")


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """List available Firestore tools."""
    return [
        Tool(
            name="create_prep_session",
            description="Create a new prep session document in Firestore with initial patient info, symptom summary, and follow-up questions",
            inputSchema={
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
                        "description": "List of follow-up questions",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "label": {"type": "string"},
                                "type": {"type": "string"}
                            }
                        }
                    },
                    "patient_info": {
                        "type": "object",
                        "description": "Patient information (name, age, gender, allergies, medications)"
                    },
                    "language_code": {
                        "type": "string",
                        "description": "Language code (en, hi, kn)"
                    }
                },
                "required": ["session_id", "created_at", "initial_input_text", "ai_summary", "followup_questions", "patient_info", "language_code"]
            }
        ),
        Tool(
            name="update_prep_session",
            description="Update a prep session with follow-up answers, final HTML output, and optional PDF URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID to update"
                    },
                    "answers": {
                        "type": "array",
                        "description": "List of answers to follow-up questions",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "answer": {"type": "string"}
                            }
                        }
                    },
                    "final_output_html": {
                        "type": "string",
                        "description": "Final prep sheet HTML"
                    },
                    "pdf_url": {
                        "type": "string",
                        "description": "Optional GCS URL for generated PDF"
                    }
                },
                "required": ["session_id", "answers", "final_output_html"]
            }
        )
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute Firestore operations based on tool name."""
    
    if db is None:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Firestore client not initialized"
            })
        )]
    
    try:
        if name == "create_prep_session":
            session_id = arguments["session_id"]
            doc_data = {
                "id": session_id,
                "created_at": arguments["created_at"],
                "initial_input_text": arguments["initial_input_text"],
                "ai_summary": arguments["ai_summary"],
                "followup_data": {
                    "questions": arguments["followup_questions"],
                    "answers": []
                },
                "patient_info": arguments["patient_info"],
                "language_code": arguments["language_code"],
                "consentToStore": True
            }
            
            db.collection("prep_sessions").document(session_id).set(doc_data)
            logger.info(f"Created session {session_id}")
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "session_id": session_id,
                    "message": "Session created successfully"
                })
            )]
        
        elif name == "update_prep_session":
            session_id = arguments["session_id"]
            update_data = {
                "followup_data.answers": arguments["answers"],
                "final_output_html": arguments["final_output_html"]
            }
            
            if "pdf_url" in arguments and arguments["pdf_url"]:
                update_data["pdf_url"] = arguments["pdf_url"]
            
            db.collection("prep_sessions").document(session_id).update(update_data)
            logger.info(f"Updated session {session_id}")
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "session_id": session_id,
                    "message": "Session updated successfully"
                })
            )]
        
        else:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"Unknown tool: {name}"
                })
            )]
    
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            })
        )]


def get_server():
    """Return the MCP server instance."""
    return mcp_server

