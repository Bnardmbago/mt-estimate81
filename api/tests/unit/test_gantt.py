from datetime import date

from app.calculation.gantt import (
    GanttFeatureItem,
    _task_working_days,
    build_gantt_timeline,
    build_gantt_timeline_two_pass,
)


PHASE_ORDER = ["requirement", "design", "development", "testing", "deployment"]


def test_task_duration_scales_with_headcount():
    assert _task_working_days(40, 1) == 5
    assert _task_working_days(40, 2) == 3


def test_gantt_orders_by_phase_then_sort_order():
    items = [
        GanttFeatureItem("2", 1, "Dev task", 40, "development", "developer"),
        GanttFeatureItem("1", 0, "Req task", 16, "requirement", "PM"),
    ]
    result = build_gantt_timeline(items, PHASE_ORDER, date(2026, 6, 9))

    assert result["tasks"][0]["name"] == "Req task"
    assert result["tasks"][1]["name"] == "Dev task"
    assert result["tasks"][0]["start_date"] == "2026-06-09"
    assert result["tasks"][1]["start_date"] == "2026-06-09"


def test_gantt_overlaps_different_roles_from_project_start():
    items = [
        GanttFeatureItem("1", 0, "Req task", 16, "requirement", "PM"),
        GanttFeatureItem("2", 1, "Dev task", 40, "development", "developer"),
    ]
    result = build_gantt_timeline(items, PHASE_ORDER, date(2026, 6, 9))

    assert result["tasks"][0]["start_date"] == "2026-06-09"
    assert result["tasks"][1]["start_date"] == "2026-06-09"


def test_gantt_same_role_serial_when_one_track():
    items = [
        GanttFeatureItem("1", 0, "Dev A", 40, "development", "developer"),
        GanttFeatureItem("2", 1, "Dev B", 24, "development", "developer"),
    ]
    result = build_gantt_timeline(
        items,
        PHASE_ORDER,
        date(2026, 6, 9),
        role_headcount={"developer": 1},
    )

    assert result["tasks"][0]["start_date"] == "2026-06-09"
    assert result["tasks"][1]["start_date"] != "2026-06-09"
    assert result["tasks"][0]["parallel_track"] == 0
    assert result["tasks"][1]["parallel_track"] == 0


def test_gantt_same_role_parallel_when_headcount_allows():
    items = [
        GanttFeatureItem("1", 0, "Dev A", 40, "development", "developer"),
        GanttFeatureItem("2", 1, "Dev B", 40, "development", "developer"),
    ]
    result = build_gantt_timeline(
        items,
        PHASE_ORDER,
        date(2026, 6, 9),
        role_headcount={"developer": 2},
    )

    assert result["tasks"][0]["start_date"] == "2026-06-09"
    assert result["tasks"][1]["start_date"] == "2026-06-09"
    assert result["tasks"][0]["parallel_track"] != result["tasks"][1]["parallel_track"]


def test_gantt_cross_phase_overlap():
    items = [
        GanttFeatureItem("1", 0, "Req", 16, "requirement", "PM"),
        GanttFeatureItem("2", 1, "Build", 40, "development", "developer"),
    ]
    result = build_gantt_timeline(items, PHASE_ORDER, date(2026, 6, 9))

    assert result["tasks"][0]["start_date"] == result["tasks"][1]["start_date"]


def test_gantt_includes_personnel_count_on_tasks():
    items = [
        GanttFeatureItem("1", 0, "Dev", 40, "development", "developer"),
    ]
    result = build_gantt_timeline(
        items,
        PHASE_ORDER,
        date(2026, 6, 9),
        role_headcount={"developer": 2},
    )

    assert result["tasks"][0]["personnel_count"] == 2
    assert result["tasks"][0]["duration_working_days"] == 3


def test_gantt_two_pass_shorter_than_sequential_chain():
    items = [
        GanttFeatureItem("1", 0, "Req", 16, "requirement", "PM"),
        GanttFeatureItem("2", 1, "Dev A", 40, "development", "developer"),
        GanttFeatureItem("3", 2, "Dev B", 40, "development", "developer"),
    ]
    parallel = build_gantt_timeline_two_pass(items, PHASE_ORDER, date(2026, 6, 9))
    sequential_headcount = {"PM": 1, "developer": 1}
    sequential = build_gantt_timeline(
        items,
        PHASE_ORDER,
        date(2026, 6, 9),
        role_headcount=sequential_headcount,
    )

    assert parallel["total_working_days"] <= sequential["total_working_days"]


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
