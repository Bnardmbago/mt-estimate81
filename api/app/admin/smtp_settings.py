from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.smtp_config import get_smtp_config, mask_secret, smtp_runtime_config, update_smtp_config
from app.admin.smtp_connection_test import test_smtp_connection
from app.dependencies import get_db, require_admin
from app.email.smtp import smtp_configured
from app.models.user import User

router = APIRouter(prefix="/admin/smtp-settings", tags=["admin"])


class SMTPSettingsResponse(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_from: str
    smtp_use_tls: bool
    smtp_password_configured: bool
    smtp_password_hint: str | None
    smtp_configured: bool
    env_fallback: bool


class SMTPSettingsUpdate(BaseModel):
    smtp_host: str | None = Field(default=None, max_length=255)
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
    smtp_user: str | None = Field(default=None, max_length=255)
    smtp_password: str | None = Field(default=None, max_length=255)
    smtp_from: EmailStr | None = None
    smtp_use_tls: bool | None = None
    clear_smtp_password: bool = False


class SMTPConnectionTestRequest(BaseModel):
    smtp_host: str | None = Field(default=None, max_length=255)
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
    smtp_user: str | None = Field(default=None, max_length=255)
    smtp_password: str | None = Field(default=None, max_length=255)
    smtp_from: EmailStr | None = None
    smtp_use_tls: bool | None = None


class SMTPConnectionTestResponse(BaseModel):
    success: bool
    message: str


async def build_smtp_settings_response(db: AsyncSession) -> SMTPSettingsResponse:
    from app.admin.smtp_config import _get_config_row

    row = await _get_config_row(db)
    config = await get_smtp_config(db)
    runtime = smtp_runtime_config(config)
    env_fallback = any(
        getattr(row, field) is None
        for field in (
            "smtp_host",
            "smtp_port",
            "smtp_user",
            "smtp_password",
            "smtp_from",
            "smtp_use_tls",
        )
    )

    return SMTPSettingsResponse(
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        smtp_user=config.smtp_user,
        smtp_from=config.smtp_from,
        smtp_use_tls=config.smtp_use_tls,
        smtp_password_configured=bool(config.smtp_password),
        smtp_password_hint=mask_secret(config.smtp_password),
        smtp_configured=smtp_configured(runtime),
        env_fallback=env_fallback,
    )


def _resolve_test_config(
    saved: SMTPSettingsResponse,
    body: SMTPConnectionTestRequest,
    saved_password: str,
) -> dict:
    password = body.smtp_password.strip() if body.smtp_password else saved_password
    return {
        "smtp_host": body.smtp_host if body.smtp_host is not None else saved.smtp_host,
        "smtp_port": body.smtp_port if body.smtp_port is not None else saved.smtp_port,
        "smtp_user": body.smtp_user if body.smtp_user is not None else saved.smtp_user,
        "smtp_password": password,
        "smtp_from": str(body.smtp_from) if body.smtp_from is not None else saved.smtp_from,
        "smtp_use_tls": body.smtp_use_tls if body.smtp_use_tls is not None else saved.smtp_use_tls,
    }


@router.get("", response_model=SMTPSettingsResponse)
async def get_smtp_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    return await build_smtp_settings_response(db)


@router.patch("", response_model=SMTPSettingsResponse)
async def patch_smtp_settings(
    body: SMTPSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    password = body.smtp_password.strip() if body.smtp_password else None

    await update_smtp_config(
        db,
        smtp_host=body.smtp_host.strip() if body.smtp_host is not None else None,
        smtp_port=body.smtp_port,
        smtp_user=body.smtp_user.strip() if body.smtp_user is not None else None,
        smtp_password=password if password else None,
        smtp_from=str(body.smtp_from) if body.smtp_from is not None else None,
        smtp_use_tls=body.smtp_use_tls,
        clear_smtp_password=body.clear_smtp_password,
    )
    return await build_smtp_settings_response(db)


@router.post("/test-connection", response_model=SMTPConnectionTestResponse)
async def test_smtp_settings_connection(
    body: SMTPConnectionTestRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    from app.admin.smtp_config import SMTPConfig

    saved = await build_smtp_settings_response(db)
    saved_config = await get_smtp_config(db)
    resolved = _resolve_test_config(saved, body, saved_config.smtp_password)
    config = SMTPConfig(**resolved)

    success, message = await test_smtp_connection(config)
    return SMTPConnectionTestResponse(success=success, message=message)
