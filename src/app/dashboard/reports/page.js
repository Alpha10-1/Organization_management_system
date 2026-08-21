"use client";

import { useEffect, useMemo, useState } from "react";
import { Download } from "lucide-react";
import {
  fetchActivityLogs,
  exportClientsCsv,
  exportClientsPdf,
  exportFilesCsv,
  exportTasksCsv,
  exportActivityLogsCsv,
  fetchUsers,
  fetchClients,
  fetchPartnerDashboard,
  fetchClientDashboard,
  fetchComplianceDashboard,
  fetchCapacityDashboard,
  fetchAtRiskEngagements,
  fetchTimeEntryAnomaliesReport,
  searchEngagements,
} from "@/lib/api";

function clientDisplayName(client) {
  if (!client) return "";
  if ((client.client_type === "business" || client.client_type === "npo") && client.company_name) {
    return client.company_name;
  }
  const name = [client.first_name, client.last_name].filter(Boolean).join(" ");
  return name || client.company_name || `Client #${client.id}`;
}

function formatMoney(value) {
  if (value === null || value === undefined) return "—";
  return `$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString();
}

function PartnerDashboardPanel() {
  const [users, setUsers] = useState([]);
  const [partnerEmail, setPartnerEmail] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchUsers().then(setUsers).catch(() => setUsers([]));
  }, []);

  useEffect(() => {
    if (!partnerEmail) {
      setData(null);
      return;
    }
    setLoading(true);
    setError("");
    fetchPartnerDashboard(partnerEmail)
      .then(setData)
      .catch((err) => setError(err.message || "Failed to load partner dashboard"))
      .finally(() => setLoading(false));
  }, [partnerEmail]);

  return (
    <div className="space-y-4">
      <select
        value={partnerEmail}
        onChange={(e) => setPartnerEmail(e.target.value)}
        className="w-full max-w-sm rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
      >
        <option value="">Choose a partner...</option>
        {users.map((u) => (
          <option key={u.email} value={u.email}>
            {u.name}
          </option>
        ))}
      </select>

      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      ) : null}

      {loading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : data ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs text-slate-500">Active Engagements</p>
              <p className="mt-1 text-2xl font-bold text-slate-900">{data.active_engagement_count}</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs text-slate-500">Overdue Tasks</p>
              <p className="mt-1 text-2xl font-bold text-rose-600">{data.overdue_task_count}</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs text-slate-500">Upcoming (14d)</p>
              <p className="mt-1 text-2xl font-bold text-slate-900">
                {data.upcoming_deadlines.tasks.length + data.upcoming_deadlines.milestones.length}
              </p>
            </div>
          </div>

          <div>
            <p className="mb-2 text-sm font-semibold text-slate-700">Engagements</p>
            <div className="space-y-2">
              {data.engagements.map((e) => (
                <div key={e.id} className="rounded-xl border border-slate-200 bg-white p-3 text-sm">
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-slate-800">{e.name}</p>
                    <span className="text-xs capitalize text-slate-500">{e.status}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    {e.hours_logged}h logged
                    {e.budget !== null ? ` · Budget ${formatMoney(e.budget)}` : ""}
                    {e.risk_level === "high" ? (
                      <span className="ml-2 rounded-full bg-rose-100 px-2 py-0.5 text-[10px] font-semibold text-rose-700">
                        high risk
                      </span>
                    ) : null}
                  </p>
                </div>
              ))}
              {data.engagements.length === 0 ? (
                <p className="text-sm text-slate-400">No active engagements.</p>
              ) : null}
            </div>
          </div>

          <div>
            <p className="mb-2 text-sm font-semibold text-slate-700">Overdue Tasks</p>
            <div className="space-y-1">
              {data.overdue_tasks.length === 0 ? (
                <p className="text-sm text-slate-400">Nothing overdue.</p>
              ) : (
                data.overdue_tasks.map((t) => (
                  <p key={t.id} className="text-sm text-rose-600">
                    {t.title} — due {formatDate(t.due_date)}
                  </p>
                ))
              )}
            </div>
          </div>
        </div>
      ) : (
        <p className="text-sm text-slate-400">Select a partner to view their engagement dashboard.</p>
      )}
    </div>
  );
}

function ClientDashboardPanel() {
  const [clients, setClients] = useState([]);
  const [clientId, setClientId] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchClients().then(setClients).catch(() => setClients([]));
  }, []);

  useEffect(() => {
    if (!clientId) {
      setData(null);
      return;
    }
    setLoading(true);
    setError("");
    fetchClientDashboard(clientId)
      .then(setData)
      .catch((err) => setError(err.message || "Failed to load client dashboard"))
      .finally(() => setLoading(false));
  }, [clientId]);

  return (
    <div className="space-y-4">
      <select
        value={clientId}
        onChange={(e) => setClientId(e.target.value)}
        className="w-full max-w-sm rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
      >
        <option value="">Choose a client...</option>
        {clients.map((c) => (
          <option key={c.id} value={c.id}>
            {clientDisplayName(c)}
          </option>
        ))}
      </select>

      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      ) : null}

      {loading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : data ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs text-slate-500">Relationship Health</p>
              <p className="mt-1 text-lg font-bold capitalize text-slate-900">{data.relationship_health}</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs text-slate-500">Active Engagements</p>
              <p className="mt-1 text-2xl font-bold text-slate-900">{data.active_engagement_count}</p>
            </div>
          </div>

          {data.health_reasons?.length ? (
            <ul className="list-disc pl-5 text-sm text-slate-600">
              {data.health_reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          ) : null}

          <div>
            <p className="mb-2 text-sm font-semibold text-slate-700">Engagements</p>
            <div className="space-y-2">
              {data.engagements.map((e) => (
                <div key={e.id} className="rounded-xl border border-slate-200 bg-white p-3 text-sm">
                  <p className="font-medium text-slate-800">{e.name}</p>
                  <p className="mt-1 text-xs capitalize text-slate-500">
                    {e.type.replace("_", " ")} · {e.status}
                    {e.budget !== null ? ` · Budget ${formatMoney(e.budget)}` : ""}
                  </p>
                </div>
              ))}
              {data.engagements.length === 0 ? (
                <p className="text-sm text-slate-400">No engagements yet.</p>
              ) : null}
            </div>
          </div>

          {data.contracts?.length ? (
            <div>
              <p className="mb-2 text-sm font-semibold text-slate-700">Contracts</p>
              <div className="space-y-2">
                {data.contracts.map((c) => (
                  <div key={c.id} className="rounded-xl border border-slate-200 bg-white p-3 text-sm">
                    <p className="font-medium text-slate-800">{c.name}</p>
                    <p className="mt-1 text-xs capitalize text-slate-500">
                      {c.billing_type.replace("_", " ")} · {formatMoney(c.value)} · {c.status}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ) : (
        <p className="text-sm text-slate-400">Select a client to view their relationship dashboard.</p>
      )}
    </div>
  );
}

function ComplianceDashboardPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    fetchComplianceDashboard()
      .then(setData)
      .catch((err) => setError(err.message || "Failed to load compliance dashboard"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-slate-500">Loading...</p>;
  if (error) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
        {error}
      </div>
    );
  }
  if (!data) return null;

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">
        Every open engagement flagged high/medium risk or carrying a compliance flag, across
        the whole firm — the view a risk committee would use rather than one partner at a time.
      </p>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs text-slate-500">High Risk</p>
          <p className="mt-1 text-2xl font-bold text-rose-600">{data.high_risk_count}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs text-slate-500">Medium Risk</p>
          <p className="mt-1 text-2xl font-bold text-amber-600">{data.medium_risk_count}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs text-slate-500">Compliance Flagged</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">{data.compliance_flagged_count}</p>
        </div>
      </div>

      <div>
        <p className="mb-2 text-sm font-semibold text-slate-700">Flagged Engagements</p>
        <div className="space-y-2">
          {data.engagements.length === 0 ? (
            <p className="text-sm text-slate-400">
              No open engagements are currently high/medium risk or compliance-flagged.
            </p>
          ) : (
            data.engagements.map((e) => (
              <div key={e.id} className="rounded-xl border border-slate-200 bg-white p-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-medium text-slate-800">{e.name}</p>
                  <span
                    className={`shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-semibold capitalize ${
                      e.risk_level === "high"
                        ? "bg-rose-100 text-rose-700"
                        : e.risk_level === "medium"
                        ? "bg-amber-100 text-amber-700"
                        : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {e.risk_level} risk
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {e.type} · {e.status}
                  {e.engagement_partner_name ? ` · ${e.engagement_partner_name}` : ""}
                  {e.compliance_flag ? ` · Flag: ${e.compliance_flag}` : ""}
                  {e.overdue_task_count > 0 ? (
                    <span className="ml-2 font-semibold text-rose-600">
                      {e.overdue_task_count} overdue task{e.overdue_task_count === 1 ? "" : "s"}
                    </span>
                  ) : null}
                </p>
              </div>
            ))
          )}
        </div>
      </div>

      <div>
        <p className="mb-2 text-sm font-semibold text-slate-700">Recent Risk/Compliance Changes</p>
        <div className="space-y-1">
          {data.recent_risk_changes.length === 0 ? (
            <p className="text-sm text-slate-400">No recent risk or compliance changes.</p>
          ) : (
            data.recent_risk_changes.map((c, idx) => (
              <p key={`${c.project_id}-${idx}`} className="text-sm text-slate-600">
                <span className="text-xs text-slate-400">{formatDateTime(c.created_at)}</span>{" "}
                — {c.description}{" "}
                <span className="text-xs text-slate-400">({c.user_name})</span>
              </p>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function CapacityDashboardPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    fetchCapacityDashboard()
      .then(setData)
      .catch((err) => setError(err.message || "Failed to load capacity dashboard"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-slate-500">Loading...</p>;
  if (error) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
        {error}
      </div>
    );
  }
  if (!data) return null;

  const statusStyles = {
    over_allocated: "bg-rose-100 text-rose-700",
    under_allocated: "bg-amber-100 text-amber-700",
    bench: "bg-slate-200 text-slate-600",
    fully_allocated: "bg-emerald-100 text-emerald-700",
  };
  const statusLabels = {
    over_allocated: "Over-allocated",
    under_allocated: "Under-allocated",
    bench: "Bench",
    fully_allocated: "Fully allocated",
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">
        Planned % of each active staff member&apos;s time committed across open engagements, so
        you can see over- and under-allocation before assigning new work. Only individual
        assignments carry a percentage — department-wide staffing isn&apos;t split per person.
      </p>

      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs text-slate-500">Over-allocated</p>
          <p className="mt-1 text-2xl font-bold text-rose-600">{data.over_allocated_count}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs text-slate-500">Under-allocated</p>
          <p className="mt-1 text-2xl font-bold text-amber-600">{data.under_allocated_count}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs text-slate-500">On the Bench</p>
          <p className="mt-1 text-2xl font-bold text-slate-700">{data.bench_count}</p>
        </div>
      </div>

      <div className="space-y-2">
        {data.people.length === 0 ? (
          <p className="text-sm text-slate-400">No active staff members.</p>
        ) : (
          data.people.map((p) => (
            <div key={p.id} className="rounded-xl border border-slate-200 bg-white p-3 text-sm">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-medium text-slate-800">
                    {p.name}
                    {p.position ? (
                      <span className="ml-2 text-xs font-normal text-slate-400">
                        {p.position.replaceAll("_", " ")}
                      </span>
                    ) : null}
                  </p>
                  {p.engagements.length > 0 ? (
                    <p className="mt-1 text-xs text-slate-500">
                      {p.engagements.map((e) => e.project_name).join(", ")}
                      {p.unspecified_allocation_count > 0
                        ? ` (${p.unspecified_allocation_count} without a % set)`
                        : ""}
                    </p>
                  ) : null}
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span className="text-xs font-semibold text-slate-600">
                    {p.total_allocated_percent}%
                  </span>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold ${statusStyles[p.status]}`}
                  >
                    {statusLabels[p.status]}
                  </span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

const RISK_TREND_STYLES = {
  worsening: "bg-rose-100 text-rose-700",
  improving: "bg-emerald-100 text-emerald-700",
  stable: "bg-slate-100 text-slate-600",
  insufficient_data: "bg-slate-100 text-slate-400",
};

const HEALTH_BADGE_STYLES = {
  green: "bg-emerald-100 text-emerald-700",
  amber: "bg-amber-100 text-amber-700",
  red: "bg-rose-100 text-rose-700",
};

const ANOMALY_FLAG_LABELS = {
  late_logged: "Logged late",
  friday_large_block: "Large Friday block",
  possible_duplicate: "Possible duplicate",
  round_number_pattern: "Round-number pattern",
};

function AtRiskEngagementsPanel() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lookbackDays, setLookbackDays] = useState(14);

  function load(days) {
    setLoading(true);
    setError("");
    fetchAtRiskEngagements({ lookback_days: days })
      .then(setData)
      .catch((err) => setError(err.message || "Failed to load at-risk engagements"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load(lookbackDays);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-500">
          Active engagements whose risk forecast is worsening, or already trending toward a worse
          predicted health than their current badge shows — a leading indicator, not just today&apos;s
          status.
        </p>
        <div className="flex shrink-0 items-center gap-2">
          <select
            value={lookbackDays}
            onChange={(e) => {
              const days = Number(e.target.value);
              setLookbackDays(days);
              load(days);
            }}
            className="rounded-xl border border-slate-300 px-3 py-2 text-xs outline-none focus:border-slate-900"
          >
            <option value={7}>7-day trend</option>
            <option value={14}>14-day trend</option>
            <option value={30}>30-day trend</option>
          </select>
          <button
            onClick={() => load(lookbackDays)}
            className="rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
          >
            Refresh
          </button>
        </div>
      </div>

      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      ) : null}

      {loading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : data.length === 0 ? (
        <p className="text-sm text-slate-400">
          No active engagements are currently trending toward higher risk.
        </p>
      ) : (
        <div className="space-y-2">
          {data.map((e) => (
            <div key={e.project_id} className="rounded-xl border border-slate-200 bg-white p-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium text-slate-800">{e.project_name}</p>
                  <p className="text-xs text-slate-500">
                    {e.client_name || `Client #${e.client_id}`}
                    {e.engagement_partner_name ? ` · ${e.engagement_partner_name}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold capitalize ${
                      HEALTH_BADGE_STYLES[e.current_health] || HEALTH_BADGE_STYLES.green
                    }`}
                  >
                    now: {e.current_health}
                  </span>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold capitalize ${
                      HEALTH_BADGE_STYLES[e.predicted_health] || HEALTH_BADGE_STYLES.green
                    }`}
                  >
                    forecast: {e.predicted_health}
                  </span>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold capitalize ${
                      RISK_TREND_STYLES[e.trend] || RISK_TREND_STYLES.stable
                    }`}
                  >
                    {e.trend.replace("_", " ")}
                  </span>
                  <span className="rounded-full bg-slate-900 px-2.5 py-0.5 text-[10px] font-semibold text-white">
                    score {e.risk_score}
                  </span>
                </div>
              </div>
              {e.signals?.length ? (
                <p className="mt-2 text-xs text-slate-500">{e.signals.join(" · ")}</p>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TimeAnomaliesPanel() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    setError("");
    fetchTimeEntryAnomaliesReport()
      .then(setData)
      .catch((err) => setError(err.message || "Failed to load time entry anomalies"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-slate-500">
          Rules-based flags across every logged time entry firm-wide — late-logged entries, large
          Friday blocks, possible duplicates, and round-number repeat patterns. For partner review,
          not an accusation.
        </p>
        <button
          onClick={load}
          className="shrink-0 rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
        >
          Refresh
        </button>
      </div>

      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      ) : null}

      {loading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : data.length === 0 ? (
        <p className="text-sm text-slate-400">No flagged time entries.</p>
      ) : (
        <div className="max-h-96 space-y-2 overflow-y-auto">
          {data.map((a) => (
            <div key={a.time_entry_id} className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-slate-800">
                  {a.hours}h · {a.user_name} · {formatDate(a.entry_date)}
                </p>
                <div className="flex flex-wrap gap-1">
                  {a.flags.map((flag, idx) => (
                    <span
                      key={flag}
                      title={a.reasons[idx]}
                      className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-800"
                    >
                      {ANOMALY_FLAG_LABELS[flag] || flag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function EngagementSearchPanel() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSearch(e) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    try {
      const data = await searchEngagements(query.trim());
      setResult(data);
    } catch (err) {
      setError(err.message || "Search failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">
        Search engagement notes, close-out notes, client notes, and the activity log in plain
        language — e.g. &quot;every engagement where we flagged a going concern issue&quot;.
      </p>
      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Show me every engagement where we flagged a going concern issue..."
          className="w-full rounded-2xl border border-slate-300 px-4 py-3 text-sm outline-none focus:border-slate-900"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="shrink-0 rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      ) : null}

      {result ? (
        <div className="space-y-3">
          {(result.terms?.length || result.phrases?.length) ? (
            <p className="text-xs text-slate-400">
              Matched on: {[...(result.phrases || []), ...(result.terms || [])].join(", ")}
            </p>
          ) : null}
          {result.results.length === 0 ? (
            <p className="text-sm text-slate-400">No engagements matched that search.</p>
          ) : (
            result.results.map((r) => (
              <div key={r.project_id} className="rounded-xl border border-slate-200 bg-white p-3 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-medium text-slate-800">{r.project_name}</p>
                  <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[10px] font-semibold text-slate-600">
                    {r.match_count} match{r.match_count === 1 ? "" : "es"}
                  </span>
                </div>
                <p className="text-xs text-slate-500">
                  {r.client_name || `Client #${r.client_id}`} · matched: {r.matched_terms.join(", ")}
                </p>
                {r.snippets?.length ? (
                  <ul className="mt-2 space-y-1">
                    {r.snippets.map((snippet, idx) => (
                      <li key={idx} className="text-xs text-slate-500">
                        {snippet}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}

function formatDateTime(dateString) {
  const date = new Date(dateString);
  return date.toLocaleString();
}

const EXPORTS = [
  { label: "Clients (CSV)", handler: exportClientsCsv },
  { label: "Clients (PDF)", handler: exportClientsPdf },
  { label: "Files (CSV)", handler: exportFilesCsv },
  { label: "Tasks (CSV)", handler: exportTasksCsv },
  { label: "Activity Logs (CSV)", handler: exportActivityLogsCsv },
];

export default function ReportsPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("All");
  const [exporting, setExporting] = useState("");
  const [dashboardTab, setDashboardTab] = useState("partner");

  async function handleExport(item) {
    try {
      setExporting(item.label);
      setError("");
      await item.handler();
    } catch (err) {
      setError(err.message || `Failed to export ${item.label}`);
    } finally {
      setExporting("");
    }
  }

  useEffect(() => {
    async function loadLogs() {
      try {
        setError("");
        const data = await fetchActivityLogs();
        setLogs(data);
      } catch (err) {
        setError(err.message || "Failed to load activity logs");
      } finally {
        setLoading(false);
      }
    }

    loadLogs();
  }, []);

  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      const matchesSearch =
        !search ||
        log.title?.toLowerCase().includes(search.toLowerCase()) ||
        log.description?.toLowerCase().includes(search.toLowerCase()) ||
        log.user_name?.toLowerCase().includes(search.toLowerCase()) ||
        log.user_email?.toLowerCase().includes(search.toLowerCase()) ||
        log.action?.toLowerCase().includes(search.toLowerCase());

      const matchesAction =
        actionFilter === "All" || log.action === actionFilter;

      return matchesSearch && matchesAction;
    });
  }, [logs, search, actionFilter]);

  const summary = useMemo(() => {
    const counts = {
      total: logs.length,
      login: 0,
      created: 0,
      updated: 0,
      deleted: 0,
    };

    logs.forEach((log) => {
      if (log.action === "login") counts.login += 1;
      if (log.action === "client_created") counts.created += 1;
      if (log.action === "client_updated") counts.updated += 1;
      if (log.action === "client_deleted") counts.deleted += 1;
    });

    return counts;
  }, [logs]);

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold text-slate-900">Reports & Activity Logs</h1>
        <p className="mt-1 text-sm text-slate-500">
          Monitor system events, track client actions, and review user activity.
        </p>

        <div className="mt-4 flex flex-wrap gap-2">
          {EXPORTS.map((item) => (
            <button
              key={item.label}
              onClick={() => handleExport(item)}
              disabled={exporting === item.label}
              className="flex items-center gap-2 rounded-2xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:opacity-60"
            >
              <Download className="h-4 w-4" />
              {exporting === item.label ? "Exporting..." : item.label}
            </button>
          ))}
        </div>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Total Logs</p>
          <h3 className="mt-3 text-3xl font-bold tracking-tight text-slate-900">
            {summary.total}
          </h3>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Logins</p>
          <h3 className="mt-3 text-3xl font-bold tracking-tight text-slate-900">
            {summary.login}
          </h3>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Client Created</p>
          <h3 className="mt-3 text-3xl font-bold tracking-tight text-slate-900">
            {summary.created}
          </h3>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Client Updated</p>
          <h3 className="mt-3 text-3xl font-bold tracking-tight text-slate-900">
            {summary.updated}
          </h3>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Client Deleted</p>
          <h3 className="mt-3 text-3xl font-bold tracking-tight text-slate-900">
            {summary.deleted}
          </h3>
        </div>
      </section>

      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      ) : null}

      <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Engagement Dashboards</h2>
        <p className="mt-1 text-sm text-slate-500">
          Active engagements, upcoming deadlines, hours vs. budget, and relationship health.
        </p>

        <div className="mt-4 flex gap-2">
          <button
            onClick={() => setDashboardTab("partner")}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              dashboardTab === "partner" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Per-Partner
          </button>
          <button
            onClick={() => setDashboardTab("client")}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              dashboardTab === "client" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Per-Client
          </button>
          <button
            onClick={() => setDashboardTab("compliance")}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              dashboardTab === "compliance" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Compliance
          </button>
          <button
            onClick={() => setDashboardTab("capacity")}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              dashboardTab === "capacity" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Capacity
          </button>
          <button
            onClick={() => setDashboardTab("at-risk")}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              dashboardTab === "at-risk" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            At-Risk (Forecast)
          </button>
          <button
            onClick={() => setDashboardTab("time-anomalies")}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              dashboardTab === "time-anomalies" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Time Anomalies
          </button>
          <button
            onClick={() => setDashboardTab("search")}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              dashboardTab === "search" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Engagement Search
          </button>
        </div>

        <div className="mt-4">
          {dashboardTab === "partner" ? (
            <PartnerDashboardPanel />
          ) : dashboardTab === "client" ? (
            <ClientDashboardPanel />
          ) : dashboardTab === "compliance" ? (
            <ComplianceDashboardPanel />
          ) : dashboardTab === "capacity" ? (
            <CapacityDashboardPanel />
          ) : dashboardTab === "at-risk" ? (
            <AtRiskEngagementsPanel />
          ) : dashboardTab === "time-anomalies" ? (
            <TimeAnomaliesPanel />
          ) : (
            <EngagementSearchPanel />
          )}
        </div>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <input
            type="text"
            placeholder="Search logs, users, actions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full max-w-sm rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
          />

          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
          >
            <option value="All">All Actions</option>
            <option value="login">Login</option>
            <option value="client_created">Client Created</option>
            <option value="client_updated">Client Updated</option>
            <option value="client_deleted">Client Deleted</option>
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[950px] border-separate border-spacing-y-3">
            <thead>
              <tr className="text-left text-sm text-slate-500">
                <th className="pb-2">Action</th>
                <th className="pb-2">Title</th>
                <th className="pb-2">User</th>
                <th className="pb-2">Entity</th>
                <th className="pb-2">Date</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-sm text-slate-500">
                    Loading activity logs...
                  </td>
                </tr>
              ) : filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-sm text-slate-500">
                    No activity logs found.
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => (
                  <tr key={log.id} className="bg-slate-50">
                    <td className="rounded-l-2xl px-4 py-4">
                      <span className="rounded-full bg-slate-200 px-3 py-1 text-xs font-semibold text-slate-700">
                        {log.action}
                      </span>
                    </td>

                    <td className="px-4 py-4">
                      <p className="font-semibold text-slate-900">{log.title}</p>
                      <p className="mt-1 text-sm text-slate-500">
                        {log.description || "No description"}
                      </p>
                    </td>

                    <td className="px-4 py-4">
                      <p className="font-medium text-slate-900">{log.user_name}</p>
                      <p className="mt-1 text-sm text-slate-500">{log.user_email}</p>
                    </td>

                    <td className="px-4 py-4 text-slate-700">
                      <div className="space-y-1 text-sm">
                        <p>Type: {log.entity_type}</p>
                        <p>ID: {log.entity_id ?? "-"}</p>
                      </div>
                    </td>

                    <td className="rounded-r-2xl px-4 py-4 text-sm text-slate-700">
                      {formatDateTime(log.created_at)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}