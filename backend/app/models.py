from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    # Freeform details: oil type, filter model, part numbers, links...
    notes: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(100), default="", index=True)
    due_date: Mapped[date | None] = mapped_column(Date, index=True)
    # How many days before due_date the "upcoming" reminder fires.
    remind_days_before: Mapped[int] = mapped_column(Integer, default=3)

    # Recurrence: every `recur_interval` `recur_unit`s. Mode "schedule" keeps a
    # fixed cadence anchored on the due date (e.g. gutters every 1 April);
    # "completion" re-anchors on when you actually did it (e.g. oil changes).
    recur_interval: Mapped[int | None] = mapped_column(Integer)
    recur_unit: Mapped[str | None] = mapped_column(String(10))  # day|week|month|year
    recur_mode: Mapped[str | None] = mapped_column(String(12))  # schedule|completion
    # All occurrences of a recurring task share the id of the first one.
    series_id: Mapped[int | None] = mapped_column(Integer, index=True)

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    checklist: Mapped[list["ChecklistItem"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="ChecklistItem.position",
        lazy="selectin",
    )

    @property
    def is_recurring(self) -> bool:
        return self.recur_interval is not None and self.recur_unit is not None


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(String(300))
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)

    task: Mapped[Task] = relationship(back_populates="checklist")


class NotificationLog(Base):
    """One row per reminder actually sent, so restarts and repeated scheduler
    passes never ping twice for the same task occurrence and kind."""

    __tablename__ = "notification_log"
    __table_args__ = (
        UniqueConstraint("task_id", "due_date", "kind", name="uq_notification_once"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    due_date: Mapped[date] = mapped_column(Date)
    kind: Mapped[str] = mapped_column(String(20))  # upcoming|due
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
