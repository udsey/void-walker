"""Utils for db manipulation."""

import csv
import logging
import os

import psycopg2

from src.db.db import DB_CONFIG
from src.db.queries import generate_report_q
from src.setup import DATA_DIR

logger = logging.getLogger(__name__)


def generate_report(session_id: str) -> None:
    """Generates report for session_id and saves it data folder."""
    report_dir = os.path.join(DATA_DIR, f"report_session_id_{session_id}")
    os.makedirs(report_dir, exist_ok=True)

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        for name, query in generate_report_q.items():
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
