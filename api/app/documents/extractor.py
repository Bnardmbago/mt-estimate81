import asyncio
from pathlib import Path

import httpx

from app.documents.hermes_client import HermesClient

DIRECT_READ_TYPES = {"txt", "md"}
HERMES_TYPES = {"pdf", "docx", "xlsx"}
SUPPORTED_FILE_TYPES = DIRECT_READ_TYPES | HERMES_TYPES


class ExtractionError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


async def extract_document_text(
    path: str,
    file_type: str,
    hermes_client: HermesClient | None = None,
) -> str:
    normalized_type = file_type.lower()

    if normalized_type in DIRECT_READ_TYPES:
        try:
            return await asyncio.to_thread(_read_text_file, path)
        except OSError as exc:
            raise ExtractionError(f"Failed to read file: {exc}") from exc

    if normalized_type in HERMES_TYPES:
        client = hermes_client or HermesClient()
        try:
            result = await client.extract(path, normalized_type)
        except httpx.HTTPError as exc:
            raise ExtractionError(f"Hermes extraction failed: {exc}") from exc
        except Exception as exc:
            raise ExtractionError(f"Hermes extraction failed: {exc}") from exc

        markdown = result.get("markdown")
        if not isinstance(markdown, str):
            raise ExtractionError("Hermes extraction failed: missing markdown in response")
        return markdown

    raise ExtractionError(f"Unsupported file type: {file_type}")


def _read_text_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")
