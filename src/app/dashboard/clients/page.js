"use client";

import { useEffect, useMemo, useState } from "react";
import {
  createClient,
  deleteClient,
  fetchClients,
  updateClient,
  fetchDepartments,
  fetchTags,
  fetchClientTags,
  assignTagToClient,
  removeTagFromClient,
  fetchClientNotes,
  addClientNote,
  deleteClientNote,
  bulkUpdateClientStatus,
} from "@/lib/api";

const initialForm = {
  first_name: "",
  last_name: "",
  phone: "",
  email: "",
  status: "Active",
  notes: "",
  department_id: "",
};

export default function ClientsPage() {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [showModal, setShowModal] = useState(false);
  const [selectedClient, setSelectedClient] = useState(null);
  const [editingClient, setEditingClient] = useState(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState(initialForm);

  const [departments, setDepartments] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [bulkStatus, setBulkStatus] = useState("Active");
  const [bulkSaving, setBulkSaving] = useState(false);

  const [availableTags, setAvailableTags] = useState([]);
  const [clientTags, setClientTags] = useState([]);
  const [tagToAdd, setTagToAdd] = useState("");

  const [notes, setNotes] = useState([]);
  const [newNote, setNewNote] = useState("");
  const [notesLoading, setNotesLoading] = useState(false);

  async function loadClients(currentSearch = search, currentStatus = statusFilter) {
    try {
      setLoading(true);
      setError("");

      const data = await fetchClients({
        search: currentSearch,
        status: currentStatus,
      });

      setClients(data);
    } catch (err) {
      setError(err.message || "Failed to load clients");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadClients();
    fetchDepartments().then(setDepartments).catch(() => setDepartments([]));
    fetchTags().then(setAvailableTags).catch(() => setAvailableTags([]));
  }, []);

  useEffect(() => {
    if (!selectedClient) {
      setClientTags([]);
      setNotes([]);
      return;
    }

    fetchClientTags(selectedClient.id).then(setClientTags).catch(() => setClientTags([]));

    setNotesLoading(true);
    fetchClientNotes(selectedClient.id)
      .then(setNotes)
      .catch(() => setNotes([]))
      .finally(() => setNotesLoading(false));
  }, [selectedClient]);

  function toggleSelected(clientId) {
    setSelectedIds((prev) =>
      prev.includes(clientId) ? prev.filter((id) => id !== clientId) : [...prev, clientId]
    );
  }

  function toggleSelectAll() {
    if (selectedIds.length === clients.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(clients.map((c) => c.id));
    }
  }

  async function handleBulkStatusUpdate() {
    if (selectedIds.length === 0) return;
    try {
      setBulkSaving(true);
      setError("");
      await bulkUpdateClientStatus(selectedIds, bulkStatus);
      setSelectedIds([]);
      await loadClients();
    } catch (err) {
      setError(err.message || "Failed to bulk update clients");
    } finally {
      setBulkSaving(false);
    }
  }

  async function handleAddTag() {
    if (!tagToAdd || !selectedClient) return;
    try {
      setError("");
      await assignTagToClient(selectedClient.id, Number(tagToAdd));
      const updated = await fetchClientTags(selectedClient.id);
      setClientTags(updated);
      setTagToAdd("");
    } catch (err) {
      setError(err.message || "Failed to add tag");
    }
  }

  async function handleRemoveTag(tagId) {
    if (!selectedClient) return;
    try {
      setError("");
      await removeTagFromClient(selectedClient.id, tagId);
      setClientTags((prev) => prev.filter((t) => t.id !== tagId));
    } catch (err) {
      setError(err.message || "Failed to remove tag");
    }
  }

  async function handleAddNote(e) {
    e.preventDefault();
    if (!newNote.trim() || !selectedClient) return;
    try {
      setError("");
      const created = await addClientNote(selectedClient.id, newNote.trim());
      setNotes((prev) => [created, ...prev]);
      setNewNote("");
    } catch (err) {
      setError(err.message || "Failed to add note");
    }
  }

  async function handleDeleteNote(noteId) {
    if (!selectedClient) return;
    try {
      setError("");
      await deleteClientNote(selectedClient.id, noteId);
      setNotes((prev) => prev.filter((n) => n.id !== noteId));
    } catch (err) {
      setError(err.message || "Failed to delete note");
    }
  }

  function handleSearchSubmit(e) {
    e.preventDefault();
    loadClients(search, statusFilter);
  }

  function handleStatusChange(e) {
    const value = e.target.value;
    setStatusFilter(value);
    loadClients(search, value);
  }

  function handleInputChange(e) {
    setForm((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  }

  function openCreateModal() {
    setEditingClient(null);
    setForm(initialForm);
    setShowModal(true);
  }

  function openEditModal(client) {
    setEditingClient(client);
    setForm({
      first_name: client.first_name || "",
      last_name: client.last_name || "",
      phone: client.phone || "",
      email: client.email || "",
      status: client.status || "Active",
      notes: client.notes || "",
      department_id: client.department_id ?? "",
    });
    setShowModal(true);
  }

  function closeModal() {
    setShowModal(false);
    setEditingClient(null);
    setForm(initialForm);
  }

  async function handleSaveClient(e) {
    e.preventDefault();

    try {
      setSubmitting(true);
      setError("");

      const payload = {
        ...form,
        department_id: form.department_id ? Number(form.department_id) : null,
      };

      if (editingClient) {
        const updated = await updateClient(editingClient.id, payload);

        if (selectedClient?.id === editingClient.id) {
          setSelectedClient(updated);
        }
      } else {
        await createClient(payload);
      }

      closeModal();
      await loadClients();
    } catch (err) {
      setError(err.message || "Failed to save client");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeleteClient(clientId) {
    const confirmed = window.confirm("Are you sure you want to delete this client?");
    if (!confirmed) return;

    try {
      setError("");
      await deleteClient(clientId);

      if (selectedClient?.id === clientId) {
        setSelectedClient(null);
      }

      await loadClients();
    } catch (err) {
      setError(err.message || "Failed to delete client");
    }
  }

  const clientCountText = useMemo(() => {
    if (loading) return "Loading clients...";
    return `${clients.length} client${clients.length === 1 ? "" : "s"} found`;
  }, [clients, loading]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm md:flex-row md:items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Clients</h1>
          <p className="mt-1 text-sm text-slate-500">
            Track, review, and manage client records.
          </p>
          <p className="mt-2 text-xs font-medium text-slate-400">{clientCountText}</p>
        </div>

        <button
          onClick={openCreateModal}
          className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800"
        >
          Add Client
        </button>
      </div>

      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[1.4fr_0.9fr]">
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <form
            onSubmit={handleSearchSubmit}
            className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between"
          >
            <input
              type="text"
              placeholder="Search clients..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full max-w-sm rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
            />

            <div className="flex gap-3">
              <select
                value={statusFilter}
                onChange={handleStatusChange}
                className="rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
              >
                <option>All</option>
                <option>Active</option>
                <option>Pending</option>
                <option>Closed</option>
              </select>

              <button
                type="submit"
                className="rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
              >
                Search
              </button>
            </div>
          </form>

          {selectedIds.length > 0 ? (
            <div className="mb-4 flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <span className="text-sm font-semibold text-slate-700">
                {selectedIds.length} selected
              </span>
              <select
                value={bulkStatus}
                onChange={(e) => setBulkStatus(e.target.value)}
                className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
              >
                <option>Active</option>
                <option>Pending</option>
                <option>Closed</option>
              </select>
              <button
                onClick={handleBulkStatusUpdate}
                disabled={bulkSaving}
                className="rounded-xl bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-70"
              >
                {bulkSaving ? "Updating..." : "Set Status"}
              </button>
              <button
                onClick={() => setSelectedIds([])}
                className="text-sm font-semibold text-slate-500 hover:underline"
              >
                Clear
              </button>
            </div>
          ) : null}

          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] border-separate border-spacing-y-3">
              <thead>
                <tr className="text-left text-sm text-slate-500">
                  <th className="pb-2">
                    <input
                      type="checkbox"
                      checked={clients.length > 0 && selectedIds.length === clients.length}
                      onChange={toggleSelectAll}
                    />
                  </th>
                  <th className="pb-2">Name</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2">Phone</th>
                  <th className="pb-2">Email</th>
                  <th className="pb-2">Action</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-sm text-slate-500">
                      Loading clients...
                    </td>
                  </tr>
                ) : clients.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-sm text-slate-500">
                      No clients found.
                    </td>
                  </tr>
                ) : (
                  clients.map((client) => (
                    <tr key={client.id} className="bg-slate-50">
                      <td className="rounded-l-2xl px-4 py-4">
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(client.id)}
                          onChange={() => toggleSelected(client.id)}
                        />
                      </td>
                      <td className="px-4 py-4 font-medium text-slate-900">
                        {client.first_name} {client.last_name}
                      </td>
                      <td className="px-4 py-4">
                        <span className="rounded-full bg-slate-200 px-3 py-1 text-xs font-semibold text-slate-700">
                          {client.status}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-slate-700">{client.phone || "-"}</td>
                      <td className="px-4 py-4 text-slate-700">{client.email || "-"}</td>
                      <td className="rounded-r-2xl px-4 py-4">
                        <div className="flex gap-4">
                          <button
                            onClick={() => setSelectedClient(client)}
                            className="text-sm font-semibold text-slate-900 hover:underline"
                          >
                            View
                          </button>
                          <button
                            onClick={() => openEditModal(client)}
                            className="text-sm font-semibold text-blue-600 hover:underline"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDeleteClient(client.id)}
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
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-slate-900">Client Details</h2>

            {selectedClient ? (
              <button
                onClick={() => openEditModal(selectedClient)}
                className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
              >
                Edit Client
              </button>
            ) : null}
          </div>

          {selectedClient ? (
            <div className="mt-4 space-y-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Full Name
                </p>
                <p className="mt-1 text-sm text-slate-800">
                  {selectedClient.first_name} {selectedClient.last_name}
                </p>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Status
                </p>
                <p className="mt-1 text-sm text-slate-800">{selectedClient.status}</p>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Phone
                </p>
                <p className="mt-1 text-sm text-slate-800">{selectedClient.phone || "-"}</p>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Email
                </p>
                <p className="mt-1 text-sm text-slate-800">{selectedClient.email || "-"}</p>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Notes
                </p>
                <p className="mt-1 whitespace-pre-wrap text-sm text-slate-800">
                  {selectedClient.notes || "No notes added."}
                </p>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Tags
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {clientTags.length === 0 ? (
                    <span className="text-sm text-slate-400">No tags yet.</span>
                  ) : (
                    clientTags.map((tag) => (
                      <span
                        key={tag.id}
                        style={{ backgroundColor: `${tag.color}22`, color: tag.color }}
                        className="flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold"
                      >
                        {tag.name}
                        <button
                          onClick={() => handleRemoveTag(tag.id)}
                          className="ml-1 text-xs opacity-70 hover:opacity-100"
                          aria-label={`Remove ${tag.name}`}
                        >
                          ×
                        </button>
                      </span>
                    ))
                  )}
                </div>
                <div className="mt-2 flex gap-2">
                  <select
                    value={tagToAdd}
                    onChange={(e) => setTagToAdd(e.target.value)}
                    className="flex-1 rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
                  >
                    <option value="">Add a tag...</option>
                    {availableTags
                      .filter((t) => !clientTags.some((ct) => ct.id === t.id))
                      .map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                  </select>
                  <button
                    onClick={handleAddTag}
                    disabled={!tagToAdd}
                    className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-50"
                  >
                    Add
                  </button>
                </div>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Notes History
                </p>
                <form onSubmit={handleAddNote} className="mt-2 flex gap-2">
                  <input
                    type="text"
                    value={newNote}
                    onChange={(e) => setNewNote(e.target.value)}
                    placeholder="Add a dated note..."
                    className="flex-1 rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
                  />
                  <button
                    type="submit"
                    className="rounded-xl bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-800"
                  >
                    Add
                  </button>
                </form>

                <div className="mt-3 max-h-64 space-y-3 overflow-y-auto">
                  {notesLoading ? (
                    <p className="text-sm text-slate-400">Loading notes...</p>
                  ) : notes.length === 0 ? (
                    <p className="text-sm text-slate-400">No note history yet.</p>
                  ) : (
                    notes.map((note) => (
                      <div key={note.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm text-slate-800">{note.body}</p>
                          <button
                            onClick={() => handleDeleteNote(note.id)}
                            className="shrink-0 text-xs font-semibold text-rose-500 hover:underline"
                          >
                            Delete
                          </button>
                        </div>
                        <p className="mt-1 text-xs text-slate-400">
                          {note.author_name} · {new Date(note.created_at).toLocaleString()}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-4 rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500">
              Select a client from the table to view details.
            </div>
          )}
        </div>
      </div>

      {showModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="w-full max-w-2xl rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-6 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold text-slate-900">
                  {editingClient ? "Edit Client" : "Add Client"}
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  {editingClient
                    ? "Update this client record."
                    : "Create a new client record."}
                </p>
              </div>

              <button
                onClick={closeModal}
                className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
              >
                Close
              </button>
            </div>

            <form onSubmit={handleSaveClient} className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  First Name
                </label>
                <input
                  name="first_name"
                  value={form.first_name}
                  onChange={handleInputChange}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  required
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Last Name
                </label>
                <input
                  name="last_name"
                  value={form.last_name}
                  onChange={handleInputChange}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  required
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Phone
                </label>
                <input
                  name="phone"
                  value={form.phone}
                  onChange={handleInputChange}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Email
                </label>
                <input
                  name="email"
                  type="email"
                  value={form.email}
                  onChange={handleInputChange}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Status
                </label>
                <select
                  name="status"
                  value={form.status}
                  onChange={handleInputChange}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                >
                  <option>Active</option>
                  <option>Pending</option>
                  <option>Closed</option>
                </select>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Department
                </label>
                <select
                  name="department_id"
                  value={form.department_id}
                  onChange={handleInputChange}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                >
                  <option value="">None</option>
                  {departments.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="md:col-span-2">
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Notes
                </label>
                <textarea
                  name="notes"
                  value={form.notes}
                  onChange={handleInputChange}
                  rows={4}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
              </div>

              <div className="md:col-span-2 flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeModal}
                  className="rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-70"
                >
                  {submitting
                    ? editingClient
                      ? "Updating..."
                      : "Saving..."
                    : editingClient
                    ? "Update Client"
                    : "Save Client"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}