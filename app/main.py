# FastAPI app, router registration
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import init_db
from app.middleware import (
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    _RequestFormatter,
)
from app.routers import documents, health, ask
from app.services.errors import UpstreamProviderError

_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(
    _RequestFormatter(
        "%(asctime)s %(levelname)-5s %(name)s rid=%(request_id)s %(method)s %(path)s "
        "status=%(status_code)s dur_ms=%(duration_ms)s ip=%(client_ip)s %(message)s"
    )
)
logging.basicConfig(level=settings.LOG_LEVEL.upper(), handlers=[_handler])


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Grounded QA", lifespan=lifespan)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(UpstreamProviderError)
async def upstream_provider_handler(request: Request, exc: UpstreamProviderError):
    logger = logging.getLogger(__name__)
    logger.error(
        "upstream provider failure",
        extra={
            "path": request.url.path,
            "status": 502,
            "operation": exc.operation,
            "exc_type": exc.exc_type,
        },
    )
    return JSONResponse(
        status_code=502,
        content={"detail": "Upstream model provider unavailable. Try again later."},
    )


app.include_router(health.router)
app.include_router(documents.router)
app.include_router(ask.router)


@app.get("/")
def root():
    return {"message": "Grounded QA API. See /docs"}
