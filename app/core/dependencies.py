from collections.abc import Callable
from typing import cast

from fastapi import Depends, HTTPException, Request, status

from app.core.context import AuthContext


def get_auth_context(request: Request) -> AuthContext:
    context = getattr(request.state, "auth_context", None)
    if context is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return cast(AuthContext, context)


def require_admin(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if auth.role not in {"admin", "owner"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="admin role required",
        )
    return auth


def require_editor(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if auth.role not in {"admin", "owner", "editor"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="editor role required",
        )
    return auth


def require_scope(scope: str) -> Callable[..., AuthContext]:
    def _checker(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
        scopes = auth.scopes or []
        if scope not in scopes and "*" not in scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"missing scope: {scope}",
            )
        return auth

    return _checker
