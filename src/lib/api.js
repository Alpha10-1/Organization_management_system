// IMPORTANT: this must use the same hostname the frontend itself is loaded
// from (localhost vs 127.0.0.1). Browsers treat those as different sites,
// so a mismatch here means the login cookie (SameSite=Lax) gets set but
// never sent back on later requests -- every call after login 401s even
// though login itself succeeded. Override via NEXT_PUBLIC_API_URL in
// .env.local if your backend runs somewhere else.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
export const fetchDepartmentDashboard = (id) => apiGet(`/departments/${id}/dashboard`);

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

// --- Staff positions & manager hierarchy -------------------------------------------

export const updateUserPosition = (email, payload) =>
  apiSend(`/users/${encodeURIComponent(email)}/position`, "PATCH", payload);
export const fetchOrgChart = () => apiGet("/users/org-chart");
export const fetchDepartmentDetail = (id) => apiGet(`/departments/${id}`);

// --- Password reset & email verification -------------------------------------------

export const requestPasswordReset = (email) =>
  apiSend("/auth/request-password-reset", "POST", { email });
export const resetPassword = (token, newPassword) =>
  apiSend("/auth/reset-password", "POST", { token, new_password: newPassword });
export const requestEmailVerification = () => apiSend("/auth/request-verification", "POST");
export const verifyEmail = (token) => apiSend("/auth/verify-email", "POST", { token });

// --- Projects / Engagements ------------------------------------------------------

export function fetchProjects(params = {}) {
  const searchParams = new URLSearchParams();
  if (params.client_id) searchParams.append("client_id", params.client_id);
  if (params.status) searchParams.append("status", params.status);
  if (params.type) searchParams.append("type", params.type);
  if (params.risk_level) searchParams.append("risk_level", params.risk_level);
  if (params.engagement_partner_email) {
    searchParams.append("engagement_partner_email", params.engagement_partner_email);
  }
  const qs = searchParams.toString();
  return apiGet(`/projects/${qs ? `?${qs}` : ""}`);
}
export const fetchProject = (id) => apiGet(`/projects/${id}`);
export const createProject = (payload) => apiSend("/projects/", "POST", payload);
export const updateProject = (id, payload) => apiSend(`/projects/${id}`, "PUT", payload);
export const deleteProject = (id) => apiDelete(`/projects/${id}`);
export const fetchProjectBudgetBurn = (id, alertThresholdPercent) =>
  apiGet(`/projects/${id}/budget${alertThresholdPercent != null ? `?alert_threshold_percent=${alertThresholdPercent}` : ""}`);
export const fetchProjectHealth = (id) => apiGet(`/projects/${id}/health`);
export const cloneProject = (id, payload) => apiSend(`/projects/${id}/clone`, "POST", payload);

// --- Project team assignment (individuals or whole departments) -------------------

export const fetchProjectAssignments = (projectId) => apiGet(`/projects/${projectId}/assignments`);
export const createProjectAssignment = (projectId, payload) =>
  apiSend(`/projects/${projectId}/assignments`, "POST", payload);
export const updateProjectAssignment = (projectId, assignmentId, payload) =>
  apiSend(`/projects/${projectId}/assignments/${assignmentId}`, "PUT", payload);
export const deleteProjectAssignment = (projectId, assignmentId) =>
  apiDelete(`/projects/${projectId}/assignments/${assignmentId}`);
export const fetchCapacityDashboard = () => apiGet("/reports/dashboard/capacity");

// --- Client contacts & hierarchy --------------------------------------------------

export const fetchClientContacts = (clientId) => apiGet(`/clients/${clientId}/contacts`);
export const createClientContact = (clientId, payload) =>
  apiSend(`/clients/${clientId}/contacts`, "POST", payload);
export const updateClientContact = (clientId, contactId, payload) =>
  apiSend(`/clients/${clientId}/contacts/${contactId}`, "PUT", payload);
export const deleteClientContact = (clientId, contactId) =>
  apiDelete(`/clients/${clientId}/contacts/${contactId}`);
export const fetchClientHealth = (clientId) => apiGet(`/clients/${clientId}/health`);

// --- Contracts / SOWs ---------------------------------------------------------------

export function fetchContracts(params = {}) {
  const searchParams = new URLSearchParams();
  if (params.project_id) searchParams.append("project_id", params.project_id);
  if (params.status) searchParams.append("status", params.status);
  if (params.billing_type) searchParams.append("billing_type", params.billing_type);
  const qs = searchParams.toString();
  return apiGet(`/contracts/${qs ? `?${qs}` : ""}`);
}
export const createContract = (payload) => apiSend("/contracts/", "POST", payload);
export const updateContract = (id, payload) => apiSend(`/contracts/${id}`, "PUT", payload);
export const deleteContract = (id) => apiDelete(`/contracts/${id}`);
export const fetchContractMargin = (id) => apiGet(`/contracts/${id}/margin`);

// --- Change orders (contract scope/fee changes) --------------------------------------

export function fetchChangeOrders(params = {}) {
  const searchParams = new URLSearchParams();
  if (params.project_id) searchParams.append("project_id", params.project_id);
  if (params.contract_id) searchParams.append("contract_id", params.contract_id);
  if (params.status) searchParams.append("status", params.status);
  const qs = searchParams.toString();
  return apiGet(`/change-orders/${qs ? `?${qs}` : ""}`);
}
export const createChangeOrder = (payload) => apiSend("/change-orders/", "POST", payload);
export const updateChangeOrder = (id, payload) => apiSend(`/change-orders/${id}`, "PUT", payload);
export const approveChangeOrder = (id, payload = {}) =>
  apiSend(`/change-orders/${id}/approve`, "POST", payload);
export const rejectChangeOrder = (id, payload = {}) =>
  apiSend(`/change-orders/${id}/reject`, "POST", payload);
export const deleteChangeOrder = (id) => apiDelete(`/change-orders/${id}`);

// --- Milestones ----------------------------------------------------------------------

export function fetchMilestones(params = {}) {
  const searchParams = new URLSearchParams();
  if (params.project_id) searchParams.append("project_id", params.project_id);
  if (params.status) searchParams.append("status", params.status);
  const qs = searchParams.toString();
  return apiGet(`/milestones/${qs ? `?${qs}` : ""}`);
}
export const createMilestone = (payload) => apiSend("/milestones/", "POST", payload);
export const updateMilestone = (id, payload) => apiSend(`/milestones/${id}`, "PUT", payload);
export const deleteMilestone = (id) => apiDelete(`/milestones/${id}`);
export const signoffMilestone = (id, payload) => apiSend(`/milestones/${id}/signoff`, "PUT", payload);

// --- Task templates ------------------------------------------------------------------

export const fetchTaskTemplates = () => apiGet("/task-templates/");
export const createTaskTemplate = (payload) => apiSend("/task-templates/", "POST", payload);
export const updateTaskTemplate = (id, payload) => apiSend(`/task-templates/${id}`, "PUT", payload);
export const deleteTaskTemplate = (id) => apiDelete(`/task-templates/${id}`);
export const applyTaskTemplate = (id, payload) =>
  apiSend(`/task-templates/${id}/apply`, "POST", payload);
export const applyTaskTemplateToUser = (id, payload) =>
  apiSend(`/task-templates/${id}/apply-to-user`, "POST", payload);

// --- Skills & certifications matrix ---------------------------------------------------

export function fetchSkills(params = {}) {
  const searchParams = new URLSearchParams();
  if (params.user_id) searchParams.append("user_id", params.user_id);
  if (params.category) searchParams.append("category", params.category);
  if (params.name) searchParams.append("name", params.name);
  if (params.expiring_within_days != null) {
    searchParams.append("expiring_within_days", params.expiring_within_days);
  }
  const qs = searchParams.toString();
  return apiGet(`/skills/${qs ? `?${qs}` : ""}`);
}
export function fetchSkillsMatrix(params = {}) {
  const searchParams = new URLSearchParams();
  if (params.department_id) searchParams.append("department_id", params.department_id);
  if (params.name) searchParams.append("name", params.name);
  const qs = searchParams.toString();
  return apiGet(`/skills/matrix${qs ? `?${qs}` : ""}`);
}
export const createSkill = (payload) => apiSend("/skills/", "POST", payload);
export const updateSkill = (id, payload) => apiSend(`/skills/${id}`, "PUT", payload);
export const deleteSkill = (id) => apiDelete(`/skills/${id}`);

// --- Cross-department resource requests -----------------------------------------------

export function fetchResourceRequests(params = {}) {
  const searchParams = new URLSearchParams();
  if (params.requesting_department_id) {
    searchParams.append("requesting_department_id", params.requesting_department_id);
  }
  if (params.providing_department_id) {
    searchParams.append("providing_department_id", params.providing_department_id);
  }
  if (params.project_id) searchParams.append("project_id", params.project_id);
  if (params.status) searchParams.append("status", params.status);
  const qs = searchParams.toString();
  return apiGet(`/resource-requests/${qs ? `?${qs}` : ""}`);
}
export const createResourceRequest = (payload) => apiSend("/resource-requests/", "POST", payload);
export const approveResourceRequest = (id, payload = {}) =>
  apiSend(`/resource-requests/${id}/approve`, "POST", payload);
export const rejectResourceRequest = (id, payload = {}) =>
  apiSend(`/resource-requests/${id}/reject`, "POST", payload);
export const cancelResourceRequest = (id) => apiDelete(`/resource-requests/${id}`);

// --- Leave / PTO requests ---------------------------------------------------------------

export function fetchLeaveRequests(params = {}) {
  const searchParams = new URLSearchParams();
  if (params.user_id) searchParams.append("user_id", params.user_id);
  if (params.approver_user_id) searchParams.append("approver_user_id", params.approver_user_id);
  if (params.status) searchParams.append("status", params.status);
  const qs = searchParams.toString();
  return apiGet(`/leave-requests/${qs ? `?${qs}` : ""}`);
}
export const createLeaveRequest = (payload) => apiSend("/leave-requests/", "POST", payload);
export const approveLeaveRequest = (id, payload = {}) =>
  apiSend(`/leave-requests/${id}/approve`, "POST", payload);
export const rejectLeaveRequest = (id, payload = {}) =>
  apiSend(`/leave-requests/${id}/reject`, "POST", payload);
export const cancelLeaveRequest = (id) => apiDelete(`/leave-requests/${id}`);

// --- Engagement audit trail ------------------------------------------------------------

export const fetchProjectHistory = (projectId) => apiGet(`/projects/${projectId}/history`);

// --- Task detail, subtasks & dependencies ---------------------------------------------

export const fetchTaskDetail = (taskId) => apiGet(`/tasks/${taskId}/detail`);
export const fetchTaskDependencies = (taskId) => apiGet(`/tasks/${taskId}/dependencies`);
export const addTaskDependency = (taskId, dependsOnTaskId) =>
  apiSend(`/tasks/${taskId}/dependencies`, "POST", { depends_on_task_id: dependsOnTaskId });
export const deleteTaskDependency = (taskId, dependencyId) =>
  apiDelete(`/tasks/${taskId}/dependencies/${dependencyId}`);

// --- Time tracking ---------------------------------------------------------------------

export function fetchTimeEntries(params = {}) {
  const searchParams = new URLSearchParams();
  if (params.project_id) searchParams.append("project_id", params.project_id);
  if (params.task_id) searchParams.append("task_id", params.task_id);
  if (params.user_email) searchParams.append("user_email", params.user_email);
  if (params.billable !== undefined) searchParams.append("billable", String(params.billable));
  if (params.date_from) searchParams.append("date_from", params.date_from);
  if (params.date_to) searchParams.append("date_to", params.date_to);
  const qs = searchParams.toString();
  return apiGet(`/time-entries/${qs ? `?${qs}` : ""}`);
}
export const createTimeEntry = (payload) => apiSend("/time-entries/", "POST", payload);
export const updateTimeEntry = (id, payload) => apiSend(`/time-entries/${id}`, "PUT", payload);
export const deleteTimeEntry = (id) => apiDelete(`/time-entries/${id}`);
export const fetchProjectUtilization = (projectId) =>
  apiGet(`/time-entries/summary?project_id=${projectId}`);

// --- Dashboards --------------------------------------------------------------------------

export const fetchPartnerDashboard = (partnerEmail) =>
  apiGet(`/reports/dashboard/partner?partner_email=${encodeURIComponent(partnerEmail)}`);
export const fetchClientDashboard = (clientId) => apiGet(`/reports/dashboard/client/${clientId}`);
export const fetchComplianceDashboard = () => apiGet("/reports/dashboard/compliance");
