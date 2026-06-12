from fastapi import HTTPException

from app.models.estimate import Estimate
from app.models.user import User


def can_access_estimate(estimate: Estimate, user: User) -> bool:
    return user.is_admin or estimate.created_by == user.id


def require_estimate_access(estimate: Estimate, user: User) -> None:
    if not can_access_estimate(estimate, user):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "You do not have access to this estimate",
                "code": "ESTIMATE_ACCESS_DENIED",
            },
        )
