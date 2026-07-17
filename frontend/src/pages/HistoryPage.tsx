import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api, Task } from "../api";
import { formatDateTime } from "../dates";

export default function HistoryPage() {
  const [tasks, setTasks] = useState<Task[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setTasks(await api.listTasks("completed"));
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const reopen = async (task: Task) => {
    await api.reopenTask(task.id);
    await load();
  };

  const remove = async (task: Task) => {
    if (!window.confirm(`Delete "${task.title}" from history?`)) return;
    await api.deleteTask(task.id);
    await load();
  };

  return (
    <>
      <div className="page-head">
        <h1>History</h1>
        <span className="sub">{tasks ? `${tasks.length} completed` : "…"}</span>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {tasks !== null && tasks.length === 0 && !error && (
        <div className="empty-state">
          <div className="glyph">📜</div>
          <h2>Nothing completed yet</h2>
          <p>Completed tasks land here, including every past occurrence of a recurring one.</p>
        </div>
      )}

      <div className="history-page-list">
        {tasks?.map((task) => (
          <div key={task.id} className="task-row done">
            <span className="check static" aria-hidden="true">
              <svg viewBox="0 0 16 16">
                <path d="M3.5 8.5 L6.5 11.5 L12.5 4.5" />
              </svg>
            </span>
            <Link to={`/tasks/${task.id}`} className="task-main">
              <span className="task-title">{task.title}</span>
              <span className="task-chips">
                {task.completed_at && (
                  <span className="chip">{formatDateTime(task.completed_at)}</span>
                )}
                {task.recurrence && <span className="chip recur">↻</span>}
                {task.category && <span className="chip cat">{task.category}</span>}
              </span>
            </Link>
            <div className="row-actions">
              <button className="btn small" onClick={() => reopen(task)}>
                Reopen
              </button>
              <button className="btn small danger" onClick={() => remove(task)}>
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
