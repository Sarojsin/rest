"""Idempotency-Key header dependency — shared transport helper.

Contract (plan 21 §7): mutations that create revenue-critical aggregates
(orders, payments) require a client-supplied key; replays return the first
result. Scope keying moves to (branch_id, scope, key) in M4 (plan 17).

Lives in the shared kernel (not app.api) because modules compose it into
their routers — the api layer may never be imported by modules (02 §2.1).
"""

from fastapi import Header

from app.shared.errors import AppError


def idempotency_key(
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> str:
    if not idempotency_key or len(idempotency_key) < 8:
        raise AppError(
            400,
            "IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency key required",
            "Provide an Idempotency-Key header of at least 8 characters.",
        )
    return idempotency_key
