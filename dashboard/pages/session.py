from typing import Any

import dash
from dash import dash_table, html, dcc, callback, Input, Output
from dashboard.db import get_sessions, session_map
from dashboard.styles import TABLE_STYLE

dash.register_page(__name__, path="/session")

session_options = [
    {"label": f"{row['name']} — {row['session_id'][:8]}... — {row['start_time']} ", "value": row["session_id"]}
    for _, row in get_sessions().iterrows()
]

layout = html.Div([
    dcc.Location(id="url"),
    html.H1("session detail"),
    dcc.Dropdown(
        id="session-dropdown",
        options=session_options,
        placeholder="Select a session...",
        style={"marginBottom": "20px", "color": "black"}
    ),
    html.Div(id="session-content")
])


@callback(
    Output("session-dropdown", "value"),
    Input("url", "search")
)
def set_from_url(search) -> Any:
    if search and "id=" in search:
        return search.split("id=")[-1]
    return None


@callback(
    Output("session-content", "children"),
    Input("session-dropdown", "value")
)
def load_session(session_id) -> html.P:
    if not session_id:
        return html.P("Select a session to view details.")
    
    tables = {name: fn(session_id) for name, fn in session_map.items()}

    return html.Div([
        *[
            html.Div([
                html.H3(name),
                dash_table.DataTable(
                    id=f"{name.lower()}-table",
                    data=df.to_dict("records"),
                    columns=[{"name": c, "id": c} for c in df.columns],
                    page_size=20,
                    sort_action="native",
                    filter_action="native",
                    **TABLE_STYLE
                ),
                html.Hr()
            ], style={"marginBottom": "40px"})
            for name, df in tables.items()
        ]
    ])