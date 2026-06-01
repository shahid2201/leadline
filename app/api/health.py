from fastapi import APIRouter, HTTPException

from app.db.session import check_database_health

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> dict[str, str]:
    is_ready = await check_database_health()
    if not is_ready:
        raise HTTPException(status_code=503, detail="database unavailable")
    return {"status": "ready"}
