from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TITLE_MAX_LENGTH = 255
DESCRIPTION_MAX_LENGTH = 2000

TaskStatus = Literal["TODO", "IN_PROGRESS", "DONE", "ARCHIVED"]
TaskPriority = Literal["LOW", "MEDIUM", "HIGH"]


class TaskCreate(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    title: str = Field(default="", max_length=TITLE_MAX_LENGTH)
    description: str = Field(default="", max_length=DESCRIPTION_MAX_LENGTH)
    status: TaskStatus = "TODO"
    priority: TaskPriority = "MEDIUM"
    owner: str | None = None


class TaskOut(BaseModel):
    id: int
    title: str
    description: str
    status: str
    owner: str
    priority: str
    createdAt: str


class SummaryOut(BaseModel):
    owner: str
    total: int
    byStatus: dict[str, int]
    highPriorityOpen: int


class UploadOut(BaseModel):
    owner: str
    fileName: str
    storedAt: str
    size: int


class HealthOut(BaseModel):
    requestedBy: str
    status: int
    body: str
