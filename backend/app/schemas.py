from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

def _as_utc(dt: datetime | None) -> datetime | None:
    """SQLite hands back naive datetimes; they are stored as UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


RecurUnit = Literal["day", "week", "month", "year"]
RecurMode = Literal["schedule", "completion"]


class Recurrence(BaseModel):
    interval: int = Field(ge=1, le=365)
    unit: RecurUnit
    mode: RecurMode = "schedule"


class ChecklistItemIn(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    done: bool = False


class ChecklistItemOut(ChecklistItemIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    notes: str = ""
    category: str = Field(default="", max_length=100)
    due_date: date | None = None
    remind_days_before: int = Field(default=3, ge=0, le=365)
    recurrence: Recurrence | None = None
    checklist: list[ChecklistItemIn] = []

    @model_validator(mode="after")
    def recurring_needs_due_date(self) -> "TaskIn":
        if self.recurrence is not None and self.due_date is None:
            raise ValueError("A recurring task needs a due date to anchor on")
        return self


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    notes: str
    category: str
    due_date: date | None
    remind_days_before: int
    recurrence: Recurrence | None
    series_id: int | None
    completed_at: datetime | None
    created_at: datetime
    checklist: list[ChecklistItemOut]

    @classmethod
    def from_task(cls, task) -> "TaskOut":
        recurrence = None
        if task.is_recurring:
            recurrence = Recurrence(
                interval=task.recur_interval,
                unit=task.recur_unit,
                mode=task.recur_mode or "schedule",
            )
        return cls(
            id=task.id,
            title=task.title,
            notes=task.notes,
            category=task.category,
            due_date=task.due_date,
            remind_days_before=task.remind_days_before,
            recurrence=recurrence,
            series_id=task.series_id,
            completed_at=_as_utc(task.completed_at),
            created_at=_as_utc(task.created_at),
            checklist=[ChecklistItemOut.model_validate(i) for i in task.checklist],
        )


class CompleteOut(BaseModel):
    completed: TaskOut
    # The freshly spawned next occurrence, when the task recurs.
    next: TaskOut | None


class ChecklistToggle(BaseModel):
    done: bool


class NotificationStatus(BaseModel):
    enabled: bool
    url: str
    topic: str
    timezone: str
