import logging

import dash
import dash_bootstrap_components as dbc
from dash import (
    ALL,
    Input,
    Output,
    State,
    callback,
    ctx,
    dash_table,
    dcc,
    html,
)

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
        dcc.Store(id="cell-click-store"),
            dbc.Modal([
                dbc.ModalHeader(close_button=True),
                dbc.ModalBody(id="cell-modal-body"),
            ], id="cell-modal", is_open=False),
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
    if not session_id:
        return None

    tables = {name: fn(session_id) for name, fn in session_map.items()}

    return html.Div([
        *[
            html.Div([
                html.H3(name),
                dash_table.DataTable(
                    id={"type": "session-table", "index": name.lower()},
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
    Output("cell-modal", "is_open", allow_duplicate=True),
    Output("cell-modal-body", "children", allow_duplicate=True),
    Input({"type": "session-table", "index": ALL}, "active_cell"),
    State({"type": "session-table", "index": ALL}, "derived_virtual_data"),
    prevent_initial_call=True
)
def show_cell(active_cells, all_data):
    triggered = ctx.triggered_id
    if not triggered:
        return False, None
    idx = list(session_map.keys()).index(triggered["index"])
    active_cell = active_cells[idx]
    data = all_data[idx]
    if not active_cell or not data:
        return False, None
    value = data[active_cell["row"]][active_cell["column_id"]]
    return True, str(value)
