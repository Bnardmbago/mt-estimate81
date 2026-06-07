import pytest

from app.storage.local import LocalStorageBackend


@pytest.mark.asyncio
async def test_save_and_read_file(tmp_path):
    storage = LocalStorageBackend(base_path=str(tmp_path))
    path = await storage.save("uploads/test.pdf", b"pdf-content")
    assert await storage.read(path) == b"pdf-content"
    assert await storage.exists(path)


@pytest.mark.asyncio
async def test_storage_usage(tmp_path):
    storage = LocalStorageBackend(base_path=str(tmp_path))
    await storage.save("a/file1.txt", b"12345")
    await storage.save("b/file2.txt", b"678")
    assert await storage.usage() == 8
