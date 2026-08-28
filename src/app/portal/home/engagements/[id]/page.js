"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ChevronLeft,
  CircleCheck,
  CircleX,
  Clock,
  Download,
  FileText,
  Upload,
} from "lucide-react";
import {
  downloadPortalFile,
  fetchPortalEngagement,
  fetchPortalFiles,
  fetchPortalMilestones,
  fetchPortalPbcRequests,
  signoffPortalMilestone,
  uploadPortalPbcDocument,
} from "@/lib/portal-api";

const TABS = [
  { id: "milestones", label: "Milestones" },
  { id: "pbc", label: "Document Requests" },
  { id: "files", label: "Shared Files" },
];

function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatBytes(bytes) {
  if (!bytes && bytes !== 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatStatusLabel(status) {
  if (!status) return "—";
  return status
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export default function PortalEngagementDetailPage() {
  const params = useParams();
  const projectId = params.id;

  const [engagement, setEngagement] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("milestones");

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchPortalEngagement(projectId);
        setEngagement(data);
      } catch (err) {
        setError(err.message || "Failed to load this engagement");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [projectId]);

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
        Loading engagement...
      </div>
    );
  }

  if (error || !engagement) {
    return (
      <div className="space-y-4">
        <Link
          href="/portal/home"
          className="inline-flex items-center gap-1 text-sm font-semibold text-slate-500 hover:text-slate-800"
        >
          <ChevronLeft className="h-4 w-4" /> Back to engagements
        </Link>
        <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-600">
          {error || "This engagement could not be found."}
        </div>
      </div>
    );
  }

  return (
    <div>
      <Link
        href="/portal/home"
        className="mb-4 inline-flex items-center gap-1 text-sm font-semibold text-slate-500 hover:text-slate-800"
      >
        <ChevronLeft className="h-4 w-4" /> Back to engagements
      </Link>

      <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-slate-900">{engagement.name}</h1>
            <p className="mt-1 text-xs font-medium uppercase tracking-wide text-slate-400">
              {formatStatusLabel(engagement.type)} · {formatStatusLabel(engagement.status)}
            </p>
          </div>
        </div>
        {engagement.description ? (
          <p className="mt-3 text-sm text-slate-600">{engagement.description}</p>
        ) : null}
        <div className="mt-4 grid grid-cols-2 gap-4 border-t border-slate-100 pt-4 text-sm sm:grid-cols-4">
          <div>
            <p className="text-xs font-medium text-slate-400">Start date</p>
            <p className="mt-0.5 text-slate-700">{formatDate(engagement.start_date)}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Target end</p>
            <p className="mt-0.5 text-slate-700">{formatDate(engagement.end_date)}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Engagement partner</p>
            <p className="mt-0.5 text-slate-700">{engagement.engagement_partner_name || "—"}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Engagement manager</p>
            <p className="mt-0.5 text-slate-700">{engagement.engagement_manager_name || "—"}</p>
          </div>
        </div>
      </div>

      <div className="mb-5 flex gap-1 rounded-2xl border border-slate-200 bg-white p-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 rounded-xl px-4 py-2 text-sm font-semibold transition ${
              activeTab === tab.id
                ? "bg-slate-900 text-white"
                : "text-slate-500 hover:bg-slate-50 hover:text-slate-800"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "milestones" ? <MilestonesTab projectId={projectId} /> : null}
      {activeTab === "pbc" ? <PbcRequestsTab projectId={projectId} /> : null}
      {activeTab === "files" ? <FilesTab projectId={projectId} /> : null}
    </div>
  );
}

// --- Milestones ------------------------------------------------------------

function MilestonesTab({ projectId }) {
  const [milestones, setMilestones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actioningId, setActioningId] = useState(null);
  const [rejectingId, setRejectingId] = useState(null);
  const [rejectReason, setRejectReason] = useState("");

  async function load() {
    try {
      const data = await fetchPortalMilestones(projectId);
      setMilestones(data);
    } catch (err) {
      setError(err.message || "Failed to load milestones");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function handleApprove(milestoneId) {
    setActioningId(milestoneId);
    try {
      await signoffPortalMilestone(projectId, milestoneId, "approved");
      await load();
    } catch (err) {
      setError(err.message || "Failed to record sign-off");
    } finally {
      setActioningId(null);
    }
  }

  async function handleReject(milestoneId) {
    setActioningId(milestoneId);
    try {
      await signoffPortalMilestone(projectId, milestoneId, "rejected", rejectReason.trim() || undefined);
      setRejectingId(null);
      setRejectReason("");
      await load();
    } catch (err) {
      setError(err.message || "Failed to record rejection");
    } finally {
      setActioningId(null);
    }
  }

  if (loading) {
    return <TabLoading label="Loading milestones..." />;
  }

  if (error) {
    return <TabError message={error} />;
  }

  if (milestones.length === 0) {
    return <TabEmpty message="No milestones have been added to this engagement yet." />;
  }

  return (
    <div className="space-y-3">
      {milestones.map((milestone) => (
        <div key={milestone.id} className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">{milestone.name}</h3>
              {milestone.description ? (
                <p className="mt-1 text-sm text-slate-500">{milestone.description}</p>
              ) : null}
              <p className="mt-2 flex items-center gap-1 text-xs text-slate-400">
                <Clock className="h-3.5 w-3.5" /> Due {formatDate(milestone.due_date)}
              </p>
            </div>
            <ApprovalBadge status={milestone.approval_status} />
          </div>

          {milestone.approval_status === "rejected" && milestone.rejection_reason ? (
            <p className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
              Your note: {milestone.rejection_reason}
            </p>
          ) : null}

          {milestone.approval_status !== "approved" ? (
            <div className="mt-4 border-t border-slate-100 pt-4">
              {rejectingId === milestone.id ? (
                <div className="space-y-2">
                  <textarea
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Optional: let the team know what needs to change"
                    rows={2}
                    className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleReject(milestone.id)}
                      disabled={actioningId === milestone.id}
                      className="rounded-xl bg-red-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-red-700 disabled:opacity-60"
                    >
                      {actioningId === milestone.id ? "Submitting..." : "Confirm rejection"}
                    </button>
                    <button
                      onClick={() => {
                        setRejectingId(null);
                        setRejectReason("");
                      }}
                      className="rounded-xl border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex gap-2">
                  <button
                    onClick={() => handleApprove(milestone.id)}
                    disabled={actioningId === milestone.id}
                    className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-60"
                  >
                    <CircleCheck className="h-3.5 w-3.5" />
                    {actioningId === milestone.id ? "Submitting..." : "Approve"}
                  </button>
                  <button
                    onClick={() => setRejectingId(milestone.id)}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50"
                  >
                    <CircleX className="h-3.5 w-3.5" />
                    Request changes
                  </button>
                </div>
              )}
            </div>
          ) : (
            <p className="mt-3 text-xs text-slate-400">
              Approved {formatDate(milestone.approved_at)}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function ApprovalBadge({ status }) {
  if (status === "approved") {
    return (
      <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
        <CircleCheck className="h-3 w-3" /> Approved
      </span>
    );
  }
  if (status === "rejected") {
    return (
      <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-red-200 bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-600">
        <CircleX className="h-3 w-3" /> Changes requested
      </span>
    );
  }
  return (
    <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-700">
      <Clock className="h-3 w-3" /> Awaiting your review
    </span>
  );
}

// --- PBC requests ------------------------------------------------------------

function PbcRequestsTab({ projectId }) {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [uploadingId, setUploadingId] = useState(null);

  async function load() {
    try {
      const data = await fetchPortalPbcRequests(projectId);
      setRequests(data);
    } catch (err) {
      setError(err.message || "Failed to load document requests");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function handleUpload(pbcId, file) {
    if (!file) return;
    setUploadingId(pbcId);
    setError("");
    try {
      await uploadPortalPbcDocument(pbcId, file);
      await load();
    } catch (err) {
      setError(err.message || "Failed to upload document");
    } finally {
      setUploadingId(null);
    }
  }

  if (loading) {
    return <TabLoading label="Loading document requests..." />;
  }

  if (requests.length === 0) {
    return <TabEmpty message="No documents have been requested for this engagement yet." />;
  }

  return (
    <div className="space-y-3">
      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-600">{error}</div>
      ) : null}

      {requests.map((request) => (
        <div key={request.id} className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">{request.title}</h3>
              {request.description ? (
                <p className="mt-1 text-sm text-slate-500">{request.description}</p>
              ) : null}
              <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate-400">
                {request.category ? (
                  <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5">
                    {request.category}
                  </span>
                ) : null}
                <span className="flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" /> Due {formatDate(request.due_date)}
                </span>
              </div>
            </div>
            <PbcStatusBadge status={request.status} />
          </div>

          {request.status === "rejected" && request.review_notes ? (
            <p className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
              Feedback from your engagement team: {request.review_notes}
            </p>
          ) : null}

          {request.status === "submitted" || request.status === "approved" ? (
            <p className="mt-3 text-xs text-slate-400">
              Submitted {formatDate(request.submitted_at)} by {request.submitted_by_name}
            </p>
          ) : null}

          {request.status !== "approved" ? (
            <div className="mt-4 border-t border-slate-100 pt-4">
              <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50">
                <Upload className="h-3.5 w-3.5" />
                {uploadingId === request.id
                  ? "Uploading..."
                  : request.status === "requested"
                    ? "Upload document"
                    : "Upload a new version"}
                <input
                  type="file"
                  className="hidden"
                  disabled={uploadingId === request.id}
                  onChange={(e) => handleUpload(request.id, e.target.files?.[0])}
                />
              </label>
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function PbcStatusBadge({ status }) {
  const styles = {
    requested: "border-amber-200 bg-amber-50 text-amber-700",
    submitted: "border-blue-200 bg-blue-50 text-blue-700",
    approved: "border-emerald-200 bg-emerald-50 text-emerald-700",
    rejected: "border-red-200 bg-red-50 text-red-600",
  };
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${
        styles[status] || "border-slate-200 bg-slate-50 text-slate-600"
      }`}
    >
      {formatStatusLabel(status)}
    </span>
  );
}

// --- Shared files ------------------------------------------------------------

function FilesTab({ projectId }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [downloadingId, setDownloadingId] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchPortalFiles(projectId);
        setFiles(data);
      } catch (err) {
        setError(err.message || "Failed to load shared files");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [projectId]);

  async function handleDownload(file) {
    setDownloadingId(file.id);
    try {
      await downloadPortalFile(file.id, file.original_name);
    } catch (err) {
      setError(err.message || "Failed to download file");
    } finally {
      setDownloadingId(null);
    }
  }

  if (loading) {
    return <TabLoading label="Loading shared files..." />;
  }

  if (error) {
    return <TabError message={error} />;
  }

  if (files.length === 0) {
    return <TabEmpty message="Your engagement team hasn't shared any files here yet." />;
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-slate-100 bg-slate-50 text-xs uppercase tracking-wide text-slate-400">
          <tr>
            <th className="px-5 py-3 font-medium">File</th>
            <th className="px-5 py-3 font-medium">Uploaded by</th>
            <th className="px-5 py-3 font-medium">Date</th>
            <th className="px-5 py-3 font-medium">Size</th>
            <th className="px-5 py-3" />
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {files.map((file) => (
            <tr key={file.id}>
              <td className="px-5 py-3">
                <span className="flex items-center gap-2 font-medium text-slate-800">
                  <FileText className="h-4 w-4 shrink-0 text-slate-400" />
                  {file.original_name}
                </span>
              </td>
              <td className="px-5 py-3 text-slate-500">{file.uploaded_by_name}</td>
              <td className="px-5 py-3 text-slate-500">{formatDate(file.created_at)}</td>
              <td className="px-5 py-3 text-slate-500">{formatBytes(file.file_size)}</td>
              <td className="px-5 py-3 text-right">
                <button
                  onClick={() => handleDownload(file)}
                  disabled={downloadingId === file.id}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 disabled:opacity-60"
                >
                  <Download className="h-3.5 w-3.5" />
                  {downloadingId === file.id ? "Downloading..." : "Download"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// --- Shared tab states ------------------------------------------------------

function TabLoading({ label }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
      {label}
    </div>
  );
}

function TabError({ message }) {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-600">{message}</div>
  );
}

function TabEmpty({ message }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-400">
      {message}
    </div>
  );
}
