"use client";

import { useEffect, useState } from "react";
import {
  fetchCurrentUser,
  fetchDepartments,
  fetchProjects,
  fetchUsers,
  fetchResourceRequests,
  createResourceRequest,
  approveResourceRequest,
  rejectResourceRequest,
  cancelResourceRequest,
} from "@/lib/api";

function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString();
}

const STATUS_STYLES = {
  pending: "bg-amber-100 text-amber-700",
  approved: "bg-emerald-100 text-emerald-700",
  rejected: "bg-rose-100 text-rose-700",
  cancelled: "bg-slate-100 text-slate-500",
};

const initialForm = {
  requesting_department_id: "",
  providing_department_id: "",
  project_id: "",
  requested_user_id: "",
  role_needed: "",
  allocation_percent: "",
  start_date: "",
  end_date: "",
  notes: "",
};

export default function ResourceRequestsPage() {
  const [currentUser, setCurrentUser] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [projects, setProjects] = useState([]);
  const [users, setUsers] = useState([]);
  const [usersError, setUsersError] = useState("");
  const [requests, setRequests] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState(initialForm);

  useEffect(() => {
    fetchCurrentUser().then(setCurrentUser).catch(() => setCurrentUser(null));
    fetchDepartments().then(setDepartments).catch(() => setDepartments([]));
    fetchProjects().then(setProjects).catch(() => setProjects([]));
    fetchUsers()
      .then(setUsers)
      .catch(() => setUsersError("Admin access required to see the full staff directory."));
    load();
  }, []);

  async function load(overrideStatus) {
    setLoading(true);
    setError("");
    try {
      const status = overrideStatus !== undefined ? overrideStatus : statusFilter;
      const data = await fetchResourceRequests(status ? { status } : {});
      setRequests(data);
    } catch (err) {
      setError(err.message || "Failed to load resource requests");
    } finally {
      setLoading(false);
    }
  }

  function deptName(id) {
    return departments.find((d) => d.id === id)?.name || `Department #${id}`;
  }

  function projectName(id) {
    return projects.find((p) => p.id === id)?.name || `Project #${id}`;
  }

  function userLabel(id) {
    if (!id) return null;
    return users.find((u) => u.id === id)?.name || `User #${id}`;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    try {
      setSaving(true);
      setError("");
      await createResourceRequest({
        requesting_department_id: Number(form.requesting_department_id),
        providing_department_id: Number(form.providing_department_id),
        project_id: Number(form.project_id),
        requested_user_id: form.requested_user_id ? Number(form.requested_user_id) : undefined,
        role_needed: form.role_needed || undefined,
        allocation_percent: form.allocation_percent !== "" ? Number(form.allocation_percent) : undefined,
        start_date: form.start_date || undefined,
        end_date: form.end_date || undefined,
        notes: form.notes || undefined,
      });
      setShowModal(false);
      setForm(initialForm);
      await load();
    } catch (err) {
      setError(err.message || "Failed to submit resource request");
    } finally {
      setSaving(false);
    }
  }

  async function handleApprove(req) {
    try {
      setError("");
      await approveResourceRequest(req.id);
      await load();
    } catch (err) {
      setError(err.message || "Failed to approve request");
    }
  }

  async function handleReject(req) {
    try {
      setError("");
      const notes = window.prompt("Reason for rejecting (optional):") || undefined;
      await rejectResourceRequest(req.id, { notes });
      await load();
    } catch (err) {
      setError(err.message || "Failed to reject request");
    }
  }

  async function handleCancel(req) {
    if (!window.confirm("Cancel this resource request?")) return;
    try {
      setError("");
      await cancelResourceRequest(req.id);
      await load();
    } catch (err) {
      setError(err.message || "Failed to cancel request");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Cross-Department Resource Requests</h1>
          <p className="text-sm text-slate-500">
            Borrow a specialist from another department for one engagement, without moving them permanently.
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="rounded-2xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
        >
          + New Request
        </button>
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      <div className="flex items-center gap-3">
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            load(e.target.value);
          }}
          className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
        >
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {loading ? (
        <p className="text-sm text-slate-400">Loading...</p>
      ) : requests.length === 0 ? (
        <div className="rounded-3xl border border-slate-200 bg-white p-6 text-sm text-slate-400">
          No resource requests yet.
        </div>
      ) : (
        <div className="space-y-3">
          {requests.map((r) => (
            <div key={r.id} className="rounded-3xl border border-slate-200 bg-white p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-slate-800">
                    {deptName(r.requesting_department_id)} ← {deptName(r.providing_department_id)}
                  </p>
                  <p className="text-xs text-slate-500">
                    {projectName(r.project_id)}
                    {r.role_needed ? ` · ${r.role_needed}` : ""}
                    {r.allocation_percent ? ` · ${r.allocation_percent}%` : ""}
                  </p>
                  {userLabel(r.requested_user_id) ? (
                    <p className="text-xs text-slate-500">Requested: {userLabel(r.requested_user_id)}</p>
                  ) : null}
                  {r.start_date || r.end_date ? (
                    <p className="text-xs text-slate-400">
                      {formatDate(r.start_date)} – {formatDate(r.end_date)}
                    </p>
                  ) : null}
                  {r.notes ? <p className="mt-1 text-xs text-slate-600">{r.notes}</p> : null}
                </div>
                <span className={`shrink-0 rounded-full px-2 py-1 text-[10px] font-semibold capitalize ${STATUS_STYLES[r.status] || STATUS_STYLES.pending}`}>
                  {r.status}
                </span>
              </div>
              <p className="mt-2 text-[11px] text-slate-400">
                Requested by {r.requested_by_name} on {formatDate(r.created_at)}
                {r.status !== "pending" && r.decided_by_name
                  ? ` · Decided by ${r.decided_by_name} on ${formatDate(r.decided_at)}`
                  : ""}
              </p>
              {r.status === "pending" ? (
                <div className="mt-2 flex gap-3">
                  <button onClick={() => handleApprove(r)} className="text-xs font-semibold text-emerald-600 hover:underline">
                    Approve
                  </button>
                  <button onClick={() => handleReject(r)} className="text-xs font-semibold text-rose-600 hover:underline">
                    Reject
                  </button>
                  <button onClick={() => handleCancel(r)} className="text-xs font-semibold text-slate-500 hover:underline">
                    Cancel
                  </button>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      )}

      {showModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-4">
              <h2 className="text-xl font-bold text-slate-900">New Resource Request</h2>
              <button
                onClick={() => setShowModal(false)}
                className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
              >
                Close
              </button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Requesting Dept.</label>
                  <select
                    value={form.requesting_department_id}
                    onChange={(e) => setForm((p) => ({ ...p, requesting_department_id: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                    required
                  >
                    <option value="" disabled>
                      Select
                    </option>
                    {departments.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Providing Dept.</label>
                  <select
                    value={form.providing_department_id}
                    onChange={(e) => setForm((p) => ({ ...p, providing_department_id: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                    required
                  >
                    <option value="" disabled>
                      Select
                    </option>
                    {departments.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Engagement</label>
                <select
                  value={form.project_id}
                  onChange={(e) => setForm((p) => ({ ...p, project_id: e.target.value }))}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  required
                >
                  <option value="" disabled>
                    Select an engagement
                  </option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Specific Person (optional)</label>
                {usersError ? (
                  <p className="text-xs text-slate-400">{usersError}</p>
                ) : (
                  <select
                    value={form.requested_user_id}
                    onChange={(e) => setForm((p) => ({ ...p, requested_user_id: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  >
                    <option value="">Any person in that role</option>
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.name} ({u.email})
                      </option>
                    ))}
                  </select>
                )}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <input
                  type="text"
                  placeholder="Role needed"
                  value={form.role_needed}
                  onChange={(e) => setForm((p) => ({ ...p, role_needed: e.target.value }))}
                  className="rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
                <input
                  type="number"
                  min="1"
                  max="100"
                  placeholder="Allocation %"
                  value={form.allocation_percent}
                  onChange={(e) => setForm((p) => ({ ...p, allocation_percent: e.target.value }))}
                  className="rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Start Date</label>
                  <input
                    type="date"
                    value={form.start_date}
                    onChange={(e) => setForm((p) => ({ ...p, start_date: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">End Date</label>
                  <input
                    type="date"
                    value={form.end_date}
                    onChange={(e) => setForm((p) => ({ ...p, end_date: e.target.value }))}
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
                  {saving ? "Submitting..." : "Submit Request"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
