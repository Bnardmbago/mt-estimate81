from app.estimates.form_fields import (
    HEADER_FIELD_KEYS,
    SPEC_FIELD_KEYS,
    build_default_template_fields,
    normalize_suggested_form_data,
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


def test_normalize_suggested_form_data_excludes_header_fields():
    raw = {
        "desired_system": "Mobile app",
        "nature_of_work": "New build",
        "data_complexity": "moderate",
    }
    normalized = normalize_suggested_form_data(raw)
    assert "desired_system" not in normalized
    assert normalized["nature_of_work"] == "New build"
    assert normalized["data_complexity"] == "medium"


def test_normalize_complexity_aliases():
    raw = {
        "nature_of_work": "New build",
        "data_complexity": "simple",
        "ui_complexity": "COMPLEX",
    }
    normalized = normalize_suggested_form_data(raw)
    assert normalized["data_complexity"] == "low"
    assert normalized["ui_complexity"] == "high"
