from app.calculation.line_items import build_rc_export_breakdown
from app.exports.export_i18n import localize_rc_export_breakdown
from tests.unit.export_fixtures import sample_estimate_with_calculation, sample_report_context


def test_build_rc_export_breakdown_returns_five_standard_rows():
    calc = sample_estimate_with_calculation().calculation_result
    breakdown = build_rc_export_breakdown(calc, locale="en")

    assert len(breakdown["line_items"]) == 5
    cloud = next(row for row in breakdown["line_items"] if row["category_key"] == "cloud_infrastructure")
    assert cloud["category"] == "Cloud Infrastructure"
    assert cloud["service_description"] == "Server & database usage"
    assert cloud["monthly_jpy"] == 50000

    maintenance = next(
        row for row in breakdown["line_items"] if row["category_key"] == "maintenance_support"
    )
    assert maintenance["is_maintenance"] is True
    assert maintenance["monthly_jpy"] == 120000

    assert breakdown["monthly_total_jpy"] == 170000
    assert breakdown["annual_total_jpy"] == 2040000


def test_build_rc_export_breakdown_uses_markup_from_rc_detailed_breakdown():
    calc = sample_estimate_with_calculation().calculation_result
    calc = {
        **calc,
        "rc_detailed_breakdown": {
            "markup_rate_applied": 0.30,
            "line_items": [],
        },
    }
    breakdown = build_rc_export_breakdown(calc, locale="en")
    assert breakdown["monthly_total_jpy"] == 221000


def test_build_rc_export_breakdown_applies_markup_from_internal_pricing():
    calc = sample_estimate_with_calculation().calculation_result
    calc = {
        **calc,
        "internal_pricing": {"markup_rate_applied": 0.30},
    }
    breakdown = build_rc_export_breakdown(calc, locale="en")
    assert breakdown["monthly_total_jpy"] == 221000


def test_localize_rc_export_breakdown_ja():
    calc = sample_estimate_with_calculation().calculation_result
    breakdown = build_rc_export_breakdown(calc, locale="ja")
    localized = localize_rc_export_breakdown(breakdown, "ja")

    assert localized["line_items"][0]["category"] == "クラウドインフラ"
    assert localized["monthly_total_jpy"] == 170000


def test_report_context_includes_rc_breakdown():
    ctx = sample_report_context()
    rc_breakdown = ctx["rc_breakdown"]

    assert rc_breakdown["monthly_total_jpy"] == 170000
    assert rc_breakdown["annual_total_jpy"] == 2040000
    assert len(rc_breakdown["line_items"]) == 5
    assert rc_breakdown["line_items"][0]["service_description"]
