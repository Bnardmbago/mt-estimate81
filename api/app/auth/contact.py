import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.smtp_config import get_smtp_config, smtp_runtime_config
from app.auth.disposable_domains import is_disposable_email
from app.auth.service import create_access_token
from app.config import settings
from app.email.smtp import send_email, smtp_configured
from app.estimates.form_fields import snapshot_fields
from app.form_templates.service import resolve_template
from app.models.contact_magic_link import ContactMagicLink
from app.models.estimate import Estimate, EstimateStatus
from app.models.user import ACCOUNT_TYPE_CONTACT, ACCOUNT_TYPE_FULL, User
from app.rate_cards.system import attach_system_rate_card

logger = logging.getLogger(__name__)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def _verify_turnstile(token: str, remote_ip: str | None) -> None:
    secret = settings.turnstile_secret_key.strip()
    if not secret:
        if settings.app_env == "development":
            return
        raise HTTPException(
            status_code=503,
            detail={"error": "CAPTCHA is not configured", "code": "CAPTCHA_NOT_CONFIGURED"},
        )

    payload = {"secret": secret, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data=payload,
        )
    data = response.json()
    if not data.get("success"):
        raise HTTPException(
            status_code=400,
            detail={"error": "CAPTCHA verification failed", "code": "CAPTCHA_FAILED"},
        )


async def _check_magic_link_rate_limits(
    db: AsyncSession,
    *,
    email: str,
    request_ip: str | None,
) -> None:
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
    email_count = await db.scalar(
        select(func.count())
        .select_from(ContactMagicLink)
        .join(User, User.id == ContactMagicLink.user_id)
        .where(User.email == email.lower(), ContactMagicLink.created_at >= since)
    )
    if email_count and email_count >= settings.contact_magic_link_rate_limit_per_email:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Too many sign-in requests for this email. Try again later.",
                "code": "RATE_LIMIT_EMAIL",
            },
        )

    if request_ip:
        ip_count = await db.scalar(
            select(func.count())
            .select_from(ContactMagicLink)
            .where(ContactMagicLink.request_ip == request_ip, ContactMagicLink.created_at >= since)
        )
        if ip_count and ip_count >= settings.contact_magic_link_rate_limit_per_ip:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Too many sign-in requests from this network. Try again later.",
                    "code": "RATE_LIMIT_IP",
                },
            )


def _normalize_company_name(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


async def request_magic_link(
    db: AsyncSession,
    *,
    email: str,
    display_name: str,
    company_name: str,
    locale: str,
    request_ip: str | None,
    captcha_token: str,
) -> None:
    normalized_email = email.strip().lower()
    display = display_name.strip()
    company = _normalize_company_name(company_name)

    if not display and not company:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Provide your name or company name",
                "code": "NAME_OR_COMPANY_REQUIRED",
            },
        )

    if not display and company:
        display = company

    if is_disposable_email(normalized_email):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Disposable email addresses are not allowed",
                "code": "DISPOSABLE_EMAIL",
            },
        )

    await _verify_turnstile(captcha_token, request_ip)
    await _check_magic_link_rate_limits(db, email=normalized_email, request_ip=request_ip)

    result = await db.execute(select(User).where(User.email == normalized_email))
    user = result.scalar_one_or_none()

    if user and user.account_type == ACCOUNT_TYPE_FULL:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "This email is registered as a full account. Please sign in with password.",
                "code": "USE_FULL_LOGIN",
            },
        )

    if user is None:
        user = User(
            email=normalized_email,
            password_hash=None,
            display_name=display,
            company_name=company,
            account_type=ACCOUNT_TYPE_CONTACT,
            is_admin=False,
            is_active=True,
            preferred_locale=locale if locale in ("ja", "en") else "ja",
        )
        db.add(user)
        await db.flush()
    else:
        user.display_name = display
        user.company_name = company
        if locale in ("ja", "en"):
            user.preferred_locale = locale

    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=settings.contact_magic_link_ttl_minutes)
    db.add(
        ContactMagicLink(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=expires_at,
            request_ip=request_ip,
        )
    )
    await db.commit()

    verify_url = (
        f"{settings.web_base_url.rstrip('/')}/{user.preferred_locale}/contact/verify"
        f"?token={raw_token}"
    )
    subject = (
        "見積アクセス用リンク"
        if user.preferred_locale == "ja"
        else "Your estimate access link"
    )
    if user.preferred_locale == "ja":
        body = (
            f"{user.display_name} 様\n\n"
            "以下のリンクから見積作成にアクセスできます。\n"
            f"{verify_url}\n\n"
            f"このリンクは {settings.contact_magic_link_ttl_minutes} 分間有効です。"
        )
    else:
        body = (
            f"Hello {user.display_name},\n\n"
            "Use the link below to access your estimate:\n"
            f"{verify_url}\n\n"
            f"This link expires in {settings.contact_magic_link_ttl_minutes} minutes."
        )

    smtp_config = await get_smtp_config(db)
    runtime_config = smtp_runtime_config(smtp_config)
    if settings.app_env == "development" and not smtp_configured(runtime_config):
        logger.warning("Contact magic link (dev, SMTP skipped): %s", verify_url)
    await send_email(
        to_email=normalized_email,
        subject=subject,
        body_text=body,
        config=runtime_config,
    )


async def get_or_create_contact_estimate(db: AsyncSession, user: User) -> Estimate:
    result = await db.execute(
        select(Estimate)
        .where(Estimate.created_by == user.id)
        .order_by(Estimate.created_at.asc())
        .limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    template = await resolve_template(db, None)
    schema_snapshot = snapshot_fields(template.fields)
    project_name = "新規見積" if user.preferred_locale == "ja" else "New Estimate"

    estimate = Estimate(
        project_name=project_name,
        client_name=user.default_client_name(),
        locale=user.preferred_locale,
        form_data={},
        form_template_id=template.id,
        form_schema_snapshot=schema_snapshot,
        status=EstimateStatus.DRAFT.value,
        created_by=user.id,
    )
    db.add(estimate)
    await db.flush()
    await attach_system_rate_card(db, estimate)
    await db.flush()
    return estimate


async def verify_magic_link(
    db: AsyncSession,
    *,
    token: str,
    request_ip: str | None,
) -> dict:
    token_hash = _hash_token(token.strip())
    result = await db.execute(
        select(ContactMagicLink, User)
        .join(User, User.id == ContactMagicLink.user_id)
        .where(ContactMagicLink.token_hash == token_hash)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid or expired link", "code": "MAGIC_LINK_INVALID"},
        )

    link, user = row
    now = datetime.utcnow()
    if link.used_at is not None or link.expires_at < now:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid or expired link", "code": "MAGIC_LINK_INVALID"},
        )

    link.used_at = now
    user.email_verified_at = user.email_verified_at or now
    await db.flush()

    estimate = await get_or_create_contact_estimate(db, user)
    await db.commit()

    access_token = create_access_token(
        {
            "sub": str(user.id),
            "is_admin": False,
            "account_type": ACCOUNT_TYPE_CONTACT,
        },
        expiry_hours=settings.contact_jwt_expiry_hours,
    )

    return {
        "access_token": access_token,
        "estimate_id": str(estimate.id),
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "company_name": user.company_name,
            "account_type": user.account_type,
            "email_verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None,
            "is_admin": False,
            "is_active": user.is_active,
            "preferred_locale": user.preferred_locale,
            "preferred_currency": user.preferred_currency,
        },
    }
