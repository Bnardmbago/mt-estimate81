from typing import Any, Literal, Protocol

from app.ai.schemas import ExtractedRequirements


class AIProvider(Protocol):
    async def extract_requirements(
        self,
        form_data: dict[str, Any],
        document_texts: list[str],
        locale: Literal["ja", "en"],
    ) -> ExtractedRequirements: ...
