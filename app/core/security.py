import secrets
from dataclasses import dataclass
from typing import cast

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass
class RawAPIKey:
    display: str
    prefix: str


def hash_secret(secret: str) -> str:
    return cast(str, pwd_context.hash(secret))


def verify_secret(raw_secret: str, hashed_secret: str) -> bool:
    return cast(bool, pwd_context.verify(raw_secret, hashed_secret))


def build_api_key(prefix: str = "ll_live") -> RawAPIKey:
    random_part = secrets.token_urlsafe(24)
    token = f"{prefix}_{random_part}"
    # Keep a deterministic lookup prefix while storing full secret hash.
    return RawAPIKey(display=token, prefix=token[:16])
