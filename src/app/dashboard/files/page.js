"use client";

import { useEffect, useState } from "react";
import { getToken } from "@/lib/auth";
import {
  deleteFileRecord,
  downloadFileAuthenticated,
  fetchClients,
  fetchFiles,
  getAuthenticatedFileBlobUrl,
  uploadFile,
} from "@/lib/api";

function formatFileSize(bytes) {
  if (!bytes && bytes !== 0) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateString) {
  return new Date(dateString).toLocaleString();
}

export default function FilesPage() {
  const [previewUrl, setPreviewUrl] = useState("");
  const [previewType, setPreviewType] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [files, setFiles] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [fileInput, setFileInput] = useState(null);
  const [clientId, setClientId] = useState("");

  const [search, setSearch] = useState("");
  const [fileTypeFilter, setFileTypeFilter] = useState("All");
  const [clientFilter, setClientFilter] = useState("");
  const [mineOnly, setMineOnly] = useState(false);

  async function handleDownload(fileId) {
    try {
      setError("");
      const token = getToken();
      await downloadFileAuthenticated(token, fileId);
    } catch (err) {
      setError(err.message || "Failed to download file");
    }
  }

  async function loadData(overrides = {}) {
    try {
      setLoading(true);
      setError("");
      const token = getToken();

      const effectiveSearch = overrides.search ?? search;
      const effectiveFileType = overrides.fileTypeFilter ?? fileTypeFilter;
      const effectiveClientFilter = overrides.clientFilter ?? clientFilter;
      const effectiveMineOnly = overrides.mineOnly ?? mineOnly;

      const [filesData, clientsData] = await Promise.all([
        fetchFiles(token, {
          search: effectiveSearch,
          file_type: effectiveFileType,
          client_id: effectiveClientFilter,
          mine_only: effectiveMineOnly,
        }),
        fetchClients(token),
      ]);

      setFiles(filesData);
      setClients(clientsData);
    } catch (err) {
      setError(err.message || "Failed to load files");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    return () => {
      if (previewUrl) {
        window.URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  useEffect(() => {
    loadData();
  }, []);

  async function handleUpload(e) {
    e.preventDefault();

    if (!fileInput) {
      setError("Please choose a file first.");
      return;
    }

    try {
      setUploading(true);
      setError("");

      const token = getToken();
      await uploadFile(token, fileInput, clientId);

      setFileInput(null);
      setClientId("");
      setShowUploadModal(false);
      await loadData();
    } catch (err) {
      setError(err.message || "Failed to upload file");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(fileId) {
    const confirmed = window.confirm("Delete this file?");
    if (!confirmed) return;

    try {
      setError("");
      const token = getToken();
      await deleteFileRecord(token, fileId);

      if (selectedFile?.id === fileId) {
        setSelectedFile(null);
      }

      await loadData();
    } catch (err) {
      setError(err.message || "Failed to delete file");
    }
  }

  function handleFilterSubmit(e) {
    e.preventDefault();
    loadData();
  }

  function isImageFile(fileType = "") {
    return fileType.startsWith("image/");
  }

  function isPdfFile(fileType = "") {
    return fileType === "application/pdf";
  }

  async function handlePreview(file) {
    try {
      setError("");
      setSelectedFile(file);
      setPreviewLoading(true);

      if (previewUrl) {
        window.URL.revokeObjectURL(previewUrl);
        setPreviewUrl("");
      }

      if (!isImageFile(file.file_type || "") && !isPdfFile(file.file_type || "")) {
        setPreviewType("");
        return;
      }

      const token = getToken();
      const result = await getAuthenticatedFileBlobUrl(token, file.id);

      setPreviewUrl(result.blobUrl);
      setPreviewType(result.contentType || file.file_type || "");
    } catch (err) {
      setError(err.message || "Failed to preview file");
      setPreviewUrl("");
      setPreviewType("");
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handleDownload(fileId) {
    try {
      setError("");
      const token = getToken();
      await downloadFileAuthenticated(token, fileId);
    } catch (err) {
      setError(err.message || "Failed to download file");
    }
  }

  function clearFilters() {
    setSearch("");
    setFileTypeFilter("All");
    setClientFilter("");
    setMineOnly(false);

    loadData({
      search: "",
      fileTypeFilter: "All",
      clientFilter: "",
      mineOnly: false,
    });
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm md:flex-row md:items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Files</h1>
          <p className="mt-1 text-sm text-slate-500">
            Securely manage uploaded documents and file records.
          </p>
          <p className="mt-2 text-xs font-medium text-slate-400">
            {loading ? "Loading files..." : `${files.length} file${files.length === 1 ? "" : "s"} found`}
          </p>
        </div>

        <button
          onClick={() => setShowUploadModal(true)}
          className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800"
        >
          Upload File
        </button>
      </div>

      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      ) : null}

      <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <form
          onSubmit={handleFilterSubmit}
          className="grid gap-3 lg:grid-cols-5"
        >
          <input
            type="text"
            placeholder="Search files..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
          />

          <select
            value={fileTypeFilter}
            onChange={(e) => setFileTypeFilter(e.target.value)}
            className="rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
          >
            <option>All</option>
            <option>application/pdf</option>
            <option>image/png</option>
            <option>image/jpeg</option>
            <option>application/vnd.openxmlformats-officedocument.wordprocessingml.document</option>
          </select>

          <select
            value={clientFilter}
            onChange={(e) => setClientFilter(e.target.value)}
            className="rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
          >
            <option value="">All Clients</option>
            {clients.map((client) => (
              <option key={client.id} value={client.id}>
                {client.first_name} {client.last_name}
              </option>
            ))}
          </select>

          <label className="flex items-center gap-3 rounded-2xl border border-slate-300 px-4 py-3 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={mineOnly}
              onChange={(e) => setMineOnly(e.target.checked)}
            />
            My uploads only
          </label>

          <div className="flex gap-3">
            <button
              type="submit"
              className="rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
            >
              Search
            </button>
            <button
              type="button"
              onClick={clearFilters}
              className="rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
            >
              Clear
            </button>
          </div>
        </form>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.4fr_0.9fr]">
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] border-separate border-spacing-y-3">
              <thead>
                <tr className="text-left text-sm text-slate-500">
                  <th className="pb-2">File Name</th>
                  <th className="pb-2">Type</th>
                  <th className="pb-2">Size</th>
                  <th className="pb-2">Client ID</th>
                  <th className="pb-2">Uploaded By</th>
                  <th className="pb-2">Action</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-sm text-slate-500">
                      Loading files...
                    </td>
                  </tr>
                ) : files.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-sm text-slate-500">
                      No files found.
                    </td>
                  </tr>
                ) : (
                  files.map((file) => (
                    <tr key={file.id} className="bg-slate-50">
                      <td className="rounded-l-2xl px-4 py-4 font-medium text-slate-900">
                        {file.original_name}
                      </td>
                      <td className="px-4 py-4 text-slate-700">
                        {file.file_type || "-"}
                      </td>
                      <td className="px-4 py-4 text-slate-700">
                        {formatFileSize(file.file_size)}
                      </td>
                      <td className="px-4 py-4 text-slate-700">
                        {file.client_id ?? "-"}
                      </td>
                      <td className="px-4 py-4 text-slate-700">
                        {file.uploaded_by_name}
                      </td>
                      <td className="rounded-r-2xl px-4 py-4">
                        <div className="flex gap-4">
                          <button
                            onClick={() => handlePreview(file)}
                            className="text-sm font-semibold text-slate-900 hover:underline"
                          >
                            View
                          </button>
                          <button
                            onClick={() => handleDownload(file.id)}
                            className="text-sm font-semibold text-blue-600 hover:underline"
                          >
                            Download
                          </button>
                          <button
                            onClick={() => handleDelete(file.id)}
                            className="text-sm font-semibold text-red-600 hover:underline"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">File Details</h2>

          {selectedFile ? (
            <div className="mt-4 space-y-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Original Name
                </p>
                <p className="mt-1 text-sm text-slate-800">{selectedFile.original_name}</p>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Type
                </p>
                <p className="mt-1 text-sm text-slate-800">{selectedFile.file_type || "-"}</p>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Size
                </p>
                <p className="mt-1 text-sm text-slate-800">
                  {formatFileSize(selectedFile.file_size)}
                </p>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Linked Client ID
                </p>
                <p className="mt-1 text-sm text-slate-800">{selectedFile.client_id ?? "-"}</p>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Uploaded By
                </p>
                <p className="mt-1 text-sm text-slate-800">
                  {selectedFile.uploaded_by_name}
                </p>
                <p className="mt-1 text-sm text-slate-500">
                  {selectedFile.uploaded_by_email}
                </p>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Uploaded At
                </p>
                <p className="mt-1 text-sm text-slate-800">
                  {formatDate(selectedFile.created_at)}
                </p>
              </div>

              <div className="pt-2">
                <button
                  onClick={() => handleDownload(selectedFile.id)}
                  className="inline-flex rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Download File
                </button>
              </div>

              <div className="pt-2">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Preview
                </p>

                {previewLoading ? (
                  <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500">
                    Loading preview...
                  </div>
                ) : isImageFile(previewType) && previewUrl ? (
                  <div className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
                    <img
                      src={previewUrl}
                      alt={selectedFile.original_name}
                      className="h-auto w-full object-contain"
                    />
                  </div>
                ) : isPdfFile(previewType) && previewUrl ? (
                  <div className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
                    <iframe
                      src={previewUrl}
                      title={selectedFile.original_name}
                      className="h-[500px] w-full"
                    />
                  </div>
                ) : (
                  <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500">
                    Preview not available for this file type.
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="mt-4 rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500">
              Select a file from the table to view details.
            </div>
          )}
        </div>
      </div>

      {showUploadModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="w-full max-w-2xl rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-6 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold text-slate-900">Upload File</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Upload a document and optionally link it to a client.
                </p>
              </div>

              <button
                onClick={() => setShowUploadModal(false)}
                className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
              >
                Close
              </button>
            </div>

            <form onSubmit={handleUpload} className="space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Select File
                </label>
                <input
                  type="file"
                  onChange={(e) => setFileInput(e.target.files?.[0] || null)}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  required
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Link to Client
                </label>
                <select
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                >
                  <option value="">No linked client</option>
                  {clients.map((client) => (
                    <option key={client.id} value={client.id}>
                      {client.first_name} {client.last_name} (ID: {client.id})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={uploading}
                  className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-70"
                >
                  {uploading ? "Uploading..." : "Upload File"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}