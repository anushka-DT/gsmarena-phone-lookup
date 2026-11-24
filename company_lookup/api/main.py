"""Create and configure the FastAPI application."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request

from company_lookup.api.routes import router
from company_lookup.database.connection import DATABASE_PATH
from company_lookup.database.migrations.runner import run_migrations
from company_lookup.logging_config import (
    configure_logging,
    request_id_context,
)

configure_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Apply pending database migrations when the application starts."""
    run_migrations(DATABASE_PATH)
    yield


app = FastAPI(
    title="Phone Lookup API",
    description="API for retrieving mobile phone information from GSMArena.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Attach a unique request ID to each request and its response."""
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    context_token = request_id_context.set(request_id)

    try:
        logger.info(
            "Incoming request: %s %s",
            request.method,
            request.url.path,
        )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "Request completed with status %s",
            response.status_code,
        )

        return response

    finally:
        request_id_context.reset(context_token)


app.include_router(router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Check whether the API is running."""
    return {"status": "healthy"}
