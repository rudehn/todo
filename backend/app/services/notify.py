"""ntfy push notifications and the background reminder loop.

Reminders fire twice per occurrence of a task: once when it comes within
`remind_days_before` days of due ("upcoming") and once on the due date
("due"). NotificationLog deduplicates across restarts, and a pass that runs
late (server was off, quiet hours) still sends the missed reminder.
"""

import asyncio
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import config
from ..db import session_factory
from ..models import NotificationLog, Task

logger = logging.getLogger(__name__)


def enabled() -> bool:
    return bool(config.NTFY_TOPIC)


async def publish(
    title: str,
    message: str,
    priority: str = "default",
    tags: str = "spiral_calendar",
    click: str | None = None,
) -> None:
    """POST one notification to the configured ntfy topic. Raises on failure.

    Uses ntfy's JSON publish endpoint: titles and messages are UTF-8 in the
    body, unlike the X-Title header, which only allows ASCII.
    """
    payload: dict = {
        "topic": config.NTFY_TOPIC,
        "title": title,
        "message": message,
        "priority": 4 if priority == "high" else 3,
        "tags": [tags],
    }
    if click:
        payload["click"] = click
    headers = {}
    if config.NTFY_TOKEN:
        headers["Authorization"] = f"Bearer {config.NTFY_TOKEN}"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(config.NTFY_URL, json=payload, headers=headers)
        resp.raise_for_status()


def _due_phrase(due: date, today: date) -> str:
    days = (due - today).days
    if days < -1:
        return f"{-days} days overdue"
    if days == -1:
        return "1 day overdue"
    if days == 0:
        return "due today"
    if days == 1:
        return "due tomorrow"
    return f"due in {days} days"


def _reminder_kind(task: Task, today: date) -> str | None:
    """Which reminder this task needs today, if any."""
    assert task.due_date is not None
    days_left = (task.due_date - today).days
    if days_left <= 0:
        return "due"
    if days_left <= task.remind_days_before:
        return "upcoming"
    return None


async def send_due_reminders(session: AsyncSession, today: date) -> int:
    """One reminder pass: send every notification owed as of `today` that has
    not been sent yet. Returns how many were sent."""
    result = await session.execute(
        select(Task).where(Task.completed_at.is_(None), Task.due_date.is_not(None))
    )
    tasks = result.scalars().all()

    wanted = [
        (task, kind) for task in tasks if (kind := _reminder_kind(task, today))
    ]
    if not wanted:
        return 0

    logged = await session.execute(
        select(NotificationLog.task_id, NotificationLog.due_date, NotificationLog.kind)
        .where(NotificationLog.task_id.in_([t.id for t, _ in wanted]))
    )
    already_sent = set(logged.all())

    sent = 0
    for task, kind in wanted:
        if (task.id, task.due_date, kind) in already_sent:
            continue
        phrase = _due_phrase(task.due_date, today)
        title = f"{task.title} - {phrase}"
        body_lines = []
        if task.category:
            body_lines.append(task.category.capitalize())
        if task.notes:
            body_lines.append(task.notes.split("\n", 1)[0][:200])
        await publish(
            title=title,
            message="\n".join(body_lines) or f"Due {task.due_date.isoformat()}",
            priority="high" if kind == "due" else "default",
            tags="alarm_clock" if kind == "due" else "spiral_calendar",
            click=f"{config.APP_URL}/tasks/{task.id}" if config.APP_URL else None,
        )
        session.add(
            NotificationLog(task_id=task.id, due_date=task.due_date, kind=kind)
        )
        await session.commit()
        sent += 1
    return sent


def _in_notify_window(now: datetime) -> bool:
    return config.NOTIFY_FROM_HOUR <= now.hour < config.NOTIFY_UNTIL_HOUR


async def reminder_loop() -> None:
    """Background task started at app startup when ntfy is configured."""
    logger.info(
        "Reminder loop running: topic %r on %s, window %02d-%02d %s",
        config.NTFY_TOPIC,
        config.NTFY_URL,
        config.NOTIFY_FROM_HOUR,
        config.NOTIFY_UNTIL_HOUR,
        config.TIMEZONE,
    )
    tz = ZoneInfo(config.TIMEZONE)
    while True:
        try:
            now = datetime.now(tz)
            if _in_notify_window(now):
                async with session_factory() as session:
                    count = await send_due_reminders(session, now.date())
                if count:
                    logger.info("Sent %d reminder(s)", count)
        except Exception:
            logger.exception("Reminder pass failed; retrying next cycle")
        await asyncio.sleep(config.REMINDER_CHECK_SECONDS)
