"""Reusable session selection and download component."""

import io
import logging
import zipfile
from typing import Literal

from dash import Input, Output, callback, dcc, html

from dashboard.db import get_sessions
from dashboard.utils.story_utils import create_story_pdf


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


def create_session_download_layout(
    session_options: list,
    id_prefix: str = "",  # Add prefix to make IDs unique per page
    dropdown_id: str = None,
    button_container_id: str = None,
    trigger_store_id: str = None,
    download_id: str = None,
    button_text: str = "Download Report",
    button_class: str = "download-btn"
) -> list:
    """Create layout components for session selection and download."""

    # Apply prefix if provided
    dropdown_id = dropdown_id or f"{id_prefix}session-dropdown"
    button_container_id = (
        button_container_id or f"{id_prefix}download-button-container")
    trigger_store_id = trigger_store_id or f"{id_prefix}download-trigger"
    download_id = download_id or f"{id_prefix}download-report"
    button_id = f"{id_prefix}download-btn"

    # Store these IDs in the layout as data attributes for callbacks to use
    return [
        dcc.Dropdown(
            id=dropdown_id,
            options=session_options,
            placeholder="Select a session...",
            className="session-dropdown",
            clearable=False
        ),
        html.Div(id=button_container_id, **{"data-button-id": button_id}),
        dcc.Store(id=trigger_store_id, data=0),
        dcc.Download(id=download_id),
    ]


def register_session_download_callbacks(
    id_prefix: str = "",  # Must match the prefix used in layout
    dropdown_id: str = None,
    button_container_id: str = None,
    trigger_store_id: str = None,
    download_id: str = None,
    button_id: str = None,
    button_text: str = "Download",
    button_class: str = "download-btn",
    download_type: Literal['zip', 'pdf'] = 'zip',
    create_story_func=None,
    session_map_func=None,
):
    """
    Register callbacks for session selection and download.
    """

    # Generate unique IDs
    dropdown_id = dropdown_id or f"{id_prefix}session-dropdown"
    button_container_id = (
        button_container_id or f"{id_prefix}download-button-container")
    trigger_store_id = trigger_store_id or f"{id_prefix}download-trigger"
    download_id = download_id or f"{id_prefix}download-report"
    actual_button_id = button_id or f"{id_prefix}download-btn"

    # Callback to show/hide download button
    @callback(
        Output(button_container_id, "children"),
        Input(dropdown_id, "value"),
    )
    def show_download_button(session_id):
        if session_id:
            return html.Button(
                button_text,
                id=actual_button_id,
                className=button_class
            )
        return None

    # Callback to trigger download
    @callback(
        Output(trigger_store_id, "data"),
        Input(actual_button_id, "n_clicks"),
        prevent_initial_call=True
    )
    def trigger_download(n_clicks):
        if not n_clicks:
            return 0
        return n_clicks

    # Callback to generate and download file
    @callback(
        Output(download_id, "data"),
        Input(trigger_store_id, "data"),
        Input(dropdown_id, "value"),
        prevent_initial_call=True
    )
    def download_file(trigger, session_id):
        if not trigger or not session_id:
            return None

        if download_type == 'pdf':
            if not create_story_func:
                logging.error("create_story_func required for PDF download")
                return None

            story = create_story_func(session_id)
            pdf_bytes = create_story_pdf(story)
            logging.info(f"PDF bytes size: {len(pdf_bytes)}")

            return dcc.send_bytes(
                pdf_bytes,
                f"story_{session_id[:8]}.pdf",
                type="application/octet-stream"
            )

        elif download_type == 'zip':
            if not session_map_func:
                logging.error("session_map_func required for ZIP download")
                return None

            tables = {name: fn(session_id) for
                      name, fn in session_map_func.items()}

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for name, df in tables.items():
                    csv_buffer = io.StringIO()
                    df.to_csv(csv_buffer, index=False)
                    zf.writestr(f"{name}.csv", csv_buffer.getvalue())

            zip_buffer.seek(0)
            logging.info(f"ZIP bytes size: {len(zip_buffer.getvalue())}")

            return dcc.send_bytes(
                zip_buffer.getvalue(),
                f"session_{session_id[:8]}.zip",
                type="application/octet-stream"
            )

        else:
            logging.error(f"Unknown download type: {download_type}")
            return None
