from app.config import settings
from app.storage.local import LocalStorageBackend


def get_storage_backend() -> LocalStorageBackend:
    if settings.storage_backend == "local":
        return LocalStorageBackend(base_path=settings.storage_path)
    if settings.storage_backend == "gcs":
        raise NotImplementedError("GCS storage backend is not yet implemented")
    raise ValueError(f"Unknown storage backend: {settings.storage_backend}")
