from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.schemas import SummaryOut

HIGH_PRIORITY = "HIGH"
CLOSED_STATUSES = frozenset({"DONE", "ARCHIVED"})


def build_summary(owner: str, rows: Iterable[Any]) -> SummaryOut:
    by_status: dict[str, int] = {}
    total = 0
    high_priority_open = 0
    for row in rows:
        total += 1
        by_status[row["status"]] = by_status.get(row["status"], 0) + 1
        if is_open_high_priority(row):
            high_priority_open += 1
    return SummaryOut(owner=owner, total=total, byStatus=by_status, highPriorityOpen=high_priority_open)


def is_open_high_priority(row: Any) -> bool:
    return row["priority"] == HIGH_PRIORITY and row["status"] not in CLOSED_STATUSES
