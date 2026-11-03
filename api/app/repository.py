import sqlite3

TASK_COLUMNS = "id,title,description,status,owner,priority,created_at"
SELECT_TASKS_BY_OWNER = "SELECT " + TASK_COLUMNS + " FROM tasks WHERE owner = ? ORDER BY id"
SELECT_TASK_BY_ID = "SELECT " + TASK_COLUMNS + " FROM tasks WHERE id = ?"
SELECT_STATUS_PRIORITY_BY_OWNER = "SELECT status,priority FROM tasks WHERE owner = ?"
INSERT_TASK = "INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES (?,?,?,?,?,datetime('now'))"


def find_tasks_by_owner(connection: sqlite3.Connection, owner: str) -> list[sqlite3.Row]:
    return connection.execute(SELECT_TASKS_BY_OWNER, (owner,)).fetchall()


def find_task_by_id(connection: sqlite3.Connection, task_id: int) -> sqlite3.Row | None:
    return connection.execute(SELECT_TASK_BY_ID, (task_id,)).fetchone()


def find_status_priorities_by_owner(connection: sqlite3.Connection, owner: str) -> list[sqlite3.Row]:
    return connection.execute(SELECT_STATUS_PRIORITY_BY_OWNER, (owner,)).fetchall()


def insert_task(
    connection: sqlite3.Connection,
    *,
    title: str,
    description: str,
    status: str,
    owner: str,
    priority: str,
) -> int:
    cursor = connection.execute(INSERT_TASK, (title, description, status, owner, priority))
    connection.commit()
    return int(cursor.lastrowid or 0)
