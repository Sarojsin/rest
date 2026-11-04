"""TOTP and recovery-code helpers for the platform realm (PA-0.5).

Implemented with the standard library (RFC 6238 / RFC 4226) so the platform
dependency surface stays small. Secrets are generated here and encrypted at
rest by ``services.crypto``.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import struct
from datetime import UTC, datetime
from urllib.parse import quote, urlencode

TOTP_STEP_SECONDS = 30
TOTP_DIGITS = 6
TOTP_WINDOW = 1

# Unambiguous alphabet: no I, L, O, 0, 1.
_RECOVERY_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _decode_secret(secret: str) -> bytes:
    normalized = secret.strip().replace(" ", "").upper()
    padding = "=" * ((8 - len(normalized) % 8) % 8)
    return base64.b32decode(normalized + padding, casefold=True)


def totp_at(secret: str, at: datetime, *, step: int = TOTP_STEP_SECONDS) -> str:
    counter = int(at.timestamp()) // step
    digest = hmac.new(
        _decode_secret(secret), struct.pack(">Q", counter), hashlib.sha1
    ).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(value % (10**TOTP_DIGITS)).zfill(TOTP_DIGITS)


def verify_totp(
    secret: str,
    code: str,
    *,
    at: datetime | None = None,
    window: int = TOTP_WINDOW,
) -> bool:
    candidate = (code or "").strip().replace(" ", "")
    if len(candidate) != TOTP_DIGITS or not candidate.isdigit():
        return False

    now = at or datetime.now(UTC)
    for offset in range(-window, window + 1):
        moment = datetime.fromtimestamp(now.timestamp() + offset * TOTP_STEP_SECONDS, tz=UTC)
        if hmac.compare_digest(totp_at(secret, moment), candidate):
            return True
    return False


def provisioning_uri(secret: str, *, email: str, issuer: str) -> str:
    label = quote(f"{issuer}:{email}")
    params = urlencode(
        {
            "secret": secret,
            "issuer": issuer,
            "algorithm": "SHA1",
            "digits": TOTP_DIGITS,
            "period": TOTP_STEP_SECONDS,
        }
    )
    return f"otpauth://totp/{label}?{params}"


def generate_recovery_codes(count: int) -> list[str]:
    codes: list[str] = []
    for _ in range(count):
        raw = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(8))
        codes.append(f"{raw[:4]}-{raw[4:]}")
    return codes


def _normalize_recovery_code(code: str) -> str:
    return "".join(ch for ch in (code or "").upper() if ch.isalnum())


def _hash_recovery_code(code: str) -> str:
    return hashlib.sha256(_normalize_recovery_code(code).encode("utf-8")).hexdigest()


def hash_recovery_codes(codes: list[str]) -> str:
    return json.dumps([_hash_recovery_code(code) for code in codes])


def verify_and_consume_recovery_code(
    stored_json: str | None, code: str
) -> tuple[bool, str | None]:
    """Return ``(matched, remaining_json)``. A code is single use."""
    if not stored_json:
        return False, None
    try:
        hashes = json.loads(stored_json)
    except (TypeError, ValueError):
        return False, None
    if not isinstance(hashes, list):
        return False, None

    candidate = _hash_recovery_code(code)
    for index, stored in enumerate(hashes):
        if hmac.compare_digest(str(stored), candidate):
            remaining = hashes[:index] + hashes[index + 1 :]
            return True, json.dumps(remaining)
    return False, stored_json
