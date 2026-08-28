// API client for the client-facing portal (/portal/*). Kept separate from
// lib/api.js because the portal runs on its own cookie
// (portal_access_token) and its own actor="client" JWT claim -- a portal
// session and a staff session can be live in the same browser at once, and
// nothing here should accidentally touch /auth/* (staff) routes or vice
// versa. Same hostname-consistency caveat as lib/api.js: must be loaded
// from the same host (localhost vs 127.0.0.1) the backend expects, or the
// SameSite=Lax cookie won't come back on later requests.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return await response.json();
  }

  const text = await response.text();
  return { detail: text || "Unexpected server response" };
}

async function portalGet(path) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "GET",
    credentials: "include",
  });
  const data = await parseResponse(response);
  if (!response.ok) throw new Error(data.detail || "Request failed");
  return data;
}

async function portalSend(path, method, payload) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: payload !== undefined ? JSON.stringify(payload) : undefined,
  });
  const data = await parseResponse(response);
  if (!response.ok) throw new Error(data.detail || "Request failed");
  return data;
}

// --- Auth --------------------------------------------------------------

export async function portalLogin(email, password) {
  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);

  const response = await fetch(`${API_BASE_URL}/portal/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: formData.toString(),
  });

  const data = await parseResponse(response);
  if (!response.ok) throw new Error(data.detail || "Login failed");
  return data;
}

export async function portalLogout() {
  const response = await fetch(`${API_BASE_URL}/portal/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
  return parseResponse(response);
}

export const fetchPortalCurrentUser = () => portalGet("/portal/auth/me");

export const requestPortalPasswordReset = (email) =>
  portalSend("/portal/auth/request-password-reset", "POST", { email });

export const resetPortalPassword = (token, newPassword) =>
  portalSend("/portal/auth/reset-password", "POST", { token, new_password: newPassword });

// --- Engagements ---------------------------------------------------------

export const fetchPortalEngagements = () => portalGet("/portal/engagements");

export const fetchPortalEngagement = (projectId) => portalGet(`/portal/engagements/${projectId}`);

// --- Milestones ------------------------------------------------------------

export const fetchPortalMilestones = (projectId) =>
  portalGet(`/portal/engagements/${projectId}/milestones`);

export const signoffPortalMilestone = (projectId, milestoneId, status, reason) =>
  portalSend(`/portal/engagements/${projectId}/milestones/${milestoneId}/signoff`, "PUT", {
    status,
    reason,
  });

// --- PBC (prepared-by-client) requests --------------------------------------

export const fetchPortalPbcRequests = (projectId, status) => {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return portalGet(`/portal/engagements/${projectId}/pbc-requests${qs}`);
};

export async function uploadPortalPbcDocument(pbcRequestId, file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/portal/pbc-requests/${pbcRequestId}/upload`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  const data = await parseResponse(response);
  if (!response.ok) throw new Error(data.detail || "Failed to upload document");
  return data;
}

// --- Shared files ------------------------------------------------------------

export const fetchPortalFiles = (projectId) => portalGet(`/portal/engagements/${projectId}/files`);

export async function downloadPortalFile(fileId, fallbackFilename) {
  const response = await fetch(`${API_BASE_URL}/portal/files/${fileId}/download`, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    const data = await parseResponse(response);
    throw new Error(data.detail || "Failed to download file");
  }

  const blob = await response.blob();
  const contentDisposition = response.headers.get("content-disposition") || "";
  const basicMatch = contentDisposition.match(/filename="?([^"]+)"?/i);
  const filename = basicMatch?.[1] || fallbackFilename;

  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);

  return { success: true, filename };
}
