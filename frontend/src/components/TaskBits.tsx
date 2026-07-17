import { useState } from "react";
import { Link } from "react-router-dom";

import type { Task } from "../api";
import { describeRecurrence, dueLabel } from "../dates";

export function DueChip({ iso }: { iso: string }) {
  const { text, tone } = dueLabel(iso);
  return <span className={`chip due ${tone}`}>{text}</span>;
}

export function TaskChips({ task }: { task: Task }) {
  const done = task.checklist.filter((i) => i.done).length;
  return (
    <span className="task-chips">
      {task.due_date && <DueChip iso={task.due_date} />}
      {task.recurrence && (
        <span className="chip recur" title={describeRecurrence(task.recurrence)}>
          ↻ {describeRecurrence(task.recurrence)}
        </span>
      )}
      {task.checklist.length > 0 && (
        <span className="chip">
          ☑ {done}/{task.checklist.length}
        </span>
      )}
      {task.category && <span className="chip cat">{task.category}</span>}
    </span>
  );
}

export function TaskRow({
  task,
  onComplete,
}: {
  task: Task;
  onComplete: (task: Task) => Promise<void>;
}) {
  const [leaving, setLeaving] = useState(false);

  const complete = async () => {
    if (leaving) return;
    setLeaving(true);
    try {
      await onComplete(task);
    } catch {
      setLeaving(false);
    }
  };

  return (
    <div className={`task-row${leaving ? " leaving" : ""}`}>
      <button className="check" aria-label={`Complete ${task.title}`} onClick={complete}>
        <svg viewBox="0 0 16 16" aria-hidden="true">
          <path d="M3.5 8.5 L6.5 11.5 L12.5 4.5" />
        </svg>
      </button>
      <Link to={`/tasks/${task.id}`} className="task-main">
        <span className="task-title">{task.title}</span>
        <TaskChips task={task} />
      </Link>
    </div>
  );
}

export function Toast({ text }: { text: string }) {
  return <div className="toast">{text}</div>;
}
