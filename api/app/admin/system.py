from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.ai_config import get_ai_config
from app.dependencies import get_db, require_admin
from app.documents.hermes_client import HermesClient
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


async def count_estimates_stuck_extracting(db: AsyncSession, minutes: int = 10) -> int:
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

    return SystemHealthResponse(
        database=database,
        hermes=await hermes.ping(),
        ai_provider=ai_config.ai_provider,
        ai_model=ai_config.ai_model,
        openai_api_key_configured=bool(ai_config.openai_api_key),
        anthropic_api_key_configured=bool(ai_config.anthropic_api_key),
        stuck_extractions=stuck,
        storage_usage_bytes=await storage.usage(),
    )
