"use client";

import { useEffect, useMemo, useState } from "react";
import { getToken } from "@/lib/auth";
import { fetchActivityLogs } from "@/lib/api";

function formatDateTime(dateString) {
  const date = new Date(dateString);
  return date.toLocaleString();
}

export default function ReportsPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("All");

  useEffect(() => {
    async function loadLogs() {
      try {
        setError("");
        const token = getToken();
        const data = await fetchActivityLogs(token);
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