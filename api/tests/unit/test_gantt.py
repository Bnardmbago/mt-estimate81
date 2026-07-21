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


def _balanced_items(total_hours: float, n_features: int = 20) -> list[GanttFeatureItem]:
    roles = ["PM", "designer", "developer", "QA"]
    per = total_hours / n_features
    items: list[GanttFeatureItem] = []
    for index in range(n_features):
        role = roles[index % len(roles)]
        phase = PHASE_ORDER[index % len(PHASE_ORDER)]
        items.append(
            GanttFeatureItem(str(index), index, f"Feature {index}", per, phase, role)
        )
    return items


def test_gantt_match_schedule_stretches_toward_target():
    items = _balanced_items(800)
    natural = build_gantt_timeline_two_pass(items, PHASE_ORDER, date(2026, 6, 9))
    matched = build_gantt_timeline_two_pass(
        items,
        PHASE_ORDER,
        date(2026, 6, 9),
        target_working_days=130,
        staffing_mode="match_schedule",
    )

    assert natural["total_working_days"] < 130
    assert matched["total_working_days"] <= 130
    assert matched["total_working_days"] >= natural["total_working_days"]
    assert matched["staffing_mode"] == "match_schedule"
    assert matched["target_working_days"] == 130
    assert sum(task["hours"] for task in matched["tasks"]) == sum(
        task["hours"] for task in natural["tasks"]
    )


def test_gantt_match_schedule_stretches_when_one_per_role_under_target():
    """Match desired schedule must approach T even when 1/role already finishes early.

    Hours stay fixed; calendar dilutes daily capacity (no invented feature hours).
    """
    items = [
        GanttFeatureItem("1", 0, "Tiny", 8, "development", "developer"),
    ]
    natural = build_gantt_timeline_two_pass(items, PHASE_ORDER, date(2026, 6, 9))
    matched = build_gantt_timeline_two_pass(
        items,
        PHASE_ORDER,
        date(2026, 6, 9),
        target_working_days=130,
        staffing_mode="match_schedule",
    )
    assert natural["total_working_days"] < 20
    assert matched["total_working_days"] <= 130
    assert matched["total_working_days"] >= 100
    assert matched["tasks"][0]["personnel_count"] == 1
    assert matched["tasks"][0]["hours"] == 8.0
    assert matched["staffing_mode"] == "match_schedule"


def test_gantt_match_schedule_under_band_multi_role_approaches_target():
    items = [
        GanttFeatureItem("1", 0, "Doc", 80, "development", "Full Stack Engineer"),
        GanttFeatureItem("2", 1, "OCR", 120, "development", "Senior Engineer"),
        GanttFeatureItem("3", 2, "Price", 160, "development", "Tech Lead"),
        GanttFeatureItem("4", 3, "SharePoint", 60, "development", "Engineer"),
        GanttFeatureItem("5", 4, "Dashboard", 80, "development", "Full Stack Engineer"),
    ]
    natural = build_gantt_timeline_two_pass(items, PHASE_ORDER, date(2026, 7, 20))
    matched = build_gantt_timeline_two_pass(
        items,
        PHASE_ORDER,
        date(2026, 7, 20),
        target_working_days=260,
        staffing_mode="match_schedule",
    )
    assert natural["total_working_days"] < 40
    assert matched["total_working_days"] <= 260
    assert matched["total_working_days"] >= 220
    assert sum(task["hours"] for task in matched["tasks"]) == 500.0
    assert all(task["personnel_count"] == 1 for task in matched["tasks"])


def test_gantt_match_schedule_aggressive_target_stays_within_band():
    # Even a large backlog can compress near 1 day with high headcount; match
    # mode should keep span ≤ target without changing hours.
    items = [
        GanttFeatureItem(str(i), i, f"Dev {i}", 80, "development", "developer")
        for i in range(20)
    ]
    matched = build_gantt_timeline_two_pass(
        items,
        PHASE_ORDER,
        date(2026, 6, 9),
        target_working_days=5,
        staffing_mode="match_schedule",
    )
    assert matched["total_working_days"] <= 5
    assert matched["total_working_days"] >= 1
    assert sum(task["hours"] for task in matched["tasks"]) == 1600.0
    assert matched["staffing_mode"] == "match_schedule"


def test_gantt_natural_mode_ignores_target():
    items = _balanced_items(800)
    with_target = build_gantt_timeline_two_pass(
        items,
        PHASE_ORDER,
        date(2026, 6, 9),
        target_working_days=130,
        staffing_mode="natural",
    )
    without = build_gantt_timeline_two_pass(items, PHASE_ORDER, date(2026, 6, 9))
    assert with_target["total_working_days"] == without["total_working_days"]
    assert with_target["staffing_mode"] == "natural"
