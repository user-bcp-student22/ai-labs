from __future__ import annotations

import logging

import urllib3

from app.config import UPSTREAM_TIMEOUT_SECONDS
from app.schemas import HealthOut

UNAVAILABLE_STATUS = 0
UNAVAILABLE_BODY = "auth backend unavailable"
logger = logging.getLogger(__name__)


def check_backend(url: str, requested_by: str) -> HealthOut:
    try:
        response = urllib3.PoolManager().request("GET", url, timeout=UPSTREAM_TIMEOUT_SECONDS)
    except urllib3.exceptions.HTTPError as error:
        logger.warning("Auth health check unavailable: %s", type(error).__name__)
        return HealthOut(requestedBy=requested_by, status=UNAVAILABLE_STATUS, body=UNAVAILABLE_BODY)
    return HealthOut(
        requestedBy=requested_by,
        status=response.status,
        body=response.data.decode("utf-8", errors="replace"),
    )
