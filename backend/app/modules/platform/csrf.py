"""CSRF and Origin enforcement for the platform realm (PA-0.6).

Every non-GET platform request must:

1. come from ``PLATFORM_ADMIN_ORIGIN`` (Origin, falling back to Referer), and
2. carry ``X-CSRF-Token`` equal to the readable ``platform_csrf`` cookie,
   except for documented pre-session and refresh bootstrap routes.

The exemptions are bootstrap endpoints that either run before a CSRF cookie
exists (login, MFA), or are explicitly SameSite=Strict + origin-checked
(``/auth/refresh`` — see plan 03 §3.4).
"""

from __future__ import annotations

import hmac
from urllib.parse import urlsplit

from fastapi import Request

from app.core.config import settings
from app.modules.platform.constants import PLATFORM_CSRF_COOKIE, PLATFORM_CSRF_HEADER
from app.shared.errors import AppError

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

# Paths are full request paths (platform router mounted at /api/platform).
CSRF_EXEMPT_PATHS = frozenset(
    {
        "/api/platform/auth/login",
        "/api/platform/auth/mfa/enroll/start",
        "/api/platform/auth/mfa/enroll/verify",
        "/api/platform/auth/mfa/verify",
        "/api/platform/auth/refresh",
    }
)

# Token-bearing public routes cannot present a CSRF cookie before the target
# account exists. They are single-use, hashed-at-rest tokens and still pass the
# Origin check below.
CSRF_EXEMPT_PREFIXES = (
    "/api/platform/auth/invitations/",
    "/api/platform/auth/password-reset/",
    # Public self-service surface (PA-01.4): the caller has no session and
    # therefore no CSRF cookie yet. Origin is still enforced for these routes.
    "/api/platform/public/",
)


def _is_csrf_exempt(path: str) -> bool:
    return path in CSRF_EXEMPT_PATHS or path.startswith(CSRF_EXEMPT_PREFIXES)


def _normalize(origin: str) -> str:
    return origin.strip().rstrip("/")


def request_origin(request: Request) -> str | None:
    origin = request.headers.get("origin")
    if origin:
        return _normalize(origin)
    referer = request.headers.get("referer")
    if referer:
        parts = urlsplit(referer)
        if parts.scheme and parts.netloc:
            return f"{parts.scheme}://{parts.netloc}"
    return None


def _allowed_origins(request: Request) -> list[str]:
    allowed = list(settings.platform_admin_origin_list)
    path = request.url.path
    # Token-based public flows (invitations, password reset) are accepted from the
    # tenant/staff app origin as well as the admin console origin.
    if _is_csrf_exempt(path):
        tenant_origin = (settings.platform_tenant_origin or "").strip().rstrip("/")
        if tenant_origin and tenant_origin not in allowed:
            allowed.append(tenant_origin)
        invite_base = (settings.invitation_base_url or "").strip().rstrip("/")
        if invite_base and invite_base not in allowed:
            allowed.append(invite_base)
    return allowed


def validate_origin(request: Request) -> None:
    allowed = _allowed_origins(request)
    origin = request_origin(request)
    if (
        not allowed
        or origin is None
        or not any(hmac.compare_digest(origin, candidate) for candidate in allowed)
    ):
        raise AppError(
            403,
            "ORIGIN_INVALID",
            "Forbidden",
            "The request origin is not allowed.",
        )


def validate_csrf(request: Request) -> None:
    cookie = request.cookies.get(PLATFORM_CSRF_COOKIE) or ""
    header = request.headers.get(PLATFORM_CSRF_HEADER) or ""
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        raise AppError(
            403,
            "CSRF_INVALID",
            "Forbidden",
            "The request could not be verified.",
        )


def platform_request_guard(request: Request) -> None:
    """FastAPI dependency applied to the whole platform router."""
    if request.method in SAFE_METHODS:
        return

    validate_origin(request)
    if _is_csrf_exempt(request.url.path):
        return
    validate_csrf(request)
