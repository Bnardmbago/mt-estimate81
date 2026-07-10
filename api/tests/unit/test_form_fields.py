from app.estimates.form_fields import (
    HEADER_FIELD_KEYS,
    SPEC_FIELD_KEYS,
    build_default_template_fields,
    normalize_form_data,
    normalize_suggested_form_data,
    snapshot_fields,
    specification_schema,
)


def test_build_default_template_fields_has_header_and_spec_sections():
    fields = build_default_template_fields()
    header = [field for field in fields if field.get("section") == "header"]
    spec = specification_schema(fields)

    assert len(header) == len(HEADER_FIELD_KEYS)
    assert len(spec) == len(SPEC_FIELD_KEYS)
    assert all(not field["required"] for field in fields)
    assert header[0]["key"] == "desired_system"
    assert spec[0]["key"] == "nature_of_work"


def test_header_questionnaire_field_types():
    fields = build_default_template_fields()
    by_key = {field["key"]: field for field in fields}

    assert by_key["desired_system"]["type"] == "text"
    assert by_key["usage_platform"]["type"] == "select"
    assert [option["value"] for option in by_key["usage_platform"]["options"]] == [
        "web_browser",
        "iphone_app",
        "android_app",
        "cross_platform",
        "mobile_only",
        "undecided",
    ]
    assert by_key["payment_needed"]["type"] == "select"
    assert by_key["client_budget"]["type"] == "currency"
    assert by_key["expected_user_count"]["type"] == "number"
    assert by_key["concurrent_users"]["type"] == "number"
    assert by_key["delivery_schedule"]["type"] == "select"
    assert by_key["problem_to_solve"]["type"] == "textarea"
    assert by_key["required_features"]["type"] == "textarea"
    assert [option["value"] for option in by_key["payment_needed"]["options"]] == [
        "none",
        "bank_transfer",
        "credit_card",
        "both",
        "undecided",
    ]


def test_specification_field_types():
    fields = build_default_template_fields()
    by_key = {field["key"]: field for field in fields}

    assert by_key["nature_of_work"]["type"] == "select"
    assert by_key["business_domain"]["type"] == "select"
    assert by_key["development_approach"]["type"] == "select"
    assert by_key["maintenance_support"]["type"] == "select"
    assert by_key["scope_boundaries"]["type"] == "textarea"
    assert by_key["integrations"]["type"] == "textarea"
    assert by_key["scope_boundaries"]["placeholder"]["en"].startswith("In scope")


def test_normalize_form_data_select_slugs():
    schema = build_default_template_fields()
    normalized = normalize_form_data(
        schema,
        {
            "payment_needed": "bank_transfer",
            "nature_of_work": "new_build",
            "development_approach": "ai_assisted",
            "maintenance_support": "business_hours",
        },
    )
    assert normalized["payment_needed"] == "bank_transfer"
    assert normalized["nature_of_work"] == "new_build"
    assert normalized["development_approach"] == "ai_assisted"
    assert normalized["maintenance_support"] == "business_hours"


def test_normalize_form_data_maps_legacy_select_aliases():
    schema = build_default_template_fields()
    normalized = normalize_form_data(
        schema,
        {
            "nature_of_work": "Greenfield web application",
            "development_approach": "Agile",
            "payment_needed": "yes",
            "desired_system": "Customer portal",
            "business_domain": "Retail",
        },
    )
    assert normalized["nature_of_work"] == "new_build"
    assert normalized["development_approach"] == "hybrid"
    assert normalized["payment_needed"] == "both"
    assert normalized["desired_system"] == "Customer portal"
    assert normalized["business_domain"] == "retail"


def test_normalize_form_data_maps_legacy_usage_platform_aliases():
    schema = build_default_template_fields()
    normalized = normalize_form_data(
        schema,
        {
            "usage_platform": "both_mobile",
        },
    )
    assert normalized["usage_platform"] == "cross_platform"


def test_development_approach_hybrid_label_not_location_label():
    fields = build_default_template_fields()
    by_key = {field["key"]: field for field in fields}
    hybrid_option = next(
        option
        for option in by_key["development_approach"]["options"]
        if option["value"] == "hybrid"
    )
    location_hybrid = next(
        option
        for option in by_key["development_location"]["options"]
        if option["value"] == "hybrid"
    )
    assert hybrid_option["label"]["en"] == "Hybrid"
    assert location_hybrid["label"]["en"] == "Mix of Japan and offshore"


def test_snapshot_fields_patches_legacy_select_fields():
    legacy_schema = [
        {
            "key": "payment_needed",
            "type": "textarea",
            "required": False,
            "sort_order": 0,
            "section": "header",
            "label": {"en": "Payments", "ja": "決済"},
            "description": {"en": "", "ja": ""},
            "placeholder": {"en": "", "ja": ""},
        },
        {
            "key": "development_approach",
            "type": "text",
            "required": False,
            "sort_order": 10,
            "section": "specification",
            "label": {"en": "Approach", "ja": "アプローチ"},
            "description": {"en": "", "ja": ""},
            "placeholder": {"en": "", "ja": ""},
        },
    ]
    patched = snapshot_fields(legacy_schema)
    by_key = {field["key"]: field for field in patched}
    assert by_key["payment_needed"]["type"] == "select"
    assert len(by_key["payment_needed"]["options"]) == 5
    assert by_key["development_approach"]["type"] == "select"
    assert len(by_key["development_approach"]["options"]) == 4


def test_normalize_form_data_strips_numeric_formatting():
    schema = build_default_template_fields()
    normalized = normalize_form_data(
        schema,
        {
            "expected_user_count": "10,000",
            "concurrent_users": " 250 ",
            "client_budget": "¥5,000,000",
        },
    )
    assert normalized["expected_user_count"] == "10000"
    assert normalized["concurrent_users"] == "250"
    assert normalized["client_budget"] == "5000000"


def test_snapshot_fields_patches_legacy_header_types():
    legacy_schema = [
        {
            "key": "client_budget",
            "type": "text",
            "required": False,
            "sort_order": 0,
            "section": "header",
            "label": {"en": "What is your budget?", "ja": "予算を教えてください。"},
            "description": {"en": "", "ja": ""},
            "placeholder": {"en": "", "ja": ""},
        },
        {
            "key": "delivery_schedule",
            "type": "textarea",
            "required": False,
            "sort_order": 10,
            "section": "header",
            "label": {"en": "Delivery schedule", "ja": "納期"},
            "description": {"en": "", "ja": ""},
            "placeholder": {"en": "", "ja": ""},
        },
    ]
    patched = snapshot_fields(legacy_schema)
    by_key = {field["key"]: field for field in patched}
    assert by_key["client_budget"]["type"] == "currency"
    assert by_key["delivery_schedule"]["type"] == "select"
    assert len(by_key["delivery_schedule"]["options"]) == 6


def test_normalize_suggested_form_data_excludes_header_fields():
    raw = {
        "desired_system": "web_application",
        "nature_of_work": "new_build",
        "data_complexity": "moderate",
    }
    normalized = normalize_suggested_form_data(raw)
    assert "desired_system" not in normalized
    assert normalized["nature_of_work"] == "new_build"
    assert normalized["data_complexity"] == "medium"


def test_normalize_complexity_aliases():
    raw = {
        "nature_of_work": "enhancement",
        "data_complexity": "simple",
        "ui_complexity": "COMPLEX",
    }
    normalized = normalize_suggested_form_data(raw)
    assert normalized["data_complexity"] == "low"
    assert normalized["ui_complexity"] == "high"


def test_normalize_form_data_complexity_with_legacy_schema_options():
    legacy_schema = [
        {
            "key": "data_complexity",
            "type": "select",
            "required": False,
            "sort_order": 0,
            "section": "specification",
            "label": {"en": "Data complexity", "ja": "データ複雑度"},
            "description": {"en": "", "ja": ""},
            "placeholder": {"en": "", "ja": ""},
            "options": [
                {"value": "simple", "label": {"en": "Simple", "ja": "シンプル"}},
                {"value": "moderate", "label": {"en": "Moderate", "ja": "中程度"}},
                {"value": "complex", "label": {"en": "Complex", "ja": "複雑"}},
            ],
        },
        {
            "key": "ui_complexity",
            "type": "select",
            "required": False,
            "sort_order": 10,
            "section": "specification",
            "label": {"en": "UI complexity", "ja": "UI複雑度"},
            "description": {"en": "", "ja": ""},
            "placeholder": {"en": "", "ja": ""},
            "options": [
                {"value": "simple", "label": {"en": "Simple", "ja": "シンプル"}},
                {"value": "moderate", "label": {"en": "Moderate", "ja": "中程度"}},
                {"value": "complex", "label": {"en": "Complex", "ja": "複雑"}},
            ],
        },
    ]
    patched = snapshot_fields(legacy_schema)
    by_key = {field["key"]: field for field in patched}
    assert [option["value"] for option in by_key["data_complexity"]["options"]] == [
        "low",
        "medium",
        "high",
    ]

    normalized = normalize_form_data(
        legacy_schema,
        {
            "data_complexity": "simple",
            "ui_complexity": "low",
        },
    )
    assert normalized["data_complexity"] == "low"
    assert normalized["ui_complexity"] == "low"

    ai_normalized = normalize_suggested_form_data(
        {"data_complexity": "moderate", "ui_complexity": "high"},
        legacy_schema,
    )
    assert ai_normalized["data_complexity"] == "medium"
    assert ai_normalized["ui_complexity"] == "high"


def test_resolve_complexity_select_value_supports_legacy_options():
    from app.estimates.form_fields import _resolve_complexity_select_value

    legacy_options = {"simple", "moderate", "complex"}
    assert _resolve_complexity_select_value("simple", legacy_options) == "simple"
    assert _resolve_complexity_select_value("low", legacy_options) == "simple"
    assert _resolve_complexity_select_value("moderate", legacy_options) == "moderate"
    assert _resolve_complexity_select_value("high", legacy_options) == "complex"


def test_fill_complexity_from_profile_uses_schema_options():
    from app.estimates.form_fields import fill_complexity_from_profile

    legacy_schema = [
        {
            "key": "data_complexity",
            "type": "select",
            "required": False,
            "sort_order": 0,
            "section": "specification",
            "label": {"en": "Data complexity", "ja": "データ複雑度"},
            "description": {"en": "", "ja": ""},
            "placeholder": {"en": "", "ja": ""},
            "options": [
                {"value": "simple", "label": {"en": "Simple", "ja": "シンプル"}},
                {"value": "moderate", "label": {"en": "Moderate", "ja": "中程度"}},
                {"value": "complex", "label": {"en": "Complex", "ja": "複雑"}},
            ],
        },
    ]
    filled = fill_complexity_from_profile({}, "medium", legacy_schema)
    assert filled["data_complexity"] == "medium"
