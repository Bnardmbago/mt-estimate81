from app.estimates.form_fields import build_default_template_fields
from app.exports.questionnaire import (
    build_flat_form_fields,
    build_questionnaire_sections,
    format_field_value,
    questionnaire_has_content,
)
from app.i18n.localized_content import resolve_localized_dict, store_localized_dict


def _select_field(key: str) -> dict:
    for field in build_default_template_fields():
        if field["key"] == key:
            return field
    raise KeyError(key)


def test_format_field_value_select_from_schema_options():
    field = _select_field("usage_platform")
    assert format_field_value(field, "web_browser", "en") == "Web browser"
    assert format_field_value(field, "web_browser", "ja") == "Webブラウザ"


def test_format_field_value_select_fallback_to_option_labels():
    field = _select_field("development_location")
    assert format_field_value(field, "hybrid", "en") == "Mix of Japan and offshore"


def test_format_field_value_text_passthrough():
    field = _select_field("desired_system")
    assert format_field_value(field, "Customer portal", "en") == "Customer portal"


def test_build_questionnaire_sections_groups_header_and_specification():
    form_data = {
        "desired_system": "Portal",
        "development_approach": "Agile",
        "usage_platform": "web_browser",
    }
    sections = build_questionnaire_sections(form_data, None, "en")
    assert len(sections) == 2
    assert sections[0]["id"] == "header"
    assert sections[1]["id"] == "specification"
    header_labels = [field["label"] for field in sections[0]["fields"]]
    assert "What kind of system do you want to build?" in header_labels
    spec_values = {field["label"]: field["value"] for field in sections[1]["fields"]}
    assert spec_values["Development approach"] == "Agile"


def test_build_questionnaire_sections_omits_empty_sections():
    form_data = {"desired_system": "Portal"}
    sections = build_questionnaire_sections(form_data, None, "en")
    assert len(sections) == 1
    assert sections[0]["id"] == "header"


def test_build_flat_form_fields_formats_select_values():
    form_data = {"usage_platform": "web_browser"}
    fields = build_flat_form_fields(form_data, None, "en")
    assert fields[0]["value"] == "Web browser"


def test_build_questionnaire_sections_legacy_flat_form_data():
    form_data = {"nature_of_work": "Greenfield web application"}
    sections = build_questionnaire_sections(form_data, None, "en")
    spec = next(section for section in sections if section["id"] == "specification")
    assert any(field["value"] == "Greenfield web application" for field in spec["fields"])


def test_questionnaire_has_content():
    assert questionnaire_has_content(
        [{"id": "header", "title": "Header", "fields": [{"label": "A", "value": "B"}]}]
    )
    assert not questionnaire_has_content(
        [{"id": "header", "title": "Header", "fields": []}]
    )


def test_store_localized_dict_round_trip_for_sections():
    stored = store_localized_dict(None, "ja", {"desired_system": "ポータル"})
    stored = store_localized_dict(stored, "en", {"desired_system": "Portal"})
    sections_en = build_questionnaire_sections(
        resolve_localized_dict(stored, "en", "ja"),
        None,
        "en",
    )
    sections_ja = build_questionnaire_sections(
        resolve_localized_dict(stored, "ja", "en"),
        None,
        "ja",
    )
    assert sections_en[0]["fields"][0]["value"] == "Portal"
    assert sections_ja[0]["fields"][0]["value"] == "ポータル"
