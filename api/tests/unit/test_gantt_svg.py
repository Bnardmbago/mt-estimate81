from html import escape

from app.exports.gantt_svg import build_gantt_svg


def test_build_gantt_svg_returns_svg_markup():
    gantt = {
        "project_start_date": "2026-06-09",
        "project_end_date": "2026-06-13",
        "total_working_days": 5,
        "tasks": [
            {
                "name": "User login & auth",
                "phase": "development",
                "role": "developer",
                "start_date": "2026-06-09",
                "end_date": "2026-06-13",
            }
        ],
    }

    svg = build_gantt_svg(gantt)

    assert svg.startswith("<svg")
    assert "User login" in svg
    assert 'stroke="#E2E8F0"' in svg
    assert 'rx="4"' in svg
    assert "development" in svg


def test_build_gantt_svg_uses_resolved_accent_for_chart_highlights():
    gantt = {
        "project_start_date": "2026-06-09",
        "project_end_date": "2026-06-10",
        "tasks": [
            {
                "name": "Design",
                "phase": "design",
                "start_date": "2026-06-09",
                "end_date": "2026-06-10",
            }
        ],
    }

    svg = build_gantt_svg(gantt, accent_color="#C026D3")

    assert 'fill="#C026D3"' in svg


def test_build_gantt_svg_escapes_task_names():
    gantt = {
        "project_start_date": "2026-06-09",
        "project_end_date": "2026-06-10",
        "tasks": [
            {
                "name": "<script>alert</script>",
                "phase": "testing",
                "start_date": "2026-06-09",
                "end_date": "2026-06-10",
            }
        ],
    }
    svg = build_gantt_svg(gantt)
    assert escape("<script>alert</script>")[:20] in svg
    assert "<script>" not in svg


def test_build_gantt_svg_empty_without_tasks():
    assert build_gantt_svg({"tasks": []}) == ""
