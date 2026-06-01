from app.db.session import AsyncSessionLocal
from app.services.routing_service import RoutingService


async def process_routing_event(payload: dict[str, str]) -> None:
    tenant_id = payload.get("tenant_id")
    lead_id = payload.get("lead_id")
    if not tenant_id or not lead_id:
        return

    async with AsyncSessionLocal() as db:
        service = RoutingService(db)
        await service.evaluate_and_apply(tenant_id=tenant_id, lead_id=lead_id)
