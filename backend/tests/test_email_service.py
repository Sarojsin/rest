"""Unit tests for Plan 14 — Owner Invitation Email Delivery.

Tests the email service backends and invitation body rendering.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.modules.platform.services.email import (
    LogEmailService,
    SmtpEmailService,
    _invitation_body,
    get_email_service,
)


class TestInvitationBody:
    def test_body_contains_required_fields(self):
        body = _invitation_body(
            restaurant_name="MAISON Restaurant",
            owner_name="Restaurant Owner",
            owner_email="owner@maison.example",
            accept_url="https://example.com/invite/abc123",
            ttl_hours=72,
        )
        assert "MAISON Restaurant" in body
        assert "Restaurant Owner" in body
        assert "owner@maison.example" in body
        assert "https://example.com/invite/abc123" in body
        assert "72 hours" in body
        assert "Role: Owner" in body


class TestLogEmailService:
    def test_send_invitation_logs_without_error(self, caplog):
        service = LogEmailService()
        with caplog.at_level("INFO", logger="app.platform.email"):
            service.send_invitation(
                to_email="owner@maison.example",
                to_name="Restaurant Owner",
                restaurant_name="MAISON Restaurant",
                token="abc123",
                accept_url="https://example.com/invite/abc123",
                expires_at="2026-11-20T15:00:00+05:45",
            )
        assert "INVITATION_EMAIL (log backend" in caplog.text
        assert "owner@maison.example" in caplog.text


class TestGetEmailService:
    def test_returns_log_backend_by_default(self):
        service = get_email_service()
        assert isinstance(service, LogEmailService)

    @patch("app.modules.platform.services.email.settings.email_backend", "smtp")
    def test_returns_smtp_backend_when_configured(self):
        service = get_email_service()
        assert isinstance(service, SmtpEmailService)


class TestSmtpEmailService:
    def test_instantiates_from_settings(self):
        service = SmtpEmailService()
        assert service.host == "localhost"
        assert service.port == 1025
        assert service.from_email == "noreply@localhost"
