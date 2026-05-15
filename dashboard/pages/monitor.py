"""Monitor."""

import ast
import json

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dash_table, dcc, html

from dashboard.components.session_download import session_dropdown
from dashboard.styles import TABLE_STYLE
from dashboard.utils.observer_utils import get_sessions, redis_sync

dash.register_page(__name__, path="/monitor")


layout = html.Div([
    dcc.Interval(id='session-poll', interval=5000),
    dbc.Modal([dbc.ModalBody(id="cell-modal-body")],
              id="cell-modal",
              is_open=False),
    session_dropdown(
        options=get_sessions(),
        id='observer-session-dropdown'),
        html.A("Open Session",
                id="open-session-btn",
                target="_blank",
                href="#",
                className="btn btn-primary",
                style={"display": "none"}),
        html.Div(id="session-table-wrapper",
                 style={"display": "none"}, children=[
            dash_table.DataTable(
                id="session-table",
                columns=[{"name": "Key", "id": "key"},
                        {"name": "Value", "id": "value"}],
                data=[],
                **TABLE_STYLE)],
        )])


@callback(
    Output("open-session-btn", "style"),
    Input("observer-session-dropdown", "value"),
)
def show_button(session_id):
    if not session_id:
        return {"display": "none"}
    return {"display": "inline-block"}


@callback(
    Output("observer-session-dropdown", "options"),
    Input("session-poll", "n_intervals"),
)
def update_sessions(_):
    return get_sessions()


@callback(
    Output("open-session-btn", "href"),
    Input("observer-session-dropdown", "value"),
)
def set_session_link(session_id):
    if not session_id:
        return "#"
    return f"/session-view?session_id={session_id}"


@callback(
    Output("session-table", "data"),
    Output("session-table-wrapper", "style"),
    Input("session-poll", "n_intervals"),
    State("observer-session-dropdown", "value"),
    prevent_initial_call=True
)
def get_state(_, session_id: str) -> list:
    """Get current graph state."""
    if not session_id:
        return dash.no_update, {"display": "none"}
    data = redis_sync.get(f"observer:session:{session_id}:graph")
    if not data:
        return dash.no_update, {"display": "none"}
    data = json.loads(data)
    last_action = {"key": "last_action",
                   "value": str(data["actions"][-1])}
    state_list = [
        {"key": k,
         "value": str(v)} for k, v in data.items()]
    state_list.append(last_action)
    return state_list, {"display": "block"}


def format_value(value: str) -> html.Pre:
    try:
        parsed = ast.literal_eval(value)
        text = json.dumps(parsed, indent=2, ensure_ascii=False)
    except Exception:
        text = value
    return html.Pre(text, style={"whiteSpace": "pre-wrap",
                                 "wordBreak": "break-word"})


@callback(
    Output("cell-modal", "is_open", allow_duplicate=True),
    Output("cell-modal-body", "children", allow_duplicate=True),
    Input("session-table", "active_cell"),
    State("session-table", "derived_virtual_data"),
    prevent_initial_call=True
)
def show_cell(active_cell, data):
    if not active_cell or not data:
        return False, None
    row = data[active_cell["row"]]
    value = row[active_cell["column_id"]]
    return True, format_value(str(value))
