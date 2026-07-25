"use client";

import { useEffect, useState } from "react";
import {
  createTask,
  deleteTask,
  fetchClients,
  fetchTasks,
  fetchUsers,
  updateTask,
} from "@/lib/api";

const initialForm = {
  title: "",
  description: "",
  client_id: "",
  assigned_to_email: "",
  priority: "medium",
  due_date: "",
};

const STATUS_LABELS = {
  open: "Open",
  in_progress: "In Progress",
  done: "Done",
};

const PRIORITY_STYLES = {
  low: "bg-slate-100 text-slate-600",
  medium: "bg-amber-100 text-amber-700",
  high: "bg-rose-100 text-rose-700",
};

export default function TasksPage() {
  const [tasks, setTasks] = useState([]);
  const [users, setUsers] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState(initialForm);

  async function loadTasks(status = statusFilter) {
    try {
      setLoading(true);
      setError("");
      const data = await fetchTasks(status ? { status } : {});
      setTasks(data);
    } catch (err) {
      setError(err.message || "Failed to load tasks");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTasks();
    // Users/clients lists are best-effort context for the assignment
    // dropdowns; a staff account that can't list users (admin-only route)
    // simply won't get an assignee picker.
    fetchUsers().then(setUsers).catch(() => setUsers([]));
    fetchClients().then(setClients).catch(() => setClients([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadTasks(statusFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  function handleInputChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleCreateTask(e) {
    e.preventDefault();
    try {
      setSaving(true);
      setError("");
      const payload = {
        title: form.title,
        description: form.description || undefined,
        client_id: form.client_id ? Number(form.client_id) : undefined,
        assigned_to_email: form.assigned_to_email || undefined,
        priority: form.priority,
        due_date: form.due_date ? new Date(form.due_date).toISOString() : undefined,
      };
      await createTask(payload);
      setForm(initialForm);
      setShowModal(false);
      await loadTasks();
    } catch (err) {
      setError(err.message || "Failed to create task");
    } finally {
      setSaving(false);
    }
  }

  async function handleStatusChange(taskId, status) {
    try {
      setError("");
      await updateTask(taskId, { status });
      await loadTasks();
    } catch (err) {
      setError(err.message || "Failed to update task");
    }
  }

  async function handleDelete(taskId) {
    try {
      setError("");
      await deleteTask(taskId);
      await loadTasks();
    } catch (err) {
      setError(err.message || "Failed to delete task");
    }
  }

  function clientLabel(clientId) {
    const match = clients.find((c) => c.id === clientId);
    return match ? `${match.first_name} ${match.last_name}` : null;
  }

  function isOverdue(task) {
    return task.due_date && task.status !== "done" && new Date(task.due_date) < new Date();
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm md:flex-row md:items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Tasks &amp; Follow-ups</h1>
          <p className="mt-1 text-sm text-slate-500">
            Assign work, track due dates, and keep client follow-ups from falling through the cracks.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800"
        >
          New Task
        </button>
      </div>

      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2 rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        {["", "open", "in_progress", "done"].map((status) => (
          <button
            key={status || "all"}
            onClick={() => setStatusFilter(status)}
            className={`rounded-2xl px-4 py-2 text-sm font-semibold transition ${
              statusFilter === status
                ? "bg-slate-900 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {status ? STATUS_LABELS[status] : "All"}
          </button>
        ))}
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] border-separate border-spacing-y-3">
            <thead>
              <tr className="text-left text-sm text-slate-500">
                <th className="pb-2">Task</th>
                <th className="pb-2">Client</th>
                <th className="pb-2">Assigned To</th>
                <th className="pb-2">Priority</th>
                <th className="pb-2">Due</th>
                <th className="pb-2">Status</th>
                <th className="pb-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-sm text-slate-500">
                    Loading tasks...
                  </td>
                </tr>
              ) : tasks.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-sm text-slate-500">
                    No tasks found.
                  </td>
                </tr>
              ) : (
                tasks.map((task) => (
                  <tr key={task.id} className="bg-slate-50 align-top">
                    <td className="rounded-l-2xl px-4 py-4">
                      <p className="font-medium text-slate-900">{task.title}</p>
                      {task.description && (
                        <p className="mt-1 max-w-xs text-xs text-slate-500">{task.description}</p>
                      )}
                    </td>
                    <td className="px-4 py-4 text-sm text-slate-700">
                      {task.client_id ? clientLabel(task.client_id) || `#${task.client_id}` : "—"}
                    </td>
                    <td className="px-4 py-4 text-sm text-slate-700">
                      {task.assigned_to_name || "Unassigned"}
                    </td>
                    <td className="px-4 py-4">
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${PRIORITY_STYLES[task.priority] || PRIORITY_STYLES.medium}`}
                      >
                        {task.priority}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-sm">
                      {task.due_date ? (
                        <span className={isOverdue(task) ? "font-semibold text-rose-600" : "text-slate-700"}>
                          {new Date(task.due_date).toLocaleDateString()}
                        </span>
                      ) : (
                        <span className="text-slate-400">No due date</span>
                      )}
                    </td>
                    <td className="px-4 py-4">
                      <select
                        value={task.status}
                        onChange={(e) => handleStatusChange(task.id, e.target.value)}
                        className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
                      >
                        <option value="open">Open</option>
                        <option value="in_progress">In Progress</option>
                        <option value="done">Done</option>
                      </select>
                    </td>
                    <td className="rounded-r-2xl px-4 py-4">
                      <button
                        onClick={() => handleDelete(task.id)}
                        className="text-sm font-semibold text-rose-600 hover:underline"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="w-full max-w-xl rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-6 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold text-slate-900">New Task</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Create a follow-up and optionally assign it to a teammate.
                </p>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
              >
                Close
              </button>
            </div>

            <form onSubmit={handleCreateTask} className="space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Title</label>
                <input
                  name="title"
                  value={form.title}
                  onChange={handleInputChange}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  required
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Description</label>
                <textarea
                  name="description"
                  value={form.description}
                  onChange={handleInputChange}
                  rows={3}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Related Client</label>
                  <select
                    name="client_id"
                    value={form.client_id}
                    onChange={handleInputChange}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  >
                    <option value="">None</option>
                    {clients.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.first_name} {c.last_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Assign To</label>
                  <select
                    name="assigned_to_email"
                    value={form.assigned_to_email}
                    onChange={handleInputChange}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  >
                    <option value="">Unassigned</option>
                    {users.map((u) => (
                      <option key={u.email} value={u.email}>
                        {u.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Priority</label>
                  <select
                    name="priority"
                    value={form.priority}
                    onChange={handleInputChange}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Due Date</label>
                  <input
                    type="date"
                    name="due_date"
                    value={form.due_date}
                    onChange={handleInputChange}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-70"
                >
                  {saving ? "Saving..." : "Create Task"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
