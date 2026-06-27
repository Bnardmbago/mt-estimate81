from fastapi import HTTPException

from app.models.user import ACCOUNT_TYPE_CONTACT, User


def is_contact_user(user: User) -> bool:
    return user.account_type == ACCOUNT_TYPE_CONTACT


def require_full_user(user: User) -> None:
    if is_contact_user(user):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "This action is not available for contact estimate accounts",
                "code": "CONTACT_ACCESS_DENIED",
            },
        )
