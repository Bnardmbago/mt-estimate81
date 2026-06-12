from datetime import date

from app.calculation.calendar import (
    add_working_days,
    count_working_days,
    default_project_start_date,
    normalize_start_date,
)


def test_normalize_start_date_snaps_saturday_to_monday():
    assert normalize_start_date(date(2026, 6, 6)) == date(2026, 6, 8)


def test_normalize_start_date_snaps_sunday_to_monday():
    assert normalize_start_date(date(2026, 6, 7)) == date(2026, 6, 8)


def test_normalize_start_date_keeps_weekday():
    assert normalize_start_date(date(2026, 6, 9)) == date(2026, 6, 9)


def test_add_working_days_single_day():
    assert add_working_days(date(2026, 6, 9), 1) == date(2026, 6, 9)


def test_add_working_days_skips_weekend():
    assert add_working_days(date(2026, 6, 12), 2) == date(2026, 6, 15)


def test_count_working_days_inclusive():
    assert count_working_days(date(2026, 6, 9), date(2026, 6, 15)) == 5


def test_default_project_start_date_is_weekday():
    start = default_project_start_date(today=date(2026, 6, 6))
    assert start.weekday() < 5
