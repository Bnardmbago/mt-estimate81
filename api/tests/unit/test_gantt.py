from datetime import date

from app.calculation.gantt import GanttFeatureItem, build_gantt_timeline


PHASE_ORDER = ["requirement", "design", "development", "testing", "deployment"]


def test_gantt_orders_by_phase_then_sort_order():
    items = [
        GanttFeatureItem("2", 1, "Dev task", 40, "development", "developer"),
        GanttFeatureItem("1", 0, "Req task", 16, "requirement", "PM"),
    ]
    result = build_gantt_timeline(items, PHASE_ORDER, date(2026, 6, 9))

    assert result["tasks"][0]["name"] == "Req task"
    assert result["tasks"][1]["name"] == "Dev task"
    assert result["tasks"][0]["start_date"] == "2026-06-09"
    assert result["tasks"][1]["start_date"] == "2026-06-11"


def test_gantt_skips_zero_hour_items():
    items = [
        GanttFeatureItem("1", 0, "Real", 8, "development", "developer"),
        GanttFeatureItem("2", 1, "Empty", 0, "development", "developer"),
    ]
    result = build_gantt_timeline(items, PHASE_ORDER, date(2026, 6, 9))
    assert len(result["tasks"]) == 1


def test_gantt_unknown_phase_appended():
    items = [
        GanttFeatureItem("1", 0, "Custom", 8, "custom", "developer"),
        GanttFeatureItem("2", 0, "Req", 8, "requirement", "PM"),
    ]
    result = build_gantt_timeline(items, PHASE_ORDER, date(2026, 6, 9))
    assert result["tasks"][0]["phase"] == "requirement"
    assert result["tasks"][1]["phase"] == "custom"


def test_gantt_empty_items():
    result = build_gantt_timeline([], PHASE_ORDER, date(2026, 6, 9))
    assert result["total_working_days"] == 0
    assert result["tasks"] == []
