import io
import zipfile
from typing import Any

import dash
from dash import Input, Output, callback, ctx, dash_table, dcc, html

from dashboard.db import get_sessions, session_map
from dashboard.styles import TABLE_STYLE

dash.register_page(__name__, path="/session")

session_options = [
    {"label":
        f"{row['name']} — {row['session_id'][:8]}... — {row['start_time']}",
     "value": row["session_id"]}
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
    html.Button("download report", id="generate-report-btn",
        style={
            "marginBottom": "20px",
            "backgroundColor": "#0a0a0a",
            "color": "#a78bfa",
            "border": "1px solid #2a1a3e",
            "padding": "8px 16px",
            "cursor": "pointer",
            "letterSpacing": "0.08em",
            "fontWeight": "300"
        }
    ),
    dcc.Download(id="download-report"),
    html.Div(id="report-status"),
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
    """Load session."""
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


@callback(
    Output("download-report", "data"),
    Output("report-status", "children"),
    Input("generate-report-btn", "n_clicks"),
    Input("session-dropdown", "value"),
    prevent_initial_call=True
)
def download_report(n_clicks, session_id):
    """Download report."""
    if ctx.triggered_id != "generate-report-btn":
        return None, ""
    if not session_id:
        return None, html.P("select a session first.",
                            style={"color": "#b07090"})

    tables = {name: fn(session_id) for name, fn in session_map.items()}

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, df in tables.items():
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            zf.writestr(f"{name}.csv", csv_buffer.getvalue())

    zip_buffer.seek(0)
    return dcc.send_bytes(zip_buffer.read(),
                          f"session_{session_id[:8]}.zip"), ""
