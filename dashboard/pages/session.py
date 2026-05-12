from typing import Any

import dash
from dash import Input, Output, callback, dash_table, dcc, html

from dashboard.components.session_download import (
    create_session_download_layout,
    get_session_options,
    register_session_download_callbacks,
)
from dashboard.db import session_map
from dashboard.styles import TABLE_STYLE

dash.register_page(__name__, path="/session")

session_options = get_session_options("{name} — {session_id}... ")

layout = html.Div([
    dcc.Location(id="url"),
    *create_session_download_layout(
        session_options=session_options,
        id_prefix="session_",  # Add unique prefix
        button_text="Download Report",
        button_class="download-btn"
    ),
    html.Div(id="report-status"),
    html.Div(id="session-content")
])

register_session_download_callbacks(
    id_prefix="session_",  # Must match layout prefix
    button_text="Download Report",
    button_class="download-btn",
    download_type="zip",
    session_map_func=session_map
)


@callback(
    Output("session_session-dropdown", "value"),  # Changed to use prefixed ID
    Input("url", "search")
)
def set_from_url(search) -> Any:
    if search and "id=" in search:
        return search.split("id=")[-1]
    return None


@callback(
    Output("session-content", "children"),
    Input("session_session-dropdown", "value")  # Changed to use prefixed ID
)
def load_session(session_id) -> html.P:
    """Load session."""
    if not session_id:
        return None

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