import pytest

from app.feedback.service import compute_variance, extract_estimated, primary_variance_pct


def test_variance_percentage():
    result = compute_variance(
        estimated={
            "effort_hours": 640,
            "effort_days": 80,
            "nrc_jpy": 4950000,
            "rc_monthly_jpy": 300000,
        },
        actual={
            "effort_hours": 720,
            "effort_days": 90,
            "nrc_jpy": 5400000,
            "rc_monthly_jpy": 280000,
        },
    )
    assert result["effort_hours"]["variance_pct"] == 12.5
    assert result["effort_hours"]["severity"] == "amber"
    assert result["nrc_jpy"]["variance_pct"] == pytest.approx(9.09, rel=0.01)
    assert result["nrc_jpy"]["severity"] == "green"


def test_variance_green_within_ten_percent():
    result = compute_variance(
        estimated={
            "effort_hours": 100,
            "effort_days": 12.5,
            "nrc_jpy": 1000000,
            "rc_monthly_jpy": 50000,
        },
        actual={
            "effort_hours": 105,
            "effort_days": 13,
            "nrc_jpy": 950000,
            "rc_monthly_jpy": 52000,
        },
    )
    assert result["effort_hours"]["severity"] == "green"
    assert result["nrc_jpy"]["severity"] == "green"


def test_variance_red_beyond_twenty_five_percent():
    result = compute_variance(
        estimated={
            "effort_hours": 100,
            "effort_days": 12.5,
            "nrc_jpy": 1000000,
            "rc_monthly_jpy": 50000,
        },
        actual={
            "effort_hours": 140,
            "effort_days": 17.5,
            "nrc_jpy": 1400000,
            "rc_monthly_jpy": 70000,
        },
    )
    assert result["effort_hours"]["severity"] == "red"
    assert result["effort_hours"]["variance_pct"] == 40.0


def test_variance_includes_effort_days_and_rc():
    result = compute_variance(
        estimated={
            "effort_hours": 80,
            "effort_days": 10,
            "nrc_jpy": 800000,
            "rc_monthly_jpy": 40000,
        },
        actual={
            "effort_hours": 88,
            "effort_days": 11,
            "nrc_jpy": 880000,
            "rc_monthly_jpy": 36000,
        },
    )
    assert result["effort_days"]["variance_pct"] == 10.0
    assert result["effort_days"]["severity"] == "green"
    assert result["rc_monthly_jpy"]["variance_pct"] == -10.0
    assert result["rc_monthly_jpy"]["severity"] == "green"


def test_extract_estimated_from_calculation_result():
    estimated = extract_estimated(
        {
            "total_effort_hours": 640,
            "total_effort_days": 80,
            "nrc": {"total_jpy": 4950000},
            "rc": {"monthly_total_jpy": 300000},
        }
    )
    assert estimated["effort_hours"] == 640
    assert estimated["effort_days"] == 80
    assert estimated["nrc_jpy"] == 4950000
    assert estimated["rc_monthly_jpy"] == 300000


def test_primary_variance_pct():
    variance = compute_variance(
        estimated={
            "effort_hours": 640,
            "effort_days": 80,
            "nrc_jpy": 100,
            "rc_monthly_jpy": 100,
        },
        actual={
            "effort_hours": 720,
            "effort_days": 90,
            "nrc_jpy": 200,
            "rc_monthly_jpy": 100,
        },
    )
    assert primary_variance_pct(variance) == 12.5
