import dash
import plotly.express as px
from dash import dcc, html
import dash_bootstrap_components as dbc
from dashboard.db import personas_map
from dashboard.styles import PLOTLY_LAYOUT

dash.register_page(__name__, path="/personas")

data = {name: fn() for name, fn in personas_map.items()}

world_fig = px.choropleth(
    data["world_map"], locations="country",
    locationmode="country names",
    color="count",
    title="personas by country",
    template="plotly_dark",
    color_continuous_scale="Purples"
)
world_fig.update_layout(
    **PLOTLY_LAYOUT,
    height=500,
    margin={"r": 0, "t": 40, "l": 0, "b": 0},
    geo=dict(
        bgcolor="#000000",
        lakecolor="#000000",
        landcolor="#1a1a1a",
        showframe=False,
        showcoastlines=True,
        coastlinecolor="#333333",
    )
)

archetype_fig = px.bar(
    data["archetypes"], x="count", y="archetype",
    orientation="h",
    title="archetype distribution",
    template="plotly_dark"
).update_layout(**PLOTLY_LAYOUT)

social_fig = px.pie(
    data["social_tendency"], names="social_tendency", values="count",
    title="social tendency",
    template="plotly_dark"
)
social_fig.update_layout(**PLOTLY_LAYOUT)

generation_fig = px.bar(
    data["generations"], x="generation", y="count",
    title="generation distribution",
    template="plotly_dark",
    category_orders={"generation": ["Boomer", "Gen X", "Millennial", "Gen Z"]}
)
generation_fig.update_layout(**PLOTLY_LAYOUT)

layout = html.Div([
    html.H1("personas", className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(figure=world_fig, config={"responsive": True}, style={"width": "100%"}), width=12, style={"padding": "0", "margin": "0"}),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(figure=archetype_fig), width=6),
        dbc.Col(dcc.Graph(figure=social_fig), width=3),
        dbc.Col(dcc.Graph(figure=generation_fig), width=3),
    ]),
])
