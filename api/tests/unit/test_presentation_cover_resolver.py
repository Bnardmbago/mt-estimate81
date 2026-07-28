from __future__ import annotations

from copy import deepcopy

from app.presentation.cover import resolve_cover_fields


def _localized(**locales: dict[str, str]) -> dict:
    return {"_i18n": locales}


def test_cover_value_override_beats_auto_fill_and_template_default():
    template_fields = [
        {
            "key": "title",
            "content": _localized(
                en={"label": "Title", "default_text": "Template title"},
                ja={"label": "件名", "default_text": "既定の件名"},
            ),
            "required": True,
            "auto_fill": "title",
            "emphasis": "title",
        }
    ]
    cover_values = {
        "title": _localized(
            en={"value": "User title"},
            ja={"value": "利用者の件名"},
        )
    }

    fields, warnings = resolve_cover_fields(
        template_fields,
        cover_values,
        display_locale="en",
        fallback_locale="ja",
        document_facts={"title": "Document title"},
    )

    assert fields == [
        {
            "key": "title",
            "label": "Title",
            "value": "User title",
            "required": True,
            "emphasis": "title",
            "source": "override",
        }
    ]
    assert warnings == []


def test_auto_fill_beats_template_default_and_supports_dotted_fact_paths():
    fields, warnings = resolve_cover_fields(
        [
            {
                "key": "client",
                "content": _localized(
                    en={"label": "Client", "default_text": "Default client"}
                ),
                "auto_fill": "client.name",
            }
        ],
        {},
        display_locale="en",
        fallback_locale="ja",
        document_facts={"client": {"name": "Example Corp"}},
    )

    assert fields[0]["value"] == "Example Corp"
    assert fields[0]["source"] == "auto_fill"
    assert warnings == []


def test_template_default_is_localized_with_fallback_locale():
    fields, warnings = resolve_cover_fields(
        [
            {
                "key": "subtitle",
                "content": _localized(
                    ja={"label": "副題", "default_text": "既定の副題"}
                ),
            }
        ],
        {},
        display_locale="en",
        fallback_locale="ja",
        document_facts={},
    )

    assert fields[0]["label"] == "副題"
    assert fields[0]["value"] == "既定の副題"
    assert fields[0]["source"] == "default"
    assert warnings == []


def test_missing_required_field_is_flagged():
    fields, warnings = resolve_cover_fields(
        [
            {
                "key": "title",
                "content": _localized(en={"label": "Title"}),
                "required": True,
            }
        ],
        {},
        display_locale="en",
        fallback_locale="ja",
        document_facts={},
    )

    assert fields[0]["value"] is None
    assert fields[0]["source"] == "missing"
    assert warnings == ["Missing required cover field: title"]


def test_unknown_cover_values_are_retained_but_not_rendered():
    cover_values = {
        "known": _localized(en={"value": "Rendered"}),
        "from_previous_template": _localized(en={"value": "Keep me"}),
    }
    original = deepcopy(cover_values)

    fields, warnings = resolve_cover_fields(
        [{"key": "known", "content": _localized(en={"label": "Known"})}],
        cover_values,
        display_locale="en",
        fallback_locale="ja",
        document_facts={},
    )

    assert [field["key"] for field in fields] == ["known"]
    assert cover_values == original
    assert warnings == []


def test_resolved_cover_field_includes_normalized_geometry_and_style():
    fields, warnings = resolve_cover_fields(
        [
            {
                "key": "title",
                "content": _localized(en={"label": "Title", "default_text": "Hello"}),
                "geometry": {
                    "x_pct": -10,
                    "y_pct": 25,
                    "width_pct": 120,
                    "height_pct": 0,
                    "z_index": 1000,
                },
                "style": {
                    "font_family": "Noto Sans JP",
                    "font_size_pt": 200,
                    "font_weight": 700,
                    "italic": True,
                    "color": "#112233",
                    "text_align": "right",
                    "line_height": 1.5,
                    "letter_spacing_em": -0.05,
                    "opacity": 0.75,
                    "background_color": "#ffffff",
                    "padding_mm": 2,
                },
            }
        ],
        {},
        display_locale="en",
        fallback_locale="ja",
        document_facts={},
    )

    assert fields[0]["geometry"] == {
        "x_pct": 0.0,
        "y_pct": 25.0,
        "width_pct": 100.0,
        "height_pct": 1.0,
        "z_index": 999,
    }
    assert fields[0]["style"] == {
        "font_family": "Noto Sans JP",
        "font_size_pt": 144.0,
        "font_weight": 700,
        "italic": True,
        "color": "#112233",
        "text_align": "right",
        "line_height": 1.5,
        "letter_spacing_em": -0.05,
        "opacity": 0.75,
        "background_color": "#ffffff",
        "padding_mm": 2.0,
    }
    assert warnings == []


def test_legacy_resolved_cover_field_does_not_gain_geometry_or_style():
    fields, warnings = resolve_cover_fields(
        [{"key": "title", "content": _localized(en={"default_text": "Legacy"})}],
        {},
        display_locale="en",
        fallback_locale="ja",
        document_facts={},
    )

    assert "geometry" not in fields[0]
    assert "style" not in fields[0]
    assert warnings == []
