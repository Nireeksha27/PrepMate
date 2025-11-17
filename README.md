# PrepMate

PrepMate is a two-tier demo (Streamlit frontend + FastAPI backend) that helps patients prepare for doctor visits by generating a personalized prep sheet.

## Features

- Streamlit frontend collects patient info and symptom descriptions.
- FastAPI backend with Google ADK Agent orchestration (Gemini brain + MCP tools).
- Backend service calls Gemini to produce summaries and clarifying questions.
- MCP Server handles Firestore operations for session storage.
- Users can edit responses, generate an HTML/text prep sheet, and download a PDF.
- Firestore session storage and GCS PDF uploads happen server-side only when the user consents.

## Architecture

```
┌─────────────────┐
│   Streamlit     │
│    Frontend     │
└────────┬────────┘
         │ HTTP Requests
         ▼
┌─────────────────┐
│  FastAPI        │
│  Backend        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ADK Agent      │
│  Orchestrator   │
├─────────────────┤
│  Brain:         │
│  - Gemini API   │
│                 │
│  Tools:         │
│  - MCP Server   │
│    (Firestore)  │
└─────────────────┘
```

## Repository layout

```
PrepMate/
├── backend/        # FastAPI + ADK Agent + MCP (deploy to Cloud Run)
│   ├── app.py              # FastAPI REST API
│   ├── agent.py            # ADK Agent with Gemini
│   ├── mcp/
│   │   ├── firestore_server.py  # MCP Server for Firestore
│   │   ├── db.py           # Firestore helpers
│   │   ├── llm.py          # (legacy, now using agent.py)
│   │   ├── pdf.py          # PDF generation
│   │   └── storage.py      # GCS storage
│   ├── prompts/
│   │   ├── suggest.txt     # Prompt for symptom analysis
│   │   └── generate.txt    # Prompt for prep sheet generation
│   ├── templates/
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
└── frontend/       # Streamlit UI that calls backend APIs
    ├── app.py
    └── requirements.txt
```

## Local development

1. **Clone the repo**

    ```bash
    git clone https://github.com/Nireeksha27/PrepMate.git
    cd PrepMate
    ```

2. **Run backend**

    ```bash
    cd backend
    python -m venv venv && source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    
    # Copy and configure environment variables
    cp .env.example .env
    # Edit .env and add your GEMINI_API_KEY (or leave empty for mock mode)
    
    # Run the FastAPI server
    uvicorn app:app --reload --port 8080
    # or: python app.py
    ```

3. **Run frontend**

    ```bash
    cd ../frontend
    python -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    BACKEND_URL=http://localhost:8080 streamlit run app.py
    ```

## Development vs Production

**Development Mode (Mock Responses):**
- Leave `GEMINI_API_KEY` empty in `.env` to use mock responses
- `backend/agent.py` returns deterministic responses so you can validate the UI without API keys
- `backend/mcp/db.py` and `backend/mcp/storage.py` expect Google Cloud credentials; when unavailable they simply log warnings

**Production Mode (Real Gemini API):**
- Set `GEMINI_API_KEY` in `.env` or as environment variable
- Configure `GOOGLE_APPLICATION_CREDENTIALS` for Firestore and GCS
- The ADK Agent will use real Gemini API calls via `google-genai` package

## Deploying the backend to Cloud Run

### Prerequisites

- Google Cloud project with billing
- `gcloud` CLI authenticated
- Firestore (Native mode) initialized
- Optional GCS bucket for PDF uploads

### Build & deploy

```bash
cd backend
gcloud builds submit --tag gcr.io/PROJECT_ID/prepmate-backend
gcloud run deploy prepmate-backend \
    --image gcr.io/PROJECT_ID/prepmate-backend \
    --platform managed \
    --region REGION \
    --allow-unauthenticated \
    --memory 1Gi \
    --set-env-vars GCS_BUCKET_NAME=your-bucket
```

Point the Streamlit frontend to the deployed backend with `BACKEND_URL=https://prepmate-backend-xyz.a.run.app`.

## Firestore schema example

Collection: `prep_sessions`

```json
{
  "id": "<UUID>",
  "created_at": "<timestamp>",
  "initial_input_text": "<user's description>",
  "ai_summary": "<summary>",
  "followup_data": {
    "questions": [ { "id": "q1", "label": "When did it start?", "type": "text" } ],
    "answers":   [ { "id": "q1", "answer": "3 days ago" } ]
  },
  "patient_info": {
    "name": "John Doe",
    "age": 30,
    "gender": "Male",
    "allergies": "Pollen",
    "medications": "None"
  },
  "language_code": "en",
  "final_output_html": "<HTML>",
  "pdf_url": "<optional GCS link>"
}
```

## Security advice

- Redact PII from logs before writing to stdout/stderr (see TODOs in `mcp/db.py`).
- Use Firestore security rules so only Cloud Run service accounts can read/write `prep_sessions`.
- Grant least privilege roles (Datastore User, Storage Object Admin) to the Cloud Run service account.
- Store API keys/credentials in env vars or Secret Manager—never commit them.

