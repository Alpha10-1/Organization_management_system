"use client";

import { useEffect, useState } from "react";
import { ShieldCheck, Lock, Trash2 } from "lucide-react";
import {
  fetchCurrentUser,
  fetchRoles,
  fetchRolePermissionCatalog,
  createRole,
  updateRole,
  deleteRole,
} from "@/lib/api";

const initialForm = { name: "", description: "", permissions: [] };

export default function RolesPage() {
  const [currentUserRole, setCurrentUserRole] = useState("");
  const [roles, setRoles] = useState([]);
  const [catalog, setCatalog] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const [showModal, setShowModal] = useState(false);
  const [editingRoleId, setEditingRoleId] = useState(null);
  const [form, setForm] = useState(initialForm);

  useEffect(() => {
    init();
  }, []);

  async function init() {
    try {
      const me = await fetchCurrentUser();
      setCurrentUserRole(me.role);
      if (me.role !== "admin") {
        setError("You do not have permission to access this page.");
        return;
      }
      const [roleData, catalogData] = await Promise.all([fetchRoles(), fetchRolePermissionCatalog()]);
      setRoles(roleData);
      setCatalog(catalogData);
    } catch (err) {
      setError(err.message || "Failed to load roles");
    } finally {
      setLoading(false);
    }
  }

  function openCreateModal() {
    setEditingRoleId(null);
    setForm(initialForm);
    setShowModal(true);
  }

  function openEditModal(role) {
    setEditingRoleId(role.id);
    setForm({ name: role.name, description: role.description || "", permissions: [...role.permissions] });
    setShowModal(true);
  }

  function togglePermission(key) {
    setForm((prev) => ({
      ...prev,
      permissions: prev.permissions.includes(key)
        ? prev.permissions.filter((p) => p !== key)
        : [...prev.permissions, key],
    }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      if (editingRoleId) {
        await updateRole(editingRoleId, {
          name: form.name,
          description: form.description || null,
          permissions: form.permissions,
        });
      } else {
        await createRole({ name: form.name, description: form.description || null, permissions: form.permissions });
      }
      setShowModal(false);
      const updated = await fetchRoles();
      setRoles(updated);
    } catch (err) {
      setError(err.message || "Failed to save role");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(role) {
    if (!window.confirm(`Delete role "${role.name}"? This can't be undone.`)) return;
    try {
      await deleteRole(role.id);
      setRoles((prev) => prev.filter((r) => r.id !== role.id));
    } catch (err) {
      window.alert(err.message || "Failed to delete role");
    }
  }

  if (currentUserRole && currentUserRole !== "admin") {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
        You do not have permission to access this page.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="rounded-2xl bg-slate-900 p-3 text-white">
            <ShieldCheck size={20} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Roles & Permissions</h1>
            <p className="text-sm text-slate-500">
              Delegate a slice of admin capability to staff — Partner, Manager, or a role you
              define — without making them a full admin. Assigning roles to users happens on the
              Users page; only an admin can create, edit, delete, or assign a role.
            </p>
          </div>
        </div>
        <button
          onClick={openCreateModal}
          className="shrink-0 rounded-2xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
        >
          + New Role
        </button>
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
      ) : null}

      {loading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {roles.map((role) => (
            <div key={role.id} className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="flex items-center gap-1.5 font-semibold text-slate-900">
                    {role.name}
                    {role.is_system ? <Lock size={13} className="text-slate-400" /> : null}
                  </p>
                  {role.description ? <p className="mt-1 text-xs text-slate-500">{role.description}</p> : null}
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-1">
                {role.permissions.length === 0 ? (
                  <span className="text-xs text-slate-300">No permissions granted</span>
                ) : (
                  role.permissions.map((p) => (
                    <span key={p} className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
                      {p}
                    </span>
                  ))
                )}
              </div>
              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => openEditModal(role)}
                  className="rounded-xl border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Edit
                </button>
                {!role.is_system ? (
                  <button
                    onClick={() => handleDelete(role)}
                    className="flex items-center gap-1 rounded-xl border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-600 hover:bg-rose-50"
                  >
                    <Trash2 size={12} /> Delete
                  </button>
                ) : (
                  <span className="flex items-center gap-1 px-3 py-1.5 text-xs text-slate-400">
                    <Lock size={12} /> System role — can't be deleted
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-4">
              <h2 className="text-xl font-bold text-slate-900">{editingRoleId ? "Edit Role" : "New Role"}</h2>
              <button
                onClick={() => setShowModal(false)}
                className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
              >
                Close
              </button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-3">
              <input
                placeholder="Role name"
                value={form.name}
                onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                required
              />
              <textarea
                placeholder="Description (optional)"
                value={form.description}
                onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                rows={2}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
              />
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Permissions</p>
                <div className="max-h-64 space-y-2 overflow-y-auto rounded-2xl border border-slate-200 p-3">
                  {Object.entries(catalog).map(([key, description]) => (
                    <label key={key} className="flex items-start gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={form.permissions.includes(key)}
                        onChange={() => togglePermission(key)}
                        className="mt-1"
                      />
                      <span>
                        <span className="font-medium text-slate-800">{key}</span>
                        <span className="block text-xs text-slate-500">{description}</span>
                      </span>
                    </label>
                  ))}
                </div>
              </div>
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
                  {saving ? "Saving..." : "Save Role"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
