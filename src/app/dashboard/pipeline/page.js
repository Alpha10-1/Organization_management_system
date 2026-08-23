"use client";

import { useEffect, useMemo, useState } from "react";
import {
  fetchProspects,
  fetchPipelineSummary,
  createProspect,
  updateProspectStatus,
  fetchProspectStageHistory,
  convertProspect,
  deleteProspect,
  fetchProposals,
  createProposal,
  updateProposalStatus,
  fetchDepartments,
  fetchUsers,
} from "@/lib/api";

const STAGES = ["new", "contacted", "qualified", "proposal_sent", "negotiating", "won", "lost"];

const STAGE_LABELS = {
  new: "New",
  contacted: "Contacted",
  qualified: "Qualified",
  proposal_sent: "Proposal Sent",
  negotiating: "Negotiating",
  won: "Won",
  lost: "Lost",
};

// Mirrors app.core.pipeline.ALLOWED_PROSPECT_TRANSITIONS -- informational
// only, the backend is the source of truth and re-validates on submit.
const ALLOWED_TRANSITIONS = {
  new: ["contacted", "lost"],
  contacted: ["qualified", "lost"],
  qualified: ["proposal_sent", "lost"],
  proposal_sent: ["negotiating", "won", "lost"],
  negotiating: ["won", "lost"],
  won: [],
  lost: [],
};

const PROPOSAL_STAGE_LABELS = {
  draft: "Draft",
  sent: "Sent",
  accepted: "Accepted",
  rejected: "Rejected",
  expired: "Expired",
};

const PROPOSAL_TRANSITIONS = {
  draft: ["sent"],
  sent: ["accepted", "rejected", "expired"],
  accepted: [],
  rejected: [],
  expired: [],
};

function formatCurrency(value) {
  if (value == null) return "—";
  return `$${Number(value).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString();
}

const initialForm = {
  name: "",
  company_name: "",
  contact_email: "",
  contact_phone: "",
  industry: "",
  website: "",
  source: "referral",
  department_id: "",
  estimated_value: "",
  expected_close_date: "",
  assigned_to_user_id: "",
  notes: "",
};

export default function PipelinePage() {
  const [prospects, setProspects] = useState([]);
  const [summary, setSummary] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [form, setForm] = useState(initialForm);
  const [saving, setSaving] = useState(false);

  const [selectedProspect, setSelectedProspect] = useState(null);

  useEffect(() => {
    load();
    fetchDepartments().then(setDepartments).catch(() => setDepartments([]));
    fetchUsers().then(setUsers).catch(() => setUsers([]));
  }, []);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [prospectData, summaryData] = await Promise.all([fetchProspects(), fetchPipelineSummary()]);
      setProspects(prospectData);
      setSummary(summaryData);
    } catch (err) {
      setError(err.message || "Failed to load pipeline");
    } finally {
      setLoading(false);
    }
  }

  const columns = useMemo(() => {
    const grouped = {};
    STAGES.forEach((s) => (grouped[s] = []));
    prospects.forEach((p) => {
      if (grouped[p.status]) grouped[p.status].push(p);
    });
    return grouped;
  }, [prospects]);

  async function handleCreate(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload = {
        name: form.name,
        company_name: form.company_name || undefined,
        contact_email: form.contact_email || undefined,
        contact_phone: form.contact_phone || undefined,
        industry: form.industry || undefined,
        website: form.website || undefined,
        source: form.source,
        department_id: form.department_id ? Number(form.department_id) : undefined,
        estimated_value: form.estimated_value || undefined,
        expected_close_date: form.expected_close_date || undefined,
        assigned_to_user_id: form.assigned_to_user_id ? Number(form.assigned_to_user_id) : undefined,
        notes: form.notes || undefined,
      };
      await createProspect(payload);
      setShowCreateModal(false);
      setForm(initialForm);
      await load();
    } catch (err) {
      setError(err.message || "Failed to create prospect");
    } finally {
      setSaving(false);
    }
  }

  async function handleQuickAdvance(prospect, nextStatus) {
    if (nextStatus === "lost") {
      const reason = window.prompt("Reason for marking this prospect lost:");
      if (!reason) return;
      try {
        await updateProspectStatus(prospect.id, "lost", reason);
        await load();
      } catch (err) {
        window.alert(err.message || "Failed to update status");
      }
      return;
    }
    try {
      await updateProspectStatus(prospect.id, nextStatus);
      await load();
    } catch (err) {
      window.alert(err.message || "Failed to update status");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Pipeline</h1>
          <p className="text-sm text-slate-500">
            Prospects → proposals → won engagements. Winning a prospect requires an accepted
            proposal; converting it creates the client record.
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="rounded-2xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
        >
          + New Prospect
        </button>
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
      ) : null}

      {summary ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <p className="text-xs text-slate-500">Open Pipeline Value</p>
            <p className="mt-1 text-xl font-bold text-slate-900">{formatCurrency(summary.open_pipeline_value)}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <p className="text-xs text-slate-500">Win Rate</p>
            <p className="mt-1 text-xl font-bold text-slate-900">
              {summary.win_rate_percent != null ? `${summary.win_rate_percent}%` : "—"}
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <p className="text-xs text-slate-500">Won</p>
            <p className="mt-1 text-xl font-bold text-emerald-600">{summary.won_count}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <p className="text-xs text-slate-500">Lost</p>
            <p className="mt-1 text-xl font-bold text-rose-600">{summary.lost_count}</p>
          </div>
        </div>
      ) : null}

      {loading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 overflow-x-auto sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
          {STAGES.map((stage) => (
            <div key={stage} className="min-w-[220px] rounded-2xl border border-slate-200 bg-slate-50 p-3">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
                {STAGE_LABELS[stage]} ({columns[stage].length})
              </p>
              <div className="space-y-2">
                {columns[stage].map((p) => (
                  <div
                    key={p.id}
                    className="cursor-pointer rounded-xl border border-slate-200 bg-white p-3 text-sm shadow-sm hover:border-slate-400"
                    onClick={() => setSelectedProspect(p)}
                  >
                    <p className="font-medium text-slate-800">{p.name}</p>
                    {p.company_name ? <p className="text-xs text-slate-500">{p.company_name}</p> : null}
                    <p className="mt-1 text-xs text-slate-400">{formatCurrency(p.estimated_value)}</p>
                    {p.assigned_to_name ? (
                      <p className="mt-1 text-[11px] text-slate-400">Owner: {p.assigned_to_name}</p>
                    ) : null}
                    {ALLOWED_TRANSITIONS[stage].length > 0 ? (
                      <div className="mt-2 flex flex-wrap gap-1" onClick={(e) => e.stopPropagation()}>
                        {ALLOWED_TRANSITIONS[stage].map((next) => (
                          <button
                            key={next}
                            onClick={() => handleQuickAdvance(p, next)}
                            className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                              next === "lost"
                                ? "bg-rose-100 text-rose-700 hover:bg-rose-200"
                                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                            }`}
                          >
                            → {STAGE_LABELS[next]}
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ))}
                {columns[stage].length === 0 ? <p className="text-xs text-slate-300">Empty</p> : null}
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreateModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-4">
              <h2 className="text-xl font-bold text-slate-900">New Prospect</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
              >
                Close
              </button>
            </div>
            <form onSubmit={handleCreate} className="space-y-3">
              <input
                placeholder="Name (person or org)"
                value={form.name}
                onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                required
              />
              <input
                placeholder="Company name (optional)"
                value={form.company_name}
                onChange={(e) => setForm((p) => ({ ...p, company_name: e.target.value }))}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
              />
              <div className="grid grid-cols-2 gap-3">
                <input
                  placeholder="Contact email"
                  value={form.contact_email}
                  onChange={(e) => setForm((p) => ({ ...p, contact_email: e.target.value }))}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
                <input
                  placeholder="Contact phone"
                  value={form.contact_phone}
                  onChange={(e) => setForm((p) => ({ ...p, contact_phone: e.target.value }))}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <input
                  placeholder="Industry"
                  value={form.industry}
                  onChange={(e) => setForm((p) => ({ ...p, industry: e.target.value }))}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
                <select
                  value={form.source}
                  onChange={(e) => setForm((p) => ({ ...p, source: e.target.value }))}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                >
                  <option value="referral">Referral</option>
                  <option value="outbound">Outbound</option>
                  <option value="inbound">Inbound</option>
                  <option value="event">Event</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <input
                  type="number"
                  placeholder="Estimated value"
                  value={form.estimated_value}
                  onChange={(e) => setForm((p) => ({ ...p, estimated_value: e.target.value }))}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
                <input
                  type="date"
                  value={form.expected_close_date}
                  onChange={(e) => setForm((p) => ({ ...p, expected_close_date: e.target.value }))}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <select
                  value={form.department_id}
                  onChange={(e) => setForm((p) => ({ ...p, department_id: e.target.value }))}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                >
                  <option value="">No department</option>
                  {departments.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
                <select
                  value={form.assigned_to_user_id}
                  onChange={(e) => setForm((p) => ({ ...p, assigned_to_user_id: e.target.value }))}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                >
                  <option value="">Unassigned</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.name}
                    </option>
                  ))}
                </select>
              </div>
              <textarea
                placeholder="Notes (optional)"
                value={form.notes}
                onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))}
                rows={2}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
              />
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-70"
                >
                  {saving ? "Saving..." : "Create Prospect"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {selectedProspect ? (
        <ProspectDetailModal
          prospect={selectedProspect}
          onClose={() => setSelectedProspect(null)}
          onChanged={async () => {
            await load();
            const refreshed = prospects.find((p) => p.id === selectedProspect.id);
            if (refreshed) setSelectedProspect(refreshed);
          }}
        />
      ) : null}
    </div>
  );
}

function ProspectDetailModal({ prospect, onClose, onChanged }) {
  const [history, setHistory] = useState([]);
  const [proposals, setProposals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showProposalForm, setShowProposalForm] = useState(false);
  const [proposalForm, setProposalForm] = useState({ title: "", scope_summary: "", proposed_value: "" });

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prospect.id]);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [historyData, proposalData] = await Promise.all([
        fetchProspectStageHistory(prospect.id),
        fetchProposals({ prospect_id: prospect.id }),
      ]);
      setHistory(historyData);
      setProposals(proposalData);
    } catch (err) {
      setError(err.message || "Failed to load prospect detail");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateProposal(e) {
    e.preventDefault();
    try {
      await createProposal({
        prospect_id: prospect.id,
        title: proposalForm.title,
        scope_summary: proposalForm.scope_summary || undefined,
        proposed_value: proposalForm.proposed_value || undefined,
      });
      setShowProposalForm(false);
      setProposalForm({ title: "", scope_summary: "", proposed_value: "" });
      await load();
    } catch (err) {
      window.alert(err.message || "Failed to create proposal");
    }
  }

  async function handleProposalTransition(proposal, next) {
    let notes;
    if (next === "rejected") {
      notes = window.prompt("Rejection notes (optional):") || undefined;
    }
    try {
      await updateProposalStatus(proposal.id, next, notes);
      await load();
    } catch (err) {
      window.alert(err.message || "Failed to update proposal");
    }
  }

  async function handleConvert() {
    if (!window.confirm("Convert this won prospect into a client record?")) return;
    try {
      await convertProspect(prospect.id);
      await onChanged();
      onClose();
    } catch (err) {
      window.alert(err.message || "Failed to convert prospect");
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Delete prospect "${prospect.name}"? This can't be undone.`)) return;
    try {
      await deleteProspect(prospect.id);
      await onChanged();
      onClose();
    } catch (err) {
      window.alert(err.message || "Failed to delete prospect");
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900">{prospect.name}</h2>
            {prospect.company_name ? <p className="text-sm text-slate-500">{prospect.company_name}</p> : null}
          </div>
          <button
            onClick={onClose}
            className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
          >
            Close
          </button>
        </div>

        {error ? (
          <div className="mb-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
        ) : null}

        <div className="mb-4 grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-xs text-slate-400">Stage</p>
            <p className="font-medium text-slate-800">{STAGE_LABELS[prospect.status]}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400">Estimated Value</p>
            <p className="font-medium text-slate-800">{formatCurrency(prospect.estimated_value)}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400">Expected Close</p>
            <p className="font-medium text-slate-800">{formatDate(prospect.expected_close_date)}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400">Source</p>
            <p className="font-medium capitalize text-slate-800">{prospect.source}</p>
          </div>
          {prospect.lost_reason ? (
            <div className="col-span-2">
              <p className="text-xs text-slate-400">Lost Reason</p>
              <p className="font-medium text-rose-600">{prospect.lost_reason}</p>
            </div>
          ) : null}
        </div>

        {prospect.status === "won" ? (
          <div className="mb-4">
            {prospect.converted_client_id ? (
              <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
                Converted to client #{prospect.converted_client_id}
              </span>
            ) : (
              <button
                onClick={handleConvert}
                className="rounded-2xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
              >
                Convert to Client
              </button>
            )}
          </div>
        ) : null}

        <div className="mb-4">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Proposals</h3>
            {!["won", "lost"].includes(prospect.status) ? (
              <button
                onClick={() => setShowProposalForm((s) => !s)}
                className="text-xs font-semibold text-slate-600 hover:underline"
              >
                {showProposalForm ? "Cancel" : "+ Add Proposal"}
              </button>
            ) : null}
          </div>

          {showProposalForm ? (
            <form onSubmit={handleCreateProposal} className="mb-3 space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3">
              <input
                placeholder="Proposal title"
                value={proposalForm.title}
                onChange={(e) => setProposalForm((p) => ({ ...p, title: e.target.value }))}
                className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
                required
              />
              <textarea
                placeholder="Scope summary (optional)"
                value={proposalForm.scope_summary}
                onChange={(e) => setProposalForm((p) => ({ ...p, scope_summary: e.target.value }))}
                rows={2}
                className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
              />
              <input
                type="number"
                placeholder="Proposed value"
                value={proposalForm.proposed_value}
                onChange={(e) => setProposalForm((p) => ({ ...p, proposed_value: e.target.value }))}
                className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
              />
              <button
                type="submit"
                className="rounded-xl bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-800"
              >
                Save Proposal
              </button>
            </form>
          ) : null}

          {loading ? (
            <p className="text-sm text-slate-400">Loading...</p>
          ) : proposals.length === 0 ? (
            <p className="text-sm text-slate-400">No proposals yet.</p>
          ) : (
            <div className="space-y-2">
              {proposals.map((prop) => (
                <div key={prop.id} className="rounded-xl border border-slate-200 bg-white p-3 text-sm">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-medium text-slate-800">{prop.title}</p>
                      <p className="text-xs text-slate-400">{formatCurrency(prop.proposed_value)}</p>
                    </div>
                    <span className="shrink-0 rounded-full bg-slate-100 px-2.5 py-0.5 text-[10px] font-semibold text-slate-600">
                      {PROPOSAL_STAGE_LABELS[prop.status]}
                    </span>
                  </div>
                  {PROPOSAL_TRANSITIONS[prop.status].length > 0 ? (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {PROPOSAL_TRANSITIONS[prop.status].map((next) => (
                        <button
                          key={next}
                          onClick={() => handleProposalTransition(prop, next)}
                          className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600 hover:bg-slate-200"
                        >
                          → {PROPOSAL_STAGE_LABELS[next]}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="mb-4">
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">Stage History</h3>
          {history.length === 0 ? (
            <p className="text-sm text-slate-400">No stage changes yet.</p>
          ) : (
            <div className="space-y-1 text-xs text-slate-500">
              {history.map((h) => (
                <p key={h.id}>
                  {formatDate(h.created_at)}: {h.from_status || "created"} → {h.to_status} by {h.actor_name}
                  {h.notes ? ` — ${h.notes}` : ""}
                </p>
              ))}
            </div>
          )}
        </div>

        <div className="flex justify-end">
          <button onClick={handleDelete} className="text-xs font-semibold text-rose-600 hover:underline">
            Delete Prospect
          </button>
        </div>
      </div>
    </div>
  );
}
