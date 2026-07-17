from datetime import date, timedelta

import pytest

from app.db import session_factory
from app.services import notify

TODAY = date(2026, 7, 16)


@pytest.fixture
def sent(monkeypatch):
    """Capture ntfy publishes instead of hitting the network."""
    calls: list[dict] = []

    async def fake_publish(title, message, priority="default", tags="", click=None):
        calls.append({"title": title, "priority": priority})

    monkeypatch.setattr(notify, "publish", fake_publish)
    return calls


async def _make_task(client, title: str, due: date, remind_days: int = 3) -> dict:
    resp = await client.post(
        "/api/tasks",
        json={
            "title": title,
            "due_date": due.isoformat(),
            "remind_days_before": remind_days,
        },
    )
    assert resp.status_code == 201
    return resp.json()


async def _run_pass(today: date) -> int:
    async with session_factory() as session:
        return await notify.send_due_reminders(session, today)


async def test_upcoming_reminder_sent_once(client, sent):
    await _make_task(client, "Change furnace filter", TODAY + timedelta(days=2))

    assert await _run_pass(TODAY) == 1
    assert sent[0]["title"] == "Change furnace filter - due in 2 days"
    assert sent[0]["priority"] == "default"

    # Second pass the same day: already logged, nothing new.
    assert await _run_pass(TODAY) == 0
    assert len(sent) == 1


async def test_due_reminder_is_high_priority_and_separate_from_upcoming(client, sent):
    await _make_task(client, "Oil change", TODAY + timedelta(days=1), remind_days=3)

    assert await _run_pass(TODAY) == 1  # upcoming
    assert await _run_pass(TODAY + timedelta(days=1)) == 1  # due today
    assert sent[1]["title"] == "Oil change - due today"
    assert sent[1]["priority"] == "high"

    # Overdue afterwards: both kinds already sent, stay quiet.
    assert await _run_pass(TODAY + timedelta(days=5)) == 0


async def test_overdue_task_found_after_downtime(client, sent):
    """If the server was off when the task came due, the reminder still goes
    out on the next pass, with the overdue phrasing."""
    await _make_task(client, "Renew registration", TODAY - timedelta(days=3))

    assert await _run_pass(TODAY) == 1
    assert sent[0]["title"] == "Renew registration - 3 days overdue"


async def test_far_future_and_completed_tasks_are_quiet(client, sent):
    await _make_task(client, "Winterize sprinklers", TODAY + timedelta(days=60))
    done = await _make_task(client, "Done thing", TODAY)
    await client.post(f"/api/tasks/{done['id']}/complete")

    assert await _run_pass(TODAY) == 0
    assert sent == []


async def test_notification_status_and_test_endpoint_disabled(client):
    status = (await client.get("/api/notifications/status")).json()
    assert status["enabled"] is False

    resp = await client.post("/api/notifications/test")
    assert resp.status_code == 400


async def test_notification_test_endpoint_enabled(client, monkeypatch, sent):
    monkeypatch.setattr("app.config.NTFY_TOPIC", "tend-test-topic")
    status = (await client.get("/api/notifications/status")).json()
    assert status["enabled"] is True
    assert (await client.post("/api/notifications/test")).status_code == 200
    assert sent[0]["title"] == "Tend test notification"
