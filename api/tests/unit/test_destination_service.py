"""Tests for destination send-to Google/Canva (mocked HTTP)."""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.destinations import service as destination_service
from app.exceptions import AppError
from app.models.estimate import Export
from app.models.user import ACCOUNT_TYPE_CONTACT, ACCOUNT_TYPE_FULL, User


def _user(*, contact: bool = False) -> User:
    return User(
        id=uuid.uuid4(),
        email="tester@example.com",
        display_name="Tester",
        account_type=ACCOUNT_TYPE_CONTACT if contact else ACCOUNT_TYPE_FULL,
        password_hash="x",
    )


@pytest.mark.asyncio
async def test_send_estimate_export_to_google_happy_path():
    user = _user()
    export_id = uuid.uuid4()
    estimate_id = uuid.uuid4()
    export_record = Export(
        id=export_id,
        estimate_id=estimate_id,
        format="docx",
        storage_path="exports/test.docx",
        locale="en",
        generated_at=datetime.utcnow(),
        generated_by=user.id,
    )
    estimate = MagicMock()

    db = AsyncMock()
    with (
        patch.object(
            destination_service,
            "_load_estimate_export",
            AsyncMock(return_value=(export_record, estimate)),
        ),
        patch("app.destinations.service.get_storage_backend") as storage_factory,
        patch(
            "app.destinations.service.google_client.ensure_access_token",
            AsyncMock(return_value="token"),
        ),
        patch(
            "app.destinations.service.google_client.upload_and_convert",
            AsyncMock(
                return_value=(
                    "google_docs",
                    "file123",
                    "https://docs.google.com/document/d/file123",
                )
            ),
        ),
    ):
        storage = MagicMock()
        storage.read = AsyncMock(return_value=b"docx-bytes")
        storage_factory.return_value = storage
        result = await destination_service.send_estimate_export_to_google(
            db, export_id, user
        )

    assert result["destination"] == "google_docs"
    assert result["external_url"].startswith("https://docs.google.com")
    assert export_record.external_file_id == "file123"
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_send_md_to_google_rejected():
    user = _user()
    export_record = Export(
        id=uuid.uuid4(),
        estimate_id=uuid.uuid4(),
        format="md",
        storage_path="exports/test.md",
        locale="en",
        generated_at=datetime.utcnow(),
        generated_by=user.id,
    )
    estimate = MagicMock()
    db = AsyncMock()
    with patch.object(
        destination_service,
        "_load_estimate_export",
        AsyncMock(return_value=(export_record, estimate)),
    ):
        with pytest.raises(AppError) as exc:
            await destination_service.send_estimate_export_to_google(
                db, export_record.id, user
            )
    assert exc.value.code == "DESTINATION_FORMAT_UNSUPPORTED"


@pytest.mark.asyncio
async def test_contact_cannot_use_destinations():
    user = _user(contact=True)
    db = AsyncMock()
    with pytest.raises(AppError) as exc:
        await destination_service.send_estimate_export_to_google(db, uuid.uuid4(), user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_load_estimate_export_requires_admin_for_internal_format():
    """Task 7 leftover: send-to must gate internal formats even when destinations WIP is present."""
    non_admin = _user()
    non_admin.is_admin = False
    export_id = uuid.uuid4()
    estimate_id = uuid.uuid4()
    export_record = Export(
        id=export_id,
        estimate_id=estimate_id,
        format="pdf_internal",
        storage_path="exports/internal.pdf",
        locale="en",
        generated_at=datetime.utcnow(),
        generated_by=non_admin.id,
    )
    estimate = MagicMock()
    estimate.id = estimate_id
    estimate.created_by = non_admin.id

    result = MagicMock()
    result.one_or_none.return_value = (export_record, estimate)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)

    with (
        patch(
            "app.estimates.access.require_estimate_access",
            return_value=None,
        ),
        pytest.raises(AppError) as exc,
    ):
        await destination_service._load_estimate_export(db, export_id, non_admin)

    assert exc.value.status_code == 403
    assert exc.value.code == "INTERNAL_EXPORT_ADMIN_REQUIRED"


@pytest.mark.asyncio
async def test_load_estimate_export_allows_admin_for_internal_format():
    admin = _user()
    admin.is_admin = True
    export_id = uuid.uuid4()
    estimate_id = uuid.uuid4()
    export_record = Export(
        id=export_id,
        estimate_id=estimate_id,
        format="md_internal",
        storage_path="exports/internal.md",
        locale="en",
        generated_at=datetime.utcnow(),
        generated_by=admin.id,
    )
    estimate = MagicMock()
    estimate.id = estimate_id
    estimate.created_by = admin.id

    result = MagicMock()
    result.one_or_none.return_value = (export_record, estimate)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)

    with patch("app.estimates.access.require_estimate_access", return_value=None):
        loaded_export, loaded_estimate = await destination_service._load_estimate_export(
            db, export_id, admin
        )

    assert loaded_export is export_record
    assert loaded_estimate is estimate


@pytest.mark.asyncio
async def test_canva_rejects_non_pdf_format():
    from app.models.proposal import ProposalExport

    user = _user()
    proposal = MagicMock()
    proposal.id = uuid.uuid4()
    export_record = ProposalExport(
        id=uuid.uuid4(),
        proposal_id=proposal.id,
        format="docx",
        variant="proposal",
        storage_path="proposals/x.docx",
        locale="en",
        revision=1,
        generated_at=datetime.utcnow(),
        generated_by=user.id,
    )
    db = AsyncMock()
    with patch.object(
        destination_service,
        "_load_proposal_export",
        AsyncMock(return_value=(export_record, proposal)),
    ):
        with pytest.raises(AppError) as exc:
            await destination_service.send_proposal_export_to_canva(
                db, proposal.id, export_record.id, user
            )
    assert exc.value.code == "CANVA_FORMAT_FORBIDDEN"
