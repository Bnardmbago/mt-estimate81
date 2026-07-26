"""MIME mapping for Google Drive convert-on-upload."""

from app.exceptions import AppError

GOOGLE_DOCS_MIME = "application/vnd.google-apps.document"
GOOGLE_SHEETS_MIME = "application/vnd.google-apps.spreadsheet"

DOCX_SOURCE_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX_SOURCE_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF_SOURCE_MIME = "application/pdf"

_DOCX_FORMATS = frozenset({"docx", "docx_quotation", "docx_internal"})
_XLSX_FORMATS = frozenset({"xlsx", "xlsx_internal"})
_PDF_FORMATS = frozenset({"pdf", "pdf_quotation", "pdf_preliminary", "pdf_internal"})


def google_source_mime_for_format(export_format: str) -> str:
    if export_format in _DOCX_FORMATS:
        return DOCX_SOURCE_MIME
    if export_format in _XLSX_FORMATS:
        return XLSX_SOURCE_MIME
    if export_format in _PDF_FORMATS:
        return PDF_SOURCE_MIME
    raise AppError(
        f"Format '{export_format}' cannot be sent to Google",
        "DESTINATION_FORMAT_UNSUPPORTED",
        status_code=400,
    )


def google_convert_mime_for_format(export_format: str) -> str | None:
    """Return Drive native MIME for conversion, or None for file-only upload (PDF)."""
    if export_format in _DOCX_FORMATS:
        return GOOGLE_DOCS_MIME
    if export_format in _XLSX_FORMATS:
        return GOOGLE_SHEETS_MIME
    if export_format in _PDF_FORMATS:
        return None
    raise AppError(
        f"Format '{export_format}' cannot be sent to Google",
        "DESTINATION_FORMAT_UNSUPPORTED",
        status_code=400,
    )


def google_destination_label(export_format: str) -> str:
    if export_format in _DOCX_FORMATS:
        return "google_docs"
    if export_format in _XLSX_FORMATS:
        return "google_sheets"
    if export_format in _PDF_FORMATS:
        return "google_drive"
    raise AppError(
        f"Format '{export_format}' cannot be sent to Google",
        "DESTINATION_FORMAT_UNSUPPORTED",
        status_code=400,
    )


def is_google_editable_format(export_format: str) -> bool:
    return export_format in _DOCX_FORMATS or export_format in _XLSX_FORMATS
