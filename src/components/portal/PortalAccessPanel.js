"use client";

import { useEffect, useState } from "react";
import {
  fetchClientPortalUsers,
  invitePortalUser,
  revokePortalUser,
  updatePortalUser,
} from "@/lib/api";

function formatDateTime(value) {
  if (!value) return "Never";
  return new Date(value).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const initialInviteForm = { name: "", email: "" };

export default function PortalAccessPanel({ clientId, contacts = [] }) {
  const [portalUsers, setPortalUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showInviteForm, setShowInviteForm] = useState(false);
  const [inviteForm, setInviteForm] = useState(initialInviteForm);
  const [inviteContactId, setInviteContactId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [busyId, setBusyId] = useState(null);

  async function load() {
    try {
      const data = await fetchClientPortalUsers(clientId);
      setPortalUsers(data);
    } catch (err) {
      setError(err.message || "Failed to load portal access");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!clientId) return;
    setLoading(true);
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clientId]);

  async function handleInvite(e) {
    e.preventDefault();
    if (!inviteForm.name.trim() || !inviteForm.email.trim()) return;

    setSubmitting(true);
    setError("");
    try {
      await invitePortalUser(clientId, {
        name: inviteForm.name.trim(),
        email: inviteForm.email.trim(),
        client_contact_id: inviteContactId ? Number(inviteContactId) : null,
      });
      setInviteForm(initialInviteForm);
      setInviteContactId("");
      setShowInviteForm(false);
      await load();
    } catch (err) {
      setError(err.message || "Failed to send invite");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleToggleDisabled(portalUser) {
    setBusyId(portalUser.id);
    setError("");
    try {
      await updatePortalUser(clientId, portalUser.id, { disabled: !portalUser.disabled });
      await load();
    } catch (err) {
      setError(err.message || "Failed to update portal access");
    } finally {
      setBusyId(null);
    }
  }

  async function handleRevoke(portalUser) {
    if (!window.confirm(`Revoke portal access for ${portalUser.name}? This cannot be undone.`)) return;
    setBusyId(portalUser.id);
    setError("");
    try {
      await revokePortalUser(clientId, portalUser.id);
      await load();
    } catch (err) {
      setError(err.message || "Failed to revoke portal access");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-700">Client Portal Access</h3>
        <button
          onClick={() => setShowInviteForm((prev) => !prev)}
          className="rounded-lg border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-600 transition hover:bg-slate-50"
        >
          {showInviteForm ? "Cancel" : "+ Invite user"}
        </button>
      </div>

      {error ? (
        <p className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
          {error}
        </p>
      ) : null}

      {showInviteForm ? (
        <form onSubmit={handleInvite} className="mb-4 space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3">
          <div className="grid grid-cols-2 gap-2">
            <input
              placeholder="Full name"
              value={inviteForm.name}
              onChange={(e) => setInviteForm((prev) => ({ ...prev, name: e.target.value }))}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
              required
            />
            <input
              placeholder="Email"
              type="email"
              value={inviteForm.email}
              onChange={(e) => setInviteForm((prev) => ({ ...prev, email: e.target.value }))}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
              required
            />
          </div>
          {contacts.length > 0 ? (
            <select
              value={inviteContactId}
              onChange={(e) => setInviteContactId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
            >
              <option value="">Link to an existing contact (optional)</option>
              {contacts.map((contact) => (
                <option key={contact.id} value={contact.id}>
                  {contact.name} {contact.role ? `— ${contact.role}` : ""}
                </option>
              ))}
            </select>
          ) : null}
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60"
          >
            {submitting ? "Sending invite..." : "Send invite"}
          </button>
          <p className="text-xs text-slate-400">
            The client will receive an email with a link to set their password and log in
            at the client portal.
          </p>
        </form>
      ) : null}

      {loading ? (
        <p className="text-sm text-slate-400">Loading portal access...</p>
      ) : portalUsers.length === 0 ? (
        <p className="text-sm text-slate-400">No one has portal access for this client yet.</p>
      ) : (
        <div className="space-y-2">
          {portalUsers.map((portalUser) => (
            <div
              key={portalUser.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 px-3 py-2"
            >
              <div>
                <p className="text-sm font-medium text-slate-800">
                  {portalUser.name}{" "}
                  {portalUser.disabled ? (
                    <span className="ml-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">
                      Disabled
                    </span>
                  ) : (
                    <span className="ml-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                      Active
                    </span>
                  )}
                </p>
                <p className="text-xs text-slate-400">{portalUser.email}</p>
                <p className="text-xs text-slate-400">
                  Last login: {formatDateTime(portalUser.last_login_at)}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleToggleDisabled(portalUser)}
                  disabled={busyId === portalUser.id}
                  className="rounded-lg border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 disabled:opacity-60"
                >
                  {portalUser.disabled ? "Enable" : "Disable"}
                </button>
                <button
                  onClick={() => handleRevoke(portalUser)}
                  disabled={busyId === portalUser.id}
                  className="rounded-lg border border-red-200 px-3 py-1 text-xs font-semibold text-red-600 transition hover:bg-red-50 disabled:opacity-60"
                >
                  Revoke
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
