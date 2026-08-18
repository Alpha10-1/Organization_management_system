"use client";

import { useEffect, useState } from "react";
import {
  fetchCurrentUser,
  fetchLeaveRequests,
  createLeaveRequest,
  approveLeaveRequest,
  rejectLeaveRequest,
  cancelLeaveRequest,
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

const initialForm = { leave_type: "pto", start_date: "", end_date: "", reason: "" };

export default function LeaveRequestsPage() {
  const [currentUser, setCurrentUser] = useState(null);
  const [requests, setRequests] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState(initialForm);

  useEffect(() => {
    fetchCurrentUser().then(setCurrentUser).catch(() => setCurrentUser(null));
    load();
  }, []);

  async function load(overrideStatus) {
    setLoading(true);
    setError("");
    try {
      const status = overrideStatus !== undefined ? overrideStatus : statusFilter;
      const data = await fetchLeaveRequests(status ? { status } : {});
      setRequests(data);
    } catch (err) {
      setError(err.message || "Failed to load leave requests");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    try {
      setSaving(true);
      setError("");
      await createLeaveRequest({
        leave_type: form.leave_type,
        start_date: form.start_date,
        end_date: form.end_date,
        reason: form.reason || undefined,
      });
      setShowModal(false);
      setForm(initialForm);
      await load();
    } catch (err) {
      setError(err.message || "Failed to submit leave request");
    } finally {
      setSaving(false);
    }
  }

  async function handleApprove(req) {
    try {
      setError("");
      await approveLeaveRequest(req.id);
      await load();
    } catch (err) {
      setError(err.message || "Failed to approve request");
    }
  }

  async function handleReject(req) {
    try {
      setError("");
      const notes = window.prompt("Reason for rejecting (optional):") || undefined;
      await rejectLeaveRequest(req.id, { notes });
      await load();
    } catch (err) {
      setError(err.message || "Failed to reject request");
    }
  }

  async function handleCancel(req) {
    if (!window.confirm("Cancel this leave request?")) return;
    try {
      setError("");
      await cancelLeaveRequest(req.id);
      await load();
    } catch (err) {
      setError(err.message || "Failed to cancel request");
    }
  }

  const mine = currentUser ? requests.filter((r) => r.user_id === currentUser.id) : [];
  const forApproval = currentUser
    ? requests.filter((r) => r.approver_user_id === currentUser.id && r.user_id !== currentUser.id)
    : [];

  function RequestCard({ req, showApprovalActions }) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-sm font-medium capitalize text-slate-800">
              {req.leave_type} · {formatDate(req.start_date)} – {formatDate(req.end_date)}
            </p>
            {req.reason ? <p className="mt-1 text-xs text-slate-600">{req.reason}</p> : null}
          </div>
          <span className={`shrink-0 rounded-full px-2 py-1 text-[10px] font-semibold capitalize ${STATUS_STYLES[req.status] || STATUS_STYLES.pending}`}>
            {req.status}
          </span>
        </div>
        {req.status !== "pending" && req.decided_by_name ? (
          <p className="mt-2 text-[11px] text-slate-400">
            Decided by {req.decided_by_name} on {formatDate(req.decided_at)}
            {req.decision_notes ? ` — ${req.decision_notes}` : ""}
          </p>
        ) : null}
        <div className="mt-2 flex gap-3">
          {showApprovalActions && req.status === "pending" ? (
            <>
              <button onClick={() => handleApprove(req)} className="text-xs font-semibold text-emerald-600 hover:underline">
                Approve
              </button>
              <button onClick={() => handleReject(req)} className="text-xs font-semibold text-rose-600 hover:underline">
                Reject
              </button>
            </>
          ) : null}
          {!showApprovalActions && req.status === "pending" ? (
            <button onClick={() => handleCancel(req)} className="text-xs font-semibold text-slate-500 hover:underline">
              Cancel
            </button>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Leave &amp; PTO</h1>
          <p className="text-sm text-slate-500">
            Requests route to your manager automatically for approval.
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="rounded-2xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
        >
          + Request Leave
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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-3xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
            My Requests ({mine.length})
          </h2>
          {loading ? (
            <p className="text-sm text-slate-400">Loading...</p>
          ) : mine.length === 0 ? (
            <p className="text-sm text-slate-400">No requests yet.</p>
          ) : (
            <div className="space-y-2">
              {mine.map((r) => (
                <RequestCard key={r.id} req={r} showApprovalActions={false} />
              ))}
            </div>
          )}
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Awaiting My Approval ({forApproval.length})
          </h2>
          {loading ? (
            <p className="text-sm text-slate-400">Loading...</p>
          ) : forApproval.length === 0 ? (
            <p className="text-sm text-slate-400">Nothing routed to you right now.</p>
          ) : (
            <div className="space-y-2">
              {forApproval.map((r) => (
                <RequestCard key={r.id} req={r} showApprovalActions={true} />
              ))}
            </div>
          )}
        </div>
      </div>

      {showModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-4">
              <h2 className="text-xl font-bold text-slate-900">Request Leave</h2>
              <button
                onClick={() => setShowModal(false)}
                className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
              >
                Close
              </button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
              <select
                value={form.leave_type}
                onChange={(e) => setForm((p) => ({ ...p, leave_type: e.target.value }))}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
              >
                <option value="pto">PTO</option>
                <option value="sick">Sick</option>
                <option value="unpaid">Unpaid</option>
                <option value="other">Other</option>
              </select>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Start Date</label>
                  <input
                    type="date"
                    value={form.start_date}
                    onChange={(e) => setForm((p) => ({ ...p, start_date: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                    required
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">End Date</label>
                  <input
                    type="date"
                    value={form.end_date}
                    onChange={(e) => setForm((p) => ({ ...p, end_date: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                    required
                  />
                </div>
              </div>
              <textarea
                placeholder="Reason (optional)"
                value={form.reason}
                onChange={(e) => setForm((p) => ({ ...p, reason: e.target.value }))}
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
