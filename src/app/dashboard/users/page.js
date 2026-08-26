"use client";

import { useEffect, useState } from "react";
import {
  createUser,
  fetchCurrentUser,
  fetchUsers,
  updateUserRole,
  updateUserStatus,
  fetchDepartments,
  createDepartment,
  updateDepartment,
  deleteDepartment,
  updateUserDepartment,
  updateUserPosition,
  fetchOrgChart,
  fetchRoles,
  updateUserCustomRole,
} from "@/lib/api";

const POSITION_LEVELS = [
  "associate",
  "senior_associate",
  "manager",
  "senior_manager",
  "director",
  "partner",
];

function positionLabel(position) {
  if (!position) return "—";
  return position
    .split("_")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}

const initialForm = {
  name: "",
  email: "",
  password: "",
  role: "staff",
  department_id: "",
  position: "",
  manager_id: "",
};

function OrgChartTree({ nodes, depth = 0 }) {
  return (
    <ul className={depth === 0 ? "space-y-3" : "mt-2 space-y-2 border-l border-slate-200 pl-4"}>
      {nodes.map((node) => (
        <li key={node.id}>
          <div className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2 text-sm">
            <span className="font-medium text-slate-800">{node.name}</span>
            {node.position ? (
              <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs text-slate-600">
                {positionLabel(node.position)}
              </span>
            ) : null}
          </div>
          {node.reports.length > 0 ? <OrgChartTree nodes={node.reports} depth={depth + 1} /> : null}
        </li>
      ))}
    </ul>
  );
}

export default function UsersPage() {
  const [currentUserRole, setCurrentUserRole] = useState("");
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState(initialForm);

  const [departments, setDepartments] = useState([]);
  const [newDeptName, setNewDeptName] = useState("");
  const [deptSaving, setDeptSaving] = useState(false);

  const [roles, setRoles] = useState([]);

  const [orgChart, setOrgChart] = useState([]);
  const [orgChartLoading, setOrgChartLoading] = useState(false);
  const [showOrgChart, setShowOrgChart] = useState(false);

  async function loadUsers() {
    try {
      setLoading(true);
      setError("");
      const data = await fetchUsers();
      setUsers(data);
    } catch (err) {
      setError(err.message || "Failed to load users");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    async function init() {
        try {
        const me = await fetchCurrentUser();
        setCurrentUserRole(me.role);
        if (me.role !== "admin") {
            setError("You do not have permission to access this page.");
        } else {
            const data = await fetchUsers();
            setUsers(data);
            fetchDepartments().then(setDepartments).catch(() => setDepartments([]));
            fetchRoles().then(setRoles).catch(() => setRoles([]));
        }
        } catch (err) {
        setError(err.message || "Failed to load users");
        } finally {
        setLoading(false);
        }
    }

    init();
    }, []);

  useEffect(() => {
    loadUsers();
  }, []);

  async function handleCreateDepartment(e) {
    e.preventDefault();
    if (!newDeptName.trim()) return;
    try {
      setDeptSaving(true);
      setError("");
      await createDepartment({ name: newDeptName.trim() });
      setNewDeptName("");
      const updated = await fetchDepartments();
      setDepartments(updated);
    } catch (err) {
      setError(err.message || "Failed to create department");
    } finally {
      setDeptSaving(false);
    }
  }

  async function handleDeleteDepartment(id) {
    const confirmed = window.confirm("Delete this department? Users/clients in it become unassigned.");
    if (!confirmed) return;
    try {
      setError("");
      await deleteDepartment(id);
      setDepartments((prev) => prev.filter((d) => d.id !== id));
      await loadUsers();
    } catch (err) {
      setError(err.message || "Failed to delete department");
    }
  }

  async function handleUserDepartmentChange(email, departmentId) {
    try {
      setError("");
      await updateUserDepartment(email, departmentId ? Number(departmentId) : null);
      await loadUsers();
    } catch (err) {
      setError(err.message || "Failed to update department");
    }
  }

  async function handleUserPositionChange(email, position) {
    try {
      setError("");
      await updateUserPosition(email, { position: position || null });
      await loadUsers();
    } catch (err) {
      setError(err.message || "Failed to update position");
    }
  }

  async function handleUserManagerChange(email, managerId) {
    try {
      setError("");
      await updateUserPosition(email, { manager_id: managerId ? Number(managerId) : null });
      await loadUsers();
    } catch (err) {
      setError(err.message || "Failed to update manager");
    }
  }

  async function handleUserCustomRoleChange(email, customRoleId) {
    try {
      setError("");
      await updateUserCustomRole(email, customRoleId ? Number(customRoleId) : null);
      await loadUsers();
    } catch (err) {
      setError(err.message || "Failed to update delegated role");
    }
  }

  async function handleDepartmentHeadChange(departmentId, headUserId) {
    try {
      setError("");
      await updateDepartment(departmentId, {
        department_head_user_id: headUserId ? Number(headUserId) : null,
      });
      const updated = await fetchDepartments();
      setDepartments(updated);
    } catch (err) {
      setError(err.message || "Failed to update department head");
    }
  }

  async function toggleOrgChart() {
    const next = !showOrgChart;
    setShowOrgChart(next);
    if (next && orgChart.length === 0) {
      try {
        setOrgChartLoading(true);
        setOrgChart(await fetchOrgChart());
      } catch (err) {
        setError(err.message || "Failed to load org chart");
      } finally {
        setOrgChartLoading(false);
      }
    }
  }

  function handleInputChange(e) {
    setForm((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  }

  async function handleCreateUser(e) {
    e.preventDefault();

    try {
      setSaving(true);
      setError("");
      await createUser({
        ...form,
        department_id: form.department_id ? Number(form.department_id) : null,
        position: form.position || null,
        manager_id: form.manager_id ? Number(form.manager_id) : null,
      });
      setForm(initialForm);
      setShowModal(false);
      await loadUsers();
    } catch (err) {
      setError(err.message || "Failed to create user");
    } finally {
      setSaving(false);
    }
  }

  async function handleRoleChange(email, role) {
    try {
      setError("");
      await updateUserRole(email, role);
      await loadUsers();
    } catch (err) {
      setError(err.message || "Failed to update role");
    }
  }

  async function handleStatusToggle(email, disabled) {
    try {
      setError("");
      await updateUserStatus(email, disabled);
      await loadUsers();
    } catch (err) {
      setError(err.message || "Failed to update status");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm md:flex-row md:items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">User Management</h1>
          <p className="mt-1 text-sm text-slate-500">
            Manage staff accounts, roles, and access status.
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={toggleOrgChart}
            className="rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
          >
            {showOrgChart ? "Hide Org Chart" : "View Org Chart"}
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800"
          >
            Add User
          </button>
        </div>
      </div>

      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      ) : null}

      {showOrgChart ? (
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Org Chart</h2>
          <p className="mt-1 text-sm text-slate-500">
            Reporting lines across the firm, built from each user&apos;s manager assignment.
          </p>
          <div className="mt-4">
            {orgChartLoading ? (
              <p className="text-sm text-slate-500">Loading...</p>
            ) : orgChart.length === 0 ? (
              <p className="text-sm text-slate-400">No reporting lines set yet.</p>
            ) : (
              <OrgChartTree nodes={orgChart} />
            )}
          </div>
        </div>
      ) : null}

      <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Departments</h2>
        <p className="mt-1 text-sm text-slate-500">
          Organize staff and clients by team (e.g. Sales, Support, Ops).
        </p>

        <form onSubmit={handleCreateDepartment} className="mt-4 flex gap-2">
          <input
            type="text"
            value={newDeptName}
            onChange={(e) => setNewDeptName(e.target.value)}
            placeholder="New department name"
            className="flex-1 max-w-xs rounded-2xl border border-slate-300 px-4 py-2 text-sm outline-none focus:border-slate-900"
          />
          <button
            type="submit"
            disabled={deptSaving}
            className="rounded-2xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-70"
          >
            {deptSaving ? "Adding..." : "Add"}
          </button>
        </form>

        <div className="mt-4 space-y-2">
          {departments.length === 0 ? (
            <span className="text-sm text-slate-400">No departments yet.</span>
          ) : (
            departments.map((d) => (
              <div
                key={d.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3"
              >
                <span className="text-sm font-medium text-slate-800">{d.name}</span>
                <div className="flex items-center gap-2">
                  <label className="text-xs text-slate-500">Head:</label>
                  <select
                    value={d.department_head_user_id ?? ""}
                    onChange={(e) => handleDepartmentHeadChange(d.id, e.target.value)}
                    className="rounded-xl border border-slate-300 px-2 py-1.5 text-xs outline-none focus:border-slate-900"
                  >
                    <option value="">None</option>
                    {users.map((u) => (
                      <option key={u.email} value={u.id}>
                        {u.name}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => handleDeleteDepartment(d.id)}
                    className="text-xs text-slate-400 hover:text-rose-500"
                    aria-label={`Delete ${d.name}`}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1100px] border-separate border-spacing-y-3">
            <thead>
              <tr className="text-left text-sm text-slate-500">
                <th className="pb-2">Name</th>
                <th className="pb-2">Email</th>
                <th className="pb-2">Role</th>
                <th className="pb-2">Department</th>
                <th className="pb-2">Position</th>
                <th className="pb-2">Manager</th>
                <th className="pb-2">Delegated Role</th>
                <th className="pb-2">Status</th>
                <th className="pb-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-sm text-slate-500">
                    Loading users...
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-sm text-slate-500">
                    No users found.
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.email} className="bg-slate-50">
                    <td className="rounded-l-2xl px-4 py-4 font-medium text-slate-900">
                      {user.name}
                    </td>
                    <td className="px-4 py-4 text-slate-700">{user.email}</td>
                    <td className="px-4 py-4">
                      <select
                        value={user.role}
                        onChange={(e) => handleRoleChange(user.email, e.target.value)}
                        className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
                      >
                        <option value="staff">staff</option>
                        <option value="admin">admin</option>
                      </select>
                    </td>
                    <td className="px-4 py-4">
                      <select
                        value={user.department_id ?? ""}
                        onChange={(e) => handleUserDepartmentChange(user.email, e.target.value)}
                        className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
                      >
                        <option value="">None</option>
                        {departments.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-4">
                      <select
                        value={user.position ?? ""}
                        onChange={(e) => handleUserPositionChange(user.email, e.target.value)}
                        className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
                      >
                        <option value="">None</option>
                        {POSITION_LEVELS.map((p) => (
                          <option key={p} value={p}>
                            {positionLabel(p)}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-4">
                      <select
                        value={user.manager_id ?? ""}
                        onChange={(e) => handleUserManagerChange(user.email, e.target.value)}
                        className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
                      >
                        <option value="">None</option>
                        {users
                          .filter((u) => u.id !== user.id)
                          .map((u) => (
                            <option key={u.email} value={u.id}>
                              {u.name}
                            </option>
                          ))}
                      </select>
                    </td>
                    <td className="px-4 py-4">
                      <select
                        value={user.custom_role_id ?? ""}
                        onChange={(e) => handleUserCustomRoleChange(user.email, e.target.value)}
                        className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
                      >
                        <option value="">None</option>
                        {roles.map((r) => (
                          <option key={r.id} value={r.id}>
                            {r.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-4">
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold ${
                          user.disabled
                            ? "bg-red-100 text-red-700"
                            : "bg-green-100 text-green-700"
                        }`}
                      >
                        {user.disabled ? "Disabled" : "Active"}
                      </span>
                    </td>
                    <td className="rounded-r-2xl px-4 py-4">
                      <button
                        onClick={() => handleStatusToggle(user.email, !user.disabled)}
                        className="text-sm font-semibold text-slate-900 hover:underline"
                      >
                        {user.disabled ? "Enable" : "Disable"}
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
                <h2 className="text-2xl font-bold text-slate-900">Add User</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Create a new system user with a role.
                </p>
              </div>

              <button
                onClick={() => setShowModal(false)}
                className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
              >
                Close
              </button>
            </div>

            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Full Name
                </label>
                <input
                  name="name"
                  value={form.name}
                  onChange={handleInputChange}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  required
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Email
                </label>
                <input
                  name="email"
                  type="email"
                  value={form.email}
                  onChange={handleInputChange}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  required
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Password
                </label>
                <input
                  name="password"
                  type="password"
                  value={form.password}
                  onChange={handleInputChange}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  required
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Role
                </label>
                <select
                  name="role"
                  value={form.role}
                  onChange={handleInputChange}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                >
                  <option value="staff">staff</option>
                  <option value="admin">admin</option>
                </select>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Department
                </label>
                <select
                  name="department_id"
                  value={form.department_id}
                  onChange={handleInputChange}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                >
                  <option value="">None</option>
                  {departments.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Position
                </label>
                <select
                  name="position"
                  value={form.position}
                  onChange={handleInputChange}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                >
                  <option value="">None</option>
                  {POSITION_LEVELS.map((p) => (
                    <option key={p} value={p}>
                      {positionLabel(p)}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Manager
                </label>
                <select
                  name="manager_id"
                  value={form.manager_id}
                  onChange={handleInputChange}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                >
                  <option value="">None</option>
                  {users.map((u) => (
                    <option key={u.email} value={u.id}>
                      {u.name}
                    </option>
                  ))}
                </select>
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
                  {saving ? "Saving..." : "Create User"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}