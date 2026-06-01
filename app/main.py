import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.api.admin import router as admin_router
from app.api.auth_debug import router as auth_router
from app.api.conversations import messages_router
from app.api.conversations import router as sessions_router
from app.api.health import router as health_router
from app.api.integrations import router as integrations_router
from app.api.leads import router as leads_router
from app.api.leads import timeline_router
from app.api.metrics import router as metrics_router
from app.api.routing import router as routing_rules_router
from app.api.sequences import router as sequences_router
from app.api.webhooks import router as webhooks_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.middleware.auth import AuthMiddleware
from app.models import (  # noqa: F401
    APIKey,
    AuditLog,
    IntegrationConnection,
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
    WebhookEvent,
)
from app.observability.metrics import api_request_latency_ms, api_requests_total
from app.observability.tracing import configure_tracing, traced_span
from app.security.masking import mask_pii
from app.security.posture import report_security_posture
from app.services.audit_service import AuditService

settings = get_settings()
configure_logging(settings.log_level)
configure_tracing()
logger = logging.getLogger("leadline.api")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    report_security_posture()
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

    with traced_span(
        "http.request",
        {
            "http.path": request.url.path,
            "http.method": request.method,
            "request.id": request_id,
        },
    ):
        response = await call_next(request)
    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    context = getattr(request.state, "auth_context", None)
    logger.info(
        "request",
        extra={
            "request_id": request_id,
            "tenant_id": getattr(context, "tenant_id", None),
            "user_id": getattr(context, "user_id", None),
            "path": (
                mask_pii(request.url.path)
                if settings.pii_masking_enabled
                else request.url.path
            ),
            "method": request.method,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
        },
    )

    api_requests_total.labels(
        path=request.url.path,
        method=request.method,
        status_code=str(response.status_code),
        tenant_id=getattr(context, "tenant_id", "anonymous") or "anonymous",
    ).inc()
    api_request_latency_ms.labels(path=request.url.path, method=request.method).observe(latency_ms)

    if settings.audit_log_enabled and request.url.path not in {"/healthz", "/readyz", "/metrics"}:
        audit_service = AuditService()
        audit = audit_service.build_entry(
            tenant_id=getattr(context, "tenant_id", "anonymous") or "anonymous",
            action=f"{request.method}:{request.url.path}",
            resource_type=request.url.path.strip("/").split("/")[0] or "root",
            status_code=response.status_code,
            actor_user_id=getattr(context, "user_id", None),
            actor_api_key_id=getattr(context, "api_key_id", None),
            resource_id=None,
            metadata={
                "query": dict(request.query_params),
                "headers": {
                    "x-request-id": request.headers.get("x-request-id", ""),
                    "user-agent": request.headers.get("user-agent", ""),
                    "authorization": request.headers.get("authorization", ""),
                },
            },
        )
        if audit:
            async with AsyncSessionLocal() as session:
                session.add(audit)
                await session.commit()

    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
app.include_router(leads_router, prefix=settings.api_prefix)
app.include_router(timeline_router, prefix=settings.api_prefix)
app.include_router(sessions_router, prefix=settings.api_prefix)
app.include_router(messages_router, prefix=settings.api_prefix)
app.include_router(routing_rules_router, prefix=settings.api_prefix)
app.include_router(sequences_router, prefix=settings.api_prefix)
app.include_router(integrations_router, prefix=settings.api_prefix)
app.include_router(webhooks_router, prefix=settings.api_prefix)
