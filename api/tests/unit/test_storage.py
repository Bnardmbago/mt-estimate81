import pytest

from app.storage.local import LocalStorageBackend


@pytest.mark.asyncio
async def test_save_and_read_file(tmp_path):
    storage = LocalStorageBackend(base_path=str(tmp_path))
    path = await storage.save("uploads/test.pdf", b"pdf-content")
    assert await storage.read(path) == b"pdf-content"
    assert await storage.exists(path)
