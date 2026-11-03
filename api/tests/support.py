import base64
import os
import time
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

from app.main import create_app

JWT_ISSUER = "workshop-auth"
JWT_AUDIENCE = "workshop-api"


def legacy_secret() -> str:
    return os.environ["WORKSHOP_LEGACY_TOKEN_SECRET"]


def jwt_secret() -> str:
    return os.environ["WORKSHOP_JWT_SECRET"]


def bearer(username: str = "student", role: str = "STUDENT", expires_in: int = 3600, secret: str | None = None) -> dict[str, str]:
    raw = f"{username}|{role}|{int(time.time()) + expires_in}|{secret or legacy_secret()}"
    return {"Authorization": "Bearer " + base64.b64encode(raw.encode()).decode()}


def jwt_bearer(
    username: str = "student",
    role: str = "STUDENT",
    expires_in: int = 3600,
    secret: str | None = None,
    issuer: str = JWT_ISSUER,
    audience: str = JWT_AUDIENCE,
) -> dict[str, str]:
    now = int(time.time())
    claims = {"sub": username, "role": role, "iat": now, "exp": now + expires_in, "iss": issuer, "aud": audience}
    return {"Authorization": "Bearer " + jwt.encode(claims, secret or jwt_secret(), algorithm="HS256")}


def make_client(tmp_path: Path) -> TestClient:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    return TestClient(app)
