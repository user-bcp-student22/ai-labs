from __future__ import annotations

import sqlite3
from pathlib import Path

CREATE_TASKS_TABLE = (
    "CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, "
    "description TEXT NOT NULL, status TEXT NOT NULL, owner TEXT NOT NULL, priority TEXT NOT NULL, "
    "created_at TEXT NOT NULL)"
)
COUNT_TASKS = "SELECT COUNT(*) AS total FROM tasks"
INSERT_SEED_TASK = (
    "INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES (?,?,?,?,?,datetime('now'))"
)
SEED_TASKS = (
    ("Refactor login", "Separar responsabilidades en frontend", "TODO", "student", "HIGH"),
    ("Review API", "Revisar seguridad de endpoints", "IN_PROGRESS", "student", "MEDIUM"),
    ("Trainer notes", "Preparar retrospectiva", "TODO", "trainer", "LOW"),
)


def open_database(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute(CREATE_TASKS_TABLE)
    seed_if_empty(connection)
    return connection


def seed_if_empty(connection: sqlite3.Connection) -> None:
    if connection.execute(COUNT_TASKS).fetchone()["total"]:
        return
    connection.executemany(INSERT_SEED_TASK, SEED_TASKS)
    connection.commit()
