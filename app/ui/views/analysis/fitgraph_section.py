import streamlit as st
from components.fitgraph_chart import render_fitgraph_radar

def render_fitgraph_section(result):
    st.subheader("FitGraph Radar Chart")
    fig = render_fitgraph_radar(result["fitgraph"])
    st.plotly_chart(fig, use_container_width=True)
    st.metric("Match Score", f"{result['fitgraph']['match_score']}%")