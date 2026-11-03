from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.schemas import HealthOut
from app.security import Identity, get_identity
from app.services.health import check_backend

router = APIRouter(prefix="/api")


@router.get("/backend-health", response_model=HealthOut)
def backend_health(request: Request, identity: Identity = Depends(get_identity)) -> HealthOut:
    return check_backend(request.app.state.settings.auth_health_url, identity.username)
