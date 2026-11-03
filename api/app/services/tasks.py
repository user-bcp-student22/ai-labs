from __future__ import annotations

import sqlite3
from typing import Any

from app import repository
from app.schemas import SummaryOut, TaskCreate, TaskOut
from app.security import Identity
from app.services.summary import build_summary

TRAINER_ROLE = "TRAINER"


class ForbiddenOwnerError(Exception):
    """El owner solicitado no coincide con la identidad del token."""


def resolve_owner(identity: Identity, requested: Any) -> str:
    if not requested or str(requested) == identity.username:
        return identity.username
    raise ForbiddenOwnerError


def resolve_read_owner(identity: Identity, requested: Any) -> str:
    if identity.role == TRAINER_ROLE and requested:
        return str(requested)
    return resolve_owner(identity, requested)


def to_task(row: sqlite3.Row) -> TaskOut:
    return TaskOut(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        status=row["status"],
        owner=row["owner"],
        priority=row["priority"],
        createdAt=row["created_at"],
    )


def list_tasks(connection: sqlite3.Connection, identity: Identity, requested_owner: Any) -> list[TaskOut]:
    owner = resolve_read_owner(identity, requested_owner)
    return [to_task(row) for row in repository.find_tasks_by_owner(connection, owner)]


def create_task(connection: sqlite3.Connection, identity: Identity, payload: TaskCreate) -> TaskOut:
    task_id = repository.insert_task(
        connection,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        owner=resolve_owner(identity, payload.owner),
        priority=payload.priority,
    )
    return to_task(repository.find_task_by_id(connection, task_id))


def summarize(connection: sqlite3.Connection, identity: Identity, requested_owner: Any) -> SummaryOut:
    owner = resolve_read_owner(identity, requested_owner)
    return build_summary(owner, repository.find_status_priorities_by_owner(connection, owner))
