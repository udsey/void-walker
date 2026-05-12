import logging

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html

from dashboard.components.session_download import (
    create_session_download_layout,
    get_session_options,
    register_session_download_callbacks,
)
from dashboard.utils.story_utils import create_story
from dashboard.utils.translation_utils import translator

logger = logging.getLogger(__name__)

dash.register_page(
    __name__,
    path="/story",
)


session_options = get_session_options("Walker #{session_id} ({name})")

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


layout = dbc.Container([
    html.Div(
        create_session_download_layout(
            session_options=session_options,
            id_prefix="story_",
            button_text="Download PDF",
            button_class="download-btn"
        ) + [
            html.Div(id="language-selector-container",
                     style={"margin": "20px 0", "display":
                            "flex", "alignItems": "center"}),
            dcc.Store(id="original-story-store"),  # Store original story
            dcc.Store(id="translated-story-store"),  # Store translated version
            dcc.Loading(
                id="translation-loading",
                type="circle",
                style={f"position": "fixed", "top": "400px",
                       "left": "50%", "zIndex": 9999},
                children=html.Div(id="story-content"),
            ),

        ],
        className="story-shell",
        id="story-shell"
    )
], fluid=True, className="story-container")



register_session_download_callbacks(
    id_prefix="story_",
    button_text="Download PDF",
    button_class="download-btn",
    download_type='pdf',
    create_story_func=create_story
)


@callback(
    Output("original-story-store", "data"),
    Output("story-content", "children"),
    Input("story_session-dropdown", "value")
)
def load_and_store_story(session_id):
    """Load story and store original version."""
    if not session_id:
        return None, None

    story = create_story(session_id)

    # Render the story (original language)
    rendered = render_story_content(story)

    return story, rendered



@callback(
    Output("translated-story-store", "data"),
    Output("story-content", "children", allow_duplicate=True),
    Input("story-language-dropdown", "value"),
    State("original-story-store", "data"),
    prevent_initial_call=True
)
def translate_story_on_language_change(target_lang, original_story):
    """Translate story when language changes."""
    if not original_story:
        return None, None

    if target_lang == "original":
        # Show original story
        rendered = render_story_content(original_story)
        return None, rendered

    # Translate the story
    translated_story = translator.translate_story(original_story, target_lang)

    # Render translated story
    rendered = render_story_content(translated_story)

    return translated_story, rendered



def render_story_content(story: dict) -> dbc.Card:
    """Render story content from story dictionary."""
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


@callback(
    Output("story_download-pdf", "data"),
    Input("story_download-trigger", "data"),
    State("story_session-dropdown", "value"),
    State("story-language-dropdown", "value"),
    State("original-story-store", "data"),
    prevent_initial_call=True
)
def download_pdf_with_language(trigger, session_id, target_lang,
                               original_story, translated_story):
    """Download PDF in selected language."""
    if not trigger or not session_id:
        return None

    if not target_lang or target_lang == "original" or not translated_story:
        story = original_story
    else:
        story = translated_story

    if not story:
        return None

    from dashboard.utils.story_utils import create_story_pdf
    pdf_bytes = create_story_pdf(story)

    return dcc.send_bytes(
        pdf_bytes,
        f"story_{session_id[:8]}_{target_lang}.pdf",
        type="application/octet-stream"
    )


@callback(
    Output("language-selector-container", "children"),
    Input("story_session-dropdown", "value")
)
def show_language_selector(session_id):
    if session_id and translator.translator:
        return html.Div([
            html.Label("Language:", style={"marginRight": "10px",
                                           "color": "#cccccc"}),
            dcc.Dropdown(
                id="story-language-dropdown",
                options=LANGUAGE_OPTIONS,
                value="original",
                clearable=False,
                className="language-dropdown",
                style={"width": "200px", "display": "inline-block"}
            ),
        ], style={"display": "flex", "alignItems": "center"})
    return None  # Hide when no session selected
