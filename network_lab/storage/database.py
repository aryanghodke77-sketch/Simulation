"""SQLite storage for the Network Lab.

Stores saved scenarios and evaluation experiments. Kept deliberately small:
we do not persist every simulated packet forever.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent / "network_lab.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                participant TEXT NOT NULL,
                session_id TEXT NOT NULL,
                task TEXT NOT NULL,
                completion_time REAL NOT NULL,
                score INTEGER NOT NULL,
                attempts INTEGER NOT NULL,
                feedback TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        conn.commit()
    finally:
        conn.close()


def save_scenario(name: str, scenario_data: Dict[str, Any]) -> int:
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO scenarios (name, data) VALUES (?, ?)",
            (name, json.dumps(scenario_data)),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_scenarios() -> List[Dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute("SELECT id, name, created_at FROM scenarios ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_experiment(
    participant: str,
    session_id: str,
    task: str,
    completion_time: float,
    score: int,
    attempts: int,
    feedback: Optional[str] = None,
) -> int:
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO experiments (participant, session_id, task, completion_time, score, attempts, feedback) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (participant, session_id, task, completion_time, score, attempts, feedback),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_experiments() -> List[Dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, participant, session_id, task, completion_time, score, attempts, feedback, created_at "
            "FROM experiments ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
