from typing import cast

from fastapi import HTTPException, Request

from app.core.context import AuthContext


def get_auth_context(request: Request) -> AuthContext:
    context = getattr(request.state, "auth_context", None)
    if context is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return cast(AuthContext, context)
