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

def render_resume_page():
    st.header("Upload or Paste Your Resume")

    # File upload section
    st.subheader("Upload Resume File (PDF, DOCX, TXT)")
    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx", "txt"])

    if uploaded_file:
        extracted = extract_text_from_file(uploaded_file)

        if extracted.strip():
            st.text_area("Extracted Resume Text", extracted, height=300)
            if st.button("Use Extracted Resume"):
                st.session_state["resume_text"] = extracted
                st.success("Resume text saved from uploaded file")
        else:
            st.error("Could not extract text from this file")

    # Manual paste section
    st.subheader("Or Paste Resume Text Manually")
    resume_text = st.text_area(
        "Paste your resume text here",
        height=300,
        value=st.session_state.get("resume_text", "")
    )

    if st.button("Save Resume"):
        if resume_text.strip():
            st.session_state["resume_text"] = resume_text
            st.success("Resume saved successfully")
        else:
            st.error("Please paste your resume text")