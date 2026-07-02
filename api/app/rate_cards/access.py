from fastapi import HTTPException
from sqlalchemy import or_

from app.models.rate_card import RateCard
from app.models.user import User


def rate_cards_visible_to_user_filter(user: User):
    if user.is_admin:
        return None
    return or_(RateCard.created_by == user.id, RateCard.is_system.is_(True))


def can_access_rate_card(rate_card: RateCard, user: User) -> bool:
    if rate_card.is_system:
        return True
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
