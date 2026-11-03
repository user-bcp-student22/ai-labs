from app.services.summary import build_summary


def task_row(status: str, priority: str) -> dict[str, str]:
    return {"status": status, "priority": priority}


def test_summary_counts_only_open_high_priority_tasks() -> None:
    rows = [
        task_row("TODO", "HIGH"),
        task_row("DONE", "HIGH"),
        task_row("ARCHIVED", "HIGH"),
        task_row("IN_PROGRESS", "LOW"),
    ]
    summary = build_summary("student", rows)
    assert summary.total == 4
    assert summary.byStatus == {"TODO": 1, "DONE": 1, "ARCHIVED": 1, "IN_PROGRESS": 1}
    assert summary.highPriorityOpen == 1


def test_summary_of_no_rows_is_empty() -> None:
    summary = build_summary("student", [])
    assert summary.model_dump() == {"owner": "student", "total": 0, "byStatus": {}, "highPriorityOpen": 0}
