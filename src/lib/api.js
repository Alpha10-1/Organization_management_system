const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return await response.json();
  }

  const text = await response.text();
  return { detail: text || "Unexpected server response" };
}

export async function updateClient(clientId, payload) {
  const response = await fetch(`${API_BASE_URL}/clients/${clientId}`, {
    method: "PUT",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to update client");
  }

  return data;
}

export async function fetchActivityLogs() {
  const response = await fetch(`${API_BASE_URL}/activity-logs`, {
    method: "GET",
    credentials: "include",
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to fetch activity logs");
  }

  return data;
}

export async function loginUser(email, password) {
  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData.toString(),
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Login failed");
  }

  return data;
}

export async function logoutUser() {
  const response = await fetch(`${API_BASE_URL}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });

  return parseResponse(response);
}

export async function fetchCurrentUser() {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    method: "GET",
    credentials: "include",
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to fetch user");
  }

  return data;
}

export async function fetchDashboardSummary() {
  const response = await fetch(`${API_BASE_URL}/dashboard-summary`, {
    method: "GET",
    credentials: "include",
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to fetch dashboard");
  }

  return data;
}

export async function fetchClients(params = {}) {
  const searchParams = new URLSearchParams();

  if (params.search) searchParams.append("search", params.search);
  if (params.status && params.status !== "All") {
    searchParams.append("status", params.status);
  }

  const queryString = searchParams.toString();
  const url = `${API_BASE_URL}/clients/${queryString ? `?${queryString}` : ""}`;

  const response = await fetch(url, {
    method: "GET",
    credentials: "include",
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to fetch clients");
  }

  return data;
}

export async function createClient(payload) {
  const response = await fetch(`${API_BASE_URL}/clients/`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to create client");
  }

  return data;
}

export async function fetchUsers() {
  const response = await fetch(`${API_BASE_URL}/users/`, {
    method: "GET",
    credentials: "include",
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to fetch users");
  }

  return data;
}

export async function createUser(payload) {
  const response = await fetch(`${API_BASE_URL}/users/`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to create user");
  }

  return data;
}

export async function updateUserRole(email, role) {
  const response = await fetch(`${API_BASE_URL}/users/${encodeURIComponent(email)}/role`, {
    method: "PATCH",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ role }),
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to update user role");
  }

  return data;
}

export async function updateUserStatus(email, disabled) {
  const response = await fetch(`${API_BASE_URL}/users/${encodeURIComponent(email)}/status`, {
    method: "PATCH",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ disabled }),
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to update user status");
  }

  return data;
}

export async function fetchFiles(params = {}) {
  const searchParams = new URLSearchParams();

  if (params.search) searchParams.append("search", params.search);
  if (params.file_type && params.file_type !== "All") {
    searchParams.append("file_type", params.file_type);
  }
  if (params.client_id) {
    searchParams.append("client_id", params.client_id);
  }
  if (params.mine_only) {
    searchParams.append("mine_only", "true");
  }

  const queryString = searchParams.toString();
  const url = `${API_BASE_URL}/files/${queryString ? `?${queryString}` : ""}`;

  const response = await fetch(url, {
    method: "GET",
    credentials: "include",
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to fetch files");
  }

  return data;
}


export async function uploadFile(file, clientId = "") {
  const formData = new FormData();
  formData.append("file", file);

  if (clientId) {
    formData.append("client_id", clientId);
  }

  const response = await fetch(`${API_BASE_URL}/files/upload`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to upload file");
  }

  return data;
}

export async function deleteFileRecord(fileId) {
  const response = await fetch(`${API_BASE_URL}/files/${fileId}`, {
    method: "DELETE",
    credentials: "include",
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to delete file");
  }

  return data;
}

export async function deleteClient(clientId) {
  const response = await fetch(`${API_BASE_URL}/clients/${clientId}`, {
    method: "DELETE",
    credentials: "include",
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to delete client");
  }

  return data;
}

export async function fetchFileRecord(fileId) {
  const response = await fetch(`${API_BASE_URL}/files/${fileId}`, {
    method: "GET",
    credentials: "include",
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to fetch file details");
  }

  return data;
}

export async function downloadFileAuthenticated(fileId) {
  const response = await fetch(`${API_BASE_URL}/files/${fileId}/download`, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    const data = await parseResponse(response);
    throw new Error(data.detail || "Failed to download file");
  }

  const blob = await response.blob();

  const contentDisposition = response.headers.get("content-disposition") || "";
  let filename = "downloaded-file";

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  const basicMatch = contentDisposition.match(/filename="?([^"]+)"?/i);

  if (utf8Match?.[1]) {
    filename = decodeURIComponent(utf8Match[1]);
  } else if (basicMatch?.[1]) {
    filename = basicMatch[1];
  }

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

export async function getAuthenticatedFileBlobUrl(fileId) {
  const response = await fetch(`${API_BASE_URL}/files/${fileId}/download`, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    const data = await parseResponse(response);
    throw new Error(data.detail || "Failed to load file preview");
  }

  const blob = await response.blob();
  const blobUrl = window.URL.createObjectURL(blob);

  return {
    blobUrl,
    contentType: response.headers.get("content-type") || "",
  };
}
// --- Generic helpers for the new resources -----------------------------

async function apiGet(path) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "GET",
    credentials: "include",
  });
  const data = await parseResponse(response);
  if (!response.ok) throw new Error(data.detail || "Request failed");
  return data;
}

async function apiSend(path, method, payload) {
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

async function apiDelete(path) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "DELETE",
    credentials: "include",
  });
  const data = await parseResponse(response);
  if (!response.ok) throw new Error(data.detail || "Request failed");
  return data;
}

async function downloadBlob(path, fallbackFilename) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
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

// --- Departments ---------------------------------------------------------

export const fetchDepartments = () => apiGet("/departments/");
export const createDepartment = (payload) => apiSend("/departments/", "POST", payload);
export const updateDepartment = (id, payload) => apiSend(`/departments/${id}`, "PUT", payload);
export const deleteDepartment = (id) => apiDelete(`/departments/${id}`);

// --- Tags ------------------------------------------------------------------

export const fetchTags = () => apiGet("/tags/");
export const createTag = (payload) => apiSend("/tags/", "POST", payload);
export const updateTag = (id, payload) => apiSend(`/tags/${id}`, "PUT", payload);
export const deleteTag = (id) => apiDelete(`/tags/${id}`);
export const fetchClientTags = (clientId) => apiGet(`/tags/clients/${clientId}`);
export const assignTagToClient = (clientId, tagId) =>
  apiSend(`/tags/clients/${clientId}/${tagId}`, "POST");
export const removeTagFromClient = (clientId, tagId) =>
  apiDelete(`/tags/clients/${clientId}/${tagId}`);

// --- Client notes history ---------------------------------------------------

export const fetchClientNotes = (clientId) => apiGet(`/clients/${clientId}/notes`);
export const addClientNote = (clientId, body) =>
  apiSend(`/clients/${clientId}/notes`, "POST", { body });
export const deleteClientNote = (clientId, noteId) =>
  apiDelete(`/clients/${clientId}/notes/${noteId}`);

// --- Bulk client actions ------------------------------------------------------

export const bulkUpdateClientStatus = (clientIds, status) =>
  apiSend("/clients/bulk/status", "POST", { client_ids: clientIds, status });

// --- Tasks -------------------------------------------------------------------

export function fetchTasks(params = {}) {
  const searchParams = new URLSearchParams();
  if (params.status) searchParams.append("status", params.status);
  if (params.client_id) searchParams.append("client_id", params.client_id);
  if (params.assigned_to_me) searchParams.append("assigned_to_me", "true");
  if (params.overdue_only) searchParams.append("overdue_only", "true");
  const qs = searchParams.toString();
  return apiGet(`/tasks/${qs ? `?${qs}` : ""}`);
}
export const createTask = (payload) => apiSend("/tasks/", "POST", payload);
export const updateTask = (taskId, payload) => apiSend(`/tasks/${taskId}`, "PUT", payload);
export const deleteTask = (taskId) => apiDelete(`/tasks/${taskId}`);

// --- Notifications -------------------------------------------------------------

export function fetchNotifications(unreadOnly = false) {
  return apiGet(`/notifications/${unreadOnly ? "?unread_only=true" : ""}`);
}
export const fetchUnreadNotificationCount = () => apiGet("/notifications/unread-count");
export const markNotificationRead = (id) => apiSend(`/notifications/${id}/read`, "PATCH");
export const markAllNotificationsRead = () => apiSend("/notifications/read-all", "PATCH");

// --- Comments / mentions -------------------------------------------------------

export const fetchComments = (entityType, entityId) =>
  apiGet(`/comments/?entity_type=${encodeURIComponent(entityType)}&entity_id=${entityId}`);
export const createComment = (entityType, entityId, body) =>
  apiSend("/comments/", "POST", { entity_type: entityType, entity_id: entityId, body });
export const deleteComment = (commentId) => apiDelete(`/comments/${commentId}`);

// --- Global search --------------------------------------------------------------

export const globalSearch = (query) => apiGet(`/search/?q=${encodeURIComponent(query)}`);

// --- Reports / exports ------------------------------------------------------------

export const exportClientsCsv = () => downloadBlob("/reports/clients/csv", "clients.csv");
export const exportClientsPdf = () => downloadBlob("/reports/clients/pdf", "clients.pdf");
export const exportFilesCsv = () => downloadBlob("/reports/files/csv", "files.csv");
export const exportTasksCsv = () => downloadBlob("/reports/tasks/csv", "tasks.csv");
export const exportActivityLogsCsv = () =>
  downloadBlob("/reports/activity-logs/csv", "activity_logs.csv");

// --- File versioning & bulk file actions ---------------------------------------

export async function uploadFileVersion(file, replacesFileId, clientId = "") {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("replaces_file_id", String(replacesFileId));
  if (clientId) formData.append("client_id", clientId);

  const response = await fetch(`${API_BASE_URL}/files/upload`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  const data = await parseResponse(response);
  if (!response.ok) throw new Error(data.detail || "Failed to upload new version");
  return data;
}

export const fetchFileVersions = (fileId) => apiGet(`/files/${fileId}/versions`);
export const bulkDeleteFiles = (fileIds) => apiSend("/files/bulk/delete", "POST", { file_ids: fileIds });
export async function bulkDownloadFiles(fileIds) {
  const response = await fetch(`${API_BASE_URL}/files/bulk/download`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_ids: fileIds }),
  });

  if (!response.ok) {
    const data = await parseResponse(response);
    throw new Error(data.detail || "Failed to download files");
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "files.zip";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);

  return { success: true };
}

// --- User department assignment --------------------------------------------------

export const updateUserDepartment = (email, departmentId) =>
  apiSend(`/users/${encodeURIComponent(email)}/department`, "PATCH", { department_id: departmentId });

// --- Password reset & email verification -------------------------------------------

export const requestPasswordReset = (email) =>
  apiSend("/auth/request-password-reset", "POST", { email });
export const resetPassword = (token, newPassword) =>
  apiSend("/auth/reset-password", "POST", { token, new_password: newPassword });
export const requestEmailVerification = () => apiSend("/auth/request-verification", "POST");
export const verifyEmail = (token) => apiSend("/auth/verify-email", "POST", { token });
