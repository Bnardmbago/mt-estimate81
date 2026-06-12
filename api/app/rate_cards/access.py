from fastapi import HTTPException

from app.models.rate_card import RateCard
from app.models.user import User


def can_access_rate_card(rate_card: RateCard, user: User) -> bool:
    return user.is_admin or rate_card.created_by == user.id


def require_rate_card_access(rate_card: RateCard, user: User) -> None:
    if not can_access_rate_card(rate_card, user):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "You do not have access to this rate card",
                "code": "RATE_CARD_ACCESS_DENIED",
            },
        )
