import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.admin.smtp_config import SMTPConfig
from app.exports.service import _export_filename, send_exports_email
from app.models.estimate import Export, ExportFormat


def test_export_filename_includes_format_and_locale():
    export_record = Export(
        id=uuid.uuid4(),
        estimate_id=uuid.uuid4(),
        format=ExportFormat.PDF_QUOTATION.value,
        storage_path="exports/example.pdf",
        locale="ja",
        generated_by=uuid.uuid4(),
    )

    assert _export_filename(export_record) == "estimate-pdf-quotation-ja.pdf"


@pytest.mark.asyncio
async def test_send_exports_email_attaches_selected_files():
    estimate_id = uuid.uuid4()
    export_id = uuid.uuid4()
    user_id = uuid.uuid4()

    export_record = Export(
        id=export_id,
        estimate_id=estimate_id,
        format=ExportFormat.MD.value,
        storage_path=f"exports/{estimate_id}/{export_id}.md",
        locale="en",
        generated_by=user_id,
    )

    class FakeEstimate:
        id = estimate_id
        project_name = "Sample Project"
        exports = []

    class FakeUser:
        id = user_id

    class FakeStorage:
        async def exists(self, path: str) -> bool:
            return True

        async def read(self, path: str) -> bytes:
            return b"# Estimate"

    mock_db = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [export_record]
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute = AsyncMock(return_value=mock_result)

    smtp_config = SMTPConfig(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="user",
        smtp_password="pass",
        smtp_from="from@example.com",
        smtp_use_tls=True,
    )

    with (
        patch("app.exports.service._get_estimate_for_export", new=AsyncMock(return_value=FakeEstimate())),
        patch("app.exports.service.get_storage_backend", return_value=FakeStorage()),
        patch("app.exports.service.get_smtp_config", new=AsyncMock(return_value=smtp_config)),
        patch("app.exports.service.send_email_with_attachments", new=AsyncMock()) as mock_send,
        patch("app.exports.service.log_change", new=AsyncMock()),
    ):
        result = await send_exports_email(
            mock_db,
            estimate_id,
            [export_id],
            "client@example.com",
            "Please review",
            FakeUser(),
        )

    assert result["to_email"] == "client@example.com"
    assert result["export_ids"] == [export_id]
    mock_send.assert_awaited_once()
    kwargs = mock_send.await_args.kwargs
    assert kwargs["to_email"] == "client@example.com"
    assert kwargs["subject"] == "Estimate export: Sample Project"
    assert "Please review" in kwargs["body_text"]
    assert len(kwargs["attachments"]) == 1
    assert kwargs["attachments"][0].filename == "estimate-md-en.md"
