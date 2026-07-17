import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api, RecurMode, RecurUnit, TaskInput } from "../api";

interface ChecklistDraft {
  key: number;
  text: string;
  done: boolean;
}

let draftKey = 0;

export default function TaskFormPage() {
  const { id } = useParams();
  const taskId = id ? Number(id) : null;
  const navigate = useNavigate();

  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [category, setCategory] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [remindDays, setRemindDays] = useState(3);
  const [recurring, setRecurring] = useState(false);
  const [interval, setInterval] = useState(1);
  const [unit, setUnit] = useState<RecurUnit>("month");
  const [mode, setMode] = useState<RecurMode>("schedule");
  const [checklist, setChecklist] = useState<ChecklistDraft[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(taskId === null);

  useEffect(() => {
    api.listCategories().then(setCategories).catch(() => {});
    if (taskId === null) return;
    api
      .getTask(taskId)
      .then((task) => {
        setTitle(task.title);
        setNotes(task.notes);
        setCategory(task.category);
        setDueDate(task.due_date ?? "");
        setRemindDays(task.remind_days_before);
        setRecurring(task.recurrence !== null);
        if (task.recurrence) {
          setInterval(task.recurrence.interval);
          setUnit(task.recurrence.unit);
          setMode(task.recurrence.mode);
        }
        setChecklist(
          task.checklist.map((i) => ({ key: draftKey++, text: i.text, done: i.done })),
        );
        setLoaded(true);
      })
      .catch((e) => setError((e as Error).message));
  }, [taskId]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (recurring && !dueDate) {
      setError("A recurring task needs a due date for its first occurrence.");
      return;
    }
    const data: TaskInput = {
      title: title.trim(),
      notes,
      category: category.trim(),
      due_date: dueDate || null,
      remind_days_before: remindDays,
      recurrence: recurring ? { interval, unit, mode } : null,
      checklist: checklist
        .filter((i) => i.text.trim())
        .map((i) => ({ text: i.text.trim(), done: i.done })),
    };
    setSaving(true);
    try {
      const task =
        taskId === null
          ? await api.createTask(data)
          : await api.updateTask(taskId, data);
      navigate(`/tasks/${task.id}`);
    } catch (err) {
      setError((err as Error).message);
      setSaving(false);
    }
  };

  if (!loaded && !error) return null;

  return (
    <>
      <div className="page-head">
        <h1>{taskId === null ? "New task" : "Edit task"}</h1>
      </div>

      <form className="form" onSubmit={submit}>
        {error && <div className="error-banner">{error}</div>}

        <div className="field">
          <label htmlFor="title">Title</label>
          <input
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Change furnace filter"
            required
            maxLength={200}
            autoFocus={taskId === null}
          />
        </div>

        <div className="field-row">
          <div className="field">
            <label htmlFor="category">Category</label>
            <input
              id="category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="house, car, health…"
              list="category-options"
              maxLength={100}
            />
            <datalist id="category-options">
              {categories.map((c) => (
                <option key={c} value={c} />
              ))}
            </datalist>
          </div>
          <div className="field">
            <label htmlFor="due">Due date</label>
            <input
              id="due"
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="remind">Remind (days before)</label>
            <input
              id="remind"
              type="number"
              min={0}
              max={365}
              value={remindDays}
              onChange={(e) => setRemindDays(Number(e.target.value))}
            />
          </div>
        </div>

        <div className="field recur-box">
          <label className="check-label">
            <input
              type="checkbox"
              checked={recurring}
              onChange={(e) => setRecurring(e.target.checked)}
            />
            <span>Repeats</span>
          </label>
          {recurring && (
            <div className="recur-controls">
              <div className="recur-every">
                <span>every</span>
                <input
                  type="number"
                  min={1}
                  max={365}
                  value={interval}
                  onChange={(e) => setInterval(Number(e.target.value))}
                  aria-label="Repeat interval"
                />
                <select
                  value={unit}
                  onChange={(e) => setUnit(e.target.value as RecurUnit)}
                  aria-label="Repeat unit"
                >
                  <option value="day">day{interval !== 1 && "s"}</option>
                  <option value="week">week{interval !== 1 && "s"}</option>
                  <option value="month">month{interval !== 1 && "s"}</option>
                  <option value="year">year{interval !== 1 && "s"}</option>
                </select>
              </div>
              <div className="recur-modes">
                <label className="check-label">
                  <input
                    type="radio"
                    name="mode"
                    checked={mode === "schedule"}
                    onChange={() => setMode("schedule")}
                  />
                  <span>
                    On a fixed schedule
                    <em>Cadence never drifts - good for “gutters every April”.</em>
                  </span>
                </label>
                <label className="check-label">
                  <input
                    type="radio"
                    name="mode"
                    checked={mode === "completion"}
                    onChange={() => setMode("completion")}
                  />
                  <span>
                    After each completion
                    <em>Next one counts from the day you finish - good for oil changes.</em>
                  </span>
                </label>
              </div>
            </div>
          )}
        </div>

        <div className="field">
          <label htmlFor="notes">Details</label>
          <textarea
            id="notes"
            rows={5}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder={"0W-20 full synthetic, 4.4 qt\nFilter: Toyota 04152-YZZA6"}
          />
          <span className="hint">
            Part numbers, sizes, links - the stuff you look up every time.
          </span>
        </div>

        <div className="field">
          <label>Checklist</label>
          {checklist.map((item, idx) => (
            <div key={item.key} className="checklist-row">
              <input
                value={item.text}
                onChange={(e) =>
                  setChecklist((list) =>
                    list.map((i, j) => (j === idx ? { ...i, text: e.target.value } : i)),
                  )
                }
                placeholder="Step…"
                maxLength={300}
              />
              <button
                type="button"
                className="icon-btn"
                aria-label="Remove step"
                onClick={() =>
                  setChecklist((list) => list.filter((_, j) => j !== idx))
                }
              >
                ✕
              </button>
            </div>
          ))}
          <button
            type="button"
            className="btn small"
            onClick={() =>
              setChecklist((list) => [...list, { key: draftKey++, text: "", done: false }])
            }
          >
            + Add step
          </button>
        </div>

        <div className="form-actions">
          <button className="btn primary" type="submit" disabled={saving || !title.trim()}>
            {taskId === null ? "Create task" : "Save changes"}
          </button>
          <button type="button" className="btn" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </>
  );
}
