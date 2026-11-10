# Security headers and request logging middleware.
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)

_REQUEST_FIELDS = ("request_id", "method", "path", "status_code", "duration_ms", "client_ip")


class _RequestFormatter(logging.Formatter):
    """Render request log fields safely; missing fields render as '-'."""

    def format(self, record: logging.LogRecord) -> str:
        for field in _REQUEST_FIELDS:
            record.__dict__.setdefault(field, "-")
        return super().format(record)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add defensive response headers to every response."""

    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)
        # Prevent MIME-type sniffing.
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Avoid clickjacking via framing.
        response.headers["X-Frame-Options"] = "DENY"
        # Limit referrer information sent to third parties.
        response.headers["Referrer-Policy"] = "no-referrer"
        # No content-security policy is needed for a pure JSON API, but
        # declare an empty default-src to be explicit.
        response.headers["Content-Security-Policy"] = "default-src 'none'"
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log one structured line per completed request.

    Fields are emitted via logging `extra` so they stay structured rather
    than glued into the message string. Missing fields render as "-".
    """

    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        start = time.monotonic()
        response: Response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)
        client_host = "unknown"
        if request.client:
            client_host = getattr(request.client, "host", str(request.client))
        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": client_host,
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response
