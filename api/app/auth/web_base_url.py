import os

from fastapi import Request

from app.config import settings

_LOCAL_DEFAULTS = {
    "http://localhost:3000",
    "http://localhost",
    "https://localhost:3000",
    "https://localhost",
}

_INTERNAL_HOSTS = {
    "api",
    "api:8000",
    "web",
    "web:3000",
    "localhost:8000",
    "localhost:3000",
    "127.0.0.1:8000",
    "127.0.0.1:3000",
}


def _is_local_default(url: str) -> bool:
    return url.rstrip("/") in _LOCAL_DEFAULTS


def _base_url_from_request(request: Request) -> str | None:
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if not host:
        return None

    host = host.split(",")[0].strip().lower()
    if host in _INTERNAL_HOSTS:
        return None

    proto = request.headers.get("x-forwarded-proto") or request.url.scheme or "http"
    return f"{proto}://{host}".rstrip("/")


def resolve_web_base_url(request: Request | None = None) -> str:
    """Prefer WEB_BASE_URL env, then a non-local settings value, then the public request host."""
    env_value = os.environ.get("WEB_BASE_URL", "").strip()
    if env_value:
        return env_value.rstrip("/")

    configured = settings.web_base_url.strip().rstrip("/")
    if configured and not _is_local_default(configured):
        return configured

    if request is not None:
        derived = _base_url_from_request(request)
        if derived:
            return derived

    return configured or "http://localhost:3000"
