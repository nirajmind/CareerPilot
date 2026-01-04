import plotly.graph_objects as go

def render_fitgraph_radar(fitgraph: dict):
    categories = [
        "Matching Skills",
        "Missing Skills",
        "Growth Potential",
        "Risk Areas"
    ]

    values = [
        len(fitgraph.get("matching_skills", [])),
        len(fitgraph.get("missing_skills", [])),
        len(fitgraph.get("growth_potential", [])),
        len(fitgraph.get("risk_areas", [])),
    ]

    # Close the loop for radar chart
    values += values[:1]
    categories += categories[:1]

    fig = go.Figure(
        data=[
            go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name='FitGraph'
            )
        ]
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, max(values) + 1])
        ),
        showlegend=False,
        title="FitGraph Radar Chart"
    )

    return fig