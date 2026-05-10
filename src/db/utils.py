"""Utils for db manipulation."""

import csv
import logging
import os

import psycopg2

from src.db.db import DB_CONFIG
from src.setup import DATA_DIR, SQL_DIR

logger = logging.getLogger(__name__)


def generate_report(session_id: str) -> None:
    """Generates report for session_id and saves it data folder."""
    report_dir = os.path.join(DATA_DIR, f"report_session_id_{session_id}")
    os.makedirs(report_dir, exist_ok=True)

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        filenames = ["session_overview_per_session.sql",
                     "actions_sequence_per_session.sql",
                     "messages_per_session.sql",
                     "tool_usage_per_session.sql",
                     "feedback_per_session.sql",
                     "mood_timeline_per_session.sql",
                     "invites_per_session.sql"]

        for filename in filenames:
            query = (SQL_DIR / filename).read_text()
            name = filename.split('.sql')[0]
            cur.execute(query, (session_id,))
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

            filepath = os.path.join(report_dir, f"{name}.csv")
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                writer.writerows(rows)

        print(f"Report saved to {report_dir}")
    except Exception as e:
        logger.error(f"Failed to save report for session {session_id}: {e}")
        raise e
    finally:
        cur.close()
        conn.close()
