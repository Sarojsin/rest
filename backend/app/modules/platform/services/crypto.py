"""Symmetric encryption for platform MFA secrets (PA-0.5).

Fernet (AES-128-CBC + HMAC-SHA256) with a key derived from
``PLATFORM_MFA_KEY``. The key is never logged and no secret is returned to a
client after enrollment completes.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet(key: str | None = None) -> Fernet:
    material = key if key is not None else settings.platform_mfa_key
    if not material:
        raise RuntimeError("PLATFORM_MFA_KEY is not configured")
    derived = base64.urlsafe_b64encode(hashlib.sha256(material.encode("utf-8")).digest())
    return Fernet(derived)


def encrypt_secret(plaintext: str, *, key: str | None = None) -> str:
    return _fernet(key).encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_secret(ciphertext: str, *, key: str | None = None) -> str:
    try:
        return _fernet(key).decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("Platform MFA secret could not be decrypted") from exc
