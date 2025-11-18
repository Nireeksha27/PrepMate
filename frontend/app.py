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
    st.set_page_config(
        page_title="PrepMate",
        layout="centered",
        initial_sidebar_state="auto",
        menu_items={
            'Get help': 'https://www.extremely.cool/help',
            'Report a bug': "https://www.extremely.cool/bug",
            'About': "# PrepMate is a Streamlit-based web application designed to help patients prepare for doctor visits by generating a personalized prep sheet."
        }
    )

    # Custom CSS for a more attractive and colorful UI
    st.markdown("""
    <style>
    .stApp {
        background-color: #e6f7ff; /* Light blue background */
    }
    .stTextInput>div>div>input,
    .stTextArea>div>div>textarea,
    .stSelectbox>div>div:first-child {
        background-color: #ffffff;
        border: 1px solid #87ceeb; /* Sky blue border */
        border-radius: 5px;
        color: #333333;
        padding: 0.5rem;
    }
    .stButton>button {
        background-color: #4CAF50; /* Green */
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        border: none;
        cursor: pointer;
        font-size: 16px;
        transition: background-color 0.3s;
    }
    .stButton>button:hover {
        background-color: #45a049; /* Darker green on hover */
    }
    h1, h2, h3, h4, h5, h6 {
        color: #0056b3; /* Darker blue for headers */
        font-family: 'Segoe UI', sans-serif;
    }
    .stAlert {
        border-radius: 8px;
        background-color: #fff3cd; /* Light yellow for warnings */
        color: #856404;
        border-color: #ffeeba;
    }
    .stMarkdown p {
        color: #333333;
    }
    .css-1d391kg {
        padding-top: 3.5rem;
        padding-right: 1rem;
        padding-bottom: 3.5rem;
        padding-left: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

    st.container()
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image("https://cdn-icons-png.flaticon.com/512/3063/3063821.png", width=80) # Placeholder for a logo/icon
    with col2:
        st.title("PrepMate – Doctor Visit Prep Sheet")
        st.markdown("<p style=\"color: #555555;\";>Communication aid only. Not medical advice.</p>", unsafe_allow_html=True)

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
    st.info(
        "💡 Disclaimer: PrepMate is for communication support only. "
        "Consult medical professionals for diagnosis or treatment."
    )


def step_patient_info():
    st.header("1. Patient information & consent 📝")
    with st.expander("Enter your details here", expanded=True):
        with st.form("patient_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name *")
                age = st.number_input("Age *", min_value=1, max_value=120, step=1)
            with col2:
                gender = st.selectbox(
                    "Gender *", ["Female", "Male", "Other", "Prefer not to say"]
                )
                allergies = st.text_input("Allergies *", placeholder="Enter 'None' if none")
            medications = st.text_input(
                "Current medications *", placeholder="Enter 'None' if none"
            )
            st.markdown("---")
            st.subheader("Data Usage Consent")
            st.info(
                "By proceeding, you consent to PrepMate using the information provided to generate a preparation sheet for your doctor's visit. Your data will be stored securely for this purpose. You can choose to download a PDF, which may be uploaded to cloud storage."
            )
            consent = st.checkbox(
                "I understand and consent to my data being used and stored as described.",
                value=False,
            )
            submitted = st.form_submit_button("Continue ▶️")

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
        
        # Optional: Display a success message for patient info
        st.success("Patient information saved successfully! Proceed to symptom description.")
        st.session_state.step = 2
        st.experimental_rerun()


def step_symptom_input():
    st.header("2. Describe your symptoms 🗣️")
    with st.expander("Tell us what you're experiencing", expanded=True):
        symptom = st.text_area(
            "Explain what you're experiencing in one or two sentences.",
            height=120,
        )
        language = st.selectbox("Language", ["en", "hi", "kn"], index=0)
    if st.button("Generate summary & questions ✨"):
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
            with st.spinner("Generating... please wait."):
                data = post_json("/suggest", payload)
            st.success("Summary and questions generated successfully!")
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
    st.header("3. Review summary & answer quick questions 🧐")
    
    st.subheader("Your Symptom Summary (editable)")
    st.session_state.summary = st.text_area(
        "Summary", value=st.session_state.summary, height=120
    )

    st.subheader("Clarifying questions")
    with st.expander("Answer your doctor's follow-up questions", expanded=True):
        with st.form("followup_form"):
            answered_questions = {}
            num_questions = len(st.session_state.questions)
            cols_per_row = 2 # Number of columns for questions

            for i, question in enumerate(st.session_state.questions):
                if i % cols_per_row == 0:
                    cols = st.columns(cols_per_row)
                
                qid = question.get("id") or question.get("label")
                label = question.get("label", "Question")
                qtype = question.get("type", "text")
                key = f"answer_{qid}"

                with cols[i % cols_per_row]:
                    if qtype == "choice":
                        options = question.get("options") or ["Yes", "No"]
                        answered_questions[qid] = st.selectbox(
                            label, options, key=key, index=0
                        )
                    elif qtype == "scale":
                        min_val = question.get("min", 1)
                        max_val = question.get("max", 10)
                        answered_questions[qid] = st.slider(
                            label,
                            min_value=min_val,
                            max_value=max_val,
                            value=(min_val + max_val) // 2,
                            key=key,
                        )
                    else:
                        answered_questions[qid] = st.text_input(
                            label, key=key, value=st.session_state.answers.get(qid, "")
                        )
            
            generate_button = st.form_submit_button("Generate prep sheet 📄")

            if generate_button:
                st.session_state.answers = answered_questions
                st.success("Answers saved. Generating your prep sheet...")

                # Prepare answers in the format expected by the backend
                formatted_answers = [
                    {
                        "id": q.get("id") or q.get("label"),
                        "label": q.get("label", "Question"),
                        "answer": answered_questions.get(q.get("id") or q.get("label"), ""),
                    }
                    for q in st.session_state.questions
                ]

                payload = {
                    "session_id": st.session_state.session_id,
                    "patient_info": st.session_state.patient_info,
                    "summary": st.session_state.summary,
                    "answers": formatted_answers, # Use the formatted answers
                    "language": st.session_state.language,
                    "consent": st.session_state.consent,
                }
                try:
                    with st.spinner("Finalizing prep sheet..."):
                        data = post_json("/generate", payload)
                    st.success("Prep sheet generated successfully!")
                except Exception as exc:
                    st.error(f"Backend error: {exc}")
                    return
                st.session_state.prep_sheet_html = data.get("prep_sheet_html", "")
                st.session_state.prep_sheet_text = data.get("prep_sheet_text", "")
                st.session_state.pdf_base64 = data.get("pdf_base64", "")
                st.session_state.step = 4
                st.experimental_rerun()

    if st.button("Back to Symptom Description ◀️"):
        st.session_state.step = 2
        st.experimental_rerun()


def step_prep_sheet():
    st.header("4. Prep sheet ready! ✅")
    
    st.markdown("### Your Generated Prep Sheet")
    st.components.v1.html(
        st.session_state.prep_sheet_html or "<p>No content</p>",
        height=600,
        scrolling=True,
    )

    with st.expander("View Plain Text Version", expanded=False):
        st.text_area(
            label="",
            value=st.session_state.prep_sheet_text,
            height=200,
        )

    if st.session_state.pdf_base64:
        pdf_bytes = base64.b64decode(st.session_state.pdf_base64)
        st.download_button(
            "Download PDF ⬇️",
            data=pdf_bytes,
            file_name=f"prep_{st.session_state.session_id}.pdf",
            mime="application/pdf",
        )

    if st.button("Start over 🔄"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.experimental_rerun()


if __name__ == "__main__":
    main()


