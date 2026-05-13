"""Reusable session selection and download component."""

import logging
from typing import Callable, List

from dash import Input, Output, State, callback, dcc, html
from pydantic import BaseModel

from dashboard.db import get_sessions

logger = logging.getLogger(__name__)
class ButtonModel(BaseModel):
    id: str
    text: str
    func: Callable
    output_id: str
    extra_state_ids: List[str] = []

    class Config:
        arbitrary_types_allowed = True


def get_session_options(label_template: str):
    sessions_df = get_sessions()
    session_options = [
        {
            "label": label_template.format(
                session_id=str(row['session_id'])[:8],
                name=row['name'],
            ),
            "value": row["session_id"]
        } for _, row in sessions_df.iterrows()
    ]
    return session_options


def session_dropdown(options,
                     id="session-dropdown",
                     value=None) -> dcc.Dropdown:
    return dcc.Dropdown(
        id=id,
        options=options,
        value=value,
        placeholder="Select a session...",
        className="session-dropdown",
        clearable=False
    )



def register_session_callbacks(
    dropdown_id,
    button_container_id,
    buttons: List[ButtonModel],
):
    @callback(
        Output(button_container_id, "children", allow_duplicate=True),
        Input(dropdown_id, "value"),
        prevent_initial_call=True
    )
    def show_buttons(session_id) -> list:
        if not session_id:
            return None
        return [html.Button(b.text, id=b.id,
                            className='download-btn') for b in buttons]

    for b in buttons:
        extra_states = [State(sid, "data") for sid in b.extra_state_ids]

        @callback(
            Output(b.output_id, "data", allow_duplicate=True),
            Input(b.id, "n_clicks"),
            State(dropdown_id, "value"),
            *extra_states,
            prevent_initial_call=True
        )
        def handle_click(*args, func=b.func) -> Callable:
            n_clicks = args[0]
            if not n_clicks:
                return
            session_id = args[1]
            extra_args = args[2:]
            return func(session_id, *extra_args)

