import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { api, Task } from "../api";
import { TaskRow, Toast } from "../components/TaskBits";
import { daysUntil, formatDate, todayISO } from "../dates";

interface Group {
  key: string;
  label: string;
  tasks: Task[];
}

function groupTasks(tasks: Task[]): Group[] {
  const groups: Group[] = [
    { key: "overdue", label: "Overdue", tasks: [] },
    { key: "today", label: "Today", tasks: [] },
    { key: "week", label: "This week", tasks: [] },
    { key: "upcoming", label: "Upcoming", tasks: [] },
    { key: "someday", label: "Someday", tasks: [] },
  ];
  const [overdue, today, week, upcoming, someday] = groups;
  for (const task of tasks) {
    if (!task.due_date) {
      someday.tasks.push(task);
      continue;
    }
    const days = daysUntil(task.due_date);
    if (days < 0) overdue.tasks.push(task);
    else if (days === 0) today.tasks.push(task);
    else if (days <= 7) week.tasks.push(task);
    else upcoming.tasks.push(task);
  }
  return groups.filter((g) => g.tasks.length > 0);
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[] | null>(null);
  const [categories, setCategories] = useState<string[]>([]);
  const [category, setCategory] = useState<string>("");
  const [quickTitle, setQuickTitle] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const toastTimer = useRef<number>();

  const load = useCallback(async (cat: string) => {
    try {
      const [tasks, categories] = await Promise.all([
        api.listTasks("open", cat || undefined),
        api.listCategories(),
      ]);
      setTasks(tasks);
      setCategories(categories);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load(category);
  }, [load, category]);

  const showToast = (text: string) => {
    setToast(text);
    window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(null), 4000);
  };

  const complete = async (task: Task) => {
    const result = await api.completeTask(task.id);
    showToast(
      result.next?.due_date
        ? `Done. Next "${task.title}" scheduled for ${formatDate(result.next.due_date)}.`
        : `"${task.title}" completed.`,
    );
    await load(category);
  };

  const quickAdd = async (e: FormEvent) => {
    e.preventDefault();
    const title = quickTitle.trim();
    if (!title) return;
    await api.createTask({
      title,
      notes: "",
      category: category,
      due_date: null,
      remind_days_before: 3,
      recurrence: null,
      checklist: [],
    });
    setQuickTitle("");
    await load(category);
  };

  const openCount = tasks?.length ?? 0;
  const overdueCount = tasks?.filter(
    (t) => t.due_date && daysUntil(t.due_date) < 0,
  ).length;

  return (
    <>
      <div className="page-head">
        <h1>Tasks</h1>
        <span className="sub">
          {tasks === null
            ? "…"
            : overdueCount
              ? `${openCount} open · ${overdueCount} overdue`
              : `${openCount} open`}
        </span>
        <span className="spacer" />
        <Link to="/tasks/new" className="btn primary">
          + New task
        </Link>
      </div>

      {categories.length > 0 && (
        <div className="cat-filter">
          <button
            className={`chip clickable${category === "" ? " on" : ""}`}
            onClick={() => setCategory("")}
          >
            All
          </button>
          {categories.map((c) => (
            <button
              key={c}
              className={`chip clickable${category === c ? " on" : ""}`}
              onClick={() => setCategory(category === c ? "" : c)}
            >
              {c}
            </button>
          ))}
        </div>
      )}

      <form className="quick-add" onSubmit={quickAdd}>
        <input
          value={quickTitle}
          onChange={(e) => setQuickTitle(e.target.value)}
          placeholder={
            category ? `Add a ${category} task…` : "Add a task… (details later)"
          }
          aria-label="New task title"
        />
        <button className="btn" type="submit" disabled={!quickTitle.trim()}>
          Add
        </button>
      </form>

      {error && <div className="error-banner">{error}</div>}

      {tasks !== null && tasks.length === 0 && !error && (
        <div className="empty-state">
          <div className="glyph">🌿</div>
          <h2>All clear</h2>
          <p>
            Nothing on the list{category ? ` for “${category}”` : ""}. Add a task
            above, or set up a recurring one with the New task button.
          </p>
        </div>
      )}

      {tasks !== null &&
        groupTasks(tasks).map((group) => (
          <section key={group.key} className={`task-group ${group.key}`}>
            <h2>
              {group.label} <span className="count">{group.tasks.length}</span>
            </h2>
            {group.tasks.map((task) => (
              <TaskRow key={task.id} task={task} onComplete={complete} />
            ))}
          </section>
        ))}

      {toast && <Toast text={toast} />}
      {tasks !== null && tasks.length > 0 && (
        <p className="due-note">
          Today is {formatDate(todayISO())}. Tasks disappear here when completed -
          find them under History.
        </p>
      )}
    </>
  );
}
