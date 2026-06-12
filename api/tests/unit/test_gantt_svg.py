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
    assert "#4f46e5" in svg


def test_build_gantt_svg_empty_without_tasks():
    assert build_gantt_svg({"tasks": []}) == ""
