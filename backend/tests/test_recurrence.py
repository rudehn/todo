from datetime import date

import pytest

from app.services.recurrence import add_interval, next_due_date


def test_add_days_and_weeks():
    assert add_interval(date(2026, 1, 15), 10, "day") == date(2026, 1, 25)
    assert add_interval(date(2026, 1, 15), 2, "week") == date(2026, 1, 29)


def test_add_months_clamps_short_months():
    assert add_interval(date(2026, 1, 31), 1, "month") == date(2026, 2, 28)
    assert add_interval(date(2024, 1, 31), 1, "month") == date(2024, 2, 29)  # leap
    assert add_interval(date(2026, 10, 31), 1, "month") == date(2026, 11, 30)


def test_add_months_across_year_boundary():
    assert add_interval(date(2026, 11, 15), 3, "month") == date(2027, 2, 15)


def test_add_years():
    assert add_interval(date(2026, 3, 1), 2, "year") == date(2028, 3, 1)
    assert add_interval(date(2024, 2, 29), 1, "year") == date(2025, 2, 28)


def test_unknown_unit_rejected():
    with pytest.raises(ValueError):
        add_interval(date(2026, 1, 1), 1, "fortnight")


def test_completion_mode_anchors_on_completion_date():
    # Oil change due Jan 10, actually done Feb 1: next is 6 months from Feb 1.
    assert next_due_date(
        date(2026, 1, 10), date(2026, 2, 1), 6, "month", "completion"
    ) == date(2026, 8, 1)


def test_schedule_mode_keeps_cadence():
    # Monthly on the 15th, completed on time: next is the next 15th.
    assert next_due_date(
        date(2026, 1, 15), date(2026, 1, 15), 1, "month", "schedule"
    ) == date(2026, 2, 15)
    # Completed a few days late: cadence is kept, not shifted.
    assert next_due_date(
        date(2026, 1, 15), date(2026, 1, 20), 1, "month", "schedule"
    ) == date(2026, 2, 15)


def test_schedule_mode_skips_missed_occurrences():
    # Monthly task completed 3 months late: due date rolls past the missed
    # occurrences so the new one is not born overdue.
    assert next_due_date(
        date(2026, 1, 15), date(2026, 4, 20), 1, "month", "schedule"
    ) == date(2026, 5, 15)
