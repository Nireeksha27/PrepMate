# PrepMate

PrepMate is a Streamlit-based web application designed to help patients prepare for doctor visits by generating a personalized prep sheet.

## Features

*   Collects patient information (name, age, gender, allergies, medications).
*   Takes a natural-language symptom description.
*   Uses Gemini (mocked for local development) to generate a symptom summary and clarifying follow-up questions.
*   Allows users to edit the summary and answer follow-up questions.
*   Generates a clean prep sheet in HTML and plain text formats.
*   Provides an option to download the prep sheet as a PDF.
*   Integrates with Firestore for session management (optional, based on user consent).

## Local Development Setup

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/Nireeksha27/PrepMate.git
    cd PrepMate
    ```

2.  **Create and activate a virtual environment:**

    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Streamlit application:**

    ```bash
    streamlit run app.py
    ```

    The app will open in your web browser, usually at `http://localhost:8501`.

## Mocked Gemini and Firestore

For local development, both Gemini and Firestore interactions are mocked:

*   `mcp/llm.py`: Contains a placeholder `call_gemini` function that returns predefined responses. To use the actual Gemini API, you will need to replace this with a Vertex AI client call and configure your Google Cloud credentials.
*   `mcp/db.py`: Contains `create_session` and `update_session_answers` functions that currently print to the console instead of interacting with a live Firestore database. To enable live Firestore, you'll need to set up Google Cloud authentication (e.g., `GOOGLE_APPLICATION_CREDENTIALS` environment variable pointing to a service account key file).

## Deployment to Google Cloud Run

### Prerequisites

*   A Google Cloud Project with Billing Enabled.
*   Google Cloud SDK installed and authenticated (`gcloud auth login`, `gcloud config set project YOUR_PROJECT_ID`).
*   Cloud Run API enabled.
*   Firestore in Native Mode initialized.
*   A Google Cloud Storage bucket if you plan to upload PDFs.

### 1. Build and Deploy to Cloud Run

The `Dockerfile` includes instructions to install `wkhtmltopdf` for PDF generation.

```bash
gcloud run deploy prepmate \
    --source . \
    --platform managed \
    --region YOUR_GCP_REGION \
    --allow-unauthenticated \
    --memory 1Gi \
    --set-env-vars GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
```

Replace `YOUR_GCP_REGION` with your desired Google Cloud region (e.g., `us-central1`) and `YOUR_PROJECT_ID` with your Google Cloud Project ID.

### 2. Firestore Setup

Firestore will be used to store session data. Ensure you have Firestore initialized in Native Mode in your Google Cloud Project.

#### Service Account

Cloud Run will use its default service account or a specified service account to interact with Firestore. Ensure this service account has the `Cloud Datastore User` role (or custom roles with `datastore.entities.create`, `datastore.entities.update` permissions for `prep_sessions` collection) and `Storage Object Admin` (if uploading PDFs to GCS) on your project.

### 3. Google Cloud Storage (Optional - for PDF uploads)

If you want to enable PDF uploads, you'll need a Google Cloud Storage bucket. Make sure the service account used by Cloud Run has the necessary permissions to write to this bucket.

## Firestore Document Schema Example

Collection: `prep_sessions`
Document ID: UUID (e.g., `a1b2c3d4-e5f6-7890-1234-567890abcdef`)

```json
{
  "id": "<UUID>",
  "created_at": "<timestamp>",
  "initial_input_text": "<user's initial symptom description>",
  "ai_summary": "<AI-generated symptom summary>",
  "followup_data": {
    "questions": {
      "What makes it worse?": "_input",
      "How long have you had this?": "_input"
    },
    "answers": {
      "What makes it worse?": "Eating certain foods",
      "How long have you had this?": "About 3 days"
    }
  },
  "patient_info": {
    "name": "John Doe",
    "age": 30,
    "gender": "Male",
    "allergies": "Pollen",
    "medications": "None"
  },
  "language_code": "en-US",
  "final_output_html": "<HTML content of the prep sheet>",
  "pdf_url": "<URL to the uploaded PDF in GCS (optional)>",
  "updated_at": "<timestamp>"
}
```

## Security Advice

*   **PII Redaction:** Sensitive Personally Identifiable Information (PII) should be redacted from logs before being written to any persistent storage or logs accessible to a wide audience. Look for `TODO: Redact sensitive PII from logs` in `mcp/db.py`.
*   **Firestore Security Rules:** Implement strict Firestore Security Rules to ensure that data can only be accessed and modified by authorized Cloud Run instances (via service accounts) and not directly by end-users. For example:

    ```firestore
    rules_version = '2';
    service cloud.firestore {
      match /databases/{database}/documents {
        match /prep_sessions/{sessionId} {
          allow read, write: if request.auth.uid == "service-YOUR_PROJECT_NUMBER@robot.gserviceaccount.com";
        }
      }
    }
    ```
    Replace `YOUR_PROJECT_NUMBER` with your actual Google Cloud Project Number.

*   **Service Account Least Privilege:** Grant the Cloud Run service account only the minimum necessary permissions (least privilege) required to interact with Firestore and Google Cloud Storage.
*   **API Key Security:** Never hardcode API keys or sensitive credentials directly in your code. Use environment variables or Google Cloud Secret Manager for secure handling of credentials. (Not directly applicable to mocked Gemini, but crucial for actual Gemini API integration).
