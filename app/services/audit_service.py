from app.core.config import get_settings
from app.models.audit_log import AuditLog
from app.security.masking import mask_pii


class AuditService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def build_entry(
        self,
        tenant_id: str,
        action: str,
        resource_type: str,
        status_code: int,
        actor_user_id: str | None,
        actor_api_key_id: str | None,
        resource_id: str | None,
        metadata: dict[str, object],
    ) -> AuditLog | None:
        if not self.settings.audit_log_enabled:
            return None

        stored_metadata = metadata
        if self.settings.pii_masking_enabled:
            stored_metadata = mask_pii(metadata)

        return AuditLog(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            actor_api_key_id=actor_api_key_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status_code=status_code,
            metadata_json=stored_metadata,
        )
