import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.config import get_settings


@dataclass
class WindowState:
    window_started_at: datetime
    count: int


class TenantRateLimiter:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._lock = asyncio.Lock()
        self._windows: dict[str, WindowState] = {}

    async def allow(self, tenant_id: str) -> bool:
        if not self.settings.rate_limit_enabled:
            return True

        now = datetime.now(UTC)
        async with self._lock:
            state = self._windows.get(tenant_id)
            if state is None:
                self._windows[tenant_id] = WindowState(window_started_at=now, count=1)
                return True

            if now - state.window_started_at >= timedelta(minutes=1):
                self._windows[tenant_id] = WindowState(window_started_at=now, count=1)
                return True

            if state.count >= self.settings.rate_limit_per_minute:
                return False

            state.count += 1
            return True


rate_limiter = TenantRateLimiter()
