import httpx

from app.config import settings


class HermesClient:
    def __init__(self, base_url: str = settings.hermes_url) -> None:
        self.base_url = base_url.rstrip("/")

    async def extract(self, file_path: str, file_type: str) -> dict:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/internal/extract",
                json={"file_path": file_path, "file_type": file_type},
            )
            response.raise_for_status()
            return response.json()
