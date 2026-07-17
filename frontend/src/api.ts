export type RecurUnit = "day" | "week" | "month" | "year";
export type RecurMode = "schedule" | "completion";
export type TaskStatus = "open" | "completed" | "all";

export interface Recurrence {
  interval: number;
  unit: RecurUnit;
  mode: RecurMode;
}

export interface ChecklistItem {
  id: number;
  text: string;
  done: boolean;
}

export interface Task {
  id: number;
  title: string;
  notes: string;
  category: string;
  due_date: string | null;
  remind_days_before: number;
  recurrence: Recurrence | null;
  series_id: number | null;
  completed_at: string | null;
  created_at: string;
  checklist: ChecklistItem[];
}

export interface TaskInput {
  title: string;
  notes: string;
  category: string;
  due_date: string | null;
  remind_days_before: number;
  recurrence: Recurrence | null;
  checklist: { text: string; done: boolean }[];
}

export interface CompleteResult {
  completed: Task;
  next: Task | null;
}

export interface NotificationStatus {
  enabled: boolean;
  url: string;
  topic: string;
  timezone: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // keep statusText
    }
    throw new Error(detail);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json();
}

export const api = {
  listTasks: (status: TaskStatus = "open", category?: string) => {
    const params = new URLSearchParams({ status });
    if (category) params.set("category", category);
    return request<Task[]>(`/api/tasks?${params}`);
  },
  listCategories: () => request<string[]>("/api/tasks/categories"),
  getTask: (id: number) => request<Task>(`/api/tasks/${id}`),
  taskHistory: (id: number) => request<Task[]>(`/api/tasks/${id}/history`),
  createTask: (data: TaskInput) =>
    request<Task>("/api/tasks", { method: "POST", body: JSON.stringify(data) }),
  updateTask: (id: number, data: TaskInput) =>
    request<Task>(`/api/tasks/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteTask: (id: number) => request<void>(`/api/tasks/${id}`, { method: "DELETE" }),
  completeTask: (id: number) =>
    request<CompleteResult>(`/api/tasks/${id}/complete`, { method: "POST" }),
  reopenTask: (id: number) =>
    request<Task>(`/api/tasks/${id}/reopen`, { method: "POST" }),
  toggleChecklistItem: (taskId: number, itemId: number, done: boolean) =>
    request<Task>(`/api/tasks/${taskId}/checklist/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify({ done }),
    }),

  notificationStatus: () => request<NotificationStatus>("/api/notifications/status"),
  sendTestNotification: () =>
    request<{ ok: boolean }>("/api/notifications/test", { method: "POST" }),
};
