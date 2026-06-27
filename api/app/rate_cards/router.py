from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_full_account
from app.models.user import User
from app.rate_cards import service
from app.rate_cards.management import router as management_router
from app.schemas.rate_card import RateCardVersionOption

router = APIRouter(prefix="/rate-cards", tags=["rate-cards"])
router.include_router(management_router)


@router.get("/versions", response_model=list[RateCardVersionOption])
async def list_rate_card_versions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_full_account),
):
    return await service.list_active_rate_card_version_options(db, user)
