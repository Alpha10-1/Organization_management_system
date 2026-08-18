"use client";

import { useEffect, useMemo, useState } from "react";
import {
  fetchCurrentUser,
  fetchDepartments,
  fetchSkillsMatrix,
  fetchUsers,
  createSkill,
  updateSkill,
  deleteSkill,
} from "@/lib/api";

function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString();
}

function isExpiringSoon(expiry) {
  if (!expiry) return false;
  const days = (new Date(expiry).getTime() - Date.now()) / (1000 * 60 * 60 * 24);
  return days >= 0 && days <= 60;
}

function isExpired(expiry) {
  if (!expiry) return false;
  return new Date(expiry).getTime() < Date.now();
}

const initialForm = {
  user_id: "",
  name: "",
  category: "skill",
  proficiency_level: "",
  issued_date: "",
  expiry_date: "",
  notes: "",
};

export default function SkillsPage() {
  const [currentUser, setCurrentUser] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [departments, setDepartments] = useState([]);
  const [users, setUsers] = useState([]);
  const [usersError, setUsersError] = useState("");
  const [matrix, setMatrix] = useState([]);
  const [deptFilter, setDeptFilter] = useState("");
  const [nameFilter, setNameFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const [showModal, setShowModal] = useState(false);
  const [editingSkill, setEditingSkill] = useState(null);
  const [form, setForm] = useState(initialForm);

  useEffect(() => {
    fetchCurrentUser()
      .then((u) => {
        setCurrentUser(u);
        setIsAdmin(u?.role === "admin");
      })
      .catch(() => setCurrentUser(null));
    fetchDepartments().then(setDepartments).catch(() => setDepartments([]));
    fetchUsers()
      .then(setUsers)
      .catch(() => setUsersError("Admin access required to see the full staff directory."));
    loadMatrix();
  }, []);

  async function loadMatrix(overrides = {}) {
    setLoading(true);
    setError("");
    try {
      const params = {
        department_id: overrides.deptFilter ?? (deptFilter || undefined),
        name: overrides.nameFilter ?? (nameFilter || undefined),
      };
      const data = await fetchSkillsMatrix(params);
      setMatrix(data);
    } catch (err) {
      setError(err.message || "Failed to load skills matrix");
    } finally {
      setLoading(false);
    }
  }

  function applyFilters() {
    loadMatrix();
  }

  function userLabel(id) {
    const u = users.find((x) => x.id === id);
    return u ? `${u.name} (${u.email})` : `User #${id}`;
  }

  function openCreate(userId) {
    setEditingSkill(null);
    setForm({ ...initialForm, user_id: userId ? String(userId) : "" });
    setShowModal(true);
  }

  function openEdit(entry, skill) {
    setEditingSkill(skill);
    setForm({
      user_id: String(entry.user_id),
      name: skill.name,
      category: skill.category,
      proficiency_level: skill.proficiency_level || "",
      issued_date: skill.issued_date || "",
      expiry_date: skill.expiry_date || "",
      notes: skill.notes || "",
    });
    setShowModal(true);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    try {
      setSaving(true);
      setError("");
      const payload = {
        user_id: Number(form.user_id),
        name: form.name,
        category: form.category,
        proficiency_level: form.proficiency_level || undefined,
        issued_date: form.issued_date || undefined,
        expiry_date: form.expiry_date || undefined,
        notes: form.notes || undefined,
      };
      if (editingSkill) {
        await updateSkill(editingSkill.id, payload);
      } else {
        await createSkill(payload);
      }
      setShowModal(false);
      await loadMatrix();
    } catch (err) {
      setError(err.message || "Failed to save entry");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(skill) {
    if (!window.confirm(`Remove "${skill.name}"?`)) return;
    try {
      setError("");
      await deleteSkill(skill.id);
      await loadMatrix();
    } catch (err) {
      setError(err.message || "Failed to delete entry");
    }
  }

  const totalEntries = useMemo(
    () => matrix.reduce((sum, entry) => sum + entry.skills.length, 0),
    [matrix]
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Skills &amp; Certifications</h1>
          <p className="text-sm text-slate-500">
            Staffing decisions, made data-driven — who can go on this engagement.
          </p>
        </div>
        <button
          onClick={() => openCreate(currentUser?.id)}
          className="rounded-2xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
        >
          + Add Skill / Certification
        </button>
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-white p-4">
        <select
          value={deptFilter}
          onChange={(e) => setDeptFilter(e.target.value)}
          className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
        >
          <option value="">All departments</option>
          {departments.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Filter by skill/certification name"
          value={nameFilter}
          onChange={(e) => setNameFilter(e.target.value)}
          className="flex-1 min-w-[200px] rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
        />
        <button
          onClick={applyFilters}
          className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
        >
          Apply
        </button>
        <span className="text-xs text-slate-400">{totalEntries} total entries</span>
      </div>

      {loading ? (
        <p className="text-sm text-slate-400">Loading...</p>
      ) : matrix.length === 0 ? (
        <div className="rounded-3xl border border-slate-200 bg-white p-6 text-sm text-slate-400">
          No skills or certifications recorded yet.
        </div>
      ) : (
        <div className="space-y-4">
          {matrix.map((entry) => (
            <div key={entry.user_id} className="rounded-3xl border border-slate-200 bg-white p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">{entry.user_name}</h3>
                </div>
                <button
                  onClick={() => openCreate(entry.user_id)}
                  className="text-xs font-semibold text-slate-700 hover:underline"
                >
                  + Add
                </button>
              </div>
              {entry.skills.length === 0 ? (
                <p className="mt-2 text-xs text-slate-400">No entries.</p>
              ) : (
                <div className="mt-3 flex flex-wrap gap-2">
                  {entry.skills.map((s) => {
                    const expired = isExpired(s.expiry_date);
                    const expiring = !expired && isExpiringSoon(s.expiry_date);
                    return (
                      <div
                        key={s.id}
                        className={`rounded-xl border px-3 py-2 text-xs ${
                          expired
                            ? "border-rose-200 bg-rose-50"
                            : expiring
                            ? "border-amber-200 bg-amber-50"
                            : "border-slate-200 bg-slate-50"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-800">{s.name}</span>
                          <span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-semibold uppercase text-slate-500">
                            {s.category}
                          </span>
                        </div>
                        {s.proficiency_level ? (
                          <p className="mt-0.5 capitalize text-slate-500">{s.proficiency_level}</p>
                        ) : null}
                        {s.expiry_date ? (
                          <p className={`mt-0.5 ${expired ? "text-rose-600" : expiring ? "text-amber-700" : "text-slate-500"}`}>
                            {expired ? "Expired" : "Expires"} {formatDate(s.expiry_date)}
                          </p>
                        ) : null}
                        <div className="mt-1 flex gap-2">
                          <button
                            onClick={() => openEdit(entry, s)}
                            className="font-semibold text-slate-600 hover:underline"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDelete(s)}
                            className="font-semibold text-rose-500 hover:underline"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {showModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-4">
              <h2 className="text-xl font-bold text-slate-900">
                {editingSkill ? "Edit Entry" : "Add Skill / Certification"}
              </h2>
              <button
                onClick={() => setShowModal(false)}
                className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
              >
                Close
              </button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Person</label>
                {usersError ? (
                  <input
                    type="number"
                    placeholder="User ID"
                    value={form.user_id}
                    onChange={(e) => setForm((p) => ({ ...p, user_id: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                    required
                  />
                ) : (
                  <select
                    value={form.user_id}
                    onChange={(e) => setForm((p) => ({ ...p, user_id: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                    required
                  >
                    <option value="" disabled>
                      Select a person
                    </option>
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.name} ({u.email})
                      </option>
                    ))}
                  </select>
                )}
              </div>
              <input
                type="text"
                placeholder="Skill or certification name"
                value={form.name}
                onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                required
              />
              <div className="grid grid-cols-2 gap-3">
                <select
                  value={form.category}
                  onChange={(e) => setForm((p) => ({ ...p, category: e.target.value }))}
                  className="rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                >
                  <option value="skill">Skill</option>
                  <option value="certification">Certification</option>
                </select>
                <input
                  type="text"
                  placeholder="Proficiency level"
                  value={form.proficiency_level}
                  onChange={(e) => setForm((p) => ({ ...p, proficiency_level: e.target.value }))}
                  className="rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Issued</label>
                  <input
                    type="date"
                    value={form.issued_date}
                    onChange={(e) => setForm((p) => ({ ...p, issued_date: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Expires</label>
                  <input
                    type="date"
                    value={form.expiry_date}
                    onChange={(e) => setForm((p) => ({ ...p, expiry_date: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  />
                </div>
              </div>
              <textarea
                placeholder="Notes"
                value={form.notes}
                onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))}
                rows={2}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
              />
              <div className="flex justify-end gap-3">
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
                  {saving ? "Saving..." : "Save"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
