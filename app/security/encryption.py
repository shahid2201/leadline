import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet

from app.core.config import get_settings


class EncryptionService:
    def __init__(self) -> None:
        settings = get_settings()
        key_material = settings.app_data_encryption_key
        self._fernet: Fernet | None = None
        if key_material:
            digest = hashlib.sha256(key_material.encode("utf-8")).digest()
            key = base64.urlsafe_b64encode(digest)
            self._fernet = Fernet(key)

    def encrypt_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._fernet is None:
            return payload
        raw = json.dumps(payload).encode("utf-8")
        token = self._fernet.encrypt(raw).decode("utf-8")
        return {"encrypted": token}

    def decrypt_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._fernet is None or "encrypted" not in payload:
            return payload
        raw = self._fernet.decrypt(str(payload["encrypted"]).encode("utf-8"))
        decoded = json.loads(raw.decode("utf-8"))
        if isinstance(decoded, dict):
            return decoded
        return {}
