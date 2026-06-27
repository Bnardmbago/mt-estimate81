from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.ai_config import get_ai_config
from app.admin.smtp_config import get_smtp_config, smtp_runtime_config
from app.auth.web_base_url import resolve_web_base_url
from app.config import settings
from app.dependencies import get_db, require_admin
from app.email.smtp import smtp_configured
from app.rate_cards.system import get_system_rate_card
from app.documents.hermes_client import HermesClient
from app.estimates.extraction import STUCK_EXTRACTION_MINUTES
from app.models.estimate import Estimate, EstimateStatus
from app.models.user import User
from app.storage.factory import get_storage_backend

router = APIRouter(prefix="/admin/system", tags=["admin"])


class SystemHealthResponse(BaseModel):
    database: str
    hermes: str
    ai_provider: str
    ai_model: str
    openai_api_key_configured: bool
    anthropic_api_key_configured: bool
    stuck_extractions: int
    storage_usage_bytes: int
    app_version: str = "0.1.0"
    smtp_configured: bool
    turnstile_configured: bool
    contact_export_limit: int
    contact_magic_link_ttl_minutes: int
    web_base_url: str
    system_rate_card_configured: bool


async def count_estimates_stuck_extracting(
    db: AsyncSession,
    minutes: int = STUCK_EXTRACTION_MINUTES,
) -> int:
    threshold = datetime.utcnow() - timedelta(minutes=minutes)
    result = await db.execute(
        select(func.count())
        .select_from(Estimate)
        .where(
            Estimate.status == EstimateStatus.EXTRACTING.value,
            Estimate.updated_at < threshold,
        )
    )
    return result.scalar_one()


def get_hermes_client() -> HermesClient:
    return HermesClient()


@router.get("/health", response_model=SystemHealthResponse)
async def system_health(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
    hermes: HermesClient = Depends(get_hermes_client),
):
    database = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        database = "error"

    storage = get_storage_backend()
    stuck = await count_estimates_stuck_extracting(db)
    ai_config = await get_ai_config(db)
    smtp_config = await get_smtp_config(db)
    smtp_runtime = smtp_runtime_config(smtp_config)
    system_rate_card = await get_system_rate_card(db)

    return SystemHealthResponse(
        database=database,
        hermes=await hermes.ping(),
        ai_provider=ai_config.ai_provider,
        ai_model=ai_config.ai_model,
        openai_api_key_configured=bool(ai_config.openai_api_key),
        anthropic_api_key_configured=bool(ai_config.anthropic_api_key),
        stuck_extractions=stuck,
        storage_usage_bytes=await storage.usage(),
        smtp_configured=smtp_configured(smtp_runtime),
        turnstile_configured=bool(settings.turnstile_secret_key.strip()),
        contact_export_limit=settings.contact_export_limit,
        contact_magic_link_ttl_minutes=settings.contact_magic_link_ttl_minutes,
        web_base_url=resolve_web_base_url(),
        system_rate_card_configured=system_rate_card is not None,
    )
