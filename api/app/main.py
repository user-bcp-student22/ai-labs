from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings, load_settings
from app.db import open_database
from app.routes.health import router as health_router
from app.routes.requirements import router as requirements_router
from app.routes.tasks import router as tasks_router
from app.services.tasks import ForbiddenOwnerError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    app.state.connection.close()


def forbidden_owner_handler(request: Request, error: ForbiddenOwnerError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": "Forbidden"})


def create_app(db_path: str | None = None, upload_dir: str | None = None) -> FastAPI:
    settings: Settings = load_settings(db_path, upload_dir)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="Workshop Requirements API", version="0.1.0", lifespan=lifespan)
    app.state.connection = open_database(settings.db_path)
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_exception_handler(ForbiddenOwnerError, forbidden_owner_handler)
    app.include_router(tasks_router)
    app.include_router(requirements_router)
    app.include_router(health_router)
    return app


app = create_app()
