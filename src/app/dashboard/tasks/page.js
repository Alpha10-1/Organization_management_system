"use client";

import { useEffect, useState } from "react";
import {
  createTask,
  deleteTask,
  fetchClients,
  fetchTasks,
  fetchUsers,
  updateTask,
  fetchProjects,
  fetchTaskDetail,
  fetchTaskDependencies,
  addTaskDependency,
  deleteTaskDependency,
  fetchTaskTemplates,
  createTaskTemplate,
} from "@/lib/api";

function clientDisplayName(client) {
  if (!client) return "";
  if ((client.client_type === "business" || client.client_type === "npo") && client.company_name) {
    return client.company_name;
  }
  const name = [client.first_name, client.last_name].filter(Boolean).join(" ");
  return name || client.company_name || `Client #${client.id}`;
}

const initialForm = {
  title: "",
  description: "",
  client_id: "",
  project_id: "",
  parent_task_id: "",
  assigned_to_email: "",
  priority: "medium",
  due_date: "",
  recurrence_rule: "",
  recurrence_end_date: "",
};

const RECURRENCE_OPTIONS = ["", "daily", "weekly", "monthly"];

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

  const [projects, setProjects] = useState([]);
  const [detailTask, setDetailTask] = useState(null);
  const [taskDetail, setTaskDetail] = useState(null);
  const [dependencies, setDependencies] = useState([]);
  const [depToAdd, setDepToAdd] = useState("");
  const [detailLoading, setDetailLoading] = useState(false);

  const [templates, setTemplates] = useState([]);
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [templateForm, setTemplateForm] = useState({ name: "", engagement_type: "", description: "" });
  const [templateItems, setTemplateItems] = useState([
    { title: "", relative_due_days: "", priority: "medium" },
  ]);
  const [savingTemplate, setSavingTemplate] = useState(false);

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
    fetchProjects().then(setProjects).catch(() => setProjects([]));
    fetchTaskTemplates().then(setTemplates).catch(() => setTemplates([]));
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
        project_id: form.project_id ? Number(form.project_id) : undefined,
        parent_task_id: form.parent_task_id ? Number(form.parent_task_id) : undefined,
        assigned_to_email: form.assigned_to_email || undefined,
        priority: form.priority,
        due_date: form.due_date ? new Date(form.due_date).toISOString() : undefined,
        recurrence_rule: form.recurrence_rule || undefined,
        recurrence_end_date: form.recurrence_end_date
          ? new Date(form.recurrence_end_date).toISOString()
          : undefined,
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

  async function openTaskDetail(task) {
    setDetailTask(task);
    setDetailLoading(true);
    try {
      const [detail, deps] = await Promise.all([
        fetchTaskDetail(task.id),
        fetchTaskDependencies(task.id),
      ]);
      setTaskDetail(detail);
      setDependencies(deps);
    } catch (err) {
      setError(err.message || "Failed to load task detail");
    } finally {
      setDetailLoading(false);
    }
  }

  function closeTaskDetail() {
    setDetailTask(null);
    setTaskDetail(null);
    setDependencies([]);
    setDepToAdd("");
  }

  async function handleAddDependency() {
    if (!detailTask || !depToAdd) return;
    try {
      setError("");
      await addTaskDependency(detailTask.id, Number(depToAdd));
      setDepToAdd("");
      await openTaskDetail(detailTask);
    } catch (err) {
      setError(err.message || "Failed to add dependency");
    }
  }

  async function handleRemoveDependency(dependencyId) {
    if (!detailTask) return;
    try {
      setError("");
      await deleteTaskDependency(detailTask.id, dependencyId);
      await openTaskDetail(detailTask);
    } catch (err) {
      setError(err.message || "Failed to remove dependency");
    }
  }

  function taskTitle(taskId) {
    const match = tasks.find((t) => t.id === taskId);
    return match ? match.title : `#${taskId}`;
  }

  function addTemplateItem() {
    setTemplateItems((prev) => [...prev, { title: "", relative_due_days: "", priority: "medium" }]);
  }

  function updateTemplateItem(index, field, value) {
    setTemplateItems((prev) =>
      prev.map((item, i) => (i === index ? { ...item, [field]: value } : item))
    );
  }

  function removeTemplateItem(index) {
    setTemplateItems((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleCreateTemplate(e) {
    e.preventDefault();
    try {
      setSavingTemplate(true);
      setError("");
      await createTaskTemplate({
        name: templateForm.name,
        engagement_type: templateForm.engagement_type || undefined,
        description: templateForm.description || undefined,
        items: templateItems
          .filter((i) => i.title.trim())
          .map((i, idx) => ({
            title: i.title,
            priority: i.priority,
            relative_due_days: i.relative_due_days !== "" ? Number(i.relative_due_days) : undefined,
            order_index: idx,
          })),
      });
      setTemplateForm({ name: "", engagement_type: "", description: "" });
      setTemplateItems([{ title: "", relative_due_days: "", priority: "medium" }]);
      setShowTemplateModal(false);
      const updated = await fetchTaskTemplates();
      setTemplates(updated);
    } catch (err) {
      setError(err.message || "Failed to create template");
    } finally {
      setSavingTemplate(false);
    }
  }

  function clientLabel(clientId) {
    const match = clients.find((c) => c.id === clientId);
    return match ? clientDisplayName(match) : null;
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

        <div className="flex gap-3">
          <button
            onClick={() => setShowTemplateModal(true)}
            className="rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
          >
            New Template
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800"
          >
            New Task
          </button>
        </div>
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
                      <p className="font-medium text-slate-900">
                        {task.parent_task_id ? <span className="mr-1 text-slate-400">↳</span> : null}
                        {task.title}
                      </p>
                      {task.description && (
                        <p className="mt-1 max-w-xs text-xs text-slate-500">{task.description}</p>
                      )}
                      {task.recurrence_rule && (
                        <span className="mt-1 inline-block rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-semibold text-indigo-700">
                          Recurs {task.recurrence_rule}
                        </span>
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
                      <div className="flex gap-3">
                        <button
                          onClick={() => openTaskDetail(task)}
                          className="text-sm font-semibold text-slate-700 hover:underline"
                        >
                          Detail
                        </button>
                        <button
                          onClick={() => handleDelete(task.id)}
                          className="text-sm font-semibold text-rose-600 hover:underline"
                        >
                          Delete
                        </button>
                      </div>
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
                        {clientDisplayName(c)}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Engagement</label>
                  <select
                    name="project_id"
                    value={form.project_id}
                    onChange={handleInputChange}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  >
                    <option value="">None</option>
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Parent Task (subtask of)</label>
                  <select
                    name="parent_task_id"
                    value={form.parent_task_id}
                    onChange={handleInputChange}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  >
                    <option value="">None (top-level task)</option>
                    {tasks.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.title}
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

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Recurrence</label>
                  <select
                    name="recurrence_rule"
                    value={form.recurrence_rule}
                    onChange={handleInputChange}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  >
                    {RECURRENCE_OPTIONS.map((r) => (
                      <option key={r || "none"} value={r}>
                        {r ? r.charAt(0).toUpperCase() + r.slice(1) : "None"}
                      </option>
                    ))}
                  </select>
                </div>

                {form.recurrence_rule ? (
                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Recurrence Ends</label>
                    <input
                      type="date"
                      name="recurrence_end_date"
                      value={form.recurrence_end_date}
                      onChange={handleInputChange}
                      className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                    />
                  </div>
                ) : null}
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

      {detailTask ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-slate-900">{detailTask.title}</h2>
                <p className="mt-1 text-sm text-slate-500">Subtasks, dependencies &amp; blockers</p>
              </div>
              <button
                onClick={closeTaskDetail}
                className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
              >
                Close
              </button>
            </div>

            {detailLoading ? (
              <p className="text-sm text-slate-500">Loading...</p>
            ) : taskDetail ? (
              <div className="space-y-4">
                {taskDetail.is_blocked ? (
                  <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
                    This task is blocked — one or more prerequisites aren&apos;t done yet.
                  </div>
                ) : null}

                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Subtasks</p>
                    <p className="mt-1 text-slate-800">
                      {taskDetail.open_subtask_count} open / {taskDetail.subtask_count} total
                    </p>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Status</p>
                    <p className="mt-1 capitalize text-slate-800">{STATUS_LABELS[taskDetail.status]}</p>
                  </div>
                </div>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Blocked By (this task waits on)
                  </p>
                  <div className="mt-2 space-y-2">
                    {dependencies.length === 0 ? (
                      <p className="text-sm text-slate-400">No dependencies.</p>
                    ) : (
                      dependencies.map((dep) => (
                        <div
                          key={dep.id}
                          className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-3 py-2"
                        >
                          <span className="text-sm text-slate-700">{taskTitle(dep.depends_on_task_id)}</span>
                          <button
                            onClick={() => handleRemoveDependency(dep.id)}
                            className="text-xs font-semibold text-rose-500 hover:underline"
                          >
                            Remove
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                  <div className="mt-2 flex gap-2">
                    <select
                      value={depToAdd}
                      onChange={(e) => setDepToAdd(e.target.value)}
                      className="flex-1 rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
                    >
                      <option value="">Add a dependency...</option>
                      {tasks
                        .filter((t) => t.id !== detailTask.id)
                        .map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.title}
                          </option>
                        ))}
                    </select>
                    <button
                      onClick={handleAddDependency}
                      disabled={!depToAdd}
                      className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-50"
                    >
                      Add
                    </button>
                  </div>
                </div>

                {taskDetail.blocks.length > 0 ? (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Blocks (waiting on this task)
                    </p>
                    <div className="mt-2 space-y-1">
                      {taskDetail.blocks.map((id) => (
                        <p key={id} className="text-sm text-slate-700">
                          {taskTitle(id)}
                        </p>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {showTemplateModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="max-h-[85vh] w-full max-w-xl overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-slate-900">New Task Template</h2>
                <p className="mt-1 text-sm text-slate-500">
                  A standard checklist (e.g. an audit kickoff) you can clone onto any engagement.
                </p>
              </div>
              <button
                onClick={() => setShowTemplateModal(false)}
                className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
              >
                Close
              </button>
            </div>

            <form onSubmit={handleCreateTemplate} className="space-y-4">
              <input
                placeholder="Template name"
                value={templateForm.name}
                onChange={(e) => setTemplateForm((p) => ({ ...p, name: e.target.value }))}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                required
              />
              <input
                placeholder="Engagement type (e.g. audit)"
                value={templateForm.engagement_type}
                onChange={(e) => setTemplateForm((p) => ({ ...p, engagement_type: e.target.value }))}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
              />
              <textarea
                placeholder="Description (optional)"
                value={templateForm.description}
                onChange={(e) => setTemplateForm((p) => ({ ...p, description: e.target.value }))}
                rows={2}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
              />

              <div>
                <p className="mb-2 text-sm font-medium text-slate-700">Checklist Items</p>
                <div className="space-y-2">
                  {templateItems.map((item, index) => (
                    <div key={index} className="flex gap-2">
                      <input
                        placeholder="Item title"
                        value={item.title}
                        onChange={(e) => updateTemplateItem(index, "title", e.target.value)}
                        className="flex-1 rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
                      />
                      <input
                        type="number"
                        placeholder="Due (days)"
                        value={item.relative_due_days}
                        onChange={(e) => updateTemplateItem(index, "relative_due_days", e.target.value)}
                        className="w-28 rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
                      />
                      <button
                        type="button"
                        onClick={() => removeTemplateItem(index)}
                        className="rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-50"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={addTemplateItem}
                  className="mt-2 text-sm font-semibold text-slate-700 hover:underline"
                >
                  + Add item
                </button>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowTemplateModal(false)}
                  className="rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingTemplate}
                  className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-70"
                >
                  {savingTemplate ? "Saving..." : "Create Template"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
