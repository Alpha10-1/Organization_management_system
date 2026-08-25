"use client";

import { useEffect, useState } from "react";
import { BookOpen, Search } from "lucide-react";
import { fetchKnowledgeBase, fetchKnowledgeBaseFacets } from "@/lib/api";

const RISK_STYLES = {
  low: "bg-emerald-100 text-emerald-700",
  medium: "bg-amber-100 text-amber-700",
  high: "bg-rose-100 text-rose-700",
};

function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString();
}

export default function KnowledgeBasePage() {
  const [facets, setFacets] = useState(null);
  const [q, setQ] = useState("");
  const [engagementType, setEngagementType] = useState("");
  const [industry, setIndustry] = useState("");
  const [complianceFlag, setComplianceFlag] = useState("");
  const [riskLevel, setRiskLevel] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    fetchKnowledgeBaseFacets().then(setFacets).catch(() => setFacets(null));
    runSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runSearch(overrides = {}) {
    setLoading(true);
    setError("");
    try {
      const params = {
        q: overrides.q ?? q,
        engagement_type: overrides.engagement_type ?? engagementType,
        industry: overrides.industry ?? industry,
        compliance_flag: overrides.compliance_flag ?? complianceFlag,
        risk_level: overrides.risk_level ?? riskLevel,
      };
      const data = await fetchKnowledgeBase(params);
      setResults(data.results);
    } catch (err) {
      setError(err.message || "Failed to load knowledge base");
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    runSearch();
  }

  function clearFilters() {
    setQ("");
    setEngagementType("");
    setIndustry("");
    setComplianceFlag("");
    setRiskLevel("");
    runSearch({ q: "", engagement_type: "", industry: "", compliance_flag: "", risk_level: "" });
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-3">
        <div className="rounded-2xl bg-slate-900 p-3 text-white">
          <BookOpen size={20} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Knowledge Base</h1>
          <p className="text-sm text-slate-500">
            Every engagement's close-out retrospective, firm-wide and searchable — "how did we
            handle this before" for engagement types, industries, and compliance issues you've
            already seen.
            {facets ? ` ${facets.total_entries} retrospective${facets.total_entries === 1 ? "" : "s"} on file.` : ""}
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder='Try "going concern", "material weakness", "fraud risk"...'
              className="w-full rounded-2xl border border-slate-300 py-3 pl-9 pr-4 text-sm outline-none focus:border-slate-900"
            />
          </div>
          <button
            type="submit"
            className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white hover:bg-slate-800"
          >
            Search
          </button>
        </div>

        {facets ? (
          <div className="flex flex-wrap gap-2">
            <select
              value={engagementType}
              onChange={(e) => {
                setEngagementType(e.target.value);
                runSearch({ engagement_type: e.target.value });
              }}
              className="rounded-xl border border-slate-300 px-3 py-2 text-xs outline-none focus:border-slate-900"
            >
              <option value="">All engagement types</option>
              {facets.engagement_types.map((t) => (
                <option key={t} value={t}>
                  {t.replaceAll("_", " ")}
                </option>
              ))}
            </select>
            <select
              value={industry}
              onChange={(e) => {
                setIndustry(e.target.value);
                runSearch({ industry: e.target.value });
              }}
              className="rounded-xl border border-slate-300 px-3 py-2 text-xs outline-none focus:border-slate-900"
            >
              <option value="">All industries</option>
              {facets.industries.map((i) => (
                <option key={i} value={i}>
                  {i}
                </option>
              ))}
            </select>
            <select
              value={complianceFlag}
              onChange={(e) => {
                setComplianceFlag(e.target.value);
                runSearch({ compliance_flag: e.target.value });
              }}
              className="rounded-xl border border-slate-300 px-3 py-2 text-xs outline-none focus:border-slate-900"
            >
              <option value="">All compliance flags</option>
              {facets.compliance_flags.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <select
              value={riskLevel}
              onChange={(e) => {
                setRiskLevel(e.target.value);
                runSearch({ risk_level: e.target.value });
              }}
              className="rounded-xl border border-slate-300 px-3 py-2 text-xs outline-none focus:border-slate-900"
            >
              <option value="">All risk levels</option>
              {facets.risk_levels.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
            {(q || engagementType || industry || complianceFlag || riskLevel) && (
              <button
                type="button"
                onClick={clearFilters}
                className="rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100"
              >
                Clear filters
              </button>
            )}
          </div>
        ) : null}
      </form>

      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
      ) : null}

      {loading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : results.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-400">
          No retrospectives match yet. Close-out notes are captured when an engagement wraps up —
          try a different search or filter.
        </div>
      ) : (
        <div className="space-y-3">
          {results.map((entry) => {
            const expanded = expandedId === entry.project_id;
            return (
              <div key={entry.project_id} className="rounded-2xl border border-slate-200 bg-white p-4">
                <button
                  onClick={() => setExpandedId(expanded ? null : entry.project_id)}
                  className="flex w-full items-start justify-between gap-3 text-left"
                >
                  <div>
                    <p className="font-semibold text-slate-800">{entry.project_name}</p>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {entry.client_name}
                      {entry.client_industry ? ` · ${entry.client_industry}` : ""} ·{" "}
                      {entry.engagement_type.replaceAll("_", " ")} · closed out {formatDate(entry.closed_out_at)}
                    </p>
                    {entry.snippet ? (
                      <p className="mt-2 text-sm italic text-slate-500">…{entry.snippet}…</p>
                    ) : null}
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold ${RISK_STYLES[entry.risk_level] || "bg-slate-100 text-slate-600"}`}
                    >
                      {entry.risk_level} risk
                    </span>
                    {entry.compliance_flag ? (
                      <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[10px] font-semibold text-slate-600">
                        {entry.compliance_flag}
                      </span>
                    ) : null}
                  </div>
                </button>

                {expanded ? (
                  <div className="mt-3 border-t border-slate-100 pt-3">
                    <p className="whitespace-pre-wrap text-sm text-slate-700">{entry.close_out_notes}</p>
                    {entry.engagement_partner_name ? (
                      <p className="mt-2 text-xs text-slate-400">Engagement partner: {entry.engagement_partner_name}</p>
                    ) : null}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
