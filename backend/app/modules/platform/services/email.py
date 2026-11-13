"""Email delivery service for platform invitations (Plan 14).

Two backends:

* ``smtp`` — real SMTP delivery for production.
* ``log``  — writes the invitation link to the application log for local/dev
  testing (no real email is sent).

Administrators never receive or see the owner's password. The raw invitation
token travels only in the email (and, in dev, the log).
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

import httpx
from app.core.config import settings

logger = logging.getLogger("app.platform.email")


class EmailService(Protocol):
    """Send an invitation email."""

    def send_invitation(
        self,
        *,
        to_email: str,
        to_name: str,
        restaurant_name: str,
        token: str,
        accept_url: str,
        expires_at: str,
    ) -> None:
        """Send the invitation email. Raises on permanent failure."""
        ...


class LogEmailService:
    """Dev backend: log the invitation link instead of sending real email."""

    def send_invitation(
        self,
        *,
        to_email: str,
        to_name: str,
        restaurant_name: str,
        token: str,
        accept_url: str,
        expires_at: str,
    ) -> None:
        logger.info(
            "INVITATION_EMAIL (log backend, not sent): "
            "to=%s name=%s restaurant=%s token=%s accept_url=%s expires_at=%s",
            to_email,
            to_name,
            restaurant_name,
            token,
            accept_url,
            expires_at,
        )


class SmtpEmailService:
    """Production backend: deliver over SMTP."""

    def __init__(self) -> None:
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_password
        self.from_email = settings.smtp_from or settings.smtp_user or "noreply@localhost"

    def send_invitation(
        self,
        *,
        to_email: str,
        to_name: str,
        restaurant_name: str,
        token: str,
        accept_url: str,
        expires_at: str,
    ) -> None:
        subject = f"Set up your account for {restaurant_name}"
        body = _invitation_body(
            restaurant_name=restaurant_name,
            owner_name=to_name,
            owner_email=to_email,
            accept_url=accept_url,
            ttl_hours=settings.invitation_ttl_hours,
        )

        msg = EmailMessage()
        msg["From"] = self.from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if self.user and self.password:
                smtp.login(self.user, self.password)
            smtp.send_message(msg)

        logger.info(
            "INVITATION_EMAIL sent: to=%s restaurant=%s ttl_hours=%s",
            to_email,
            restaurant_name,
            settings.invitation_ttl_hours,
        )


class ResendEmailService:
    """HTTP email backend via Resend (https://resend.com).

    Used when outbound SMTP is blocked (e.g. Render free tier). Requires
    ``RESEND_API_KEY`` to be set in the environment.
    """

    def __init__(self) -> None:
        self.api_key = settings.resend_api_key
        self.from_email = settings.resend_from or "noreply@localhost"
        if not self.api_key:
            raise RuntimeError("RESEND_API_KEY is not set; cannot send email via Resend")

    def send_invitation(
        self,
        *,
        to_email: str,
        to_name: str,
        restaurant_name: str,
        token: str,
        accept_url: str,
        expires_at: str,
    ) -> None:
        subject = f"Set up your account for {restaurant_name}"
        body = _invitation_body(
            restaurant_name=restaurant_name,
            owner_name=to_name,
            owner_email=to_email,
            accept_url=accept_url,
            ttl_hours=settings.invitation_ttl_hours,
        )

        with httpx.Client(timeout=15) as client:
            resp = client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": self.from_email,
                    "to": [to_email],
                    "subject": subject,
                    "text": body,
                },
            )
            if resp.status_code >= 300:
                raise RuntimeError(
                    f"Resend API error {resp.status_code}: {resp.text[:300]}"
                )

        logger.info(
            "INVITATION_EMAIL sent via Resend: to=%s restaurant=%s ttl_hours=%s",
            to_email,
            restaurant_name,
            settings.invitation_ttl_hours,
        )


def _invitation_body(
    *,
    restaurant_name: str,
    owner_name: str,
    owner_email: str,
    accept_url: str,
    ttl_hours: int,
) -> str:
    return (
        f"Hello {owner_name},\n\n"
        f"{restaurant_name} has been registered on our restaurant management "
        f"platform.\n\n"
        f"Your owner account is ready for setup:\n"
        f"- Restaurant: {restaurant_name}\n"
        f"- Account: {owner_email}\n"
        f"- Role: Owner\n\n"
        f"Click the secure link below to verify your email and create your "
        f"password:\n"
        f"{accept_url}\n\n"
        f"This link expires after {ttl_hours} hours and can be used only once.\n\n"
        f"If you did not sign up for this, you can ignore this email.\n"
    )


def get_email_service() -> EmailService:
    """Return the configured email service backend."""
    backend = settings.email_backend
    if backend == "smtp":
        return SmtpEmailService()
    if backend == "resend":
        return ResendEmailService()
    # Default to log backend for dev / tests.
    return LogEmailService()
