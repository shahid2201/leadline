from dataclasses import dataclass


@dataclass
class AuthContext:
    auth_type: str
    tenant_id: str
    user_id: str | None = None
    api_key_id: str | None = None
    role: str | None = None
    scopes: list[str] | None = None
