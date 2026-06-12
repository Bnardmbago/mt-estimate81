import asyncio
import logging
import smtplib
from dataclasses import dataclass
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings
from app.exceptions import AppError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailAttachment:
    filename: str
    content: bytes
    content_type: str


@dataclass(frozen=True)
class SMTPRuntimeConfig:
    host: str
    port: int
    user: str
    password: str
    from_address: str
    use_tls: bool


def default_smtp_runtime_config() -> SMTPRuntimeConfig:
    return SMTPRuntimeConfig(
        host=settings.smtp_host,
        port=settings.smtp_port,
        user=settings.smtp_user,
        password=settings.smtp_password,
        from_address=settings.smtp_from,
        use_tls=settings.smtp_use_tls,
    )


def smtp_configured(config: SMTPRuntimeConfig) -> bool:
    return bool(config.host.strip() and config.from_address.strip())


def _send_sync(
    *,
    to_email: str,
    subject: str,
    body_text: str,
    attachments: list[EmailAttachment],
    config: SMTPRuntimeConfig,
) -> None:
    message = MIMEMultipart()
    message["From"] = config.from_address
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body_text, "plain", "utf-8"))

    for attachment in attachments:
        part = MIMEApplication(attachment.content, Name=attachment.filename)
        part.add_header(
            "Content-Disposition",
            "attachment",
            filename=attachment.filename,
        )
        if attachment.content_type:
            part.set_type(attachment.content_type)
        message.attach(part)

    if config.use_tls:
        with smtplib.SMTP(config.host, config.port, timeout=30) as server:
            server.starttls()
            if config.user:
                server.login(config.user, config.password)
            server.send_message(message)
    else:
        with smtplib.SMTP(config.host, config.port, timeout=30) as server:
            if config.user:
                server.login(config.user, config.password)
            server.send_message(message)


async def send_email_with_attachments(
    *,
    to_email: str,
    subject: str,
    body_text: str,
    attachments: list[EmailAttachment],
    config: SMTPRuntimeConfig | None = None,
) -> None:
    if not attachments:
        raise AppError("At least one attachment is required", "EMAIL_ATTACHMENT_REQUIRED")

    runtime_config = config or default_smtp_runtime_config()

    if not smtp_configured(runtime_config):
        if settings.app_env == "development":
            logger.info(
                "Email not sent (SMTP not configured): to=%s subject=%s attachments=%s",
                to_email,
                subject,
                [item.filename for item in attachments],
            )
            return

        raise AppError(
            "Email is not configured on the server",
            "EMAIL_NOT_CONFIGURED",
            status_code=503,
        )

    try:
        await asyncio.to_thread(
            _send_sync,
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            attachments=attachments,
            config=runtime_config,
        )
    except Exception as exc:
        logger.exception("Failed to send email to %s", to_email)
        raise AppError(
            "Failed to send email",
            "EXPORT_EMAIL_FAILED",
            status_code=502,
            details={"reason": str(exc)},
        ) from exc
