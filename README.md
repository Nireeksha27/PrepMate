# PrepMate

PrepMate is a two-tier demo (Streamlit frontend + FastAPI backend) that helps patients prepare for doctor visits by generating a personalized prep sheet.

## Features

- **Streamlit frontend** collects patient info and symptom descriptions with a multi-step form
- **FastAPI backend** with Google ADK framework integration
- **Gemini 2.5 Flash** as the LLM brain for generating summaries and prep sheets
- **ADK agent structure** for organized prompts and future tool integration
- **Firestore integration** for session storage (when user consents)
- **PDF generation** using wkhtmltopdf with download option
- **GCS storage** for PDF uploads (optional, when bucket configured)
- Users can edit responses, generate HTML/text prep sheets, and download PDFs

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
│  Gemini API     │
│  (via ADK        │
│   structure)     │
├─────────────────┤
│  suggest_agent:  │
│  - Instruction   │
│    templates     │
│  - Gemini 2.5    │
│    Flash         │
│                 │
│  generate_agent: │
│  - Instruction   │
│    templates     │
│  - Gemini 2.5    │
│    Flash         │
└────────┬─────────┘
         │
         ▼
┌─────────────────┐
│  Firestore      │
│  Tools          │
│  - create_session│
│  - update_session│
└─────────────────┘
```

## Repository layout

```
PrepMate/
├── backend/        # FastAPI + Google ADK (deploy to Cloud Run)
│   ├── app.py              # FastAPI REST API
│   ├── agent.py            # Google ADK agents with Gemini
│   ├── tools/
│   │   ├── db.py           # Firestore helpers (ADK tools)
│   │   ├── pdf.py          # PDF generation
│   │   ├── storage.py      # GCS storage
│   │   └── firestore_server.py  # (optional MCP server)
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
    # Edit .env and add:
    # - GOOGLE_API_KEY or GEMINI_API_KEY (or leave empty for mock mode)
    # - GOOGLE_APPLICATION_CREDENTIALS (path to service account JSON)
    # - GCS_BUCKET_NAME (optional, for PDF storage)
    
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
- Leave `GOOGLE_API_KEY` or `GEMINI_API_KEY` empty in `.env` to use mock responses
- `backend/agent.py` returns deterministic responses so you can validate the UI without API keys
- `backend/tools/db.py` and `backend/tools/storage.py` expect Google Cloud credentials; when unavailable they simply log warnings

**Production Mode (Real Gemini API):**
- Set `GOOGLE_API_KEY` in `.env` (preferred) or `GEMINI_API_KEY`
- Configure `GOOGLE_APPLICATION_CREDENTIALS` pointing to your service account JSON key
- Set `GCS_BUCKET_NAME` if you want PDF uploads to Google Cloud Storage
- The backend uses direct Gemini API calls with structured JSON output

## Deploying the backend to Cloud Run

### Prerequisites

- Google Cloud project with billing enabled
- `gcloud` CLI installed and authenticated
- Firestore (Native mode) database created
- Service account with Firestore permissions
- Optional: GCS bucket for PDF uploads

### Build & deploy

```bash
cd backend

# Build the Docker image
gcloud builds submit --tag gcr.io/PROJECT_ID/prepmate-backend

# Deploy to Cloud Run
gcloud run deploy prepmate-backend \
    --image gcr.io/PROJECT_ID/prepmate-backend \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 1Gi \
    --timeout 300 \
    --set-env-vars "GOOGLE_API_KEY=your-api-key,GCS_BUCKET_NAME=your-bucket-name" \
    --set-secrets "GOOGLE_APPLICATION_CREDENTIALS=service-account-key:latest"
```

**Note:** For production, use Secret Manager for API keys instead of env vars:
```bash
# Create secrets
echo -n "your-api-key" | gcloud secrets create google-api-key --data-file=-
echo -n "path/to/service-account.json" | gcloud secrets create service-account-path --data-file=-

# Deploy with secrets
gcloud run deploy prepmate-backend \
    --set-secrets "GOOGLE_API_KEY=google-api-key:latest,GOOGLE_APPLICATION_CREDENTIALS=service-account-path:latest"
```

Point the Streamlit frontend to the deployed backend:
```bash
BACKEND_URL=https://prepmate-backend-xyz.a.run.app streamlit run app.py
```

## API Endpoints

The FastAPI backend provides the following endpoints:

- **`GET /health`** - Health check endpoint
- **`POST /suggest`** - Generate symptom summary and follow-up questions
  - Request: `{patient_info, symptom_description, language, consent, session_id?}`
  - Response: `{session_id, summary, questions}`
- **`POST /generate`** - Generate final prep sheet HTML/PDF
  - Request: `{session_id, patient_info, summary, answers, language, consent}`
  - Response: `{session_id, prep_sheet_html, prep_sheet_text, pdf_url?, pdf_base64?}`

See `/docs` endpoint for interactive API documentation (Swagger UI).

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

