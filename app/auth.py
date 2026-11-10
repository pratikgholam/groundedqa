# API key authentication and simple rate limiting.
import threading
import time
from collections import deque

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

from app.config import settings

# X-API-Key header; auto_error=False so we can return a clear 401 ourselves.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# X-Tenant-ID header; required on all data endpoints.
tenant_id_header = APIKeyHeader(name="X-Tenant-ID", auto_error=False)


def get_tenant_id(tenant_id: str | None = Depends(tenant_id_header)) -> str:
    """Extract the tenant ID from the X-Tenant-ID header.

    Required on every data endpoint so retrieval and ingestion are always
    scoped to a single tenant. When API_KEY and TENANT_ID are both set,
    X-Tenant-ID must match TENANT_ID or the caller gets 403.
    """
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header is required",
        )
    expected_tenant = settings.TENANT_ID or None
    if settings.API_KEY and expected_tenant and tenant_id != expected_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant ID not authorized for this API key",
        )
    return tenant_id


def verify_api_key(api_key: str | None = Depends(api_key_header)) -> None:
    """Require a valid API key when auth is configured.

    Skips enforcement when no API_KEY is set (dev/local only). Callers that
    need /health to stay open should not apply this dependency to that route.
    """
    expected = settings.API_KEY or None
    if not expected:
        return  # auth disabled
    if api_key is None or api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


# --- simple in-memory token-bucket rate limiter ----------------------------

_rate_lock = threading.Lock()
_clients: dict[str, deque[float]] = {}


def rate_limit(request: Request) -> None:
    """Allow at most RATE_LIMIT_REQUESTS per RATE_LIMIT_WINDOW seconds per client IP.

    Best-effort in-memory limiter; not shared across workers. Returns 429 when
    the client exceeds the budget.
    """
    max_requests = settings.RATE_LIMIT_REQUESTS
    window = settings.RATE_LIMIT_WINDOW
    if max_requests <= 0:
        return  # rate limiting disabled

    client = request.client.host if request.client else "unknown"
    now = time.monotonic()
    cutoff = now - window

    with _rate_lock:
        timestamps = _clients.setdefault(client, deque())
        while timestamps and timestamps[0] < cutoff:
            timestamps.popleft()
        if len(timestamps) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again later.",
            )
        timestamps.append(now)
