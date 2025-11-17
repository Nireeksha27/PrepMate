
import streamlit as st
import uuid
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import os

# Import helper modules
from mcp import llm, db, pdf, storage

# --- Configuration --- #
# TODO: Replace with your actual GCS bucket name if using PDF upload
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "your-gcs-bucket-name")

# Setup Jinja2 environment
env = Environment(loader=FileSystemLoader("templates"))

def load_prompt_file(prompt_name: str) -> str:
    with open(f"prompts/{prompt_name}", "r") as f:
        return f.read()

# --- Streamlit UI Components & Logic ---
def validate_patient_info(name, age, gender, allergies, medications):
    if not name:
        st.error("Name is required.")
        return False
    if not age or not (1 <= int(age) <= 120):
        st.error("Age is required and must be between 1 and 120.")
        return False
    if not gender:
        st.error("Gender is required.")
        return False
    return True

def main():
    st.set_page_config(page_title="PrepMate", layout="centered")
    st.title("🩺 PrepMate - Doctor Visit Preparation")

    # Initialize session state
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.step = 1
        st.session_state.patient_info = {}
        st.session_state.initial_input_text = ""
        st.session_state.ai_summary = ""
        st.session_state.followup_data = {"questions": {}, "answers": {}}
        st.session_state.final_output_html = ""
        st.session_state.consent_given = False
        st.session_state.language_code = "en-US"
        # Load prompts once and store in session state
        st.session_state.suggest_prompt_template = load_prompt_file("suggest.txt")
        st.session_state.generate_prompt_template = load_prompt_file("generate.txt")

    # --- Step 1: Patient Information and Consent ---
    if st.session_state.step == 1:
        st.header("1. Patient Information and Consent")
        with st.form("patient_info_form"):
            name = st.text_input("Name")
            age = st.number_input("Age", min_value=1, max_value=120, format="%d")
            gender = st.selectbox("Gender", ["", "Male", "Female", "Other", "Prefer not to say"])
            allergies = st.text_area("Allergies (e.g., Penicillin, Peanuts)")
            medications = st.text_area("Current Medications (e.g., Ibuprofen, Insulin)")
            
            st.markdown("---")
            st.subheader("Data Usage Consent")
            st.write("By proceeding, you consent to PrepMate using the information provided to generate a preparation sheet for your doctor's visit. Your data will be stored securely for this purpose. You can choose to download a PDF, which may be uploaded to cloud storage.")
            consent_given = st.checkbox("I understand and consent to my data being used and stored as described.")

            submitted = st.form_submit_button("Next")

            if submitted:
                if validate_patient_info(name, age, gender, allergies, medications) and consent_given:
                    st.session_state.patient_info = {
                        "name": name,
                        "age": age,
                        "gender": gender,
                        "allergies": allergies,
                        "medications": medications,
                    }
                    st.session_state.consent_given = consent_given
                    st.session_state.created_at = datetime.now().isoformat()

                    # Create session in Firestore
                    if consent_given:
                        doc = {
                            "id": st.session_state.session_id,
                            "created_at": st.session_state.created_at,
                            "patient_info": st.session_state.patient_info,
                            "language_code": st.session_state.language_code,
                            "initial_input_text": "", # Will be updated in next step
                            "ai_summary": "",
                            "followup_data": {"questions": {}, "answers": {}}
                        }
                        db.create_session(st.session_state.session_id, doc)

                    st.session_state.step = 2
                    st.experimental_rerun()
                elif not consent_given:
                    st.error("You must give consent to proceed.")

    # --- Step 2: Symptom Description and Gemini Call ---
    elif st.session_state.step == 2:
        st.header("2. Describe Your Symptoms")
        symptom_description = st.text_area("Tell me about your symptoms in one line:", height=100)

        if st.button("Get Summary & Questions"):
            if symptom_description:
                st.session_state.initial_input_text = symptom_description
                # Prepare prompt for Gemini
                prompt = st.session_state.suggest_prompt_template.format(
                    name=st.session_state.patient_info["name"],
                    age=st.session_state.patient_info["age"],
                    gender=st.session_state.patient_info["gender"],
                    allergies=st.session_state.patient_info["allergies"],
                    medications=st.session_state.patient_info["medications"],
                    symptom_description=st.session_state.initial_input_text
                )

                with st.spinner("Generating summary and questions..."):
                    gemini_response = llm.call_gemini(prompt)

                # Parse Gemini response
                # Expected format: Summary: <summary>\nQuestions: <Q1>_input|<Q2>_input
                try:
                    summary_part, questions_part = gemini_response.split("\nQuestions:", 1)
                    st.session_state.ai_summary = summary_part.replace("Summary:", "").strip()
                    question_strings = [q.strip() for q in questions_part.split("|") if q.strip()]
                    st.session_state.followup_data["questions"] = {q.replace("_input", ""): "" for q in question_strings}
                except ValueError:
                    st.error("Failed to parse Gemini response. Please try again.")
                    st.session_state.ai_summary = gemini_response # Fallback
                    st.session_state.followup_data["questions"] = {}
                
                # Update initial_input_text in Firestore
                if st.session_state.consent_given:
                    doc_update = {"initial_input_text": st.session_state.initial_input_text}
                    # TODO: db.update_session_partial(st.session_state.session_id, doc_update) if partial updates were available
                    # For now, we will update in the final step with all data.

                st.session_state.step = 3
                st.experimental_rerun()
            else:
                st.error("Please describe your symptoms.")

    # --- Step 3: Show Summary & Follow-up Questions ---
    elif st.session_state.step == 3:
        st.header("3. Review Summary and Answer Follow-up Questions")
        
        st.subheader("Your Symptom Summary (editable)")
        st.session_state.ai_summary = st.text_area("Summary", value=st.session_state.ai_summary, height=150)

        st.subheader("Clarifying Questions")
        with st.form("followup_form"):
            answered_questions = {}
            for q_key in st.session_state.followup_data["questions"]:
                answered_questions[q_key] = st.text_input(q_key, value=st.session_state.followup_data["answers"].get(q_key, ""))
            
            generate_button = st.form_submit_button("Generate Prep Sheet")

            if generate_button:
                st.session_state.followup_data["answers"] = answered_questions
                st.session_state.step = 4
                st.experimental_rerun()

    # --- Step 4: Generate Prep Sheet and Download PDF ---
    elif st.session_state.step == 4:
        st.header("4. Your Doctor Visit Prep Sheet")

        # Prepare prompt for Gemini to generate the final prep sheet
        prompt = st.session_state.generate_prompt_template.format(
            patient_info=st.session_state.patient_info,
            ai_summary=st.session_state.ai_summary,
            followup_answers=st.session_state.followup_data["answers"],
        )

        with st.spinner("Generating prep sheet..."):
            gemini_response_full = llm.call_gemini(prompt)
        
        # Parse Gemini response for HTML and Plain Text
        html_start = gemini_response_full.find("HTML Prep Sheet:")
        plain_text_start = gemini_response_full.find("Plain Text Prep Sheet:")

        final_html_content = "<p>Error generating HTML prep sheet.</p>"
        plain_text_content = "Error generating plain text prep sheet."

        if html_start != -1 and plain_text_start != -1:
            final_html_content = gemini_response_full[html_start + len("HTML Prep Sheet:"):plain_text_start].strip()
            plain_text_content = gemini_response_full[plain_text_start + len("Plain Text Prep Sheet:"):].strip()
        elif html_start != -1:
            final_html_content = gemini_response_full[html_start + len("HTML Prep Sheet:"):].strip()
        elif plain_text_start != -1:
            plain_text_content = gemini_response_full[plain_text_start + len("Plain Text Prep Sheet:"):].strip()
        else:
            # Fallback if parsing fails, show raw response
            st.warning("Could not parse HTML and Plain Text from Gemini. Displaying raw response.")
            plain_text_content = gemini_response_full
            final_html_content = f"<pre>{gemini_response_full}</pre>"

        st.session_state.final_output_html = final_html_content

        # Render HTML prep sheet (using components.html for full control)
        st.subheader("Generated Prep Sheet")
        st.components.v1.html(final_html_content, height=600, scrolling=True)

        st.subheader("Plain Text Version")
        st.text_area("", value=plain_text_content, height=300)

        # Generate and Download PDF
        st.subheader("Download Options")
        if st.button("Download PDF"):
            try:
                # Render the Jinja2 template with dynamic data
                template = env.get_template("prepsheet.html")
                rendered_html = template.render(
                    patient_info=st.session_state.patient_info,
                    ai_summary=st.session_state.ai_summary,
                    followup_answers=st.session_state.followup_data["answers"]
                )

                pdf_bytes = pdf.html_to_pdf_bytes(rendered_html)
                pdf_filename = f"prepmate_prep_sheet_{st.session_state.session_id}.pdf"
                
                # Optional: Upload to GCS
                pdf_url = None
                # TODO: Uncomment and configure GCS_BUCKET_NAME for PDF upload
                # if GCS_BUCKET_NAME != "your-gcs-bucket-name": # Check if bucket name is configured
                #     pdf_url = storage.upload_pdf(GCS_BUCKET_NAME, pdf_filename, pdf_bytes)
                #     st.success(f"PDF uploaded to: {pdf_url}")

                st.download_button(
                    label="Click to Download",
                    data=pdf_bytes,
                    file_name=pdf_filename,
                    mime="application/pdf"
                )

                # Update session in Firestore with final data and PDF URL
                if st.session_state.consent_given:
                    db.update_session_answers(
                        st.session_state.session_id,
                        st.session_state.followup_data["answers"],
                        st.session_state.final_output_html,
                        pdf_url
                    )

            except Exception as e:
                st.error(f"Error generating or downloading PDF: {e}")

        if st.button("Start Over"):
            st.session_state.clear()
            st.experimental_rerun()

    # --- Safety Guardrails & Disclaimer (always visible) ---
    st.markdown("---")
    st.warning("Disclaimer: PrepMate is an AI assistant for informational purposes only and does not provide medical advice. Always consult a qualified healthcare professional for medical concerns.")

if __name__ == "__main__":
    main()
