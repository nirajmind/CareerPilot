import streamlit as st
import json
import os

RESOURCE_PATH = os.path.join("app", "resources", "learning_links.json")
with open(RESOURCE_PATH, "r") as f:
    RESOURCE_LINKS = json.load(f)

def enrich_next_steps(steps):
    enriched = []
    for step in steps:
        updated = step
        for keyword, link in RESOURCE_LINKS.items():
            if keyword.lower() in step.lower():
                updated += f" — [Learn {keyword}]({link})"
        enriched.append(updated)
    return enriched

def render_next_steps_section(result):
    st.subheader("Next Steps")

    steps = enrich_next_steps(result["next_steps"])

    for step in steps:
        st.markdown(f"- {step}", unsafe_allow_html=True)
