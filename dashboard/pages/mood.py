"""Mood."""

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html

from dashboard.db import mood_map
from dashboard.styles import MOOD_COLORS, PLOTLY_LAYOUT

dash.register_page(__name__, path="/mood")

data = {name: fn() for name, fn in mood_map.items()}

# Sankey
sankey_df = data["sankey"]
sankey_df["pair"] = sankey_df.apply(
    lambda r: tuple(sorted([r["mood_before"], r["mood_after"]])), axis=1
)
sankey_df = sankey_df.groupby("pair", as_index=False)["count"].sum()
sankey_df["mood_before"] = sankey_df["pair"].apply(lambda x: x[0])
sankey_df["mood_after"] = sankey_df["pair"].apply(lambda x: x[1])

all_moods = list(pd.Series(
    sankey_df["mood_before"].tolist() + sankey_df["mood_after"].tolist()
).unique())
mood_index = {m: i for i, m in enumerate(all_moods)}

def hex_to_rgba(hex_color, alpha=0.4) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

link_colors = [hex_to_rgba(MOOD_COLORS.get(m, "#888888"))
               for m in sankey_df["mood_before"]]


sankey_fig = go.Figure(go.Sankey(
    node=dict(
        label=all_moods,
        color= [MOOD_COLORS.get(m, "#888") for m in all_moods],
        pad=40,
        thickness=20,
    ),
    link=dict(
        source=sankey_df["mood_before"].map(mood_index).tolist(),
        target=sankey_df["mood_after"].map(mood_index).tolist(),
        value=sankey_df["count"].tolist(),
        color=link_colors,

    )
))
sankey_fig.update_layout(**PLOTLY_LAYOUT)

# Shift counts
shift_fig = px.bar(
    data["shift_counts"], x="mood", y="shifts_into",
    title="most shifted-into moods",
    template="plotly_dark"
)
shift_fig.update_layout(**PLOTLY_LAYOUT)

# Timeline by archetype
timeline_fig = px.line(
    data["timeline_by_archetype"], x="timestamp", y="mood",
    color="archetype",
    title="mood over time by archetype",
    template="plotly_dark",
    markers=True
)
timeline_fig.update_layout(**PLOTLY_LAYOUT)

layout = html.Div([
    html.H1("mood", className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(figure=sankey_fig), width=8),
        dbc.Col(dcc.Graph(figure=shift_fig), width=4),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(figure=timeline_fig), width=12),
    ]),
])

