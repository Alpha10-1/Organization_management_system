const API_BASE_URL = "http://127.0.0.1:8000";

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return await response.json();
  }

  const text = await response.text();
  return { detail: text || "Unexpected server response" };
}

export async function updateClient(token, clientId, payload) {
  const response = await fetch(`${API_BASE_URL}/clients/${clientId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to update client");
  }

  return data;
}

export async function fetchActivityLogs(token) {
  const response = await fetch(`${API_BASE_URL}/activity-logs`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
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

export async function fetchCurrentUser(token) {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to fetch user");
  }

  return data;
}

export async function fetchDashboardSummary(token) {
  const response = await fetch(`${API_BASE_URL}/dashboard-summary`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to fetch dashboard");
  }

  return data;
}

export async function fetchClients(token, params = {}) {
  const searchParams = new URLSearchParams();

  if (params.search) searchParams.append("search", params.search);
  if (params.status && params.status !== "All") {
    searchParams.append("status", params.status);
  }

  const queryString = searchParams.toString();
  const url = `${API_BASE_URL}/clients/${queryString ? `?${queryString}` : ""}`;

  const response = await fetch(url, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to fetch clients");
  }

  return data;
}

export async function createClient(token, payload) {
  const response = await fetch(`${API_BASE_URL}/clients/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to create client");
  }

  return data;
}

export async function fetchUsers(token) {
  const response = await fetch(`${API_BASE_URL}/users/`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to fetch users");
  }

  return data;
}

export async function createUser(token, payload) {
  const response = await fetch(`${API_BASE_URL}/users/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to create user");
  }

  return data;
}

export async function updateUserRole(token, email, role) {
  const response = await fetch(`${API_BASE_URL}/users/${encodeURIComponent(email)}/role`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ role }),
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to update user role");
  }

  return data;
}

export async function updateUserStatus(token, email, disabled) {
  const response = await fetch(`${API_BASE_URL}/users/${encodeURIComponent(email)}/status`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ disabled }),
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to update user status");
  }

  return data;
}

export async function fetchFiles(token, params = {}) {
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
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to fetch files");
  }

  return data;
}


export async function uploadFile(token, file, clientId = "") {
  const formData = new FormData();
  formData.append("file", file);

  if (clientId) {
    formData.append("client_id", clientId);
  }

  const response = await fetch(`${API_BASE_URL}/files/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to upload file");
  }

  return data;
}

export async function deleteFileRecord(token, fileId) {
  const response = await fetch(`${API_BASE_URL}/files/${fileId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to delete file");
  }

  return data;
}

export async function deleteClient(token, clientId) {
  const response = await fetch(`${API_BASE_URL}/clients/${clientId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to delete client");
  }

  return data;
}

export async function fetchFileRecord(token, fileId) {
  const response = await fetch(`${API_BASE_URL}/files/${fileId}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to fetch file details");
  }

  return data;
}

export async function downloadFileAuthenticated(token, fileId) {
  const response = await fetch(`${API_BASE_URL}/files/${fileId}/download`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
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

export async function getAuthenticatedFileBlobUrl(token, fileId) {
  const response = await fetch(`${API_BASE_URL}/files/${fileId}/download`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
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