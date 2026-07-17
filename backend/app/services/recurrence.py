"""Date math for recurring tasks."""

import calendar
from datetime import date, timedelta


def add_interval(start: date, interval: int, unit: str) -> date:
    """Advance `start` by `interval` units, clamping month/year overflow
    (Jan 31 + 1 month -> Feb 28/29)."""
    if unit == "day":
        return start + timedelta(days=interval)
    if unit == "week":
        return start + timedelta(weeks=interval)
    if unit == "month":
        months = start.year * 12 + (start.month - 1) + interval
        year, month = divmod(months, 12)
        month += 1
        day = min(start.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    if unit == "year":
        return add_interval(start, interval * 12, "month")
    raise ValueError(f"Unknown recurrence unit: {unit}")


def next_due_date(
    due: date, completed_on: date, interval: int, unit: str, mode: str
) -> date:
    """Due date for the next occurrence after completing one.

    "completion" re-anchors on when the work was actually done (oil change:
    6 months from this one). "schedule" keeps the fixed cadence from the due
    date, rolling forward past occurrences already missed so the next due
    date is never in the past when a task is completed late.
    """
    if mode == "completion":
        return add_interval(completed_on, interval, unit)
    next_due = add_interval(due, interval, unit)
    while next_due <= completed_on:
        next_due = add_interval(next_due, interval, unit)
    return next_due
