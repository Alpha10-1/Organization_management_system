"use client";

import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { getToken } from "@/lib/auth";
import { fetchDashboardSummary } from "@/lib/api";

function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString();
}

export default function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadSummary() {
      try {
        setError("");
        const token = getToken();
        const data = await fetchDashboardSummary(token);
        setSummary(data);
      } catch (error) {
        console.error("Failed to load dashboard summary:", error);
        setError("Failed to load dashboard data.");
      } finally {
        setLoading(false);
      }
    }

    loadSummary();
  }, []);

  if (loading) {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm text-slate-500">Loading dashboard data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-3xl border border-red-200 bg-red-50 p-6 shadow-sm">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    );
  }

  const stats = summary
    ? [
        { label: "Total Clients", value: summary.stats.total_clients },
        { label: "Staff Members", value: summary.stats.staff_members },
        { label: "Total Files", value: summary.stats.total_files ?? 0 },
        { label: "New This Week", value: summary.stats.recent_clients },
      ]
    : [];
    
  const statusCards = summary
    ? [
        { label: "Pending Clients", value: summary.stats.pending_clients },
        { label: "Closed Clients", value: summary.stats.closed_clients },
      ]
    : [];

  const chartData = summary?.status_distribution || [];

  return (
    <div className="space-y-6">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((item) => (
          <div
            key={item.label}
            className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <p className="text-sm text-slate-500">{item.label}</p>
            <h3 className="mt-3 text-3xl font-bold tracking-tight text-slate-900">
              {item.value}
            </h3>
          </div>
        ))}
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        {statusCards.map((item) => (
          <div
            key={item.label}
            className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <p className="text-sm text-slate-500">{item.label}</p>
            <h3 className="mt-3 text-2xl font-bold tracking-tight text-slate-900">
              {item.value}
            </h3>
          </div>
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-3">
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm xl:col-span-2">
          <div className="flex items-center justify-between gap-4">
            <h3 className="text-lg font-semibold text-slate-900">
              Recent Clients
            </h3>
            <span className="text-sm text-slate-500">Latest 5 records</span>
          </div>

          <div className="mt-6 space-y-3">
            {summary?.recent_clients?.length ? (
              summary.recent_clients.map((client) => (
                <div
                  key={client.id}
                  className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4"
                >
                  <div>
                    <p className="font-semibold text-slate-900">{client.name}</p>
                    <p className="mt-1 text-sm text-slate-500">
                      Added on {formatDate(client.created_at)}
                    </p>
                    <p className="mt-1 text-sm text-slate-500">
                      {client.email || client.phone || "No contact info"}
                    </p>
                  </div>

                  <span className="rounded-full bg-slate-200 px-3 py-1 text-xs font-semibold text-slate-700">
                    {client.status}
                  </span>
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500">
                No recent clients found.
              </div>
            )}
          </div>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">Session Info</h3>

          <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
            <p className="text-sm text-slate-600">Signed in as:</p>
            <p className="mt-1 font-semibold text-slate-900">
              {summary?.message || "Authenticated user"}
            </p>
            <p className="mt-2 text-sm text-slate-500">
              Role: {summary?.role || "Unknown"}
            </p>
          </div>

          <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
            <p className="text-sm text-slate-600">System Snapshot</p>
            <div className="mt-3 space-y-2 text-sm text-slate-700">
              <p>Total files: {summary?.stats?.total_files ?? 0}</p>
              <p>Active: {summary?.stats?.active_clients ?? 0}</p>
              <p>Pending: {summary?.stats?.pending_clients ?? 0}</p>
              <p>Closed: {summary?.stats?.closed_clients ?? 0}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <h3 className="text-lg font-semibold text-slate-900">
              Client Status Distribution
            </h3>
          </div>

          <div className="mt-6 h-72">
            {chartData.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    dataKey="value"
                    nameKey="name"
                    outerRadius={90}
                    innerRadius={55}
                    paddingAngle={4}
                  >
                    {chartData.map((entry) => (
                      <Cell key={entry.name} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 text-sm text-slate-500">
                No chart data available.
              </div>
            )}
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            {chartData.map((item) => (
              <div
                key={item.name}
                className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
              >
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  {item.name}
                </p>
                <p className="mt-2 text-xl font-bold text-slate-900">
                  {item.value}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <h3 className="text-lg font-semibold text-slate-900">
              Recent Activity
            </h3>
            <span className="text-sm text-slate-500">Latest system actions</span>
          </div>

          <div className="mt-6 space-y-3">
            {summary?.recent_activity?.length ? (
              summary.recent_activity.map((activity) => (
                <div
                  key={activity.id}
                  className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4"
                >
                  <p className="font-semibold text-slate-900">
                    {activity.title}
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    {activity.description}
                  </p>
                  <p className="mt-2 text-xs text-slate-400">
                    {formatDate(activity.date)}
                  </p>
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500">
                No recent activity found.
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}