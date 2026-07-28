import pytest
from httpx import AsyncClient

from app.estimates.form_fields import build_default_template_fields


def _custom_field_payload() -> list[dict]:
    fields = build_default_template_fields()
    fields.append(
        {
            "key": "custom_notes",
            "type": "textarea",
            "required": False,
            "sort_order": 999,
            "label": {"en": "Custom notes", "ja": "カスタムメモ"},
            "description": {"en": "", "ja": ""},
            "placeholder": {"en": "", "ja": ""},
            "options": [],
        }
    )
    return fields


@pytest.mark.asyncio
async def test_list_form_templates_requires_admin(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    response = await client.get("/admin/form-templates", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_form_template_crud_happy_path(
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    list_response = await client.get("/admin/form-templates", headers=admin_headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 1

    create = await client.post(
        "/admin/form-templates",
        headers=admin_headers,
        json={
            "name": "Extended Template",
            "description": "Adds a custom field",
            "fields": _custom_field_payload(),
            "is_default": False,
        },
    )
    assert create.status_code == 201
    created = create.json()
    template_id = created["id"]
    assert created["name"] == "Extended Template"
    assert any(field["key"] == "custom_notes" for field in created["fields"])

    get_one = await client.get(f"/admin/form-templates/{template_id}", headers=admin_headers)
    assert get_one.status_code == 200

    patch = await client.patch(
        f"/admin/form-templates/{template_id}",
        headers=admin_headers,
        json={"description": "Updated description"},
    )
    assert patch.status_code == 200
    assert patch.json()["description"] == "Updated description"

    duplicate = await client.post(
        f"/admin/form-templates/{template_id}/duplicate",
        headers=admin_headers,
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["name"].startswith("Extended Template")

    delete = await client.delete(f"/admin/form-templates/{template_id}", headers=admin_headers)
    assert delete.status_code == 204


@pytest.mark.asyncio
async def test_form_template_validation_rejects_duplicate_key(
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    fields = build_default_template_fields()
    fields[1]["key"] = fields[0]["key"]

    response = await client.post(
        "/admin/form-templates",
        headers=admin_headers,
        json={
            "name": "Invalid Duplicate Key",
            "fields": fields,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_form_template_validation_rejects_select_without_options(
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    fields = [
        {
            "key": "status_choice",
            "type": "select",
            "required": True,
            "sort_order": 0,
            "label": {"en": "Status", "ja": "ステータス"},
            "description": {"en": "", "ja": ""},
            "placeholder": {"en": "", "ja": ""},
            "options": [],
        }
    ]

    response = await client.post(
        "/admin/form-templates",
        headers=admin_headers,
        json={
            "name": "Invalid Select",
            "fields": fields,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_default_template_uniqueness(
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    create = await client.post(
        "/admin/form-templates",
        headers=admin_headers,
        json={
            "name": "New Default",
            "fields": build_default_template_fields(),
            "is_default": True,
        },
    )
    assert create.status_code == 201
    new_default_id = create.json()["id"]

    listing = await client.get("/admin/form-templates", headers=admin_headers)
    defaults = [item for item in listing.json() if item["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["id"] == new_default_id


@pytest.mark.asyncio
async def test_cannot_delete_default_template(
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    listing = await client.get("/admin/form-templates", headers=admin_headers)
    default_template = next(item for item in listing.json() if item["is_default"])

    response = await client.delete(
        f"/admin/form-templates/{default_template['id']}",
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "FORM_TEMPLATE_DEFAULT_DELETE"


@pytest.mark.asyncio
async def test_cannot_delete_template_in_use(
    client: AsyncClient,
    admin_headers: dict[str, str],
    auth_headers: dict[str, str],
):
    create_template = await client.post(
        "/admin/form-templates",
        headers=admin_headers,
        json={
            "name": "In Use Template",
            "fields": build_default_template_fields(),
        },
    )
    template_id = create_template.json()["id"]

    create_estimate = await client.post(
        "/estimates",
        headers=auth_headers,
        json={
            "project_name": "Template User",
            "client_name": "ACME",
            "locale": "en",
            "form_template_id": template_id,
        },
    )
    assert create_estimate.status_code == 201

    delete = await client.delete(
        f"/admin/form-templates/{template_id}",
        headers=admin_headers,
    )
    assert delete.status_code == 400
    assert delete.json()["code"] == "FORM_TEMPLATE_IN_USE"


@pytest.mark.asyncio
async def test_form_template_options_for_authenticated_users(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    response = await client.get("/form-templates/options", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_get_form_template_for_authenticated_users(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    options = await client.get("/form-templates/options", headers=auth_headers)
    assert options.status_code == 200
    template_id = options.json()[0]["id"]

    response = await client.get(f"/form-templates/{template_id}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == template_id
    assert isinstance(body["fields"], list)
    assert len(body["fields"]) >= 1


@pytest.mark.asyncio
async def test_create_estimate_snapshots_template_schema(
    client: AsyncClient,
    admin_headers: dict[str, str],
    auth_headers: dict[str, str],
):
    create_template = await client.post(
        "/admin/form-templates",
        headers=admin_headers,
        json={
            "name": "Snapshot Template",
            "fields": _custom_field_payload(),
        },
    )
    template_id = create_template.json()["id"]

    create_estimate = await client.post(
        "/estimates",
        headers=auth_headers,
        json={
            "project_name": "Snapshot Test",
            "client_name": "ACME",
            "locale": "en",
            "form_template_id": template_id,
        },
    )
    assert create_estimate.status_code == 201
    estimate = create_estimate.json()
    assert estimate["form_template_id"] == template_id
    assert any(field["key"] == "custom_notes" for field in estimate["form_schema_snapshot"])


@pytest.mark.asyncio
async def test_patch_form_template_on_draft_updates_snapshot(
    client: AsyncClient,
    admin_headers: dict[str, str],
    auth_headers: dict[str, str],
):
    first_template = await client.post(
        "/admin/form-templates",
        headers=admin_headers,
        json={"name": "Draft Template A", "fields": build_default_template_fields()},
    )
    second_template = await client.post(
        "/admin/form-templates",
        headers=admin_headers,
        json={"name": "Draft Template B", "fields": _custom_field_payload()},
    )
    template_a = first_template.json()["id"]
    template_b = second_template.json()["id"]

    create_estimate = await client.post(
        "/estimates",
        headers=auth_headers,
        json={
            "project_name": "Draft Switch",
            "client_name": "ACME",
            "locale": "en",
            "form_template_id": template_b,
            "form_data": {"nature_of_work": "Keep me", "custom_notes": "Drop on switch"},
        },
    )
    estimate_id = create_estimate.json()["id"]

    patch = await client.patch(
        f"/estimates/{estimate_id}",
        headers=auth_headers,
        json={"form_template_id": template_a},
    )
    assert patch.status_code == 200
    payload = patch.json()
    assert payload["form_template_id"] == template_a
    assert not any(field["key"] == "custom_notes" for field in payload["form_schema_snapshot"])
    assert payload["form_data"].get("nature_of_work") == "Keep me"
    assert "custom_notes" not in payload["form_data"]


@pytest.mark.asyncio
async def test_patch_form_template_blocked_on_review(
    client: AsyncClient,
    admin_headers: dict[str, str],
    auth_headers: dict[str, str],
    db_session,
):
    from app.models.estimate import Estimate, EstimateStatus

    second_template = await client.post(
        "/admin/form-templates",
        headers=admin_headers,
        json={"name": "Review Block Template", "fields": _custom_field_payload()},
    )
    template_b = second_template.json()["id"]

    user = client.test_user  # type: ignore[attr-defined]
    estimate = Estimate(
        project_name="Review Estimate",
        client_name="ACME",
        locale="en",
        status=EstimateStatus.REVIEW,
        created_by=user.id,
        form_data={"nature_of_work": "Existing"},
        form_schema_snapshot=build_default_template_fields(),
        maintenance_assumptions={"monthly_support_hours": 0, "support_role": "developer"},
    )
    db_session.add(estimate)
    await db_session.commit()
    await db_session.refresh(estimate)

    response = await client.patch(
        f"/estimates/{estimate.id}",
        headers=auth_headers,
        json={"form_template_id": template_b},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_form_template_validation_rejects_invalid_category(
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    response = await client.post(
        "/admin/form-templates",
        headers=admin_headers,
        json={
            "name": "Invalid Category",
            "nature_of_work_category": "invalid_category",
            "fields": build_default_template_fields(),
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_form_template_options_filter_by_locale(
    client: AsyncClient,
    admin_headers: dict[str, str],
    auth_headers: dict[str, str],
):
    for name, language in (
        ("English Only Template", "en"),
        ("Japanese Only Template", "ja"),
        ("Bilingual Template", "both"),
    ):
        response = await client.post(
            "/admin/form-templates",
            headers=admin_headers,
            json={
                "name": name,
                "language": language,
                "nature_of_work_category": "new_build",
                "fields": build_default_template_fields(),
            },
        )
        assert response.status_code == 201

    en_options = await client.get("/form-templates/options?locale=en", headers=auth_headers)
    assert en_options.status_code == 200
    en_names = {item["name"] for item in en_options.json()}
    assert "English Only Template" in en_names
    assert "Bilingual Template" in en_names
    assert "Japanese Only Template" not in en_names

    ja_options = await client.get("/form-templates/options?locale=ja", headers=auth_headers)
    assert ja_options.status_code == 200
    ja_names = {item["name"] for item in ja_options.json()}
    assert "Japanese Only Template" in ja_names
    assert "Bilingual Template" in ja_names
    assert "English Only Template" not in ja_names


@pytest.mark.asyncio
async def test_duplicate_preserves_category_and_language(
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    create = await client.post(
        "/admin/form-templates",
        headers=admin_headers,
        json={
            "name": "Tagged Template",
            "nature_of_work_category": "migration",
            "language": "ja",
            "fields": build_default_template_fields(),
        },
    )
    template_id = create.json()["id"]

    duplicate = await client.post(
        f"/admin/form-templates/{template_id}/duplicate",
        headers=admin_headers,
    )
    assert duplicate.status_code == 201
    payload = duplicate.json()
    assert payload["nature_of_work_category"] == "migration"
    assert payload["language"] == "ja"
