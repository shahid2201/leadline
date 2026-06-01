from fastapi import APIRouter, Request

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def me(request: Request) -> dict[str, str | list[str] | None]:
    context = request.state.auth_context
    return {
        "auth_type": context.auth_type,
        "tenant_id": context.tenant_id,
        "user_id": context.user_id,
        "api_key_id": context.api_key_id,
        "scopes": context.scopes,
        "role": context.role,
    }
