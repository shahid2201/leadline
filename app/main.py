import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.api.auth_debug import router as auth_router
from app.api.conversations import messages_router
from app.api.conversations import router as sessions_router
from app.api.health import router as health_router
from app.api.leads import router as leads_router
from app.api.leads import timeline_router
from app.api.routing import router as routing_rules_router
from app.api.sequences import router as sequences_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import engine
from app.middleware.auth import AuthMiddleware
from app.models import (  # noqa: F401
    APIKey,
    Lead,
    LeadTimelineEvent,
    Message,
    RoutingRule,
    Sequence,
    SequenceEnrollment,
    SequenceStep,
    Session,
    Tenant,
    User,
)

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("leadline.api")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.auto_create_tables:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(AuthMiddleware)


@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    started = time.perf_counter()
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    response = await call_next(request)
    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    context = getattr(request.state, "auth_context", None)
    logger.info(
        "request",
        extra={
            "request_id": request_id,
            "tenant_id": getattr(context, "tenant_id", None),
            "user_id": getattr(context, "user_id", None),
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
        },
    )
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(health_router)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(leads_router, prefix=settings.api_prefix)
app.include_router(timeline_router, prefix=settings.api_prefix)
app.include_router(sessions_router, prefix=settings.api_prefix)
app.include_router(messages_router, prefix=settings.api_prefix)
app.include_router(routing_rules_router, prefix=settings.api_prefix)
app.include_router(sequences_router, prefix=settings.api_prefix)
