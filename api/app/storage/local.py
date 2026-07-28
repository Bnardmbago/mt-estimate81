import asyncio
from pathlib import Path
import shutil


class LocalStorageBackend:
    def __init__(self, base_path: str) -> None:
        self._base_path = Path(base_path)

    def _resolve_path(self, storage_path: str) -> Path:
        full_path = (self._base_path / storage_path).resolve()
        base_resolved = self._base_path.resolve()
        if not str(full_path).startswith(str(base_resolved)):
            raise ValueError(f"Invalid storage path: {storage_path}")
        return full_path

    async def save(self, relative_path: str, content: bytes) -> str:
        path = self._resolve_path(relative_path)
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, content)
        return relative_path

    async def read(self, storage_path: str) -> bytes:
        path = self._resolve_path(storage_path)
        return await asyncio.to_thread(path.read_bytes)

    async def exists(self, storage_path: str) -> bool:
        path = self._resolve_path(storage_path)
        return await asyncio.to_thread(path.is_file)

    async def delete(self, storage_path: str) -> None:
        path = self._resolve_path(storage_path)
        if await asyncio.to_thread(path.is_file):
            await asyncio.to_thread(path.unlink)

    async def list_prefix(self, prefix: str) -> list[str]:
        path = self._resolve_path(prefix)

        def _list() -> list[str]:
            if path.is_file():
                return [path.relative_to(self._base_path.resolve()).as_posix()]
            if not path.is_dir():
                return []
            return sorted(
                candidate.relative_to(self._base_path.resolve()).as_posix()
                for candidate in path.rglob("*")
                if candidate.is_file()
            )

        return await asyncio.to_thread(_list)

    async def delete_prefix(self, prefix: str) -> None:
        path = self._resolve_path(prefix)

        def _delete() -> None:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)

        await asyncio.to_thread(_delete)

    async def usage(self) -> int:
        def _calc() -> int:
            if not self._base_path.exists():
                return 0
            total = 0
            for path in self._base_path.rglob("*"):
                if path.is_file():
                    total += path.stat().st_size
            return total

        return await asyncio.to_thread(_calc)
