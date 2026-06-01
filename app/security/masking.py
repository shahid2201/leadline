import re
from typing import Any

_EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
_PHONE_RE = re.compile(r"(\+?\d[\d\-\s]{7,}\d)")


def mask_text(value: str) -> str:
    masked = _EMAIL_RE.sub("***@\\2", value)
    masked = _PHONE_RE.sub("***PHONE***", masked)
    return masked


def mask_pii(value: Any) -> Any:
    if isinstance(value, str):
        return mask_text(value)
    if isinstance(value, list):
        return [mask_pii(item) for item in value]
    if isinstance(value, dict):
        masked: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in {
                "authorization",
                "api_key",
                "token",
                "secret",
                "password",
            }:
                masked[key] = "***REDACTED***"
            else:
                masked[key] = mask_pii(item)
        return masked
    return value
