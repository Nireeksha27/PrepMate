import base64
import os

import requests
import streamlit as st

API_BASE_URL = os.environ.get("BACKEND_URL", "http://localhost:8080")


def post_json(path: str, payload: dict):
    resp = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def init_state():
    defaults = {
        "step": 1,
        "patient_info": {},
        "consent": False,
        "session_id": "",
        "summary": "",
        "questions": [],
        "answers": {},
        "prep_sheet_html": "",
        "prep_sheet_text": "",
        "pdf_base64": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def main():
    st.set_page_config(page_title="PrepMate", layout="centered")
    st.title("🩺 PrepMate – Doctor Visit Prep Sheet")
    st.caption("Communication aid only. Not medical advice.")

    init_state()

    if st.session_state.step == 1:
        step_patient_info()
    elif st.session_state.step == 2:
        step_symptom_input()
    elif st.session_state.step == 3:
        step_followups()
    elif st.session_state.step == 4:
        step_prep_sheet()

    st.write("---")
    st.warning(
        "Disclaimer: PrepMate is for communication support only. "
        "Consult medical professionals for diagnosis or treatment."
    )


def step_patient_info():
    st.header("1. Patient information & consent")
    with st.form("patient_form"):
        name = st.text_input("Full Name *")
        age = st.number_input("Age *", min_value=1, max_value=120, step=1)
        gender = st.selectbox(
            "Gender *", ["Female", "Male", "Other", "Prefer not to say"]
        )
        allergies = st.text_input("Allergies *", placeholder="Enter 'None' if none")
        medications = st.text_input(
            "Current medications *", placeholder="Enter 'None' if none"
        )
        consent = st.checkbox(
            "I consent to use this information to generate/store a prep sheet.",
            value=False,
        )
        submitted = st.form_submit_button("Continue")

    if submitted:
        if not (name and allergies and medications and consent):
            st.error("All required fields must be filled and consent must be granted.")
            return
        st.session_state.patient_info = {
            "name": name.strip(),
            "age": int(age),
            "gender": gender,
            "allergies": allergies.strip(),
            "medications": medications.strip(),
        }
        st.session_state.consent = consent
        st.session_state.step = 2
        st.experimental_rerun()


def step_symptom_input():
    st.header("2. Describe your symptoms")
    symptom = st.text_area(
        "Explain what you're experiencing in one or two sentences.",
        height=120,
    )
    language = st.selectbox("Language", ["en", "hi", "kn"], index=0)
    if st.button("Generate summary & questions"):
        if not symptom.strip():
            st.error("Please provide a symptom description.")
            return
        payload = {
            "patient_info": st.session_state.patient_info,
            "symptom_description": symptom.strip(),
            "language": language,
            "consent": st.session_state.consent,
        }
        try:
            data = post_json("/suggest", payload)
        except Exception as exc:
            st.error(f"Backend error: {exc}")
            return
        st.session_state.session_id = data["session_id"]
        st.session_state.summary = data["summary"]
        st.session_state.questions = data.get("questions", [])
        st.session_state.answers = {}
        st.session_state.language = language
        st.session_state.step = 3
        st.experimental_rerun()


def step_followups():
    st.header("3. Review summary & answer quick questions")
    st.session_state.summary = st.text_area(
        "Symptom summary (editable)", value=st.session_state.summary, height=120
    )

    st.subheader("Clarifying questions")
    for question in st.session_state.questions:
        qid = question.get("id") or question.get("label")
        label = question.get("label", "Question")
        qtype = question.get("type", "text")
        key = f"answer_{qid}"

        if qtype == "choice":
            options = question.get("options") or ["Yes", "No"]
            st.session_state.answers[qid] = st.selectbox(
                label, options, key=key, index=0
            )
        elif qtype == "scale":
            min_val = question.get("min", 1)
            max_val = question.get("max", 10)
            st.session_state.answers[qid] = st.slider(
                label,
                min_value=min_val,
                max_value=max_val,
                value=(min_val + max_val) // 2,
                key=key,
            )
        else:
            st.session_state.answers[qid] = st.text_input(
                label, key=key, value=st.session_state.answers.get(qid, "")
            )

    if st.button("Generate prep sheet"):
        answers = [
            {
                "id": q.get("id"),
                "label": q.get("label"),
                "answer": st.session_state.answers.get(q.get("id")),
            }
            for q in st.session_state.questions
        ]
        payload = {
            "session_id": st.session_state.session_id,
            "patient_info": st.session_state.patient_info,
            "summary": st.session_state.summary,
            "answers": answers,
            "language": st.session_state.language,
            "consent": st.session_state.consent,
        }
        try:
            data = post_json("/generate", payload)
        except Exception as exc:
            st.error(f"Backend error: {exc}")
            return
        st.session_state.prep_sheet_html = data.get("prep_sheet_html", "")
        st.session_state.prep_sheet_text = data.get("prep_sheet_text", "")
        st.session_state.pdf_base64 = data.get("pdf_base64", "")
        st.session_state.step = 4
        st.experimental_rerun()


def step_prep_sheet():
    st.header("4. Prep sheet ready")
    st.components.v1.html(
        st.session_state.prep_sheet_html or "<p>No content</p>",
        height=600,
        scrolling=True,
    )
    st.subheader("Plain text version")
    st.text_area(
        label="",
        value=st.session_state.prep_sheet_text,
        height=200,
    )

    if st.session_state.pdf_base64:
        pdf_bytes = base64.b64decode(st.session_state.pdf_base64)
        st.download_button(
            "Download PDF",
            data=pdf_bytes,
            file_name=f"prep_{st.session_state.session_id}.pdf",
            mime="application/pdf",
        )

    if st.button("Start over"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.experimental_rerun()


if __name__ == "__main__":
    main()


