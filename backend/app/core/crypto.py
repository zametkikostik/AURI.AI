"""Lightweight secret encryption for org integration tokens (Fernet)."""

from __future__ import annotations

import base64
import hashlib

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def _fernet():
    key = getattr(settings, "settings_encryption_key", None) or ""
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet

        digest = hashlib.sha256(key.encode()).digest()
        fkey = base64.urlsafe_b64encode(digest)
        return Fernet(fkey)
    except Exception as e:
        logger.warning("fernet_init_failed", error=str(e))
        return None


def encrypt_secret(value: str | None) -> str | None:
    if value is None:
        return None
    f = _fernet()
    if not f:
        return value
    return f.encrypt(value.encode()).decode()


def decrypt_secret(value: str | None) -> str | None:
    if value is None:
        return None
    f = _fernet()
    if not f:
        return value
    try:
        return f.decrypt(value.encode()).decode()
    except Exception:
        return value
