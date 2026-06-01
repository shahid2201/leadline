import logging
from datetime import UTC, datetime

from jose import JWTError, jwt
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core.config import get_settings
from app.core.context import AuthContext
from app.core.security import verify_secret
from app.db.session import AsyncSessionLocal
from app.models.api_key import APIKey
from app.security.rate_limit import rate_limiter

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, excluded_paths: set[str] | None = None) -> None:
        super().__init__(app)
        self.settings = get_settings()
        self.excluded_paths = excluded_paths or {
            "/healthz",
            "/readyz",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/v1/webhooks/svix",
            "/v1/webhooks/hubspot",
        }

    async def dispatch(
        self,
        request: StarletteRequest,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.url.path in self.excluded_paths or request.url.path.startswith("/docs"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "missing bearer token"})

        token = auth_header.replace("Bearer ", "", 1).strip()
        if not token:
            return JSONResponse(status_code=401, content={"detail": "empty bearer token"})

        context = await self._resolve_context(token)
        if context is None:
            return JSONResponse(status_code=401, content={"detail": "invalid credentials"})

        tenant_header = request.headers.get("X-Tenant-ID")
        if (
            tenant_header
            and self.settings.enforce_tenant_header_match
            and tenant_header != context.tenant_id
        ):
            return JSONResponse(status_code=403, content={"detail": "tenant mismatch"})

        allowed = await rate_limiter.allow(context.tenant_id)
        if not allowed:
            return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})

        request.state.auth_context = context
        response = await call_next(request)
        return response

    async def _resolve_context(self, token: str) -> AuthContext | None:
        if token.count(".") == 2:
            jwt_context = self._resolve_jwt_context(token)
            if jwt_context is not None:
                return jwt_context

        return await self._resolve_api_key_context(token)

    def _resolve_jwt_context(self, token: str) -> AuthContext | None:
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret,
                algorithms=[self.settings.jwt_algorithm],
                audience=self.settings.jwt_audience,
                issuer=self.settings.jwt_issuer,
                options={"verify_exp": True},
            )
        except JWTError:
            return None

        tenant_id = payload.get("tenant_id")
        user_id = payload.get("user_id")
        role = payload.get("role")
        scopes = payload.get("scopes", [])
        if not tenant_id:
            return None

        return AuthContext(
            auth_type="jwt",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            role=str(role) if role else None,
            scopes=list(scopes) if isinstance(scopes, list) else [],
        )

    async def _resolve_api_key_context(self, token: str) -> AuthContext | None:
        prefix = token[:16]
        async with AsyncSessionLocal() as session:
            stmt = select(APIKey).where(APIKey.key_prefix == prefix, APIKey.status == "active")
            result = await session.execute(stmt)
            api_keys = result.scalars().all()

            for api_key in api_keys:
                if verify_secret(token, api_key.key_hash):
                    api_key.last_used_at = datetime.now(UTC)
                    await session.commit()
                    return AuthContext(
                        auth_type="api_key",
                        tenant_id=api_key.tenant_id,
                        api_key_id=api_key.id,
                        scopes=api_key.scopes,
                    )

            logger.warning("Failed API key auth", extra={"key_prefix": prefix})
            return None
