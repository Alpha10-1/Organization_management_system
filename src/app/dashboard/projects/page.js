"use client";

import { useEffect, useMemo, useState } from "react";
import {
  fetchProjects,
  createProject,
  updateProject,
  deleteProject,
  fetchClients,
  fetchUsers,
  fetchDepartments,
  fetchCurrentUser,
  fetchMilestones,
  createMilestone,
  updateMilestone,
  deleteMilestone,
  fetchContracts,
  createContract,
  updateContract,
  deleteContract,
  fetchContractMargin,
  fetchTimeEntries,
  createTimeEntry,
  deleteTimeEntry,
  fetchProjectUtilization,
  fetchTaskTemplates,
  applyTaskTemplate,
  fetchProjectAssignments,
  createProjectAssignment,
  deleteProjectAssignment,
} from "@/lib/api";

const PROJECT_TYPES = ["audit", "tax", "advisory", "systems_implementation", "other"];
const PROJECT_STATUSES = ["planning", "active", "on_hold", "completed", "cancelled"];
const RISK_LEVELS = ["low", "medium", "high"];
const BILLING_TYPES = ["fixed_fee", "hourly", "retainer"];

const STATUS_STYLES = {
  planning: "bg-slate-100 text-slate-600",
  active: "bg-emerald-100 text-emerald-700",
  on_hold: "bg-amber-100 text-amber-700",
  completed: "bg-blue-100 text-blue-700",
  cancelled: "bg-rose-100 text-rose-700",
};

const RISK_STYLES = {
  low: "bg-emerald-100 text-emerald-700",
  medium: "bg-amber-100 text-amber-700",
  high: "bg-rose-100 text-rose-700",
};

const initialProjectForm = {
  name: "",
  client_id: "",
  type: "other",
  status: "planning",
  start_date: "",
  end_date: "",
  budget: "",
  engagement_partner_email: "",
  engagement_manager_email: "",
  description: "",
  risk_level: "low",
  compliance_flag: "",
  objectives: "",
  deliverables: "",
  stakeholders: "",
  billing_notes: "",
};

const initialAssignmentForm = { target_type: "user", target_id: "", role: "" };

const initialMilestoneForm = { name: "", description: "", due_date: "", status: "pending" };

const initialContractForm = {
  name: "",
  billing_type: "fixed_fee",
  value: "",
  hourly_rate: "",
  signed_date: "",
  expiry_date: "",
  status: "draft",
  notes: "",
};

const initialTimeForm = { hours: "", entry_date: "", billable: true, notes: "" };

function formatMoney(value) {
  if (value === null || value === undefined || value === "") return "—";
  return `$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString();
}

function clientDisplayName(client) {
  if (!client) return "";
  if ((client.client_type === "business" || client.client_type === "npo") && client.company_name) {
    return client.company_name;
  }
  const name = [client.first_name, client.last_name].filter(Boolean).join(" ");
  return name || client.company_name || `Client #${client.id}`;
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState([]);
  const [clients, setClients] = useState([]);
  const [users, setUsers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [showMoreProjectDetail, setShowMoreProjectDetail] = useState(false);

  const [clientFilter, setClientFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [riskFilter, setRiskFilter] = useState("");

  const [selectedProject, setSelectedProject] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");

  const [showProjectModal, setShowProjectModal] = useState(false);
  const [editingProject, setEditingProject] = useState(null);
  const [projectForm, setProjectForm] = useState(initialProjectForm);

  const [milestones, setMilestones] = useState([]);
  const [showMilestoneModal, setShowMilestoneModal] = useState(false);
  const [milestoneForm, setMilestoneForm] = useState(initialMilestoneForm);

  const [contracts, setContracts] = useState([]);
  const [contractMargins, setContractMargins] = useState({});
  const [showContractModal, setShowContractModal] = useState(false);
  const [contractForm, setContractForm] = useState(initialContractForm);

  const [timeEntries, setTimeEntries] = useState([]);
  const [utilization, setUtilization] = useState(null);
  const [showTimeModal, setShowTimeModal] = useState(false);
  const [timeForm, setTimeForm] = useState(initialTimeForm);

  const [templates, setTemplates] = useState([]);
  const [templateToApply, setTemplateToApply] = useState("");
  const [applyingTemplate, setApplyingTemplate] = useState(false);

  const [assignments, setAssignments] = useState([]);
  const [assignmentForm, setAssignmentForm] = useState(initialAssignmentForm);
  const [assigningTeam, setAssigningTeam] = useState(false);

  async function loadProjects() {
    try {
      setLoading(true);
      setError("");
      const data = await fetchProjects({
        client_id: clientFilter || undefined,
        status: statusFilter || undefined,
        type: typeFilter || undefined,
        risk_level: riskFilter || undefined,
      });
      setProjects(data);
    } catch (err) {
      setError(err.message || "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProjects();
    fetchClients().then(setClients).catch(() => setClients([]));
    fetchUsers().then(setUsers).catch(() => setUsers([]));
    fetchDepartments().then(setDepartments).catch(() => setDepartments([]));
    fetchCurrentUser().then(setCurrentUser).catch(() => setCurrentUser(null));
    fetchTaskTemplates().then(setTemplates).catch(() => setTemplates([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadProjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clientFilter, statusFilter, typeFilter, riskFilter]);

  async function loadProjectDetail(project) {
    setSelectedProject(project);
    setActiveTab("overview");
    try {
      const [ms, cs, te, util, as] = await Promise.all([
        fetchMilestones({ project_id: project.id }),
        fetchContracts({ project_id: project.id }),
        fetchTimeEntries({ project_id: project.id }),
        fetchProjectUtilization(project.id).catch(() => null),
        fetchProjectAssignments(project.id).catch(() => []),
      ]);
      setMilestones(ms);
      setContracts(cs);
      setTimeEntries(te);
      setUtilization(util);
      setAssignments(as);

      const margins = {};
      await Promise.all(
        cs.map(async (c) => {
          try {
            margins[c.id] = await fetchContractMargin(c.id);
          } catch {
            // margin lookup is best-effort; skip contracts it fails for
          }
        })
      );
      setContractMargins(margins);
    } catch (err) {
      setError(err.message || "Failed to load project detail");
    }
  }

  async function refreshDetail() {
    if (selectedProject) await loadProjectDetail(selectedProject);
  }

  function clientLabel(clientId) {
    const match = clients.find((c) => c.id === clientId);
    return match ? clientDisplayName(match) : `#${clientId}`;
  }

  // --- Project CRUD ---------------------------------------------------------

  function openCreateProject() {
    setEditingProject(null);
    setProjectForm(initialProjectForm);
    setShowMoreProjectDetail(false);
    setShowProjectModal(true);
  }

  function openEditProject(project) {
    setEditingProject(project);
    setProjectForm({
      name: project.name,
      client_id: String(project.client_id),
      type: project.type,
      status: project.status,
      start_date: project.start_date ? project.start_date.slice(0, 10) : "",
      end_date: project.end_date ? project.end_date.slice(0, 10) : "",
      budget: project.budget ?? "",
      engagement_partner_email: project.engagement_partner_email || "",
      engagement_manager_email: project.engagement_manager_email || "",
      description: project.description || "",
      risk_level: project.risk_level,
      compliance_flag: project.compliance_flag || "",
      objectives: project.objectives || "",
      deliverables: project.deliverables || "",
      stakeholders: project.stakeholders || "",
      billing_notes: project.billing_notes || "",
    });
    setShowMoreProjectDetail(
      Boolean(project.objectives || project.deliverables || project.stakeholders || project.billing_notes)
    );
    setShowProjectModal(true);
  }

  function handleProjectFormChange(e) {
    const { name, value, type, checked } = e.target;
    setProjectForm((prev) => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
  }

  async function handleProjectSubmit(e) {
    e.preventDefault();
    try {
      setSaving(true);
      setError("");
      const payload = {
        name: projectForm.name,
        client_id: Number(projectForm.client_id),
        type: projectForm.type,
        status: projectForm.status,
        start_date: projectForm.start_date ? new Date(projectForm.start_date).toISOString() : undefined,
        end_date: projectForm.end_date ? new Date(projectForm.end_date).toISOString() : undefined,
        budget: projectForm.budget !== "" ? Number(projectForm.budget) : undefined,
        engagement_partner_email: projectForm.engagement_partner_email || undefined,
        engagement_manager_email: projectForm.engagement_manager_email || undefined,
        description: projectForm.description || undefined,
        risk_level: projectForm.risk_level,
        compliance_flag: projectForm.compliance_flag || undefined,
        objectives: projectForm.objectives || undefined,
        deliverables: projectForm.deliverables || undefined,
        stakeholders: projectForm.stakeholders || undefined,
        billing_notes: projectForm.billing_notes || undefined,
      };
      if (editingProject) {
        await updateProject(editingProject.id, payload);
      } else {
        await createProject(payload);
      }
      setShowProjectModal(false);
      await loadProjects();
    } catch (err) {
      setError(err.message || "Failed to save project");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteProject(project) {
    try {
      setError("");
      await deleteProject(project.id);
      if (selectedProject?.id === project.id) setSelectedProject(null);
      await loadProjects();
    } catch (err) {
      setError(err.message || "Failed to delete project");
    }
  }

  // --- Team assignment (individuals or whole departments) --------------------

  function handleAssignmentFormChange(e) {
    const { name, value } = e.target;
    setAssignmentForm((prev) => ({
      ...prev,
      [name]: value,
      ...(name === "target_type" ? { target_id: "" } : {}),
    }));
  }

  async function handleAddAssignment(e) {
    e.preventDefault();
    if (!selectedProject || !assignmentForm.target_id) return;
    try {
      setAssigningTeam(true);
      setError("");
      const payload =
        assignmentForm.target_type === "department"
          ? { department_id: Number(assignmentForm.target_id), role: assignmentForm.role || undefined }
          : { user_id: Number(assignmentForm.target_id), role: assignmentForm.role || undefined };
      await createProjectAssignment(selectedProject.id, payload);
      setAssignmentForm(initialAssignmentForm);
      await refreshDetail();
    } catch (err) {
      setError(err.message || "Failed to assign team member");
    } finally {
      setAssigningTeam(false);
    }
  }

  async function handleRemoveAssignment(assignment) {
    if (!selectedProject) return;
    try {
      setError("");
      await deleteProjectAssignment(selectedProject.id, assignment.id);
      await refreshDetail();
    } catch (err) {
      setError(err.message || "Failed to remove assignment");
    }
  }

  // --- Milestones -------------------------------------------------------------

  async function handleCreateMilestone(e) {
    e.preventDefault();
    if (!selectedProject) return;
    try {
      setSaving(true);
      setError("");
      await createMilestone({
        project_id: selectedProject.id,
        name: milestoneForm.name,
        description: milestoneForm.description || undefined,
        due_date: milestoneForm.due_date ? new Date(milestoneForm.due_date).toISOString() : undefined,
        status: milestoneForm.status,
      });
      setMilestoneForm(initialMilestoneForm);
      setShowMilestoneModal(false);
      await refreshDetail();
    } catch (err) {
      setError(err.message || "Failed to create milestone");
    } finally {
      setSaving(false);
    }
  }

  async function handleMilestoneStatus(milestone, status) {
    try {
      setError("");
      await updateMilestone(milestone.id, { status });
      await refreshDetail();
    } catch (err) {
      setError(err.message || "Failed to update milestone");
    }
  }

  async function handleDeleteMilestone(milestone) {
    try {
      setError("");
      await deleteMilestone(milestone.id);
      await refreshDetail();
    } catch (err) {
      setError(err.message || "Failed to delete milestone");
    }
  }

  // --- Contracts ----------------------------------------------------------------

  async function handleCreateContract(e) {
    e.preventDefault();
    if (!selectedProject) return;
    try {
      setSaving(true);
      setError("");
      await createContract({
        project_id: selectedProject.id,
        name: contractForm.name,
        billing_type: contractForm.billing_type,
        value: contractForm.value !== "" ? Number(contractForm.value) : undefined,
        hourly_rate: contractForm.hourly_rate !== "" ? Number(contractForm.hourly_rate) : undefined,
        signed_date: contractForm.signed_date || undefined,
        expiry_date: contractForm.expiry_date || undefined,
        status: contractForm.status,
        notes: contractForm.notes || undefined,
      });
      setContractForm(initialContractForm);
      setShowContractModal(false);
      await refreshDetail();
    } catch (err) {
      setError(err.message || "Failed to create contract");
    } finally {
      setSaving(false);
    }
  }

  async function handleContractStatus(contract, status) {
    try {
      setError("");
      await updateContract(contract.id, { status });
      await refreshDetail();
    } catch (err) {
      setError(err.message || "Failed to update contract");
    }
  }

  async function handleDeleteContract(contract) {
    try {
      setError("");
      await deleteContract(contract.id);
      await refreshDetail();
    } catch (err) {
      setError(err.message || "Failed to delete contract");
    }
  }

  // --- Time entries ---------------------------------------------------------------

  async function handleLogTime(e) {
    e.preventDefault();
    if (!selectedProject) return;
    try {
      setSaving(true);
      setError("");
      await createTimeEntry({
        project_id: selectedProject.id,
        hours: Number(timeForm.hours),
        entry_date: timeForm.entry_date || new Date().toISOString().slice(0, 10),
        billable: timeForm.billable,
        notes: timeForm.notes || undefined,
      });
      setTimeForm(initialTimeForm);
      setShowTimeModal(false);
      await refreshDetail();
    } catch (err) {
      setError(err.message || "Failed to log time");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteTimeEntry(entry) {
    try {
      setError("");
      await deleteTimeEntry(entry.id);
      await refreshDetail();
    } catch (err) {
      setError(err.message || "Failed to delete time entry");
    }
  }

  // --- Task template application --------------------------------------------------

  async function handleApplyTemplate() {
    if (!selectedProject || !templateToApply) return;
    try {
      setApplyingTemplate(true);
      setError("");
      const created = await applyTaskTemplate(Number(templateToApply), {
        project_id: selectedProject.id,
      });
      setTemplateToApply("");
      await loadProjects();
      alert(`Applied template: created ${created.length} task(s) on this engagement.`);
    } catch (err) {
      setError(err.message || "Failed to apply template");
    } finally {
      setApplyingTemplate(false);
    }
  }

  const tabs = useMemo(
    () => [
      { id: "overview", label: "Overview" },
      { id: "team", label: `Team (${assignments.length})` },
      { id: "milestones", label: `Milestones (${milestones.length})` },
      { id: "contracts", label: `Contracts (${contracts.length})` },
      { id: "time", label: `Time (${timeEntries.length})` },
      { id: "template", label: "Apply Template" },
    ],
    [assignments.length, milestones.length, contracts.length, timeEntries.length]
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm md:flex-row md:items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Engagements &amp; Projects</h1>
          <p className="mt-1 text-sm text-slate-500">
            Every client can run multiple concurrent engagements — track scope, team, budget and
            risk for each one separately.
          </p>
        </div>
        <button
          onClick={openCreateProject}
          className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800"
        >
          New Engagement
        </button>
      </div>

      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      ) : null}

      <div className="flex flex-wrap gap-3 rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <select
          value={clientFilter}
          onChange={(e) => setClientFilter(e.target.value)}
          className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
        >
          <option value="">All clients</option>
          {clients.map((c) => (
            <option key={c.id} value={c.id}>
              {clientDisplayName(c)}
            </option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
        >
          <option value="">All statuses</option>
          {PROJECT_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.replace("_", " ")}
            </option>
          ))}
        </select>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
        >
          <option value="">All types</option>
          {PROJECT_TYPES.map((t) => (
            <option key={t} value={t}>
              {t.replace("_", " ")}
            </option>
          ))}
        </select>
        <select
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value)}
          className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
        >
          <option value="">All risk levels</option>
          {RISK_LEVELS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.1fr_1fr]">
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] border-separate border-spacing-y-3">
              <thead>
                <tr className="text-left text-sm text-slate-500">
                  <th className="pb-2">Engagement</th>
                  <th className="pb-2">Client</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2">Risk</th>
                  <th className="pb-2">Tasks</th>
                  <th className="pb-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-sm text-slate-500">
                      Loading engagements...
                    </td>
                  </tr>
                ) : projects.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-sm text-slate-500">
                      No engagements found.
                    </td>
                  </tr>
                ) : (
                  projects.map((p) => (
                    <tr
                      key={p.id}
                      onClick={() => loadProjectDetail(p)}
                      className={`cursor-pointer bg-slate-50 align-top transition hover:bg-slate-100 ${
                        selectedProject?.id === p.id ? "ring-2 ring-slate-900" : ""
                      }`}
                    >
                      <td className="rounded-l-2xl px-4 py-4">
                        <p className="font-medium text-slate-900">{p.name}</p>
                        <p className="mt-1 text-xs capitalize text-slate-500">{p.type.replace("_", " ")}</p>
                      </td>
                      <td className="px-4 py-4 text-sm text-slate-700">{clientLabel(p.client_id)}</td>
                      <td className="px-4 py-4">
                        <span
                          className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${STATUS_STYLES[p.status] || STATUS_STYLES.planning}`}
                        >
                          {p.status.replace("_", " ")}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <span
                          className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${RISK_STYLES[p.risk_level] || RISK_STYLES.low}`}
                        >
                          {p.risk_level}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-sm text-slate-700">
                        {p.open_task_count}/{p.task_count} open
                        {p.overdue_task_count > 0 ? (
                          <span className="ml-2 text-xs font-semibold text-rose-600">
                            {p.overdue_task_count} overdue
                          </span>
                        ) : null}
                      </td>
                      <td className="rounded-r-2xl px-4 py-4">
                        <div className="flex gap-3">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              openEditProject(p);
                            }}
                            className="text-sm font-semibold text-slate-700 hover:underline"
                          >
                            Edit
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteProject(p);
                            }}
                            className="text-sm font-semibold text-rose-600 hover:underline"
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
          {!selectedProject ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500">
              Select an engagement from the list to view milestones, contracts, and time.
            </div>
          ) : (
            <div>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">{selectedProject.name}</h2>
                  <p className="text-sm text-slate-500">{clientLabel(selectedProject.client_id)}</p>
                </div>
              </div>

              <div className="mt-4 flex flex-wrap gap-2 border-b border-slate-200 pb-3">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`rounded-xl px-3 py-2 text-xs font-semibold transition ${
                      activeTab === tab.id
                        ? "bg-slate-900 text-white"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {activeTab === "overview" ? (
                <div className="mt-4 space-y-3">
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Budget</p>
                      <p className="mt-1 text-slate-800">{formatMoney(selectedProject.budget)}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Timeline</p>
                      <p className="mt-1 text-slate-800">
                        {formatDate(selectedProject.start_date)} – {formatDate(selectedProject.end_date)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Partner</p>
                      <p className="mt-1 text-slate-800">
                        {selectedProject.engagement_partner_name || selectedProject.engagement_partner_email || "—"}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Manager</p>
                      <p className="mt-1 text-slate-800">
                        {selectedProject.engagement_manager_name || selectedProject.engagement_manager_email || "—"}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Compliance flag</p>
                      <p className="mt-1 text-slate-800">{selectedProject.compliance_flag || "—"}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Hours logged</p>
                      <p className="mt-1 text-slate-800">
                        {utilization ? `${Number(utilization.total_hours).toFixed(1)}h total (${Number(utilization.billable_hours).toFixed(1)}h billable)` : "—"}
                      </p>
                    </div>
                  </div>
                  {selectedProject.description ? (
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Description</p>
                      <p className="mt-1 whitespace-pre-wrap text-sm text-slate-800">
                        {selectedProject.description}
                      </p>
                    </div>
                  ) : null}
                  {selectedProject.objectives || selectedProject.deliverables || selectedProject.stakeholders || selectedProject.billing_notes ? (
                    <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                        Additional Detail
                      </p>
                      {selectedProject.objectives ? (
                        <p className="text-sm text-slate-800">
                          <span className="font-semibold">Objectives: </span>
                          {selectedProject.objectives}
                        </p>
                      ) : null}
                      {selectedProject.deliverables ? (
                        <p className="text-sm text-slate-800">
                          <span className="font-semibold">Deliverables: </span>
                          {selectedProject.deliverables}
                        </p>
                      ) : null}
                      {selectedProject.stakeholders ? (
                        <p className="text-sm text-slate-800">
                          <span className="font-semibold">Stakeholders: </span>
                          {selectedProject.stakeholders}
                        </p>
                      ) : null}
                      {selectedProject.billing_notes ? (
                        <p className="text-sm text-slate-800">
                          <span className="font-semibold">Billing Notes: </span>
                          {selectedProject.billing_notes}
                        </p>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ) : null}

              {activeTab === "team" ? (
                <div className="mt-4 space-y-3">
                  <div className="max-h-56 space-y-2 overflow-y-auto">
                    {assignments.length === 0 ? (
                      <p className="text-sm text-slate-400">No one assigned yet.</p>
                    ) : (
                      assignments.map((a) => (
                        <div
                          key={a.id}
                          className="flex items-center justify-between gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3"
                        >
                          <div>
                            <p className="text-sm font-medium text-slate-800">
                              {a.user_id ? a.user_name || `User #${a.user_id}` : a.department_name || `Department #${a.department_id}`}
                              <span className="ml-2 rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-semibold uppercase text-slate-600">
                                {a.user_id ? "Individual" : "Department"}
                              </span>
                            </p>
                            {a.role ? <p className="text-xs text-slate-500">{a.role}</p> : null}
                          </div>
                          <button
                            onClick={() => handleRemoveAssignment(a)}
                            className="shrink-0 text-xs font-semibold text-rose-500 hover:underline"
                          >
                            Remove
                          </button>
                        </div>
                      ))
                    )}
                  </div>

                  <form
                    onSubmit={handleAddAssignment}
                    className="space-y-2 rounded-xl border border-slate-200 bg-white p-3"
                  >
                    <div className="flex gap-2">
                      <select
                        name="target_type"
                        value={assignmentForm.target_type}
                        onChange={handleAssignmentFormChange}
                        className="rounded-lg border border-slate-300 px-2 py-2 text-xs outline-none focus:border-slate-900"
                      >
                        <option value="user">Individual</option>
                        <option value="department">Department</option>
                      </select>
                      <select
                        name="target_id"
                        value={assignmentForm.target_id}
                        onChange={handleAssignmentFormChange}
                        className="flex-1 rounded-lg border border-slate-300 px-2 py-2 text-xs outline-none focus:border-slate-900"
                        required
                      >
                        <option value="">
                          {assignmentForm.target_type === "department" ? "Select a department..." : "Select a person..."}
                        </option>
                        {(assignmentForm.target_type === "department" ? departments : users).map((opt) => (
                          <option key={opt.id} value={opt.id}>
                            {opt.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <input
                      name="role"
                      value={assignmentForm.role}
                      onChange={handleAssignmentFormChange}
                      placeholder="Role on engagement (optional)"
                      className="w-full rounded-lg border border-slate-300 px-2 py-2 text-xs outline-none focus:border-slate-900"
                    />
                    <button
                      type="submit"
                      disabled={assigningTeam || !assignmentForm.target_id}
                      className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-50"
                    >
                      {assigningTeam ? "Assigning..." : "+ Assign"}
                    </button>
                  </form>
                </div>
              ) : null}

              {activeTab === "milestones" ? (
                <div className="mt-4 space-y-3">
                  <button
                    onClick={() => setShowMilestoneModal(true)}
                    className="rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                  >
                    + Add Milestone
                  </button>
                  <div className="max-h-72 space-y-2 overflow-y-auto">
                    {milestones.length === 0 ? (
                      <p className="text-sm text-slate-400">No milestones yet.</p>
                    ) : (
                      milestones.map((m) => (
                        <div key={m.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <p className="text-sm font-medium text-slate-800">{m.name}</p>
                              <p className="text-xs text-slate-500">Due {formatDate(m.due_date)}</p>
                            </div>
                            <button
                              onClick={() => handleDeleteMilestone(m)}
                              className="shrink-0 text-xs font-semibold text-rose-500 hover:underline"
                            >
                              Delete
                            </button>
                          </div>
                          <select
                            value={m.status}
                            onChange={(e) => handleMilestoneStatus(m, e.target.value)}
                            className="mt-2 rounded-lg border border-slate-300 px-2 py-1 text-xs outline-none focus:border-slate-900"
                          >
                            <option value="pending">Pending</option>
                            <option value="achieved">Achieved</option>
                            <option value="missed">Missed</option>
                          </select>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              ) : null}

              {activeTab === "contracts" ? (
                <div className="mt-4 space-y-3">
                  <button
                    onClick={() => setShowContractModal(true)}
                    className="rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                  >
                    + Add Contract / SOW
                  </button>
                  <div className="max-h-72 space-y-2 overflow-y-auto">
                    {contracts.length === 0 ? (
                      <p className="text-sm text-slate-400">No contracts yet.</p>
                    ) : (
                      contracts.map((c) => {
                        const margin = contractMargins[c.id];
                        return (
                          <div key={c.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <p className="text-sm font-medium text-slate-800">{c.name}</p>
                                <p className="text-xs capitalize text-slate-500">
                                  {c.billing_type.replace("_", " ")} · {formatMoney(c.value)}
                                </p>
                              </div>
                              <button
                                onClick={() => handleDeleteContract(c)}
                                className="shrink-0 text-xs font-semibold text-rose-500 hover:underline"
                              >
                                Delete
                              </button>
                            </div>
                            <select
                              value={c.status}
                              onChange={(e) => handleContractStatus(c, e.target.value)}
                              className="mt-2 rounded-lg border border-slate-300 px-2 py-1 text-xs outline-none focus:border-slate-900"
                            >
                              <option value="draft">Draft</option>
                              <option value="signed">Signed</option>
                              <option value="expired">Expired</option>
                              <option value="terminated">Terminated</option>
                            </select>
                            {margin ? (
                              <p className="mt-2 text-xs text-slate-600">
                                {Number(margin.billable_hours).toFixed(1)}h billable logged
                                {margin.remaining_value !== null && margin.remaining_value !== undefined
                                  ? ` · ${formatMoney(margin.remaining_value)} remaining`
                                  : ""}
                              </p>
                            ) : null}
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              ) : null}

              {activeTab === "time" ? (
                <div className="mt-4 space-y-3">
                  <button
                    onClick={() => setShowTimeModal(true)}
                    className="rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                  >
                    + Log Time
                  </button>
                  <div className="max-h-72 space-y-2 overflow-y-auto">
                    {timeEntries.length === 0 ? (
                      <p className="text-sm text-slate-400">No time logged yet.</p>
                    ) : (
                      timeEntries.map((t) => (
                        <div
                          key={t.id}
                          className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 p-3"
                        >
                          <div>
                            <p className="text-sm text-slate-800">
                              {t.hours}h · {t.user_name} · {formatDate(t.entry_date)}
                              {!t.billable ? <span className="ml-2 text-xs text-slate-400">(non-billable)</span> : null}
                            </p>
                            {t.notes ? <p className="text-xs text-slate-500">{t.notes}</p> : null}
                          </div>
                          <button
                            onClick={() => handleDeleteTimeEntry(t)}
                            className="text-xs font-semibold text-rose-500 hover:underline"
                          >
                            Delete
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              ) : null}

              {activeTab === "template" ? (
                <div className="mt-4 space-y-3">
                  <p className="text-sm text-slate-500">
                    Clone a standard checklist (e.g. an audit kickoff) onto this engagement.
                  </p>
                  <div className="flex gap-2">
                    <select
                      value={templateToApply}
                      onChange={(e) => setTemplateToApply(e.target.value)}
                      className="flex-1 rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
                    >
                      <option value="">Choose a template...</option>
                      {templates.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name} ({t.items.length} items)
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={handleApplyTemplate}
                      disabled={!templateToApply || applyingTemplate}
                      className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
                    >
                      {applyingTemplate ? "Applying..." : "Apply"}
                    </button>
                  </div>
                  {templates.length === 0 ? (
                    <p className="text-xs text-slate-400">
                      No task templates exist yet. Create one from the Tasks page.
                    </p>
                  ) : null}
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>

      {showProjectModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-6 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold text-slate-900">
                  {editingProject ? "Edit Engagement" : "New Engagement"}
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  Engagements sit between a client and their tasks.
                </p>
              </div>
              <button
                onClick={() => setShowProjectModal(false)}
                className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
              >
                Close
              </button>
            </div>

            <form onSubmit={handleProjectSubmit} className="space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Name</label>
                <input
                  name="name"
                  value={projectForm.name}
                  onChange={handleProjectFormChange}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  required
                />
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Client</label>
                  <select
                    name="client_id"
                    value={projectForm.client_id}
                    onChange={handleProjectFormChange}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                    required
                  >
                    <option value="">Select a client</option>
                    {clients.map((c) => (
                      <option key={c.id} value={c.id}>
                        {clientDisplayName(c)}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Type</label>
                  <select
                    name="type"
                    value={projectForm.type}
                    onChange={handleProjectFormChange}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  >
                    {PROJECT_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t.replace("_", " ")}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Status</label>
                  <select
                    name="status"
                    value={projectForm.status}
                    onChange={handleProjectFormChange}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  >
                    {PROJECT_STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {s.replace("_", " ")}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Risk Level</label>
                  <select
                    name="risk_level"
                    value={projectForm.risk_level}
                    onChange={handleProjectFormChange}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  >
                    {RISK_LEVELS.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Start Date</label>
                  <input
                    type="date"
                    name="start_date"
                    value={projectForm.start_date}
                    onChange={handleProjectFormChange}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">End Date</label>
                  <input
                    type="date"
                    name="end_date"
                    value={projectForm.end_date}
                    onChange={handleProjectFormChange}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  />
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Budget</label>
                <input
                  type="number"
                  step="0.01"
                  name="budget"
                  value={projectForm.budget}
                  onChange={handleProjectFormChange}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Engagement Partner</label>
                  <select
                    name="engagement_partner_email"
                    value={projectForm.engagement_partner_email}
                    onChange={handleProjectFormChange}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  >
                    <option value="">None</option>
                    {users.map((u) => (
                      <option key={u.email} value={u.email}>
                        {u.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Engagement Manager</label>
                  <select
                    name="engagement_manager_email"
                    value={projectForm.engagement_manager_email}
                    onChange={handleProjectFormChange}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  >
                    <option value="">None</option>
                    {users.map((u) => (
                      <option key={u.email} value={u.email}>
                        {u.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Compliance Flag</label>
                <input
                  name="compliance_flag"
                  value={projectForm.compliance_flag}
                  onChange={handleProjectFormChange}
                  placeholder="e.g. SOX, PCAOB"
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Description</label>
                <textarea
                  name="description"
                  value={projectForm.description}
                  onChange={handleProjectFormChange}
                  rows={3}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
              </div>

              <div>
                <button
                  type="button"
                  onClick={() => setShowMoreProjectDetail((prev) => !prev)}
                  className="text-sm font-semibold text-blue-600 hover:underline"
                >
                  {showMoreProjectDetail ? "Hide additional detail" : "Specify More"}
                </button>
                <p className="mt-1 text-xs text-slate-500">
                  Optional extra detail — objectives, deliverables, stakeholders and billing notes — for
                  engagements that need it.
                </p>
              </div>

              {showMoreProjectDetail ? (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Objectives</label>
                    <textarea
                      name="objectives"
                      value={projectForm.objectives}
                      onChange={handleProjectFormChange}
                      rows={3}
                      placeholder="What this engagement is meant to achieve"
                      className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                    />
                  </div>
                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Deliverables</label>
                    <textarea
                      name="deliverables"
                      value={projectForm.deliverables}
                      onChange={handleProjectFormChange}
                      rows={3}
                      placeholder="What will be handed over at completion"
                      className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                    />
                  </div>
                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Stakeholders</label>
                    <textarea
                      name="stakeholders"
                      value={projectForm.stakeholders}
                      onChange={handleProjectFormChange}
                      rows={3}
                      placeholder="Key people on the client side"
                      className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                    />
                  </div>
                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Billing Notes</label>
                    <textarea
                      name="billing_notes"
                      value={projectForm.billing_notes}
                      onChange={handleProjectFormChange}
                      rows={3}
                      placeholder="Fee structure, milestones, special terms"
                      className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                    />
                  </div>
                </div>
              ) : null}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowProjectModal(false)}
                  className="rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-70"
                >
                  {saving ? "Saving..." : editingProject ? "Save Changes" : "Create Engagement"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {showMilestoneModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-4">
              <h2 className="text-xl font-bold text-slate-900">New Milestone</h2>
              <button
                onClick={() => setShowMilestoneModal(false)}
                className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
              >
                Close
              </button>
            </div>
            <form onSubmit={handleCreateMilestone} className="space-y-4">
              <input
                placeholder="Milestone name"
                value={milestoneForm.name}
                onChange={(e) => setMilestoneForm((p) => ({ ...p, name: e.target.value }))}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                required
              />
              <textarea
                placeholder="Description (optional)"
                value={milestoneForm.description}
                onChange={(e) => setMilestoneForm((p) => ({ ...p, description: e.target.value }))}
                rows={2}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
              />
              <input
                type="date"
                value={milestoneForm.due_date}
                onChange={(e) => setMilestoneForm((p) => ({ ...p, due_date: e.target.value }))}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
              />
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowMilestoneModal(false)}
                  className="rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-70"
                >
                  {saving ? "Saving..." : "Add Milestone"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {showContractModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-4">
              <h2 className="text-xl font-bold text-slate-900">New Contract / SOW</h2>
              <button
                onClick={() => setShowContractModal(false)}
                className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
              >
                Close
              </button>
            </div>
            <form onSubmit={handleCreateContract} className="space-y-4">
              <input
                placeholder="Contract name"
                value={contractForm.name}
                onChange={(e) => setContractForm((p) => ({ ...p, name: e.target.value }))}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                required
              />
              <select
                value={contractForm.billing_type}
                onChange={(e) => setContractForm((p) => ({ ...p, billing_type: e.target.value }))}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
              >
                {BILLING_TYPES.map((b) => (
                  <option key={b} value={b}>
                    {b.replace("_", " ")}
                  </option>
                ))}
              </select>
              <div className="grid grid-cols-2 gap-3">
                <input
                  type="number"
                  step="0.01"
                  placeholder="Contract value"
                  value={contractForm.value}
                  onChange={(e) => setContractForm((p) => ({ ...p, value: e.target.value }))}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
                <input
                  type="number"
                  step="0.01"
                  placeholder="Hourly rate"
                  value={contractForm.hourly_rate}
                  onChange={(e) => setContractForm((p) => ({ ...p, hourly_rate: e.target.value }))}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-xs text-slate-500">Signed date</label>
                  <input
                    type="date"
                    value={contractForm.signed_date}
                    onChange={(e) => setContractForm((p) => ({ ...p, signed_date: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs text-slate-500">Expiry date</label>
                  <input
                    type="date"
                    value={contractForm.expiry_date}
                    onChange={(e) => setContractForm((p) => ({ ...p, expiry_date: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  />
                </div>
              </div>
              <textarea
                placeholder="Notes (optional)"
                value={contractForm.notes}
                onChange={(e) => setContractForm((p) => ({ ...p, notes: e.target.value }))}
                rows={2}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
              />
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowContractModal(false)}
                  className="rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-70"
                >
                  {saving ? "Saving..." : "Add Contract"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {showTimeModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-4">
              <h2 className="text-xl font-bold text-slate-900">Log Time</h2>
              <button
                onClick={() => setShowTimeModal(false)}
                className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
              >
                Close
              </button>
            </div>
            <form onSubmit={handleLogTime} className="space-y-4">
              <input
                type="number"
                step="0.25"
                min="0.25"
                max="24"
                placeholder="Hours"
                value={timeForm.hours}
                onChange={(e) => setTimeForm((p) => ({ ...p, hours: e.target.value }))}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                required
              />
              <input
                type="date"
                value={timeForm.entry_date}
                onChange={(e) => setTimeForm((p) => ({ ...p, entry_date: e.target.value }))}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                required
              />
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={timeForm.billable}
                  onChange={(e) => setTimeForm((p) => ({ ...p, billable: e.target.checked }))}
                />
                Billable
              </label>
              <textarea
                placeholder="Notes (optional)"
                value={timeForm.notes}
                onChange={(e) => setTimeForm((p) => ({ ...p, notes: e.target.value }))}
                rows={2}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
              />
              <p className="text-xs text-slate-400">
                Logged as {currentUser?.name || "you"}.
              </p>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowTimeModal(false)}
                  className="rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-70"
                >
                  {saving ? "Saving..." : "Log Time"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
