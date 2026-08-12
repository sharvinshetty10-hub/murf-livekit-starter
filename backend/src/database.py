import os
import sqlite3
from datetime import datetime

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

def save_user(user_id: str, name: str, language_preference: str = "Hinglish", current_level: str = "Beginner", topics_covered: str = "", mistakes_kept_making: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor()
    last_interaction = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO users (user_id, name, language_preference, current_level, topics_covered, mistakes_kept_making, last_interaction)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            name = excluded.name,
            language_preference = excluded.language_preference,
            current_level = excluded.current_level,
            topics_covered = excluded.topics_covered,
            mistakes_kept_making = excluded.mistakes_kept_making,
            last_interaction = excluded.last_interaction
    """, (user_id, name, language_preference, current_level, topics_covered, mistakes_kept_making, last_interaction))
    conn.commit()
    conn.close()

def create_ticket(user_id: str, name: str, reason: str, topics_covered: str, urgency: str, follow_up_method: str) -> str:
    import random
    conn = get_db_connection()
    cursor = conn.cursor()
    ticket_id = f"TKT-{random.randint(1000, 9999)}"
    timestamp = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO escalations (ticket_id, user_id, name, reason, topics_covered, urgency, follow_up_method, status, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (ticket_id, user_id, name, reason, topics_covered, urgency, follow_up_method, "Open", timestamp))
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
