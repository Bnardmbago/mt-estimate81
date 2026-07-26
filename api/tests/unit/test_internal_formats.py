from app.exports.internal_formats import (
    INTERNAL_FORMATS,
    is_internal_format,
    require_admin_for_internal_format,
)
from app.exceptions import AppError
from app.models.user import User
import pytest
import uuid


def test_internal_formats_set():
    assert INTERNAL_FORMATS == {
        "pdf_internal",
        "docx_internal",
        "xlsx_internal",
        "md_internal",
    }


def test_is_internal_format():
    assert is_internal_format("pdf_internal")
    assert not is_internal_format("pdf")
    assert not is_internal_format("pdf_quotation")


def test_require_admin_blocks_non_admin():
    user = User(
        id=uuid.uuid4(),
        email="u@example.com",
        password_hash="x",
        display_name="U",
        is_admin=False,
    )
    with pytest.raises(AppError) as exc:
        require_admin_for_internal_format("pdf_internal", user)
    assert exc.value.status_code == 403
    assert exc.value.code == "INTERNAL_EXPORT_ADMIN_REQUIRED"


def test_require_admin_allows_admin():
    user = User(
        id=uuid.uuid4(),
        email="a@example.com",
        password_hash="x",
        display_name="A",
        is_admin=True,
    )
    require_admin_for_internal_format("pdf_internal", user)
