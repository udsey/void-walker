import io
import zipfile
import logging
from dash import dcc

from dashboard.utils.story_utils import create_story_pdf
from dashboard.db import session_map

logger = logging.getLogger(__name__)


def download_report(session_id: str):
        if not session_id:
             return None
        logger.error(f"DOWNLOAD REPORT: {session_id}")
        tables = {name: fn(session_id) for
                  name, fn in session_map.items()}

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, df in tables.items():
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)
                zf.writestr(f"{name}.csv", csv_buffer.getvalue())

        zip_buffer.seek(0)

        return dcc.send_bytes(
            zip_buffer.getvalue(),
            f"session_{session_id[:8]}.zip",
            type="application/octet-stream"
        )


def download_story(session_id: str, current_story: dict):
    if not session_id or not current_story:
         return None
    pdf_bytes = create_story_pdf(current_story)
    return dcc.send_bytes(
                pdf_bytes,
                f"story_{session_id[:8]}.pdf",
                type="application/octet-stream"
            )