from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import AuthContext
from app.core.dependencies import get_auth_context, require_admin
from app.db.session import get_db_session
from app.schemas.routing import RoutingRuleCreate, RoutingRuleResponse, RoutingRuleUpdate
from app.services.routing_service import RoutingService

router = APIRouter(
    prefix="/routing/rules",
    tags=["routing"],
    dependencies=[Depends(require_admin)],
)


@router.post("", response_model=RoutingRuleResponse)
async def create_rule(
    payload: RoutingRuleCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> RoutingRuleResponse:
    service = RoutingService(db)
    rule = await service.create_rule(tenant_id=auth.tenant_id, payload=payload.model_dump())
    return RoutingRuleResponse.model_validate(rule)


@router.get("", response_model=list[RoutingRuleResponse])
async def list_rules(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[RoutingRuleResponse]:
    service = RoutingService(db)
    rules = await service.list_rules(tenant_id=auth.tenant_id)
    return [RoutingRuleResponse.model_validate(item) for item in rules]


@router.get("/{rule_id}", response_model=RoutingRuleResponse)
async def get_rule(
    rule_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> RoutingRuleResponse:
    service = RoutingService(db)
    rule = await service.get_rule(tenant_id=auth.tenant_id, rule_id=rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="routing rule not found")
    return RoutingRuleResponse.model_validate(rule)


@router.patch("/{rule_id}", response_model=RoutingRuleResponse)
async def update_rule(
    rule_id: str,
    payload: RoutingRuleUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> RoutingRuleResponse:
    service = RoutingService(db)
    rule = await service.update_rule(
        tenant_id=auth.tenant_id,
        rule_id=rule_id,
        payload=payload.model_dump(exclude_unset=True),
    )
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="routing rule not found")
    return RoutingRuleResponse.model_validate(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    service = RoutingService(db)
    deleted = await service.delete_rule(tenant_id=auth.tenant_id, rule_id=rule_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="routing rule not found")
