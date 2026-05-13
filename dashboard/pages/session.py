import logging

import dash
from dash import Input, Output, callback, dash_table, dcc, html

from dashboard.components.functions import download_report
from dashboard.components.session_download import (
    ButtonModel,
    get_session_options,
    register_session_callbacks,
    session_dropdown,
)
from dashboard.db import session_map
from dashboard.styles import TABLE_STYLE

logger = logging.getLogger(__name__)

dash.register_page(__name__, path="/session")


SESSION_TEMPLATE = "{session_id}... ({name})"

register_session_callbacks(
    dropdown_id="session-dropdown",
    button_container_id="session-buttons",
    buttons=[
        ButtonModel(
            id="session-download-btn",
            text="Download",
            func=download_report,
            output_id="session-download",
            extra_state_ids=[]
        ),
    ]
)


def layout(id=None, **kwargs):
    options = get_session_options(SESSION_TEMPLATE)
    return html.Div([
        session_dropdown(options, id="session-dropdown", value=id),
        dcc.Location(id="session-url"),
        html.Div(id="session-buttons"),
        dcc.Download(id="session-download"),
        html.Div(id="session-content"),
    ])


@callback(
    Output("session-content", "children"),
    Input("session-dropdown", "value"),
    prevent_initial_call=False
)
def load_session(session_id) -> html.P:
    """Load session."""
    logger.error(f"LOAD SESSION: {session_id}")
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
