from app.exceptions import AppError
from app.models.user import User

INTERNAL_FORMATS = frozenset(
    {
        "pdf_internal",
        "docx_internal",
        "xlsx_internal",
        "md_internal",
    }
)


def is_internal_format(fmt: str) -> bool:
    return fmt in INTERNAL_FORMATS


def require_admin_for_internal_format(fmt: str, user: User) -> None:
    if is_internal_format(fmt) and not user.is_admin:
        raise AppError(
            "Internal exports are restricted to administrators",
            "INTERNAL_EXPORT_ADMIN_REQUIRED",
            status_code=403,
        )
