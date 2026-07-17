import type { Recurrence } from "./api";

export function todayISO(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** Whole days from today to an ISO date (negative when past). */
export function daysUntil(iso: string): number {
  const [y, m, d] = iso.split("-").map(Number);
  const target = new Date(y, m - 1, d);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((target.getTime() - today.getTime()) / 86_400_000);
}

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

/** "Aug 12" this year, "Aug 12, 2027" otherwise. */
export function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  const suffix = y === new Date().getFullYear() ? "" : `, ${y}`;
  return `${MONTHS[m - 1]} ${d}${suffix}`;
}

export function formatDateTime(iso: string): string {
  const dt = new Date(iso);
  return `${MONTHS[dt.getMonth()]} ${dt.getDate()}${
    dt.getFullYear() === new Date().getFullYear() ? "" : `, ${dt.getFullYear()}`
  }`;
}

export type DueTone = "overdue" | "today" | "soon" | "later";

export function dueLabel(iso: string): { text: string; tone: DueTone } {
  const days = daysUntil(iso);
  if (days < 0) {
    const n = -days;
    return { text: n === 1 ? "1 day overdue" : `${n} days overdue`, tone: "overdue" };
  }
  if (days === 0) return { text: "Today", tone: "today" };
  if (days === 1) return { text: "Tomorrow", tone: "soon" };
  if (days <= 7) return { text: `In ${days} days`, tone: "soon" };
  return { text: formatDate(iso), tone: "later" };
}

export function describeRecurrence(rec: Recurrence): string {
  const every =
    rec.interval === 1 ? `Every ${rec.unit}` : `Every ${rec.interval} ${rec.unit}s`;
  return rec.mode === "completion" ? `${every} after completion` : every;
}
