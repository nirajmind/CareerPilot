import streamlit as st
import pdfplumber
import docx

def extract_text_from_file(file):
    if file.type == "application/pdf":
        with pdfplumber.open(file) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)

    elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = docx.Document(file)
        return "\n".join(p.text for p in doc.paragraphs)

    elif file.type == "text/plain":
        return file.read().decode("utf-8")

    return ""


def render_jd_page():
    st.header("Upload or Paste Job Description")

    # File upload section
    st.subheader("Upload JD File (PDF, DOCX, TXT)")
    uploaded_file = st.file_uploader("Choose a JD file", type=["pdf", "docx", "txt"])

    if uploaded_file:
        extracted = extract_text_from_file(uploaded_file)

        if extracted.strip():
            st.text_area("Extracted JD Text", extracted, height=300)
            if st.button("Use Extracted JD"):
                st.session_state["jd_text"] = extracted
                st.success("Job description saved from uploaded file")
        else:
            st.error("Could not extract text from this file")

    # Manual paste section
    st.subheader("Or Paste JD Text Manually")
    jd_text = st.text_area(
        "Paste the job description here",
        height=300,
        value=st.session_state.get("jd_text", "")
    )

    if st.button("Save JD"):
        if jd_text.strip():
            st.session_state["jd_text"] = jd_text
            st.success("Job description saved successfully")
        else:
            st.error("Please paste the job description")