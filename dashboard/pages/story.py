import logging

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html

from dashboard.components.functions import download_story
from dashboard.components.session_download import (
    ButtonModel,
    get_session_options,
    register_session_callbacks,
    session_dropdown,
)
from dashboard.utils.story_utils import create_story
from dashboard.utils.translation_utils import translator

logger = logging.getLogger(__name__)

dash.register_page(__name__, path="/story")

SESSION_TEMPLATE = "Walker #{session_id} ({name})"
LANGUAGE_OPTIONS = [
    {"label": "Original", "value": "original"},
    {"label": "English", "value": "en"},
    {"label": "Spanish", "value": "es"},
    {"label": "French", "value": "fr"},
    {"label": "German", "value": "de"},
    {"label": "Portuguese", "value": "pt"},
    {"label": "Russian", "value": "ru"},
    {"label": "Mandarin", "value": "zh"},
    {"label": "Arabic", "value": "ar"},
    {"label": "Japanese", "value": "ja"},
    {"label": "Hindi", "value": "hi"},
]



register_session_callbacks(
    dropdown_id="story-dropdown",
    button_container_id="story-buttons",
    buttons=[
        ButtonModel(
            id="story-download-btn",
            text="Download",
            func=download_story,
            output_id="story-download",
            extra_state_ids=["current-story-store"]
        ),
    ]
)


def layout() -> dbc.Container:
    options = get_session_options(SESSION_TEMPLATE)
    return dbc.Container([
        html.Div([
            session_dropdown(options, id="story-dropdown"),
            html.Div(id="story-buttons"),
            html.Div(id="language-container"),
            dcc.Store(id="original-story-store"),
            dcc.Store(id="current-story-store"),
            dcc.Download(id="story-download"),
            dcc.Loading(
                id="translation-loading",
                children=html.Div(id="story-content")
            )
        ], className="story-shell", id="story-shell")
    ], fluid=True, className="story-container")


@callback(
    Output("original-story-store", "data", allow_duplicate=True),
    Output("current-story-store", "data", allow_duplicate=True),
    Output("story-content", "children", allow_duplicate=True),
    Input("story-dropdown", "value"),
    prevent_initial_call=True
)
def on_session_select(session_id):
    if not session_id:
        return None, None, None
    story = create_story(session_id)
    return story, story, render_story_content(story)


@callback(
    Output("language-container", "children", allow_duplicate=True),
    Input("story-dropdown", "value"),
    prevent_initial_call=True
)
def show_language_dropdown(session_id):
    if not session_id or not translator.translator:
        return None
    return dcc.Dropdown(
        id="language-dropdown",
        options=LANGUAGE_OPTIONS,
        placeholder="Select a language...",
        clearable=True,
        className="language-dropdown"

    )


@callback(
    Output("current-story-store", "data", allow_duplicate=True),
    Output("story-content", "children", allow_duplicate=True),
    Input("language-dropdown", "value"),
    State("original-story-store", "data"),
    prevent_initial_call=True
)
def on_language_select(lang, original_story):
    if not lang or lang == 'original' or not original_story:
        return original_story, render_story_content(original_story)
    translated = translator.translate_story(original_story, target_lang=lang)
    return translated, render_story_content(translated)


def render_story_content(story: dict) -> dbc.Card:
    """Render story content from story dictionary."""
    if not story:
        return None
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


def render_event(event: dict) -> dbc.Card:
    """Render individual event."""
    content = []

    if not any([
        event["selection"],
        event["llm_answer"],
        event["reflection"],
        event['system_message']
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

        if event["system_message"]:
            content.append(
                html.Div(
                    event["system_message"],
                    className="story-event-system-message"
                )
            )

        if event["system_error"]:
            content.append(
                html.Div(
                    event["system_error"],
                    className="story-event-system-error"
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
