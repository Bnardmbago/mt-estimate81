import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_instruction_layers_requires_admin(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    response = await client.get("/admin/ai-instruction-layers", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_instruction_layer_preview(client: AsyncClient, admin_headers: dict[str, str]):
    response = await client.get(
        "/admin/ai-instruction-layers/extraction/en",
        headers=admin_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["location"] == "extraction"
    assert payload["locale"] == "en"
    assert "valid JSON" in payload["preview"]["system"]
    assert payload["parameter_defaults"]["max_document_chars"] == 40_000


@pytest.mark.asyncio
async def test_patch_and_reset_instruction_layers(
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    patch_response = await client.patch(
        "/admin/ai-instruction-layers/ai_spec_assistant/en",
        headers=admin_headers,
        json={
            "system_prompt": "Prefer concise enterprise wording.",
            "user_prompt": "CUSTOM_PREFIX:",
            "parameters": {"temperature": 0.2, "max_tokens": 2048},
        },
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["layer"]["system_prompt"] == "Prefer concise enterprise wording."
    assert patched["layer"]["user_prompt"] == "CUSTOM_PREFIX:"
    assert patched["layer"]["parameters"]["temperature"] == 0.2
    assert "Prefer concise enterprise wording." in patched["preview"]["system"]
    assert "valid JSON" in patched["preview"]["system"]
    assert patched["preview"]["user_prefix"] == "CUSTOM_PREFIX:"

    list_response = await client.get("/admin/ai-instruction-layers", headers=admin_headers)
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert any(
        item["location"] == "ai_spec_assistant"
        and item["locale"] == "en"
        and item["layer"]["user_prompt"] == "CUSTOM_PREFIX:"
        for item in items
    )

    delete_response = await client.delete(
        "/admin/ai-instruction-layers/ai_spec_assistant/en",
        headers=admin_headers,
    )
    assert delete_response.status_code == 200
    reset = delete_response.json()
    assert reset["layer"]["system_prompt"] is None
    assert reset["layer"]["user_prompt"] is None
    assert reset["preview"]["user_prefix"] == ""


@pytest.mark.asyncio
async def test_patch_instruction_layers_rejects_invalid_parameters(
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    response = await client.patch(
        "/admin/ai-instruction-layers/extraction/en",
        headers=admin_headers,
        json={"parameters": {"max_document_chars": 1000}},
    )
    assert response.status_code == 422
