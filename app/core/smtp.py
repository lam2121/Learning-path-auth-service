"""Async SMTP email sender using aiosmtplib."""

from __future__ import annotations

import asyncio
from email.message import EmailMessage

import aiosmtplib

from app.core.config import app_config


async def send_email_async(message: EmailMessage) -> None:
    """Send an email asynchronously via SMTP."""
    use_tls = app_config.EMAIL_SMTP_PORT == 465
    start_tls = app_config.EMAIL_SMTP_PORT == 587

    await aiosmtplib.send(
        message,
        hostname=app_config.EMAIL_SMTP_SERVER,
        port=app_config.EMAIL_SMTP_PORT,
        use_tls=use_tls,
        start_tls=start_tls,
        username=app_config.EMAIL_USERNAME,
        password=app_config.EMAIL_PASSWORD,
    )


def send_email_sync(message: EmailMessage) -> None:
    """Synchronous wrapper for ``send_email_async``."""
    asyncio.run(send_email_async(message))
