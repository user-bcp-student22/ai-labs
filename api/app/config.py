from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_DB_PATH = "./data/workshop.db"
DEFAULT_UPLOAD_DIR = "./uploads"
DEFAULT_AUTH_HEALTH_URL = "http://localhost:8080/q/health"
DEFAULT_CORS_ORIGIN = "http://localhost:4200"
UPSTREAM_TIMEOUT_SECONDS = 3.0
JWT_SECRET_ENV = "WORKSHOP_JWT_SECRET"
MIN_JWT_SECRET_BYTES = 32
LEGACY_SECRET_ENV = "WORKSHOP_LEGACY_TOKEN_SECRET"


@dataclass(frozen=True)
class Settings:
    db_path: str
    upload_dir: str
    auth_health_url: str
    cors_origins: tuple[str, ...]
    jwt_secret: str
    legacy_token_secret: str | None


def parse_origins(raw: str) -> tuple[str, ...]:
    return tuple(origin.strip() for origin in raw.split(",") if origin.strip())


def load_settings(db_path: str | None = None, upload_dir: str | None = None) -> Settings:
    jwt_secret = os.getenv(JWT_SECRET_ENV, "")
    if not jwt_secret:
        raise RuntimeError(f"{JWT_SECRET_ENV} must be set")
    if len(jwt_secret.encode("utf-8")) < MIN_JWT_SECRET_BYTES:
        raise RuntimeError(f"{JWT_SECRET_ENV} must be at least {MIN_JWT_SECRET_BYTES} UTF-8 bytes")
    return Settings(
        db_path=db_path or os.getenv("WORKSHOP_DB_PATH", DEFAULT_DB_PATH),
        upload_dir=upload_dir or os.getenv("WORKSHOP_UPLOAD_DIR", DEFAULT_UPLOAD_DIR),
        auth_health_url=os.getenv("AUTH_HEALTH_URL", DEFAULT_AUTH_HEALTH_URL),
        cors_origins=parse_origins(os.getenv("WORKSHOP_CORS_ORIGINS", DEFAULT_CORS_ORIGIN)),
        jwt_secret=jwt_secret,
        legacy_token_secret=os.getenv(LEGACY_SECRET_ENV) or None,
    )
