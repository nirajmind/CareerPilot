import streamlit as st
import pandas as pd

def normalize_columns(data: dict):
    max_len = max(len(v) for v in data.values())
    return {k: v + [""] * (max_len - len(v)) for k, v in data.items()}

def render_skill_matrix_section(result):
    st.subheader("Skill Matrix")

    skill_data = {
        "Strengths": result["skill_matrix"]["strengths"],
        "Gaps": result["skill_matrix"]["gaps"],
        "Emerging": result["skill_matrix"]["emerging"]
    }

    df = pd.DataFrame(normalize_columns(skill_data))
    st.table(df)