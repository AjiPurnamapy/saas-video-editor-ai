"""
Email service.

Sends transactional emails for verification and password reset.
Uses aiosmtplib for async SMTP delivery.

In development mode (no SMTP configured), emails are logged to
console instead of sent — no SMTP server needed for local dev.
"""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


async def _send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> bool:
    """Send an email via SMTP or log it in development.

    Args:
        to_email: Recipient email address.
        subject: Email subject line.
        html_body: HTML version of the email body.
        text_body: Plain text fallback.

    Returns:
        True if sent/logged successfully.
    """
    settings = get_settings()

    # Development fallback: log email instead of sending
    if not settings.smtp_host or settings.app_env == "development":
        logger.info(
            "EMAIL (dev mode — not sent)\n"
            "  To: %s\n"
            "  Subject: %s\n"
            "  Body:\n%s",
            to_email, subject, text_body,
        )
        return True

    # Build MIME message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        import aiosmtplib

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            use_tls=settings.smtp_port == 465,
            start_tls=settings.smtp_port == 587,
        )
        logger.info("Email sent: to=%s subject=%s", to_email, subject)
        return True
    except Exception as exc:
        logger.error("Failed to send email: to=%s error=%s", to_email, str(exc))
        return False


async def send_verification_email(email: str, token: str) -> bool:
    """Send an email verification link.

    Args:
        email: The recipient's email address.
        token: The signed verification token.

    Returns:
        True if sent successfully.
    """
    settings = get_settings()
    frontend_url = settings.frontend_url.rstrip("/")
    # S-05 FIX: Use URL fragment (#) instead of query param (?)
    # Fragments are NOT sent in Referer headers and NOT logged by servers
    verify_url = f"{frontend_url}/verify-email#token={token}"

    subject = "Verify Your Email — AI Video Editor"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #333;">Welcome to AI Video Editor! 🎬</h2>
        <p>Please verify your email address by clicking the button below:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{verify_url}"
               style="background-color: #6366f1; color: white; padding: 14px 28px;
                      text-decoration: none; border-radius: 8px; font-weight: bold;
                      display: inline-block;">
                Verify Email
            </a>
        </div>
        <p style="color: #666; font-size: 14px;">
            Or copy and paste this link into your browser:<br>
            <a href="{verify_url}" style="color: #6366f1;">{verify_url}</a>
        </p>
        <p style="color: #999; font-size: 12px;">
            This link will expire in 24 hours. If you didn't create an account,
            you can safely ignore this email.
        </p>
    </div>
    """

    text_body = (
        f"Welcome to AI Video Editor!\n\n"
        f"Please verify your email by visiting:\n{verify_url}\n\n"
        f"This link expires in 24 hours."
    )

    return await _send_email(email, subject, html_body, text_body)


async def send_password_reset_email(email: str, token: str) -> bool:
    """Send a password reset link.

    Args:
        email: The recipient's email address.
        token: The signed reset token.

    Returns:
        True if sent successfully.
    """
    settings = get_settings()
    frontend_url = settings.frontend_url.rstrip("/")
    # S-05 FIX: Use URL fragment (#) instead of query param (?)
    reset_url = f"{frontend_url}/reset-password#token={token}"

    subject = "Password Reset — AI Video Editor"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #333;">Password Reset Request</h2>
        <p>We received a request to reset your password. Click the button below:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}"
               style="background-color: #ef4444; color: white; padding: 14px 28px;
                      text-decoration: none; border-radius: 8px; font-weight: bold;
                      display: inline-block;">
                Reset Password
            </a>
        </div>
        <p style="color: #666; font-size: 14px;">
            Or copy and paste this link into your browser:<br>
            <a href="{reset_url}" style="color: #ef4444;">{reset_url}</a>
        </p>
        <p style="color: #999; font-size: 12px;">
            This link will expire in 1 hour. If you didn't request a password reset,
            you can safely ignore this email — your password won't be changed.
        </p>
    </div>
    """

    text_body = (
        f"Password Reset Request\n\n"
        f"Reset your password by visiting:\n{reset_url}\n\n"
        f"This link expires in 1 hour. If you didn't request this, ignore this email."
    )

    return await _send_email(email, subject, html_body, text_body)
