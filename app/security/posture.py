import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def report_security_posture() -> None:
    settings = get_settings()

    if not settings.app_data_encryption_key:
        logger.warning(
            "APP_DATA_ENCRYPTION_KEY is not set; "
            "sensitive integration auth data is not encrypted"
        )

    if settings.jwt_secret in {"", "change-me", "secret"}:
        logger.warning("JWT secret appears weak or default; rotate to a strong secret")

    if not settings.rate_limit_enabled:
        logger.warning("Tenant-aware rate limiting is disabled")

    if not settings.audit_log_enabled:
        logger.warning("Audit logging is disabled")
