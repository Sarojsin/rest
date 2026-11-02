"""Internal event bus skeleton (D15, plan 13 §0 / 02 §2.3).

Phase 0: registry and typed base only — no consumers yet. Handlers bind to
Pydantic event models, never to raw dicts; payloads are fabricated by
construction. The outbox dispatcher (notifications module) invokes these
handlers idempotently in Phase 2.
"""

from collections.abc import Callable

from pydantic import BaseModel


class BusEvent(BaseModel):
    """Base for all typed internal events (13 §0 rule 4: versioned)."""

    event_version: int = 1


_REGISTRY: dict[str, type[BusEvent]] = {}
_HANDLERS: dict[str, list[Callable[[BusEvent], None]]] = {}


def register_event(event_type: str, model: type[BusEvent]) -> None:
    if event_type in _REGISTRY and _REGISTRY[event_type] is not model:
        raise ValueError(f"Event type {event_type!r} already registered with a different model.")
    _REGISTRY[event_type] = model


def register_handler(event_type: str, handler: Callable[[BusEvent], None]) -> None:
    _HANDLERS.setdefault(event_type, []).append(handler)


def registered_event_types() -> list[str]:
    return sorted(_REGISTRY)


def model_for(event_type: str) -> type[BusEvent] | None:
    return _REGISTRY.get(event_type)


def handlers_for(event_type: str) -> list[Callable[[BusEvent], None]]:
    return list(_HANDLERS.get(event_type, []))
