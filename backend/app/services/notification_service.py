"""
Notification service for sending alerts via email and webhooks.
"""
import asyncio
import logging
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx

from app.config import settings
from app.models.alert import AlertEvent, AlertRule

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications."""

    def __init__(self):
        self.smtp_host = getattr(settings, "SMTP_HOST", "") or ""
        self.smtp_port = getattr(settings, "SMTP_PORT", 587)
        self.smtp_user = getattr(settings, "SMTP_USER", "") or ""
        self.smtp_password = getattr(settings, "SMTP_PASSWORD", "") or ""
        self.smtp_from = getattr(settings, "SMTP_FROM", "alerts@seoman.io")
        self.smtp_use_tls = getattr(settings, "SMTP_USE_TLS", True)
        self.app_url = settings.CORS_ORIGINS.split(",")[0] if settings.CORS_ORIGINS else "http://localhost:3000"

    async def send_notifications(
        self, event: AlertEvent, rule: AlertRule
    ) -> list[dict]:
        """Send notifications for an alert event."""
        results = []

        for channel in rule.notification_channels:
            try:
                if channel == "email":
                    result = await self._send_email(event, rule)
                elif channel == "webhook":
                    result = await self._send_webhook(event, rule)
                else:
                    result = {
                        "channel": channel,
                        "success": False,
                        "error": "Unknown channel",
                    }

                results.append(result)
            except Exception as e:
                logger.error(f"Failed to send {channel} notification: {e}")
                results.append(
                    {
                        "channel": channel,
                        "success": False,
                        "error": str(e),
                        "sent_at": datetime.now(timezone.utc).isoformat(),
                    }
                )

        return results

    async def _send_email(self, event: AlertEvent, rule: AlertRule) -> dict:
        """Send email notification."""
        config = rule.notification_config.get("email", {})
        recipients = config.get("recipients", [])

        if not recipients:
            return {
                "channel": "email",
                "success": False,
                "error": "No recipients configured",
            }

        if not self.smtp_host:
            return {
                "channel": "email",
                "success": False,
                "error": "SMTP not configured",
            }

        # Build email
        subject = f"[SEOman Alert] {event.title}"
        body = self._build_email_body(event, config.get("include_details", True))

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.smtp_from
        msg["To"] = ", ".join(recipients)

        msg.attach(MIMEText(body, "html"))

        # Send in thread pool to not block
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._send_smtp,
                msg,
                recipients,
            )

            return {
                "channel": "email",
                "success": True,
                "recipients": recipients,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            return {
                "channel": "email",
                "success": False,
                "error": str(e),
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }

    def _send_smtp(self, msg: MIMEMultipart, recipients: list[str]):
        """Sync SMTP send (run in thread pool)."""
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.smtp_use_tls:
                server.starttls()
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.smtp_from, recipients, msg.as_string())

    def _build_email_body(self, event: AlertEvent, include_details: bool) -> str:
        """Build HTML email body."""
        severity_colors = {
            "info": "#3498db",
            "warning": "#f39c12",
            "critical": "#e74c3c",
        }
        color = severity_colors.get(event.severity.value, "#3498db")

        details_html = ""
        if include_details and event.details:
            details_items = "".join(
                f"<li><strong>{k}:</strong> {v}</li>"
                for k, v in event.details.items()
            )
            details_html = f"<h3>Details</h3><ul>{details_items}</ul>"

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: {color}; color: white; padding: 20px; border-radius: 5px 5px 0 0;">
                <h1 style="margin: 0;">{event.severity.value.upper()} Alert</h1>
            </div>
            <div style="padding: 20px; border: 1px solid #ddd; border-top: none;">
                <h2>{event.title}</h2>
                <p>{event.message or ''}</p>
                <p><strong>Alert Type:</strong> {event.alert_type.value}</p>
                <p><strong>Time:</strong> {event.created_at.isoformat() if event.created_at else 'N/A'}</p>
                {details_html}
                <hr>
                <p style="color: #666; font-size: 12px;">
                    This alert was generated by SEOman.
                    <a href="{self.app_url}/alerts/{event.id}">View in dashboard</a>
                </p>
            </div>
        </body>
        </html>
        """

    async def _send_webhook(self, event: AlertEvent, rule: AlertRule) -> dict:
        """Send webhook notification."""
        config = rule.notification_config.get("webhook", {})
        url = config.get("url")

        if not url:
            return {
                "channel": "webhook",
                "success": False,
                "error": "No webhook URL configured",
            }

        headers = config.get("headers", {})
        headers.setdefault("Content-Type", "application/json")

        # Build payload (compatible with Slack/Discord incoming webhooks)
        payload = self._build_webhook_payload(
            event, config.get("include_payload", True)
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

            return {
                "channel": "webhook",
                "success": True,
                "status_code": response.status_code,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
        except httpx.HTTPError as e:
            logger.error(f"Webhook send failed: {e}")
            return {
                "channel": "webhook",
                "success": False,
                "error": str(e),
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }

    def _build_webhook_payload(
        self, event: AlertEvent, include_payload: bool
    ) -> dict:
        """Build webhook payload (Slack/Discord compatible)."""
        severity_emoji = {
            "info": ":information_source:",
            "warning": ":warning:",
            "critical": ":rotating_light:",
        }
        emoji = severity_emoji.get(event.severity.value, ":bell:")

        # Slack-compatible format (also works with Discord via webhook adapters)
        payload = {
            "text": f"{emoji} *{event.title}*",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} {event.severity.value.upper()}: {event.title}",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Alert Type:*\n{event.alert_type.value}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Time:*\n{event.created_at.strftime('%Y-%m-%d %H:%M UTC') if event.created_at else 'N/A'}",
                        },
                    ],
                },
            ],
        }

        if event.message:
            payload["blocks"].append(
                {"type": "section", "text": {"type": "mrkdwn", "text": event.message}}
            )

        if include_payload and event.details:
            details_text = "\n".join(
                f"- *{k}:* {v}" for k, v in event.details.items()
            )
            payload["blocks"].append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Details:*\n{details_text}"},
                }
            )

        return payload

    async def test_email(self, recipients: list[str]) -> dict:
        """Test email configuration."""
        if not self.smtp_host:
            return {"success": False, "error": "SMTP not configured"}

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "[SEOman] Test Email"
            msg["From"] = self.smtp_from
            msg["To"] = ", ".join(recipients)
            msg.attach(
                MIMEText("<p>This is a test email from SEOman.</p>", "html")
            )

            await asyncio.get_event_loop().run_in_executor(
                None, self._send_smtp, msg, recipients
            )
            return {"success": True}
        except Exception as e:
            logger.error(f"Email test failed: {e}")
            return {"success": False, "error": str(e)}

    async def test_webhook(self, url: str, headers: dict = None) -> dict:
        """Test webhook configuration."""
        try:
            payload = {
                "text": "Test notification from SEOman",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "This is a test webhook from SEOman.",
                        },
                    }
                ],
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers or {"Content-Type": "application/json"},
                )
                response.raise_for_status()

            return {"success": True, "status_code": response.status_code}
        except Exception as e:
            logger.error(f"Webhook test failed: {e}")
            return {"success": False, "error": str(e)}
