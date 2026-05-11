import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html
from dash import clientside_callback

from dashboard.db import get_sessions
from dashboard.utils.story_utils import create_story

dash.register_page(
    __name__,
    path="/story",
)

sessions_df = get_sessions()
session_options = [
    {"label": f"Walker #{str(row['session_id'])[:8]} ({row['name']})",
     "value": row["session_id"]
     } for _, row in sessions_df.iterrows()
     ]


def render_event(event: dict) -> dbc.Card:

    content = []

    if not any([
        event["selection"],
        event["llm_answer"],
        event["reflection"]
    ]):

        content.append(
            html.Div(
                "",
                className="story-event-empty"
            )
        )

    else:
        if event["selection"]:
            content.append(
                html.Div(
                    event["selection"],
                    className="story-event-selection"
                )
            )

        if event["llm_answer"]:
            content.append(
                html.Div(
                    event["llm_answer"],
                    className="story-event-llm-answer"
                )
            )

        if event["text"]:
            content.append(
                html.Div(
                    event["text"],
                    className="story-event-text"
                )
            )

        if event["reflection"]:
            content.append(
                html.Div(
                    event["reflection"],
                    className="story-event-reflection"
                )
            )

    return dbc.Card(
        dbc.CardBody([

            html.Div(
                event["header"],
                className="story-event-header"
            ),

            *content

        ]),
        className="story-event-card"
    )

layout = dbc.Container([
    html.Div(
        [
        dcc.Dropdown(
            id="story-session-dropdown",
            options=session_options,
            placeholder="Select a session...",
            className="story-dropdown",
            clearable=False
        ),
        html.Button("Download PDF", id="story-print-btn",
                    className="download-btn"),

        html.Div(id="story-content")
    ], className="story-shell", id="story-shell")
], fluid=True, className="story-container")


@callback(
    Output("story-content", "children"),
    Input("story-session-dropdown", "value")
)
def load_story(session_id):
    if not session_id:
        session_id='458d5468-4c4f-11f1-86f1-bbc2023f8855'

    story = create_story(session_id)

    return dbc.Card(
        dbc.CardBody([

            html.Div([
                html.H1(
                    story["title"],
                    className="story-title"
                ),
                html.Div(
                    story["sub_title"],
                    className="story-subtitle"
                ),
            ]),

            html.Hr(className="story-divider"),

            html.Div([
                html.Div([
                    html.Span(f"{key}:", className="story-header-key"),
                    html.Span(str(value), className="story-header-value"),
                ], className="story-header-row")

                for key, value in story["header"].items()
            ], className="story-header"),

            html.Hr(className="story-divider"),
            # Events
            html.Div([
                render_event(event)
                for event in story["events"]
            ]),

            html.Hr(className="story-divider"),

            html.Div([
                html.Div([
                    html.Span(f"{key}:", className="story-footer-key"),
                    html.Span(str(value), className="story-footer-value"),
                ], className="story-footer-row")

                for key, value in story["footer"].items()
            ], className="story-footer"),




        ]),
        className="story-card"
    )

clientside_callback(
    """
    function(n) {
        if(n) { window.print(); }
        return window.dash_clientside.no_update;
    }
    """,
    Output("story-shell", "id"),
    Input("story-print-btn", "n_clicks"),
    prevent_initial_call=True
)