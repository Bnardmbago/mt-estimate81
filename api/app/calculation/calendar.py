from datetime import date, timedelta


def normalize_start_date(value: date) -> date:
    """Snap weekend dates forward to the next Monday."""
    weekday = value.weekday()
    if weekday == 5:
        return value + timedelta(days=2)
    if weekday == 6:
        return value + timedelta(days=1)
    return value


def next_working_day(value: date) -> date:
    """Return the next calendar working day after value (Mon-Fri)."""
    current = value + timedelta(days=1)
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current


def add_working_days(start: date, days: int) -> date:
    """Return inclusive end date after spanning `days` working days from start."""
    if days <= 0:
        return start

    current = start
    remaining = days
    while remaining > 0:
        if current.weekday() < 5:
            remaining -= 1
            if remaining == 0:
                break
        current += timedelta(days=1)

    while current.weekday() >= 5:
        current += timedelta(days=1)

    return current


def count_working_days(start: date, end: date) -> int:
    """Count inclusive working days between start and end."""
    if end < start:
        return 0

    count = 0
    current = start
    while current <= end:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


def default_project_start_date(*, today: date | None = None) -> date:
    """Next Monday from today (or provided date), never a weekend."""
    today = today or date.today()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0 and today.weekday() < 5:
        candidate = today
    elif days_until_monday == 0:
        candidate = today + timedelta(days=7)
    else:
        candidate = today + timedelta(days=days_until_monday)
    return normalize_start_date(candidate)
