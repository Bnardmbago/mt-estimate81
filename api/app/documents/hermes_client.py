import httpx

from app.config import settings


class HermesClient:
    def __init__(self, base_url: str = settings.hermes_url) -> None:
        self.base_url = base_url.rstrip("/")

    async def ping(self) -> str:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    return "ok"
                return "error"
        except Exception:
            return "unreachable"

    async def extract(self, file_path: str, file_type: str) -> dict:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/internal/extract",
                json={"file_path": file_path, "file_type": file_type},
            )
            response.raise_for_status()
            return response.json()
