"""Firebase Cloud Messaging (FCM) server-side sender.

Requires a service-account key downloaded from the Firebase Console:

    Project settings → Service accounts → Generate new private key
    → save as backend/firebase-service-account.json

The key is git-ignored (*service-account*.json) and never committed.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import firebase_admin
from firebase_admin import credentials, messaging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Module-level flag so we only initialize the Admin SDK once per process.
_initialized = False

# Must match ANDROID_CHANNEL_ID in apps/mobile/src/lib/fcm.ts. Without an
# explicit channel id Android drops web-console settings and uses the fallback.
ANDROID_CHANNEL_ID = "restaurant-staff"


# backend/ directory — the FCM key path may be given relative to it, to the
# repository root (backend/…), or to the current working directory.
_BACKEND_ROOT = Path(__file__).resolve().parents[4]


def _resolve_credentials_path(raw: str) -> Path:
    candidate = Path(raw).expanduser()
    if candidate.is_absolute() and candidate.exists():
        return candidate
    if candidate.exists():
        return candidate.resolve()
    for base in (_BACKEND_ROOT, _BACKEND_ROOT.parent):
        resolved = (base / candidate).resolve()
        if resolved.exists():
            return resolved
    return candidate


def _initialize() -> None:
    """Lazy-initialize the Firebase Admin SDK from the service-account key."""
    global _initialized
    if _initialized:
        return
    if not settings.firebase_credentials_path:
        # Not configured — FCM is silently disabled. No exception, so the rest
        # of the app keeps working (notifications just won't be delivered).
        logger.warning(
            "FCM is disabled: FIREBASE_CREDENTIALS_PATH is not set. "
            "Set it to firebase-service-account.json to enable push."
        )
        _initialized = True
        return
    try:
        key_path = _resolve_credentials_path(settings.firebase_credentials_path)
        cred = credentials.Certificate(str(key_path))
        firebase_admin.initialize_app(cred, {"projectId": settings.firebase_project_id or None})
        _initialized = True
        logger.info("FCM initialized from %s", key_path)
    except Exception:  # noqa: BLE001 — log and continue, don't break the app
        logger.exception("Failed to initialize Firebase Admin SDK. FCM disabled.")
        _initialized = True


def _client() -> None:
    """Ensure the SDK is initialized; no return value needed for send calls."""
    _initialize()


def send_to_token(
    token: str,
    *,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> str | None:
    """Send a single FCM message to one device token.

    Returns the FCM message ID on success, or None on failure (including
    unregistered/invalid tokens — callers should delete those tokens).
    """
    _initialize()
    if not firebase_admin._apps:
        return None
    try:
        message = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
        )
        return messaging.send(message)
    except messaging.UnregisteredError:
        logger.info("FCM token unregistered, will be pruned: %s", token[:12])
        return None
    except Exception:  # noqa: BLE001
        logger.exception("FCM send failed for token %s", token[:12])
        return None


def send_to_tokens(
    tokens: list[str],
    *,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> tuple[int, int, list[str]]:
    """Send to many tokens via multicast.

    Returns (sent_count, failed_count, message_ids).
    """
    sent, failed, message_ids, _invalid = _send_multicast(
        tokens, title=title, body=body, data=data
    )
    return sent, failed, message_ids


# Token errors that mean the FCM registration is permanently dead.
_PERMANENT_TOKEN_ERRORS = {"UnregisteredError", "SenderIdMismatchError", "InvalidArgumentError"}


def _send_multicast(
    tokens: list[str],
    *,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> tuple[int, int, list[str], list[str]]:
    """Multicast send that also reports permanently-invalid tokens."""
    _initialize()
    if not firebase_admin._apps:
        return 0, len(tokens), [], []
    if not tokens:
        return 0, 0, [], []

    message_ids: list[str] = []
    invalid: list[str] = []
    try:
        response = messaging.send_each_for_multicast(
            messaging.MulticastMessage(
                tokens=tokens,
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        channel_id=ANDROID_CHANNEL_ID,
                        sound="default",
                        default_vibrate_timings=True,
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(sound="default", badge=1)
                    )
                ),
            )
        )
        for token, result in zip(tokens, response.responses, strict=False):
            if result.success:
                message_ids.append(result.message_id)
            elif type(result.exception).__name__ in _PERMANENT_TOKEN_ERRORS:
                invalid.append(token)
        return response.success_count, response.failure_count, message_ids, invalid
    except Exception:  # noqa: BLE001
        logger.exception("FCM multicast failed")
        return 0, len(tokens), [], []


def _prune_tokens(db: Any, tokens: list[str]) -> None:
    """Delete registration tokens FCM reports as permanently invalid."""
    if not tokens:
        return
    from app.modules.notifications.models import DeviceToken

    db.query(DeviceToken).filter(DeviceToken.token.in_(tokens)).delete(synchronize_session=False)
    logger.info("Pruned %d invalid FCM token(s)", len(tokens))


def send_to_restaurant(
    db: Any,
    *,
    restaurant_id: str,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
    roles: list[str] | None = None,
) -> tuple[int, int, list[str]]:
    """Send an FCM message to a restaurant's devices.

    ``roles`` limits delivery to staff whose membership role is in the list
    (e.g. only kitchen devices for a new kitchen ticket). Omit it to reach
    every registered device.
    """
    from sqlalchemy import and_

    from app.modules.identity.models import User
    from app.modules.notifications.models import DeviceToken
    from app.modules.tenancy.models import RestaurantMembership

    _initialize()
    if not firebase_admin._apps:
        return 0, 0, []

    query = (
        db.query(DeviceToken.token)
        .join(User, DeviceToken.user_id == User.id)
        .join(
            RestaurantMembership,
            and_(
                RestaurantMembership.user_id == DeviceToken.user_id,
                RestaurantMembership.restaurant_id == DeviceToken.restaurant_id,
            ),
        )
        .filter(
            DeviceToken.restaurant_id == restaurant_id,
            RestaurantMembership.status == "ACTIVE",
        )
    )
    if roles:
        query = query.filter(RestaurantMembership.role.in_(roles))

    tokens = [row.token for row in query.all()]
    if not tokens:
        return 0, 0, []

    sent, failed, message_ids, invalid = _send_multicast(
        tokens, title=title, body=body, data=data
    )
    if invalid:
        _prune_tokens(db, invalid)
        db.commit()
    return sent, failed, message_ids


def _render_message(
    event_type: str, aggregate_type: str, payload: dict[str, Any]
) -> tuple[str, str]:
    """Fallback title/body for outbox rows written without explicit copy."""
    title = payload.get("title")
    body = payload.get("body")
    if title and body:
        return str(title), str(body)

    table = payload.get("table_name") or payload.get("table") or "A table"
    ticket = payload.get("ticket_number")
    amount = payload.get("amount_minor")

    defaults = {
        "order.pending_confirmation": (
            "New table order",
            f"{table} placed an order · waiting for confirmation",
        ),
        "order.accepted": ("Order confirmed", f"{table} · order sent to the kitchen"),
        "order.escalated": ("Order escalated", f"{table} · an order needs supervisor attention"),
        "service_call.requested": ("Guest needs service", f"{table} requested service"),
        "bill.issued": ("Bill issued", f"{table} · bill ready for payment"),
        "payment.recorded": ("Payment received", f"{table} · payment recorded"),
    }
    fallback_title, fallback_body = defaults.get(
        event_type, ("Restaurant update", f"New {aggregate_type} activity")
    )
    if ticket and event_type.startswith("service_call"):
        fallback_body = f"Ticket #{ticket} is ready for pickup"
    if amount and event_type == "payment.recorded":
        try:
            fallback_body = f"Payment received · {float(amount) / 100:.2f}"
        except (TypeError, ValueError):
            pass
    return str(title or fallback_title), str(body or fallback_body)


def process_outbox(db: Any, limit: int = 100) -> int:
    """Drain unprocessed outbox_events and deliver them as FCM notifications.

    Each outbox event's payload should contain ``title``, ``body``, and
    optional ``data`` keys, plus either ``restaurant_id`` (broadcast to all
    devices of that restaurant) or ``tokens`` (explicit device list).

    Marks events processed on success, bumps attempt_count on failure.
    Returns the number of events processed.
    """
    from app.modules.notifications.models import OutboxEvent

    _initialize()
    if not firebase_admin._apps:
        return 0

    events = (
        db.query(OutboxEvent)
        .filter(OutboxEvent.processed_at.is_(None))
        .order_by(OutboxEvent.occurred_at)
        .limit(limit)
        .all()
    )
    if not events:
        return 0

    processed = 0
    now = datetime.now(UTC)
    for event in events:
        try:
            payload = json.loads(event.payload or "{}")
            if not isinstance(payload, dict):
                payload = {}
            title, body = _render_message(
                event.event_type, event.aggregate_type, payload
            )
            data = {str(k): str(v) for k, v in (payload.get("data") or {}).items()}
            data.setdefault("event_type", event.event_type)
            data.setdefault("aggregate_type", event.aggregate_type)
            data.setdefault("aggregate_id", str(event.aggregate_id))
            restaurant_id = str(payload.get("restaurant_id", event.restaurant_id))
            tokens = payload.get("tokens")
            roles = payload.get("roles")

            if tokens:
                sent, failed, _, invalid = _send_multicast(
                    [str(t) for t in tokens], title=title, body=body, data=data
                )
                if invalid:
                    _prune_tokens(db, invalid)
            else:
                sent, failed, _ = send_to_restaurant(
                    db,
                    restaurant_id=restaurant_id,
                    title=title,
                    body=body,
                    data=data,
                    roles=[str(r) for r in roles] if roles else None,
                )

            event.processed_at = now
            processed += 1
        except Exception:  # noqa: BLE001
            logger.exception("Outbox event %s processing failed", event.id)
            event.attempt_count = (event.attempt_count or 0) + 1
            if event.attempt_count >= 5:
                # Give up after 5 attempts to avoid poison-pill events.
                event.processed_at = now
            processed += 1

    db.commit()
    return processed
