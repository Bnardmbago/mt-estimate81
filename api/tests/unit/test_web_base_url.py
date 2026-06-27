import pytest
from starlette.requests import Request

from app.auth.web_base_url import resolve_web_base_url


def _request(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/auth/contact/request-link",
        "headers": [(key.lower().encode(), value.encode()) for key, value in headers.items()],
        "scheme": "http",
        "server": ("api", 8000),
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


def test_resolve_web_base_url_prefers_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WEB_BASE_URL", "http://34.153.193.172")
    request = _request({"host": "example.com"})
    assert resolve_web_base_url(request) == "http://34.153.193.172"


def test_resolve_web_base_url_uses_forwarded_host_when_env_missing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("WEB_BASE_URL", raising=False)
    request = _request(
        {
            "host": "34.153.193.172",
            "x-forwarded-proto": "http",
        }
    )
    assert resolve_web_base_url(request) == "http://34.153.193.172"


def test_resolve_web_base_url_ignores_internal_api_host(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("WEB_BASE_URL", raising=False)
    request = _request({"host": "api:8000"})
    assert resolve_web_base_url(request) == "http://localhost:3000"


def test_resolve_web_base_url_prefers_forwarded_host_header(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("WEB_BASE_URL", raising=False)
    request = _request(
        {
            "host": "api:8000",
            "x-forwarded-host": "34.153.193.172",
            "x-forwarded-proto": "http",
        }
    )
    assert resolve_web_base_url(request) == "http://34.153.193.172"
