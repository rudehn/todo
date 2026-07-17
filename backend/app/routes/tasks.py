from datetime import datetime, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import config
from ..db import get_session
from ..models import ChecklistItem, Task
from ..schemas import ChecklistToggle, CompleteOut, TaskIn, TaskOut
from ..services.recurrence import next_due_date

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def _get_task(session: AsyncSession, task_id: int) -> Task:
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _apply_input(task: Task, data: TaskIn) -> None:
    task.title = data.title.strip()
    task.notes = data.notes
    task.category = data.category.strip().lower()
    task.due_date = data.due_date
    task.remind_days_before = data.remind_days_before
    if data.recurrence is not None:
        task.recur_interval = data.recurrence.interval
        task.recur_unit = data.recurrence.unit
        task.recur_mode = data.recurrence.mode
    else:
        task.recur_interval = None
        task.recur_unit = None
        task.recur_mode = None
    task.checklist = [
        ChecklistItem(text=item.text.strip(), done=item.done, position=i)
        for i, item in enumerate(data.checklist)
    ]


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    status: Literal["open", "completed", "all"] = "open",
    category: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    query = select(Task)
    if status == "open":
        query = query.where(Task.completed_at.is_(None)).order_by(
            Task.due_date.asc().nulls_last(), Task.created_at.asc()
        )
    elif status == "completed":
        query = query.where(Task.completed_at.is_not(None)).order_by(
            Task.completed_at.desc()
        )
    else:
        query = query.order_by(Task.created_at.desc())
    if category:
        query = query.where(Task.category == category.strip().lower())
    result = await session.execute(query)
    return [TaskOut.from_task(t) for t in result.scalars().all()]


@router.get("/categories", response_model=list[str])
async def list_categories(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Task.category).where(Task.category != "").distinct().order_by(Task.category)
    )
    return [row[0] for row in result.all()]


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(data: TaskIn, session: AsyncSession = Depends(get_session)):
    task = Task()
    _apply_input(task, data)
    session.add(task)
    await session.flush()
    # Every task starts its own series; spawned occurrences inherit it.
    task.series_id = task.id
    await session.commit()
    return TaskOut.from_task(task)


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, session: AsyncSession = Depends(get_session)):
    return TaskOut.from_task(await _get_task(session, task_id))


@router.get("/{task_id}/history", response_model=list[TaskOut])
async def task_history(task_id: int, session: AsyncSession = Depends(get_session)):
    """Completed occurrences in this task's series, newest first."""
    task = await _get_task(session, task_id)
    result = await session.execute(
        select(Task)
        .where(
            Task.series_id == task.series_id,
            Task.completed_at.is_not(None),
            Task.id != task.id,
        )
        .order_by(Task.completed_at.desc())
    )
    return [TaskOut.from_task(t) for t in result.scalars().all()]


@router.put("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int, data: TaskIn, session: AsyncSession = Depends(get_session)
):
    task = await _get_task(session, task_id)
    _apply_input(task, data)
    await session.commit()
    return TaskOut.from_task(task)


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int, session: AsyncSession = Depends(get_session)):
    task = await _get_task(session, task_id)
    await session.delete(task)
    await session.commit()


@router.post("/{task_id}/complete", response_model=CompleteOut)
async def complete_task(task_id: int, session: AsyncSession = Depends(get_session)):
    task = await _get_task(session, task_id)
    if task.completed_at is not None:
        raise HTTPException(status_code=409, detail="Task is already completed")
    task.completed_at = datetime.now(timezone.utc)

    next_task: Task | None = None
    if task.is_recurring and task.due_date is not None:
        completed_on = datetime.now(ZoneInfo(config.TIMEZONE)).date()
        next_task = Task(
            title=task.title,
            notes=task.notes,
            category=task.category,
            due_date=next_due_date(
                task.due_date,
                completed_on,
                task.recur_interval,
                task.recur_unit,
                task.recur_mode or "schedule",
            ),
            remind_days_before=task.remind_days_before,
            recur_interval=task.recur_interval,
            recur_unit=task.recur_unit,
            recur_mode=task.recur_mode,
            series_id=task.series_id,
            checklist=[
                ChecklistItem(text=item.text, done=False, position=item.position)
                for item in task.checklist
            ],
        )
        session.add(next_task)

    await session.commit()
    return CompleteOut(
        completed=TaskOut.from_task(task),
        next=TaskOut.from_task(next_task) if next_task else None,
    )


@router.post("/{task_id}/reopen", response_model=TaskOut)
async def reopen_task(task_id: int, session: AsyncSession = Depends(get_session)):
    task = await _get_task(session, task_id)
    if task.completed_at is None:
        raise HTTPException(status_code=409, detail="Task is not completed")
    task.completed_at = None

    # Undo the occurrence that completing this one spawned, if it is still open.
    if task.is_recurring and task.series_id is not None:
        result = await session.execute(
            select(Task).where(
                Task.series_id == task.series_id,
                Task.completed_at.is_(None),
                Task.id != task.id,
            )
        )
        for spawned in result.scalars().all():
            await session.delete(spawned)

    await session.commit()
    return TaskOut.from_task(task)


@router.patch("/{task_id}/checklist/{item_id}", response_model=TaskOut)
async def toggle_checklist_item(
    task_id: int,
    item_id: int,
    data: ChecklistToggle,
    session: AsyncSession = Depends(get_session),
):
    task = await _get_task(session, task_id)
    item = next((i for i in task.checklist if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    item.done = data.done
    await session.commit()
    return TaskOut.from_task(task)
