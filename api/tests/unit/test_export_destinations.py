"""Unit tests for Google destination MIME mapping."""

import pytest

from app.destinations.mime import (
    DOCX_SOURCE_MIME,
    GOOGLE_DOCS_MIME,
    GOOGLE_SHEETS_MIME,
    PDF_SOURCE_MIME,
    XLSX_SOURCE_MIME,
    google_convert_mime_for_format,
    google_destination_label,
    google_source_mime_for_format,
    is_google_editable_format,
)
from app.exceptions import AppError


def test_docx_maps_to_google_docs():
    assert google_convert_mime_for_format("docx") == GOOGLE_DOCS_MIME
    assert google_convert_mime_for_format("docx_quotation") == GOOGLE_DOCS_MIME
    assert google_destination_label("docx") == "google_docs"
    assert is_google_editable_format("docx")


def test_xlsx_maps_to_google_sheets():
    assert google_convert_mime_for_format("xlsx") == GOOGLE_SHEETS_MIME
    assert google_destination_label("xlsx") == "google_sheets"
    assert "spreadsheetml" in google_source_mime_for_format("xlsx")


def test_pdf_is_file_only_no_convert():
    assert google_convert_mime_for_format("pdf") is None
    assert google_destination_label("pdf") == "google_drive"
    assert not is_google_editable_format("pdf")


def test_md_rejected():
    with pytest.raises(AppError) as exc:
        google_convert_mime_for_format("md")
    assert exc.value.code == "DESTINATION_FORMAT_UNSUPPORTED"


def test_docx_internal_maps_to_google_docs():
    assert google_source_mime_for_format("docx_internal") == DOCX_SOURCE_MIME
    assert google_convert_mime_for_format("docx_internal") == GOOGLE_DOCS_MIME
    assert google_destination_label("docx_internal") == "google_docs"
    assert is_google_editable_format("docx_internal")


def test_xlsx_internal_maps_to_google_sheets():
    assert google_source_mime_for_format("xlsx_internal") == XLSX_SOURCE_MIME
    assert google_convert_mime_for_format("xlsx_internal") == GOOGLE_SHEETS_MIME
    assert google_destination_label("xlsx_internal") == "google_sheets"
    assert is_google_editable_format("xlsx_internal")


def test_pdf_internal_is_file_only_no_convert():
    assert google_source_mime_for_format("pdf_internal") == PDF_SOURCE_MIME
    assert google_convert_mime_for_format("pdf_internal") is None
    assert google_destination_label("pdf_internal") == "google_drive"
    assert not is_google_editable_format("pdf_internal")
