import os
import sqlite3
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "memory.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            language_preference TEXT,
            current_level TEXT,
            topics_covered TEXT,
            mistakes_kept_making TEXT,
            last_interaction TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS escalations (
            ticket_id TEXT PRIMARY KEY,
            user_id TEXT,
            name TEXT,
            reason TEXT,
            topics_covered TEXT,
            urgency TEXT,
            follow_up_method TEXT,
            status TEXT,
            timestamp TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calls (
            call_id TEXT PRIMARY KEY,
            user_id TEXT,
            name TEXT,
            duration_seconds INTEGER,
            outcome TEXT,
            failure_reason TEXT,
            timestamp TEXT,
            channel TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_user(user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def save_user(
    user_id: str,
    name: str,
    language_preference: str = "Hinglish",
    current_level: str = "Beginner",
    topics_covered: str = "",
    mistakes_kept_making: str = "",
):
    conn = get_db_connection()
    cursor = conn.cursor()
    last_interaction = datetime.now().isoformat()
    cursor.execute(
        """
        INSERT INTO users (user_id, name, language_preference, current_level, topics_covered, mistakes_kept_making, last_interaction)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            name = excluded.name,
            language_preference = excluded.language_preference,
            current_level = excluded.current_level,
            topics_covered = excluded.topics_covered,
            mistakes_kept_making = excluded.mistakes_kept_making,
            last_interaction = excluded.last_interaction
    """,
        (
            user_id,
            name,
            language_preference,
            current_level,
            topics_covered,
            mistakes_kept_making,
            last_interaction,
        ),
    )
    conn.commit()
    conn.close()


def create_ticket(
    user_id: str,
    name: str,
    reason: str,
    topics_covered: str,
    urgency: str,
    follow_up_method: str,
) -> str:
    import random

    conn = get_db_connection()
    cursor = conn.cursor()
    ticket_id = f"TKT-{random.randint(1000, 9999)}"
    timestamp = datetime.now().isoformat()
    cursor.execute(
        """
        INSERT INTO escalations (ticket_id, user_id, name, reason, topics_covered, urgency, follow_up_method, status, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            ticket_id,
            user_id,
            name,
            reason,
            topics_covered,
            urgency,
            follow_up_method,
            "Open",
            timestamp,
        ),
    )
    conn.commit()
    conn.close()
    return ticket_id


def get_all_tickets():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM escalations ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def create_call_record(call_id: str, user_id: str, name: str, channel: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    cursor.execute(
        """
        INSERT INTO calls (call_id, user_id, name, duration_seconds, outcome, failure_reason, timestamp, channel)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (call_id, user_id, name, 0, "Failure", "Incomplete", timestamp, channel),
    )
    conn.commit()
    conn.close()


def update_call_outcome(
    call_id: str,
    outcome: str,
    duration_seconds: int,
    failure_reason: Optional[str] = None,
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE calls
        SET outcome = ?, duration_seconds = ?, failure_reason = ?
        WHERE call_id = ?
    """,
        (outcome, duration_seconds, failure_reason, call_id),
    )
    conn.commit()
    conn.close()


def get_call_stats():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM calls")
    total_calls = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM calls WHERE outcome = 'Success'")
    successful_calls = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM calls WHERE outcome = 'Failure'")
    failed_calls = cursor.fetchone()[0]

    success_rate = 0.0
    if total_calls > 0:
        success_rate = round((successful_calls / total_calls) * 100, 1)

    # Get failure reasons breakdown
    cursor.execute(
        "SELECT failure_reason, COUNT(*) FROM calls WHERE outcome = 'Failure' GROUP BY failure_reason"
    )
    reasons = dict(cursor.fetchall())

    conn.close()
    return {
        "total_calls": total_calls,
        "successful_calls": successful_calls,
        "failed_calls": failed_calls,
        "success_rate": success_rate,
        "failure_reasons": reasons,
    }


def get_recent_calls():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM calls ORDER BY timestamp DESC LIMIT 15")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
