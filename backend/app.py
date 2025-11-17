import base64
import json
import os
import uuid
from datetime import datetime

from flask import Flask, jsonify, request
from jinja2 import Environment, FileSystemLoader, select_autoescape

from mcp import db, llm, pdf, storage

app = Flask(__name__)

PROMPT_ENV = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "prompts")),
    autoescape=False,
)
HTML_ENV = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    autoescape=select_autoescape(enabled_extensions=("html",)),
)

GCS_BUCKET = os.environ.get("GCS_BUCKET_NAME")


def _load_prompt(name: str) -> str:
    return PROMPT_ENV.get_template(name).render


def _validate_patient_info(info: dict) -> tuple[bool, str]:
    required_fields = ["name", "age", "gender", "allergies", "medications"]
    missing = [field for field in required_fields if not info.get(field)]
    if missing:
        return False, f"Missing patient fields: {', '.join(missing)}"
    try:
        age = int(info["age"])
        if not 0 < age <= 120:
            return False, "Age must be between 1 and 120."
    except (ValueError, TypeError):
        return False, "Age must be a number."
    return True, ""


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200


@app.route("/suggest", methods=["POST"])
def suggest_followups():
    payload = request.get_json(force=True, silent=True) or {}
    patient_info = payload.get("patient_info", {})
    consent = bool(payload.get("consent", False))
    language = payload.get("language", "en")
    symptom_description = (payload.get("symptom_description") or "").strip()

    valid, message = _validate_patient_info(patient_info)
    if not valid:
        return jsonify({"error": message}), 400
    if not symptom_description:
        return jsonify({"error": "symptom_description is required"}), 400

    session_id = payload.get("session_id") or str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat() + "Z"

    template = PROMPT_ENV.get_template("suggest.txt")
    prompt = template.render(
        patient_info=patient_info,
        symptom_description=symptom_description,
        language=language,
    )

    llm_response = llm.call_gemini(prompt, mode="suggest")
    summary = llm_response.get("summary", "")
    questions = llm_response.get("followupQuestions", [])

    if consent:
        doc = {
            "id": session_id,
            "created_at": created_at,
            "patient_info": patient_info,
            "language_code": language,
            "initial_input_text": symptom_description,
            "ai_summary": summary,
            "followup_data": {"questions": questions, "answers": []},
            "consentToStore": True,
        }
        db.create_session(session_id, doc)

    return jsonify(
        {
            "session_id": session_id,
            "summary": summary,
            "questions": questions,
        }
    )


@app.route("/generate", methods=["POST"])
def generate_prep_sheet():
    payload = request.get_json(force=True, silent=True) or {}
    session_id = payload.get("session_id") or str(uuid.uuid4())
    patient_info = payload.get("patient_info", {})
    summary = payload.get("summary", "")
    followup_answers = payload.get("answers", [])
    language = payload.get("language", "en")
    consent = bool(payload.get("consent", False))

    valid, message = _validate_patient_info(patient_info)
    if not valid:
        return jsonify({"error": message}), 400
    if not summary:
        return jsonify({"error": "summary is required"}), 400

    template = PROMPT_ENV.get_template("generate.txt")
    prompt = template.render(
        summary=summary,
        followup_answers=json.dumps(followup_answers, ensure_ascii=False),
        patient_info=json.dumps(patient_info, ensure_ascii=False),
        language=language,
    )

    llm_response = llm.call_gemini(prompt, mode="generate")
    prep_html = llm_response.get("prep_sheet_html", "<p>No data</p>")
    prep_text = llm_response.get("prep_sheet_text", "")

    pdf_bytes = None
    pdf_url = None
    try:
        pdf_bytes = pdf.html_to_pdf_bytes(prep_html)
        if GCS_BUCKET:
            pdf_url = storage.upload_pdf(
                GCS_BUCKET, f"prep-sheets/{session_id}.pdf", pdf_bytes
            )
    except Exception as exc:  # pragma: no cover - optional feature
        app.logger.warning("PDF generation failed: %s", exc)

    if consent:
        db.update_session_answers(
            session_id=session_id,
            answers=followup_answers,
            final_html=prep_html,
            pdf_url=pdf_url,
        )

    response = {
        "session_id": session_id,
        "prep_sheet_html": prep_html,
        "prep_sheet_text": prep_text,
        "pdf_url": pdf_url,
    }
    if pdf_bytes:
        response["pdf_base64"] = base64.b64encode(pdf_bytes).decode("utf-8")

    return jsonify(response)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)


