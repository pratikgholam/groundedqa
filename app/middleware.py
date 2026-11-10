# Security headers middleware.
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


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
