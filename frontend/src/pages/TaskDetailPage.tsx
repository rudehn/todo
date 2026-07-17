import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api, Task } from "../api";
import { DueChip, Toast } from "../components/TaskBits";
import { describeRecurrence, formatDate, formatDateTime } from "../dates";

export default function TaskDetailPage() {
  const { id } = useParams();
  const taskId = Number(id);
  const navigate = useNavigate();

  const [task, setTask] = useState<Task | null>(null);
  const [history, setHistory] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [task, history] = await Promise.all([
        api.getTask(taskId),
        api.taskHistory(taskId),
      ]);
      setTask(task);
      setHistory(history);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [taskId]);

  useEffect(() => {
    load();
  }, [load]);

  if (error) return <div className="error-banner">{error}</div>;
  if (!task) return null;

  const complete = async () => {
    const result = await api.completeTask(task.id);
    if (result.next) {
      navigate(`/tasks/${result.next.id}`, { replace: true });
      setToast(
        `Completed. Next occurrence due ${
          result.next.due_date ? formatDate(result.next.due_date) : "later"
        }.`,
      );
      window.setTimeout(() => setToast(null), 4000);
    } else {
      await load();
    }
  };

  const reopen = async () => {
    await api.reopenTask(task.id);
    await load();
  };

  const remove = async () => {
    if (!window.confirm(`Delete "${task.title}"? This cannot be undone.`)) return;
    await api.deleteTask(task.id);
    navigate(task.completed_at ? "/history" : "/tasks");
  };

  const toggleItem = async (itemId: number, done: boolean) => {
    setTask(await api.toggleChecklistItem(task.id, itemId, done));
  };

  const doneCount = task.checklist.filter((i) => i.done).length;

  return (
    <>
      <div className="page-head">
        <div>
          <div className="crumbs">
            <Link to={task.completed_at ? "/history" : "/tasks"}>
              ← {task.completed_at ? "History" : "Tasks"}
            </Link>
          </div>
          <h1 className={task.completed_at ? "struck" : ""}>{task.title}</h1>
          <div className="detail-chips">
            {task.due_date && !task.completed_at && <DueChip iso={task.due_date} />}
            {task.due_date && (
              <span className="chip">Due {formatDate(task.due_date)}</span>
            )}
            {task.recurrence && (
              <span className="chip recur">↻ {describeRecurrence(task.recurrence)}</span>
            )}
            {task.due_date && !task.completed_at && (
              <span className="chip">
                Reminds {task.remind_days_before} day
                {task.remind_days_before === 1 ? "" : "s"} before
              </span>
            )}
            {task.category && <span className="chip cat">{task.category}</span>}
          </div>
        </div>
        <span className="spacer" />
        <div className="head-actions">
          {task.completed_at ? (
            <button className="btn" onClick={reopen}>
              Reopen
            </button>
          ) : (
            <button className="btn primary" onClick={complete}>
              ✓ Complete
            </button>
          )}
          <Link to={`/tasks/${task.id}/edit`} className="btn">
            Edit
          </Link>
          <button className="btn danger" onClick={remove}>
            Delete
          </button>
        </div>
      </div>

      {task.completed_at && (
        <div className="done-banner">
          Completed {formatDateTime(task.completed_at)}.
        </div>
      )}

      <div className="detail-cols">
        <div className="col">
          {task.checklist.length > 0 && (
            <section className="panel">
              <h2>
                Checklist{" "}
                <span className="count">
                  {doneCount}/{task.checklist.length}
                </span>
              </h2>
              <ul className="checklist">
                {task.checklist.map((item) => (
                  <li key={item.id} className={item.done ? "done" : ""}>
                    <label>
                      <input
                        type="checkbox"
                        checked={item.done}
                        onChange={(e) => toggleItem(item.id, e.target.checked)}
                      />
                      <span>{item.text}</span>
                    </label>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {history.length > 0 && (
            <section className="panel">
              <h2>
                History <span className="count">{history.length}</span>
              </h2>
              <ul className="history-list">
                {history.map((h) => (
                  <li key={h.id}>
                    <span className="when">
                      {h.completed_at ? formatDateTime(h.completed_at) : ""}
                    </span>
                    {h.due_date && (
                      <span className="was-due">was due {formatDate(h.due_date)}</span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>

        <section className="panel notes-panel">
          <h2>Details</h2>
          {task.notes ? (
            <p className="notes">{task.notes}</p>
          ) : (
            <p className="muted">
              No details yet. Use Edit to note part numbers, oil types, filter
              models - anything future-you needs.
            </p>
          )}
        </section>
      </div>

      {toast && <Toast text={toast} />}
    </>
  );
}
