"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchPortalEngagements } from "@/lib/portal-api";

const STATUS_STYLES = {
  active: "bg-emerald-50 text-emerald-700 border-emerald-200",
  on_hold: "bg-amber-50 text-amber-700 border-amber-200",
  completed: "bg-slate-100 text-slate-600 border-slate-200",
  cancelled: "bg-red-50 text-red-600 border-red-200",
};

function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatStatusLabel(status) {
  if (!status) return "—";
  return status
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export default function PortalHomePage() {
  const [engagements, setEngagements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchPortalEngagements();
        setEngagements(data);
      } catch (err) {
        setError(err.message || "Failed to load your engagements");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Your Engagements</h1>
        <p className="mt-1 text-sm text-slate-500">
          Review milestone status, respond to document requests, and access shared
          deliverables for each engagement.
        </p>
      </div>

      {loading ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
          Loading your engagements...
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-600">
          {error}
        </div>
      ) : engagements.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center">
          <p className="text-sm font-medium text-slate-600">
            No engagements are visible on your account yet.
          </p>
          <p className="mt-1 text-sm text-slate-400">
            Your engagement team will notify you once an engagement is set up.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {engagements.map((engagement) => (
            <Link
              key={engagement.id}
              href={`/portal/home/engagements/${engagement.id}`}
              className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="mb-3 flex items-start justify-between gap-3">
                <h2 className="text-base font-semibold text-slate-900 group-hover:text-slate-950">
                  {engagement.name}
                </h2>
                <span
                  className={`shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium ${
                    STATUS_STYLES[engagement.status] || "border-slate-200 bg-slate-50 text-slate-600"
                  }`}
                >
                  {formatStatusLabel(engagement.status)}
                </span>
              </div>

              <p className="mb-4 text-xs font-medium uppercase tracking-wide text-slate-400">
                {formatStatusLabel(engagement.type)}
              </p>

              {engagement.description ? (
                <p className="mb-4 line-clamp-2 text-sm text-slate-500">{engagement.description}</p>
              ) : null}

              <div className="grid grid-cols-2 gap-3 border-t border-slate-100 pt-3 text-xs text-slate-500">
                <div>
                  <p className="font-medium text-slate-400">Start date</p>
                  <p className="mt-0.5 text-slate-700">{formatDate(engagement.start_date)}</p>
                </div>
                <div>
                  <p className="font-medium text-slate-400">Target end</p>
                  <p className="mt-0.5 text-slate-700">{formatDate(engagement.end_date)}</p>
                </div>
                {engagement.engagement_partner_name ? (
                  <div className="col-span-2">
                    <p className="font-medium text-slate-400">Engagement partner</p>
                    <p className="mt-0.5 text-slate-700">{engagement.engagement_partner_name}</p>
                  </div>
                ) : null}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
