from datetime import datetime

import pytest

try:
    from weasyprint import HTML as _WeasyprintHTML
except OSError:
    pytest.skip("WeasyPrint system libraries not available", allow_module_level=True)
else:
    del _WeasyprintHTML

from app.exports.markdown import (
    format_currency,
    format_effort_days,
    format_hours,
    format_person_days,
)
from app.exports.pdf import (
    _build_template_html,
    generate_quotation_formal_pdf,
    generate_quotation_pdf,
    generate_report_pdf,
)
from app.presentation.accent_shapes import normalize_accent_shapes
from app.presentation.resolver import PresentationBundle
from tests.unit.export_fixtures import (
    sample_estimate_with_discount,
    sample_formal_quotation_context,
    sample_quotation_context,
    sample_report_context,
)


@pytest.fixture
def quotation_context():
    return sample_quotation_context()


@pytest.fixture
def report_context():
    return sample_report_context()


def _accent_shape(*, visible=True):
    shapes, warnings = normalize_accent_shapes(
        [
            {
                "id": "estimate-accent",
                "name": "Estimate accent",
                "type": "rectangle",
                "visible": visible,
                "geometry": {
                    "x_pct": 0,
                    "y_pct": 0,
                    "width_pct": 12,
                    "height_pct": 100,
                    "rotation_deg": 0,
                    "z_index": 1,
                },
                "fill": {"mode": "theme", "opacity": 1},
            }
        ]
    )
    assert not warnings
    return shapes[0]


def test_quotation_pdf_starts_with_pdf_magic_bytes(quotation_context):
    content = generate_quotation_pdf(quotation_context)
    assert content.startswith(b"%PDF")


def test_quotation_pdf_html_omits_pricing_summary_block():
    ctx = sample_quotation_context(estimate=sample_estimate_with_discount(), locale="en")
    html = _build_template_html(
        "estimate_quotation_formal.html.j2",
        ctx=ctx,
        format_currency=format_currency,
    )
    assert "pricing-summary" not in html
    assert "*Special Notes" not in html
    assert "Limited-Time Discount" not in html
    assert "Special Discount" in html
    assert "[Notes]" in html


def test_quotation_pdf_ja_locale():
    ctx = sample_quotation_context(locale="ja", generated_at=datetime(2026, 6, 7))
    content = generate_quotation_pdf(ctx)
    assert content.startswith(b"%PDF")
    assert len(content) > 1000


def test_quotation_pdf_en_locale():
    ctx = sample_quotation_context(locale="en", generated_at=datetime(2026, 6, 7))
    content = generate_quotation_pdf(ctx)
    assert content.startswith(b"%PDF")
    assert len(content) > 1000


def test_report_pdf_starts_with_pdf_magic_bytes(report_context):
    content = generate_report_pdf(report_context)
    assert content.startswith(b"%PDF")


def test_report_pdf_ja_locale():
    ctx = sample_report_context(locale="ja", generated_at=datetime(2026, 6, 7))
    content = generate_report_pdf(ctx)
    assert content.startswith(b"%PDF")
    assert len(content) > 5000


def test_report_pdf_en_locale():
    ctx = sample_report_context(locale="en", generated_at=datetime(2026, 6, 7))
    content = generate_report_pdf(ctx)
    assert content.startswith(b"%PDF")
    assert len(content) > 5000


def test_report_pdf_html_uses_presentation_theme_page_and_cover():
    estimate = sample_estimate_with_discount()
    bundle = PresentationBundle(
        theme_id="custom-theme",
        style_id="custom-style",
        template_id="landscape-cover",
        theme_tokens={"colors": {"primary": "AABBCC", "text_on_primary": "FFFFFF"}},
        layout={"cover": True, "layout": "linear"},
        page={"size": "A4", "orientation": "landscape"},
        cover_fields=[
            {
                "key": "subtitle",
                "required": True,
                "content": {"_i18n": {"en": {"label": "Subtitle"}}},
            }
        ],
        cover_design={"background_color": "#112233"},
    )
    ctx = sample_report_context(
        estimate=estimate,
        locale="en",
        presentation=bundle,
        include_cover=True,
        cover_values={"subtitle": "Estimate presentation"},
    )
    html = _build_template_html(
        "estimate_report.html.j2",
        ctx=ctx,
        format_currency=format_currency,
        format_hours=format_hours,
        format_effort_days=format_effort_days,
        format_person_days=format_person_days,
    )

    assert "--export-primary: #AABBCC" in html
    assert "size: A4 landscape" in html
    assert "estimate-cover" in html
    assert "Estimate presentation" in html


@pytest.mark.parametrize(
    ("size", "orientation", "width_mm", "height_mm"),
    [
        ("A3", "portrait", 297, 420),
        ("A3", "landscape", 420, 297),
        ("A4", "portrait", 210, 297),
        ("A4", "landscape", 297, 210),
        ("Letter", "portrait", 215.9, 279.4),
        ("Letter", "landscape", 279.4, 215.9),
        ("Legal", "portrait", 215.9, 355.6),
        ("Legal", "landscape", 355.6, 215.9),
    ],
)
def test_estimate_report_and_formal_cover_share_accent_page_geometry(
    size,
    orientation,
    width_mm,
    height_mm,
):
    bundle = PresentationBundle(
        theme_id="custom-theme",
        style_id="custom-style",
        template_id="cover",
        theme_tokens={"colors": {"primary": "17365D", "accent": "2563EB"}},
        layout={"cover": True, "layout": "linear"},
        page={"size": size, "orientation": orientation},
        cover_design={
            "colors": {"background": "#f8fafc"},
            "accent_shapes": [_accent_shape()],
        },
        accent_warnings=["Accent warning"],
    )
    report_ctx = sample_report_context(
        presentation=bundle,
        include_cover=True,
    )
    report_html = _build_template_html(
        "estimate_report.html.j2",
        ctx=report_ctx,
        format_currency=format_currency,
        format_hours=format_hours,
        format_effort_days=format_effort_days,
        format_person_days=format_person_days,
    )
    formal_ctx = sample_formal_quotation_context()
    formal_ctx.update(
        {
            "theme": report_ctx["theme"],
            "style": report_ctx["style"],
            "page": report_ctx["page"],
            "include_cover": True,
            "cover": report_ctx["cover"],
        }
    )
    formal_html = _build_template_html(
        "estimate_quotation_formal.html.j2",
        ctx=formal_ctx,
        format_currency=format_currency,
    )

    assert report_ctx["cover"]["background_color"] == "#f8fafc"
    assert f'width="{width_mm}mm"' in report_ctx["cover"]["accent_svg"]
    assert f'height="{height_mm}mm"' in report_ctx["cover"]["accent_svg"]
    assert report_ctx["cover"]["warnings"] == ["Accent warning"]
    for html in (report_html, formal_html):
        assert 'class="cover-accent-art"' in html
        assert 'fill="#2563EB"' in html
        assert "background: #f8fafc" in html
        assert f"--cover-page-width: {width_mm}mm" in html
        assert f"--cover-page-height: {height_mm}mm" in html
        assert "width: 100%; height: 100%; }" not in html or ".cover-accent-art svg { display: block; width: 100%; height: 100%; }" not in html
        assert "max-width: none; max-height: none;" in html
    if size == "A4" and orientation == "portrait":
        assert generate_report_pdf(report_ctx).startswith(b"%PDF")
        assert generate_quotation_formal_pdf(formal_ctx).startswith(b"%PDF")


def test_estimate_cover_layers_background_accent_assets_then_fields():
    ctx = sample_report_context()
    ctx.update(
        {
            "include_cover": True,
            "cover": {
                "background_color": "#f8fafc",
                "accent_svg": (
                    '<svg xmlns="http://www.w3.org/2000/svg">'
                    '<rect fill="#2563eb" /></svg>'
                ),
                "assets": [{"region": "logo", "url": "logo.png", "alt": "Logo"}],
                "fields": [
                    {
                        "key": "title",
                        "label": "Title",
                        "value": "Layered title",
                        "emphasis": "title",
                    }
                ],
                "design": {},
                "warnings": [],
            },
        }
    )
    html = _build_template_html(
        "estimate_report.html.j2",
        ctx=ctx,
        format_currency=format_currency,
        format_hours=format_hours,
        format_effort_days=format_effort_days,
        format_person_days=format_person_days,
    )

    assert html.index('class="cover-accent-art"') < html.index(
        'class="estimate-cover-asset estimate-cover-asset-logo"'
    )
    assert html.index(
        'class="estimate-cover-asset estimate-cover-asset-logo"'
    ) < html.index('data-cover-key="title"')
    assert ".cover-accent-art" in html


def test_estimate_context_uses_theme_primary_for_unsafe_background_and_omits_hidden():
    bundle = PresentationBundle(
        theme_id="theme",
        style_id="style",
        template_id="template",
        theme_tokens={"colors": {"primary": "17365D", "accent": "2563EB"}},
        layout={"cover": True},
        cover_design={
            "colors": {"background": "url(javascript:alert(1))"},
            "accent_shapes": [_accent_shape(visible=False)],
        },
    )

    ctx = sample_report_context(presentation=bundle, include_cover=True)

    assert ctx["cover"]["background_color"] == "#ffffff"
    assert ctx["cover"]["accent_svg"] == ""


def test_formal_quotation_pdf_html_contains_populated_numbers():
    ctx = sample_formal_quotation_context(locale="ja")
    html = _build_template_html(
        "estimate_quotation_formal.html.j2",
        ctx=ctx,
        format_currency=format_currency,
    )
    assert "BAI-20260629-001" in html
    assert "T9010001234562" in html
    assert "開発" in html
    assert "インフラセットアップ" in html
    assert "【備考】" in html
    assert "*特記事項" not in html
    assert "grand-total-box" in html
    assert "grand-total-row" in html
    assert "header-layout" in html
    assert "company-divider" in html
    assert "下記の通りお見積もりいたします。" in html
    # 【備考】 and 小計 share one totals-layout row
    assert "totals-layout" in html
    assert html.index("summary-notes") < html.index("totals-table")
    assert html.index("notes-heading") < html.index(ctx["labels"]["subtotal"])


def test_formal_quotation_pdf_starts_with_pdf_magic_bytes():
    ctx = sample_formal_quotation_context()
    content = generate_quotation_formal_pdf(ctx)
    assert content.startswith(b"%PDF")
