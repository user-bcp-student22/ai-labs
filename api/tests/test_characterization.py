import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from tests.support import bearer, make_client


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"UP")

    def log_message(self, format: str, *args: object) -> None:
        return

TASK_KEYS = {"id", "title", "description", "status", "owner", "priority", "createdAt"}


def test_char_list_tasks_returns_identity_tasks_in_order(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/tasks", headers=bearer())
    assert response.status_code == 200
    tasks = response.json()
    assert [task["title"] for task in tasks] == ["Refactor login", "Review API"]
    assert set(tasks[0].keys()) == TASK_KEYS
    assert tasks[0]["owner"] == "student"


def test_char_list_tasks_with_own_owner_query(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/tasks", params={"owner": "student"}, headers=bearer())
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_char_create_task_applies_defaults(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post("/api/tasks", headers=bearer(), json={"title": "T", "description": "D"})
    assert response.status_code == 201
    body = response.json()
    assert set(body.keys()) == TASK_KEYS
    assert body["status"] == "TODO"
    assert body["priority"] == "MEDIUM"
    assert body["owner"] == "student"
    assert isinstance(body["createdAt"], str)


def test_char_create_task_keeps_explicit_fields(tmp_path: Path) -> None:
    payload = {"title": "Add tests", "description": "Improve coverage", "status": "DONE", "priority": "HIGH", "owner": "student"}
    with make_client(tmp_path) as client:
        response = client.post("/api/tasks", headers=bearer(), json=payload)
    assert response.status_code == 201
    assert {key: response.json()[key] for key in payload} == payload


def test_char_summary_counts_identity_tasks(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/summary", headers=bearer())
    assert response.status_code == 200
    assert response.json() == {
        "owner": "student",
        "total": 2,
        "byStatus": {"TODO": 1, "IN_PROGRESS": 1},
        "highPriorityOpen": 1,
    }


def test_char_upload_returns_stable_shape(tmp_path: Path) -> None:
    content = b"Login must be accessible"
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/requirements",
            headers=bearer(),
            files={"file": ("requirements.txt", content, "text/plain")},
        )
    assert response.status_code == 201
    body = response.json()
    assert set(body.keys()) == {"owner", "fileName", "storedAt", "size"}
    assert body["owner"] == "student"
    assert body["fileName"] == "requirements.txt"
    assert body["size"] == len(content)
    assert (Path(body["storedAt"])).read_bytes() == content


def test_char_backend_health_shape_when_auth_is_down(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AUTH_HEALTH_URL", "http://127.0.0.1:9/q/health")
    with make_client(tmp_path) as client:
        response = client.get("/api/backend-health", headers=bearer())
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"requestedBy", "status", "body"}
    assert body["requestedBy"] == "student"
    assert body["status"] == 0
    assert isinstance(body["body"], str)


def test_char_missing_authorization_is_401(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/tasks")
    assert response.status_code == 401


def test_char_wrong_secret_is_401(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/tasks", headers=bearer(secret="OTHER"))
    assert response.status_code == 401


def test_char_expired_token_is_401(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/tasks", headers=bearer(expires_in=-10))
    assert response.status_code == 401


def test_char_numeric_title_is_stored_as_text(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post("/api/tasks", headers=bearer(), json={"title": 5, "description": "D"})
    assert response.status_code == 201
    assert response.json()["title"] == "5"


def test_char_trainer_identity_creates_own_task(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post("/api/tasks", headers=bearer(username="trainer", role="TRAINER"), json={"title": "T", "description": "D"})
    assert response.status_code == 201
    assert response.json()["owner"] == "trainer"


def test_char_cors_preflight_allows_local_frontend(tmp_path: Path) -> None:
    headers = {
        "Origin": "http://localhost:4200",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    }
    with make_client(tmp_path) as client:
        response = client.options("/api/tasks", headers=headers)
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


def test_char_token_identity_drives_response(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/summary", headers=bearer(username="trainer", role="TRAINER"))
    assert response.status_code == 200
    assert response.json()["owner"] == "trainer"


def test_char_backend_health_forwards_upstream_body_on_success(tmp_path: Path, monkeypatch) -> None:
    server = HTTPServer(("127.0.0.1", 0), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setenv("AUTH_HEALTH_URL", f"http://127.0.0.1:{server.server_port}/q/health")
        with make_client(tmp_path) as client:
            response = client.get("/api/backend-health", headers=bearer())
    finally:
        server.shutdown()
        server.server_close()
    assert response.json() == {"requestedBy": "student", "status": 200, "body": "UP"}


def test_char_malformed_token_is_401(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/tasks", headers={"Authorization": "Bearer !!!"})
    assert response.status_code == 401
