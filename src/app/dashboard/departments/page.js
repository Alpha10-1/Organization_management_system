"use client";

import { useEffect, useMemo, useState } from "react";
import {
  fetchCurrentUser,
  fetchDepartments,
  fetchDepartmentDetail,
  fetchDepartmentDashboard,
  createDepartment,
  updateDepartment,
  deleteDepartment,
  fetchUsers,
  fetchTaskTemplates,
  createTaskTemplate,
  deleteTaskTemplate,
  applyTaskTemplateToUser,
} from "@/lib/api";

function formatMoney(value) {
  if (value === null || value === undefined || value === "") return "—";
  return `$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const initialDeptForm = {
  name: "",
  description: "",
  department_head_user_id: "",
  annual_budget: "",
  cost_center_code: "",
};

const initialTemplateForm = {
  name: "",
  description: "",
  trigger_event: "onboarding",
  items: [{ title: "", relative_due_days: 1 }],
};

export default function DepartmentsPage() {
  const [currentUser, setCurrentUser] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [departments, setDepartments] = useState([]);
  const [users, setUsers] = useState([]);
  const [usersError, setUsersError] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [templates, setTemplates] = useState([]);

  const [showDeptModal, setShowDeptModal] = useState(false);
  const [editingDept, setEditingDept] = useState(null);
  const [deptForm, setDeptForm] = useState(initialDeptForm);

  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [templateForm, setTemplateForm] = useState(initialTemplateForm);

  const [applyTarget, setApplyTarget] = useState(null);
  const [applyEmail, setApplyEmail] = useState("");

  useEffect(() => {
    fetchCurrentUser()
      .then((u) => {
        setCurrentUser(u);
        setIsAdmin(u?.role === "admin");
      })
      .catch(() => setCurrentUser(null));
    loadDepartments();
    fetchUsers()
      .then(setUsers)
      .catch(() => setUsersError("Admin access required to see the full staff directory."));
  }, []);

  async function loadDepartments() {
    setLoading(true);
    setError("");
    try {
      const data = await fetchDepartments();
      setDepartments(data);
      if (data.length && !selectedId) {
        setSelectedId(data[0].id);
      }
    } catch (err) {
      setError(err.message || "Failed to load departments");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!selectedId) return;
    loadDetail(selectedId);
  }, [selectedId]);

  async function loadDetail(id) {
    try {
      setError("");
      const [d, dash, tpls] = await Promise.all([
        fetchDepartmentDetail(id),
        fetchDepartmentDashboard(id).catch(() => null),
        fetchTaskTemplates({ department_id: id }).catch(() => []),
      ]);
      setDetail(d);
      setDashboard(dash);
      setTemplates(tpls.filter((t) => t.trigger_event === "onboarding" || t.trigger_event === "offboarding"));
    } catch (err) {
      setError(err.message || "Failed to load department detail");
    }
  }

  function userLabel(id) {
    const u = users.find((x) => x.id === id);
    return u ? `${u.name} (${u.email})` : id ? `User #${id}` : "—";
  }

  function openCreateDept() {
    setEditingDept(null);
    setDeptForm(initialDeptForm);
    setShowDeptModal(true);
  }

  function openEditDept(dept) {
    setEditingDept(dept);
    setDeptForm({
      name: dept.name,
      description: dept.description || "",
      department_head_user_id: dept.department_head_user_id ? String(dept.department_head_user_id) : "",
      annual_budget: dept.annual_budget ?? "",
      cost_center_code: dept.cost_center_code || "",
    });
    setShowDeptModal(true);
  }

  async function handleSubmitDept(e) {
    e.preventDefault();
    try {
      setSaving(true);
      setError("");
      const payload = {
        name: deptForm.name,
        description: deptForm.description || undefined,
        department_head_user_id: deptForm.department_head_user_id
          ? Number(deptForm.department_head_user_id)
          : undefined,
        annual_budget: deptForm.annual_budget !== "" ? Number(deptForm.annual_budget) : undefined,
        cost_center_code: deptForm.cost_center_code || undefined,
      };
      if (editingDept) {
        await updateDepartment(editingDept.id, payload);
      } else {
        await createDepartment(payload);
      }
      setShowDeptModal(false);
      await loadDepartments();
      if (selectedId) await loadDetail(selectedId);
    } catch (err) {
      setError(err.message || "Failed to save department");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteDept(dept) {
    if (!window.confirm(`Delete department "${dept.name}"?`)) return;
    try {
      setError("");
      await deleteDepartment(dept.id);
      if (selectedId === dept.id) setSelectedId(null);
      await loadDepartments();
    } catch (err) {
      setError(err.message || "Failed to delete department");
    }
  }

  function openTemplateModal() {
    setTemplateForm({ ...initialTemplateForm, name: "" });
    setShowTemplateModal(true);
  }

  function updateTemplateItem(idx, field, value) {
    setTemplateForm((p) => {
      const items = [...p.items];
      items[idx] = { ...items[idx], [field]: value };
      return { ...p, items };
    });
  }

  function addTemplateItem() {
    setTemplateForm((p) => ({
      ...p,
      items: [...p.items, { title: "", relative_due_days: p.items.length + 1 }],
    }));
  }

  function removeTemplateItem(idx) {
    setTemplateForm((p) => ({ ...p, items: p.items.filter((_, i) => i !== idx) }));
  }

  async function handleCreateTemplate(e) {
    e.preventDefault();
    if (!selectedId) return;
    try {
      setSaving(true);
      setError("");
      await createTaskTemplate({
        name: templateForm.name,
        description: templateForm.description || undefined,
        trigger_event: templateForm.trigger_event,
        department_id: selectedId,
        items: templateForm.items
          .filter((it) => it.title.trim())
          .map((it, i) => ({
            title: it.title,
            priority: "medium",
            relative_due_days: it.relative_due_days !== "" ? Number(it.relative_due_days) : undefined,
            order_index: i,
          })),
      });
      setShowTemplateModal(false);
      await loadDetail(selectedId);
    } catch (err) {
      setError(err.message || "Failed to create checklist");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteTemplate(tpl) {
    if (!window.confirm(`Delete checklist "${tpl.name}"?`)) return;
    try {
      setError("");
      await deleteTaskTemplate(tpl.id);
      await loadDetail(selectedId);
    } catch (err) {
      setError(err.message || "Failed to delete checklist");
    }
  }

  async function handleApplyTemplate(e) {
    e.preventDefault();
    if (!applyTarget || !applyEmail) return;
    try {
      setSaving(true);
      setError("");
      await applyTaskTemplateToUser(applyTarget.id, { user_email: applyEmail });
      setApplyTarget(null);
      setApplyEmail("");
    } catch (err) {
      setError(err.message || "Failed to apply checklist");
    } finally {
      setSaving(false);
    }
  }

  const selectedDept = useMemo(
    () => departments.find((d) => d.id === selectedId) || null,
    [departments, selectedId]
  );

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Departments</h1>
          <p className="text-sm text-slate-500">
            Cost centers, staffing, and KPI visibility per department.
          </p>
        </div>
        {isAdmin ? (
          <button
            onClick={openCreateDept}
            className="rounded-2xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
          >
            + New Department
          </button>
        ) : null}
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
        <div className="space-y-2 rounded-3xl border border-slate-200 bg-white p-4">
          {loading ? (
            <p className="text-sm text-slate-400">Loading...</p>
          ) : departments.length === 0 ? (
            <p className="text-sm text-slate-400">No departments yet.</p>
          ) : (
            departments.map((d) => (
              <button
                key={d.id}
                onClick={() => setSelectedId(d.id)}
                className={`block w-full rounded-xl px-3 py-2 text-left text-sm ${
                  selectedId === d.id ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                <p className="font-medium">{d.name}</p>
                {d.cost_center_code ? (
                  <p className={`text-xs ${selectedId === d.id ? "text-slate-300" : "text-slate-400"}`}>
                    {d.cost_center_code}
                  </p>
                ) : null}
              </button>
            ))
          )}
        </div>

        <div className="space-y-6">
          {!selectedDept ? (
            <div className="rounded-3xl border border-slate-200 bg-white p-6 text-sm text-slate-400">
              Select a department to see detail.
            </div>
          ) : (
            <>
              <div className="rounded-3xl border border-slate-200 bg-white p-6">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold text-slate-900">{selectedDept.name}</h2>
                    {detail?.description ? (
                      <p className="mt-1 text-sm text-slate-500">{detail.description}</p>
                    ) : null}
                  </div>
                  {isAdmin ? (
                    <div className="flex shrink-0 gap-2">
                      <button
                        onClick={() => openEditDept(selectedDept)}
                        className="rounded-xl border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteDept(selectedDept)}
                        className="rounded-xl border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-600 hover:bg-rose-50"
                      >
                        Delete
                      </button>
                    </div>
                  ) : null}
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-400">Cost Center</p>
                    <p className="font-medium text-slate-800">{selectedDept.cost_center_code || "—"}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-400">Annual Budget</p>
                    <p className="font-medium text-slate-800">{formatMoney(selectedDept.annual_budget)}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-400">Department Head</p>
                    <p className="font-medium text-slate-800">
                      {detail?.department_head ? detail.department_head.name : "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-400">Staff Count</p>
                    <p className="font-medium text-slate-800">{detail?.staff_count ?? "—"}</p>
                  </div>
                </div>
              </div>

              {dashboard ? (
                <div className="rounded-3xl border border-slate-200 bg-white p-6">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
                    KPI Dashboard
                  </h3>
                  <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4">
                    <div>
                      <p className="text-2xl font-bold text-slate-900">
                        {dashboard.average_allocated_percent.toFixed(0)}%
                      </p>
                      <p className="text-xs text-slate-500">Avg. Utilization</p>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-slate-900">{dashboard.active_engagement_count}</p>
                      <p className="text-xs text-slate-500">Active Engagements</p>
                    </div>
                    <div>
                      <p className="text-2xl font-bold capitalize text-slate-900">
                        {dashboard.average_risk_level || "—"}
                      </p>
                      <p className="text-xs text-slate-500">Avg. Risk Level</p>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-slate-900">{formatMoney(dashboard.revenue_to_date)}</p>
                      <p className="text-xs text-slate-500">Revenue to Date</p>
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-4 text-xs text-slate-500">
                    <span>Over-allocated: {dashboard.over_allocated_count}</span>
                    <span>Under-allocated: {dashboard.under_allocated_count}</span>
                    <span>On bench: {dashboard.bench_count}</span>
                    {dashboard.budget_variance !== null && dashboard.budget_variance !== undefined ? (
                      <span>Budget variance: {formatMoney(dashboard.budget_variance)}</span>
                    ) : null}
                  </div>
                </div>
              ) : null}

              <div className="rounded-3xl border border-slate-200 bg-white p-6">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Staff</h3>
                {!detail?.staff_by_position || Object.keys(detail.staff_by_position).length === 0 ? (
                  <p className="mt-2 text-sm text-slate-400">No staff assigned to this department.</p>
                ) : (
                  <div className="mt-3 space-y-3">
                    {Object.entries(detail.staff_by_position).map(([position, members]) => (
                      <div key={position}>
                        <p className="text-xs font-semibold capitalize text-slate-500">{position}</p>
                        <div className="mt-1 flex flex-wrap gap-2">
                          {members.map((m) => (
                            <span
                              key={m.id}
                              className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700"
                            >
                              {m.name}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="rounded-3xl border border-slate-200 bg-white p-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
                    Onboarding / Offboarding Checklists
                  </h3>
                  <button
                    onClick={openTemplateModal}
                    className="rounded-xl border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                  >
                    + New Checklist
                  </button>
                </div>
                {templates.length === 0 ? (
                  <p className="mt-2 text-sm text-slate-400">No checklists for this department yet.</p>
                ) : (
                  <div className="mt-3 space-y-2">
                    {templates.map((t) => (
                      <div key={t.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <p className="text-sm font-medium text-slate-800">{t.name}</p>
                            <p className="text-xs capitalize text-slate-500">
                              {t.trigger_event} · {t.items.length} item{t.items.length === 1 ? "" : "s"}
                            </p>
                          </div>
                          <div className="flex shrink-0 gap-3">
                            <button
                              onClick={() => setApplyTarget(t)}
                              className="text-xs font-semibold text-slate-700 hover:underline"
                            >
                              Apply to Person
                            </button>
                            <button
                              onClick={() => handleDeleteTemplate(t)}
                              className="text-xs font-semibold text-rose-500 hover:underline"
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                        <ul className="mt-2 space-y-1 text-xs text-slate-600">
                          {t.items.map((it) => (
                            <li key={it.id}>
                              • {it.title}
                              {it.relative_due_days != null ? ` (day ${it.relative_due_days})` : ""}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {showDeptModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-4">
              <h2 className="text-xl font-bold text-slate-900">
                {editingDept ? "Edit Department" : "New Department"}
              </h2>
              <button
                onClick={() => setShowDeptModal(false)}
                className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
              >
                Close
              </button>
            </div>
            <form onSubmit={handleSubmitDept} className="space-y-4">
              <input
                type="text"
                placeholder="Department name"
                value={deptForm.name}
                onChange={(e) => setDeptForm((p) => ({ ...p, name: e.target.value }))}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                required
              />
              <textarea
                placeholder="Description"
                value={deptForm.description}
                onChange={(e) => setDeptForm((p) => ({ ...p, description: e.target.value }))}
                rows={2}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
              />
              <div className="grid grid-cols-2 gap-3">
                <input
                  type="number"
                  step="0.01"
                  placeholder="Annual budget"
                  value={deptForm.annual_budget}
                  onChange={(e) => setDeptForm((p) => ({ ...p, annual_budget: e.target.value }))}
                  className="rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
                <input
                  type="text"
                  placeholder="Cost center code"
                  value={deptForm.cost_center_code}
                  onChange={(e) => setDeptForm((p) => ({ ...p, cost_center_code: e.target.value }))}
                  className="rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Department Head</label>
                {usersError ? (
                  <p className="text-xs text-slate-400">{usersError}</p>
                ) : (
                  <select
                    value={deptForm.department_head_user_id}
                    onChange={(e) => setDeptForm((p) => ({ ...p, department_head_user_id: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  >
                    <option value="">None</option>
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.name} ({u.email})
                      </option>
                    ))}
                  </select>
                )}
              </div>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowDeptModal(false)}
                  className="rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-70"
                >
                  {saving ? "Saving..." : "Save"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {showTemplateModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-4">
              <h2 className="text-xl font-bold text-slate-900">New Checklist</h2>
              <button
                onClick={() => setShowTemplateModal(false)}
                className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
              >
                Close
              </button>
            </div>
            <form onSubmit={handleCreateTemplate} className="space-y-4">
              <input
                type="text"
                placeholder="Checklist name"
                value={templateForm.name}
                onChange={(e) => setTemplateForm((p) => ({ ...p, name: e.target.value }))}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                required
              />
              <select
                value={templateForm.trigger_event}
                onChange={(e) => setTemplateForm((p) => ({ ...p, trigger_event: e.target.value }))}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
              >
                <option value="onboarding">Onboarding</option>
                <option value="offboarding">Offboarding</option>
              </select>
              <div className="space-y-2">
                <label className="block text-sm font-medium text-slate-700">Checklist Items</label>
                {templateForm.items.map((it, idx) => (
                  <div key={idx} className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Item title"
                      value={it.title}
                      onChange={(e) => updateTemplateItem(idx, "title", e.target.value)}
                      className="flex-1 rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
                    />
                    <input
                      type="number"
                      placeholder="Day"
                      value={it.relative_due_days}
                      onChange={(e) => updateTemplateItem(idx, "relative_due_days", e.target.value)}
                      className="w-20 rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
                    />
                    <button
                      type="button"
                      onClick={() => removeTemplateItem(idx)}
                      className="text-xs font-semibold text-rose-500 hover:underline"
                    >
                      Remove
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={addTemplateItem}
                  className="text-xs font-semibold text-slate-700 hover:underline"
                >
                  + Add item
                </button>
              </div>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowTemplateModal(false)}
                  className="rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-70"
                >
                  {saving ? "Saving..." : "Create Checklist"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {applyTarget ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="w-full max-w-sm rounded-3xl bg-white p-6 shadow-2xl">
            <h2 className="mb-4 text-lg font-bold text-slate-900">Apply "{applyTarget.name}"</h2>
            <form onSubmit={handleApplyTemplate} className="space-y-4">
              <input
                type="email"
                placeholder="Person's email"
                value={applyEmail}
                onChange={(e) => setApplyEmail(e.target.value)}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                required
              />
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setApplyTarget(null)}
                  className="rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-70"
                >
                  {saving ? "Applying..." : "Apply"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
