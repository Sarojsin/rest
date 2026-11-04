"""Platform cookie helpers (PA-0.5).

Access and refresh tokens are HttpOnly; only the CSRF token is readable by the
admin SPA. Cookies are host-only (no Domain attribute) so they are pinned to
the platform API host.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Response

from app.core.config import settings
from app.modules.platform.constants import (
    PLATFORM_ACCESS_COOKIE,
    PLATFORM_ACCESS_PATH,
    PLATFORM_CSRF_COOKIE,
    PLATFORM_REFRESH_COOKIE,
    PLATFORM_REFRESH_PATH,
)
from app.modules.platform.services.auth import IssuedSession

_CSRF_PATH = "/"


def _max_age(expires_at: datetime) -> int:
    return max(0, int((expires_at - datetime.now(UTC)).total_seconds()))


def set_auth_cookies(response: Response, session: IssuedSession) -> None:
    secure = settings.platform_cookie_secure
    response.set_cookie(
        PLATFORM_ACCESS_COOKIE,
        session.access_token,
        max_age=session.expires_in,
        path=PLATFORM_ACCESS_PATH,
        httponly=True,
        secure=secure,
        samesite="strict",
    )
    response.set_cookie(
        PLATFORM_REFRESH_COOKIE,
        session.refresh_token,
        max_age=_max_age(session.refresh_expires_at),
        path=PLATFORM_REFRESH_PATH,
        httponly=True,
        secure=secure,
        samesite="strict",
    )
    response.set_cookie(
        PLATFORM_CSRF_COOKIE,
        session.csrf_token,
        max_age=session.expires_in,
        path=_CSRF_PATH,
        httponly=False,
        secure=secure,
        samesite="strict",
    )


def set_access_cookie(response: Response, token: str, expires_in: int) -> None:
    response.set_cookie(
        PLATFORM_ACCESS_COOKIE,
        token,
        max_age=expires_in,
        path=PLATFORM_ACCESS_PATH,
        httponly=True,
        secure=settings.platform_cookie_secure,
        samesite="strict",
    )


def clear_auth_cookies(response: Response) -> None:
    secure = settings.platform_cookie_secure
    response.delete_cookie(
        PLATFORM_ACCESS_COOKIE,
        path=PLATFORM_ACCESS_PATH,
        secure=secure,
        httponly=True,
        samesite="strict",
    )
    response.delete_cookie(
        PLATFORM_REFRESH_COOKIE,
        path=PLATFORM_REFRESH_PATH,
        secure=secure,
        httponly=True,
        samesite="strict",
    )
    response.delete_cookie(
        PLATFORM_CSRF_COOKIE,
        path=_CSRF_PATH,
        secure=secure,
        httponly=False,
        samesite="strict",
    )
