from __future__ import annotations

import base64
import hmac
import logging
import time

import jwt
from fastapi import Header, HTTPException, Request
from pydantic import BaseModel

from app.config import Settings

BEARER_PREFIX = "Bearer "
UNAUTHORIZED_DETAIL = "Invalid token"
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "workshop-auth"
JWT_AUDIENCE = "workshop-api"
JWT_REQUIRED_CLAIMS = ["exp", "iss", "aud", "sub", "role"]
LEGACY_FIELD_SEPARATOR = "|"
LEGACY_FIELD_COUNT = 4
LEGACY_EXPIRES_INDEX = 2
LEGACY_SECRET_INDEX = 3
logger = logging.getLogger(__name__)


class Identity(BaseModel):
    username: str
    role: str


class InvalidTokenError(Exception):
    """Token rechazado; el detalle nunca se devuelve al cliente."""


def verify_jwt(token: str, secret: str) -> Identity:
    claims = jwt.decode(
        token,
        secret,
        algorithms=[JWT_ALGORITHM],
        audience=JWT_AUDIENCE,
        issuer=JWT_ISSUER,
        options={"require": JWT_REQUIRED_CLAIMS},
    )
    return Identity(username=claims["sub"], role=claims["role"])


def parse_legacy_token(token: str, secret: str) -> Identity:
    parts = base64.b64decode(token).decode("utf-8").split(LEGACY_FIELD_SEPARATOR)
    if len(parts) != LEGACY_FIELD_COUNT:
        raise InvalidTokenError
    if not hmac.compare_digest(parts[LEGACY_SECRET_INDEX].encode(), secret.encode()):
        raise InvalidTokenError
    if int(parts[LEGACY_EXPIRES_INDEX]) < int(time.time()):
        raise InvalidTokenError
    return Identity(username=parts[0], role=parts[1])


def authenticate(authorization: str, settings: Settings) -> Identity:
    token = authorization.removeprefix(BEARER_PREFIX)
    try:
        return verify_jwt(token, settings.jwt_secret)
    except (jwt.PyJWTError, ValueError) as jwt_error:
        if settings.legacy_token_secret is None:
            raise InvalidTokenError from jwt_error
    try:
        return parse_legacy_token(token, settings.legacy_token_secret)
    except ValueError as legacy_error:
        raise InvalidTokenError from legacy_error


def get_identity(request: Request, authorization: str = Header(default="")) -> Identity:
    settings: Settings = request.app.state.settings
    try:
        return authenticate(authorization, settings)
    except InvalidTokenError as error:
        logger.warning("Invalid token rejected: %s", type(error.__cause__ or error).__name__)
        raise HTTPException(status_code=401, detail=UNAUTHORIZED_DETAIL) from error
