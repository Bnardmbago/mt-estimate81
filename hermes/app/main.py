import asyncio

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.extractor import ExtractionError, extract_to_markdown

app = FastAPI(title="Hermes Extractor", version="0.1.0")


class ExtractRequest(BaseModel):
    file_path: str = Field(min_length=1)
    file_type: str = Field(min_length=1)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/internal/extract")
async def extract(body: ExtractRequest) -> dict:
    try:
        return await asyncio.to_thread(extract_to_markdown, body.file_path, body.file_type)
    except ExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {exc}") from exc
