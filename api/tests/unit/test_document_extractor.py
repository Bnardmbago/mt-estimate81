from unittest.mock import AsyncMock

import httpx
import pytest

from app.documents.extractor import ExtractionError, extract_document_text


@pytest.mark.asyncio
async def test_extract_txt_direct(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("hello world", encoding="utf-8")

    text = await extract_document_text(str(txt_file), "txt", hermes_client=None)

    assert text == "hello world"


@pytest.mark.asyncio
async def test_extract_md_direct(tmp_path):
    md_file = tmp_path / "notes.md"
    md_file.write_text("# Title\n\nContent", encoding="utf-8")

    text = await extract_document_text(str(md_file), "md", hermes_client=None)

    assert "# Title" in text
    assert "Content" in text


@pytest.mark.asyncio
async def test_extract_pdf_via_hermes():
    mock_hermes = AsyncMock()
    mock_hermes.extract = AsyncMock(
        return_value={"markdown": "# Title\nContent", "page_count": 1, "method": "pymupdf"}
    )

    result = await extract_document_text("/data/test.pdf", "pdf", hermes_client=mock_hermes)

    assert "Content" in result
    mock_hermes.extract.assert_called_once_with("/data/test.pdf", "pdf")


@pytest.mark.asyncio
async def test_extract_pdf_hermes_unavailable():
    mock_hermes = AsyncMock()
    mock_hermes.extract = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

    with pytest.raises(ExtractionError, match="Hermes extraction failed"):
        await extract_document_text("/data/test.pdf", "pdf", hermes_client=mock_hermes)


@pytest.mark.asyncio
async def test_extract_unsupported_type():
    with pytest.raises(ExtractionError, match="Unsupported file type"):
        await extract_document_text("/data/test.zip", "zip", hermes_client=None)
