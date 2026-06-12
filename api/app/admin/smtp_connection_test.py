import asyncio
import smtplib

from app.admin.smtp_config import SMTPConfig


def _test_smtp_sync(config: SMTPConfig) -> None:
    if not config.smtp_host.strip():
        raise ValueError("SMTP host is required")

    if config.smtp_use_tls:
        with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=30) as server:
            server.starttls()
            if config.smtp_user:
                server.login(config.smtp_user, config.smtp_password)
            server.noop()
    else:
        with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=30) as server:
            if config.smtp_user:
                server.login(config.smtp_user, config.smtp_password)
            server.noop()


async def test_smtp_connection(config: SMTPConfig) -> tuple[bool, str]:
    try:
        await asyncio.to_thread(_test_smtp_sync, config)
        return True, "Connection successful"
    except Exception as exc:
        return False, str(exc)
