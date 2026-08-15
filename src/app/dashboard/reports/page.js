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
} from "@/lib/api";

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
            {c.first_name} {c.last_name}
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
        </div>

        <div className="mt-4">
          {dashboardTab === "partner" ? <PartnerDashboardPanel /> : <ClientDashboardPanel />}
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