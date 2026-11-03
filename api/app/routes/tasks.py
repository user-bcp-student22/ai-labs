from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.schemas import SummaryOut, TaskCreate, TaskOut
from app.security import Identity, get_identity
from app.services import tasks as task_service

router = APIRouter(prefix="/api")


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(
    request: Request,
    owner: str | None = Query(default=None),
    identity: Identity = Depends(get_identity),
) -> list[TaskOut]:
    return task_service.list_tasks(request.app.state.connection, identity, owner)


@router.post("/tasks", status_code=201, response_model=TaskOut)
def create_task(
    request: Request,
    payload: TaskCreate,
    identity: Identity = Depends(get_identity),
) -> TaskOut:
    return task_service.create_task(request.app.state.connection, identity, payload)


@router.get("/summary", response_model=SummaryOut)
def summary(
    request: Request,
    owner: str | None = Query(default=None),
    identity: Identity = Depends(get_identity),
) -> SummaryOut:
    return task_service.summarize(request.app.state.connection, identity, owner)
