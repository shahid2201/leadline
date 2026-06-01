import asyncio
import os
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./leadline_test.db")
os.environ.setdefault("AUTO_CREATE_TABLES", "true")
os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
os.environ.setdefault("OPENAI_API_KEY", "")

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.main import app


async def _reset_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    asyncio.run(_reset_database())
    with TestClient(app) as test_client:
        yield test_client


def auth_headers(
    tenant_id: str,
    user_id: str = "user-1",
    role: str = "admin",
) -> dict[str, str]:
    settings = get_settings()
    token = jwt.encode(
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "role": role,
            "scopes": ["read", "write"],
            "aud": settings.jwt_audience,
            "iss": settings.jwt_issuer,
            "exp": datetime.now(UTC) + timedelta(minutes=30),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}
