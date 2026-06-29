from app.calculation.rc_detailed import (
    RC_CATEGORY_KEYS,
    build_detailed_rc_breakdown,
    resolve_rc_category_key,
)
from tests.unit.export_fixtures import sample_estimate_with_calculation


def test_resolve_rc_category_key_maps_hosting_to_cloud():
    assert resolve_rc_category_key({"name": "hosting"}) == "cloud_infrastructure"
    assert resolve_rc_category_key({"name": "monitoring"}) == "system_monitoring"
    assert resolve_rc_category_key({"category": "Security"}) == "security"


def test_build_detailed_rc_breakdown_always_has_five_rows():
    calc = sample_estimate_with_calculation().calculation_result
    breakdown = build_detailed_rc_breakdown(calc, locale="en", markup_rate=0.0)

    assert len(breakdown["line_items"]) == len(RC_CATEGORY_KEYS)
    assert breakdown["monthly_total_jpy"] == 170000
    assert breakdown["annual_total_jpy"] == 2040000

    cloud = next(row for row in breakdown["line_items"] if row["category_key"] == "cloud_infrastructure")
    maintenance = next(
        row for row in breakdown["line_items"] if row["category_key"] == "maintenance_support"
    )
    assert cloud["monthly_jpy"] == 50000
    assert cloud["service_description"] == "Server & database usage"
    assert maintenance["monthly_jpy"] == 120000
    assert maintenance["service_description"] == "Minor fixes & inquiry support"


def test_build_detailed_rc_breakdown_applies_markup():
    calc = sample_estimate_with_calculation().calculation_result
    breakdown = build_detailed_rc_breakdown(calc, locale="en", markup_rate=0.30)

    assert breakdown["markup_rate_applied"] == 0.30
    assert breakdown["monthly_total_jpy"] == 221000
    assert breakdown["annual_total_jpy"] == 2652000
    assert sum(row["monthly_jpy"] for row in breakdown["line_items"]) == 221000


def test_build_detailed_rc_breakdown_ja_labels():
    calc = sample_estimate_with_calculation().calculation_result
    breakdown = build_detailed_rc_breakdown(calc, locale="ja", markup_rate=0.0)

    cloud = breakdown["line_items"][0]
    assert cloud["category"] == "クラウドインフラ"
    assert cloud["service_description"] == "サーバー・データベース利用"
