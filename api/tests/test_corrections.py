import logging
from pathlib import Path

import pytest

from app.main import create_app
from tests.support import bearer, jwt_bearer, make_client

MAX_UPLOAD_TEST_BYTES = 5 * 1024 * 1024 + 1


def read_pins(requirements: Path) -> dict[str, tuple[int, ...]]:
    pins: dict[str, tuple[int, ...]] = {}
    for line in requirements.read_text(encoding="utf-8").splitlines():
        if "==" not in line:
            continue
        name, version = line.split("==", 1)
        pins[name.split("[", 1)[0].strip()] = tuple(int(part) for part in version.strip().split("."))
    return pins


def test_fix_h_api_05_pins_patched_versions() -> None:
    pins = read_pins(Path(__file__).resolve().parents[1] / "requirements.txt")
    assert pins["urllib3"] >= (2, 6, 0)
    assert pins["python-multipart"] >= (0, 0, 22)


def test_fix_h_api_06_401_detail_is_generic(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/tasks", headers={"Authorization": "Bearer !!!"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_fix_h_api_06_error_detail_goes_to_server_log(tmp_path: Path, caplog) -> None:
    with caplog.at_level(logging.WARNING), make_client(tmp_path) as client:
        client.get("/api/tasks", headers={"Authorization": "Bearer !!!"})
    messages = [record.getMessage() for record in caplog.records if record.levelno == logging.WARNING]
    assert any("Invalid token" in message for message in messages)
    assert not any("!!!" in message for message in messages)


def test_fix_h_api_02_list_rejects_other_owner(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/tasks", params={"owner": "trainer"}, headers=bearer())
    assert response.status_code == 403


def test_fix_h_api_02_summary_rejects_other_owner(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/summary", params={"owner": "trainer"}, headers=bearer())
    assert response.status_code == 403


def test_fix_h_api_02_create_rejects_other_owner(tmp_path: Path) -> None:
    payload = {"title": "X", "description": "Y", "owner": "trainer"}
    with make_client(tmp_path) as client:
        response = client.post("/api/tasks", headers=bearer(), json=payload)
    assert response.status_code == 403


def test_fix_h_api_03_quoted_title_is_stored_literally(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        created = client.post("/api/tasks", headers=bearer(), json={"title": "O'Brien", "description": "a;b"})
        listed = client.get("/api/tasks", headers=bearer())
    assert created.status_code == 201
    assert created.json()["title"] == "O'Brien"
    assert created.json()["description"] == "a;b"
    assert "O'Brien" in [task["title"] for task in listed.json()]


def test_fix_h_api_03_quoted_identity_username_is_safe(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/tasks", headers=bearer(username="O'Brien"))
    assert response.status_code == 200
    assert response.json() == []


def test_fix_h_api_04_upload_name_is_reduced_to_base_name(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/requirements",
            headers=bearer(),
            files={"file": ("../evil.txt", b"x", "text/plain")},
        )
    assert response.status_code == 201
    assert response.json()["fileName"] == "evil.txt"
    stored = Path(response.json()["storedAt"])
    assert stored.parent == upload_dir
    assert stored.read_bytes() == b"x"
    assert not (tmp_path / "evil.txt").exists()


def test_fix_h_api_04_disallowed_extension_is_400(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/requirements",
            headers=bearer(),
            files={"file": ("tool.exe", b"x", "application/octet-stream")},
        )
    assert response.status_code == 400


def test_fix_h_api_04_oversized_upload_is_413(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/requirements",
            headers=bearer(),
            files={"file": ("big.txt", b"a" * MAX_UPLOAD_TEST_BYTES, "text/plain")},
        )
    assert response.status_code == 413


def test_fix_h_api_02_trainer_cannot_create_for_other_owner(tmp_path: Path) -> None:
    payload = {"title": "X", "description": "Y", "owner": "student"}
    with make_client(tmp_path) as client:
        response = client.post("/api/tasks", headers=bearer(username="trainer", role="TRAINER"), json=payload)
    assert response.status_code == 403


def test_fix_h_api_02_trainer_can_read_other_owner(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/tasks", params={"owner": "student"}, headers=bearer(username="trainer", role="TRAINER"))
    assert response.status_code == 200
    assert {task["owner"] for task in response.json()} == {"student"}


def test_fix_h_api_04_upload_is_stored_under_unique_name(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        first = client.post("/api/requirements", headers=bearer(), files={"file": ("same.txt", b"one", "text/plain")})
        second = client.post("/api/requirements", headers=bearer(), files={"file": ("same.txt", b"two", "text/plain")})
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["fileName"] == second.json()["fileName"] == "same.txt"
    assert first.json()["storedAt"] != second.json()["storedAt"]


def test_fix_h_api_04_reserved_windows_name_is_400(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post("/api/requirements", headers=bearer(), files={"file": ("CON.txt", b"x", "text/plain")})
    assert response.status_code == 400


def test_fix_h_api_08_unknown_origin_is_not_allowed(tmp_path: Path) -> None:
    headers = {"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"}
    with make_client(tmp_path) as client:
        response = client.options("/api/tasks", headers=headers)
    assert response.headers.get("access-control-allow-origin") != "https://evil.example"
    assert response.headers.get("access-control-allow-origin") != "*"


def test_fix_h_api_08_credentials_are_not_allowed(tmp_path: Path) -> None:
    headers = {"Origin": "http://localhost:4200", "Access-Control-Request-Method": "GET"}
    with make_client(tmp_path) as client:
        response = client.options("/api/tasks", headers=headers)
    assert "access-control-allow-credentials" not in response.headers


def test_fix_h_api_09_unknown_status_is_422(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post("/api/tasks", headers=bearer(), json={"title": "T", "description": "D", "status": "FOO"})
    assert response.status_code == 422


def test_fix_h_api_09_unknown_priority_is_422(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post("/api/tasks", headers=bearer(), json={"title": "T", "description": "D", "priority": "URGENT"})
    assert response.status_code == 422


def test_fix_h_api_10_upstream_error_text_is_not_forwarded(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AUTH_HEALTH_URL", "http://127.0.0.1:9/q/health")
    with make_client(tmp_path) as client:
        response = client.get("/api/backend-health", headers=bearer())
    assert response.status_code == 200
    assert "HTTPConnectionPool" not in response.json()["body"]


def test_fix_h_api_01_valid_jwt_is_accepted(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/tasks", headers=jwt_bearer())
    assert response.status_code == 200


def test_fix_h_api_01_jwt_signed_with_other_key_is_401(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/tasks", headers=jwt_bearer(secret="other-key-not-real-0123456789abcdef"))
    assert response.status_code == 401


def test_fix_h_api_01_jwt_with_wrong_audience_is_401(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/tasks", headers=jwt_bearer(audience="other-api"))
    assert response.status_code == 401


def test_fix_h_api_01_expired_jwt_is_401(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/tasks", headers=jwt_bearer(expires_in=-10))
    assert response.status_code == 401


def test_fix_h_api_01_previously_embedded_secret_is_rejected(tmp_path: Path) -> None:
    old_embedded_secret = "WORKSHOP_SECRET_2026"
    with make_client(tmp_path) as client:
        response = client.get("/api/tasks", headers=bearer(secret=old_embedded_secret))
    assert response.status_code == 401


def test_fix_h_api_01_legacy_token_rejected_when_legacy_secret_unset(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("WORKSHOP_LEGACY_TOKEN_SECRET")
    with make_client(tmp_path) as client:
        response = client.get("/api/tasks", headers=bearer(secret="test-legacy-secret-not-real"))
    assert response.status_code == 401


def test_fix_h_api_01_app_does_not_start_without_jwt_secret(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("WORKSHOP_JWT_SECRET")
    with pytest.raises(RuntimeError):
        create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
