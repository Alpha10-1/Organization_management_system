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
  updateProjectAssignment,
  deleteProjectAssignment,
  fetchProjectHistory,
  fetchProjectBudgetBurn,
  fetchProjectHealth,
  fetchProjectRiskForecast,
  fetchTimeEntryAnomalies,
  cloneProject,
  fetchChangeOrders,
  createChangeOrder,
  approveChangeOrder,
  rejectChangeOrder,
  deleteChangeOrder,
  signoffMilestone,
  fetchTasks,
} from "@/lib/api";

const initialAssignmentForm = { target_type: "user", target_id: "", role: "", allocation_percent: "" };

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

const HEALTH_STYLES = {
  green: "bg-emerald-100 text-emerald-700",
  amber: "bg-amber-100 text-amber-700",
  red: "bg-rose-100 text-rose-700",
};

const BUDGET_STATUS_STYLES = {
  on_track: "bg-emerald-500",
  at_risk: "bg-amber-500",
  over_budget: "bg-rose-500",
  hours_only: "bg-slate-400",
  no_budget: "bg-slate-300",
};

const TREND_STYLES = {
  worsening: "bg-rose-100 text-rose-700",
  improving: "bg-emerald-100 text-emerald-700",
  stable: "bg-slate-100 text-slate-600",
  insufficient_data: "bg-slate-100 text-slate-400",
};

const ANOMALY_LABELS = {
  late_logged: "Logged late",
  friday_large_block: "Large Friday block",
  possible_duplicate: "Possible duplicate",
  round_number_pattern: "Round-number pattern",
};

const CHANGE_ORDER_TYPES = ["scope_change", "fee_adjustment", "timeline_extension", "other"];

const CHANGE_ORDER_STATUS_STYLES = {
  pending: "bg-amber-100 text-amber-700",
  approved: "bg-emerald-100 text-emerald-700",
  rejected: "bg-rose-100 text-rose-700",
};

const APPROVAL_STATUS_STYLES = {
  pending: "bg-slate-100 text-slate-600",
  approved: "bg-emerald-100 text-emerald-700",
  rejected: "bg-rose-100 text-rose-700",
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
  close_out_notes: "",
};

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

const initialChangeOrderForm = {
  contract_id: "",
  title: "",
  description: "",
  change_type: "scope_change",
  amount_delta: "",
  hours_delta: "",
  requested_date: "",
};

const initialCloneForm = {
  name: "",
  start_date: "",
  end_date: "",
  include_team: true,
  include_milestones: true,
  include_tasks: false,
};

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

  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const [budgetBurn, setBudgetBurn] = useState(null);
  const [health, setHealth] = useState(null);
  const [riskForecast, setRiskForecast] = useState(null);
  const [riskForecastLoading, setRiskForecastLoading] = useState(false);
  const [riskForecastError, setRiskForecastError] = useState("");
  const [timeAnomalies, setTimeAnomalies] = useState([]);
  const [projectTasks, setProjectTasks] = useState([]);

  const [changeOrders, setChangeOrders] = useState([]);
  const [showChangeOrderModal, setShowChangeOrderModal] = useState(false);
  const [changeOrderForm, setChangeOrderForm] = useState(initialChangeOrderForm);

  const [showCloneModal, setShowCloneModal] = useState(false);
  const [cloneForm, setCloneForm] = useState(initialCloneForm);
  const [cloning, setCloning] = useState(false);

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
    setHistoryLoading(true);
    setRiskForecast(null);
    setRiskForecastError("");
    try {
      const [ms, cs, te, util, as, hist, burn, hp, cos, tks, anomalies] = await Promise.all([
        fetchMilestones({ project_id: project.id }),
        fetchContracts({ project_id: project.id }),
        fetchTimeEntries({ project_id: project.id }),
        fetchProjectUtilization(project.id).catch(() => null),
        fetchProjectAssignments(project.id).catch(() => []),
        fetchProjectHistory(project.id).catch(() => []),
        fetchProjectBudgetBurn(project.id).catch(() => null),
        fetchProjectHealth(project.id).catch(() => null),
        fetchChangeOrders({ project_id: project.id }).catch(() => []),
        fetchTasks({ project_id: project.id }).catch(() => []),
        fetchTimeEntryAnomalies({ project_id: project.id }).catch(() => []),
      ]);
      setMilestones(ms);
      setContracts(cs);
      setTimeEntries(te);
      setUtilization(util);
      setAssignments(as);
      setHistory(hist);
      setBudgetBurn(burn);
      setHealth(hp);
      setChangeOrders(cos);
      setProjectTasks(tks);
      setTimeAnomalies(anomalies);

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
    } finally {
      setHistoryLoading(false);
    }
  }

  async function refreshDetail() {
    if (selectedProject) await loadProjectDetail(selectedProject);
  }

  async function loadRiskForecast() {
    if (!selectedProject) return;
    setRiskForecastLoading(true);
    setRiskForecastError("");
    try {
      const forecast = await fetchProjectRiskForecast(selectedProject.id);
      setRiskForecast(forecast);
    } catch (err) {
      setRiskForecastError(err.message || "Failed to load risk forecast");
    } finally {
      setRiskForecastLoading(false);
    }
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
      close_out_notes: project.close_out_notes || "",
    });
    setShowMoreProjectDetail(
      Boolean(project.objectives || project.deliverables || project.stakeholders || project.billing_notes || project.close_out_notes)
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
        close_out_notes: projectForm.close_out_notes || undefined,
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
          : {
              user_id: Number(assignmentForm.target_id),
              role: assignmentForm.role || undefined,
              allocation_percent: assignmentForm.allocation_percent
                ? Number(assignmentForm.allocation_percent)
                : undefined,
            };
      await createProjectAssignment(selectedProject.id, payload);
      setAssignmentForm(initialAssignmentForm);
      await refreshDetail();
    } catch (err) {
      setError(err.message || "Failed to assign team member");
    } finally {
      setAssigningTeam(false);
    }
  }

  async function handleUpdateAssignmentAllocation(assignment, allocationPercent) {
    if (!selectedProject) return;
    try {
      setError("");
      await updateProjectAssignment(selectedProject.id, assignment.id, {
        allocation_percent: allocationPercent ? Number(allocationPercent) : null,
      });
      await refreshDetail();
    } catch (err) {
      setError(err.message || "Failed to update allocation");
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

  async function handleMilestoneSignoff(milestone, status) {
    try {
      setError("");
      let reason;
      if (status === "rejected") {
        reason = window.prompt("Reason for rejecting sign-off (optional):") || undefined;
      }
      await signoffMilestone(milestone.id, { status, reason });
      await refreshDetail();
    } catch (err) {
      setError(err.message || "Failed to update sign-off status");
    }
  }

  // --- Change orders --------------------------------------------------------------

  function openChangeOrderModal() {
    const defaultContract = contracts[0];
    setChangeOrderForm({
      ...initialChangeOrderForm,
      contract_id: defaultContract ? String(defaultContract.id) : "",
    });
    setShowChangeOrderModal(true);
  }

  async function handleCreateChangeOrder(e) {
    e.preventDefault();
    if (!changeOrderForm.contract_id) return;
    try {
      setSaving(true);
      setError("");
      await createChangeOrder({
        contract_id: Number(changeOrderForm.contract_id),
        title: changeOrderForm.title,
        description: changeOrderForm.description || undefined,
        change_type: changeOrderForm.change_type,
        amount_delta: changeOrderForm.amount_delta !== "" ? Number(changeOrderForm.amount_delta) : undefined,
        hours_delta: changeOrderForm.hours_delta !== "" ? Number(changeOrderForm.hours_delta) : undefined,
        requested_date: changeOrderForm.requested_date || undefined,
      });
      setChangeOrderForm(initialChangeOrderForm);
      setShowChangeOrderModal(false);
      await refreshDetail();
    } catch (err) {
      setError(err.message || "Failed to create change order");
    } finally {
      setSaving(false);
    }
  }

  async function handleApproveChangeOrder(co) {
    try {
      setError("");
      await approveChangeOrder(co.id);
      await refreshDetail();
    } catch (err) {
      setError(err.message || "Failed to approve change order");
    }
  }

  async function handleRejectChangeOrder(co) {
    try {
      setError("");
      const reason = window.prompt("Reason for rejecting (optional):") || undefined;
      await rejectChangeOrder(co.id, { reason });
      await refreshDetail();
    } catch (err) {
      setError(err.message || "Failed to reject change order");
    }
  }

  async function handleDeleteChangeOrder(co) {
    try {
      setError("");
      await deleteChangeOrder(co.id);
      await refreshDetail();
    } catch (err) {
      setError(err.message || "Failed to delete change order");
    }
  }

  // --- Clone engagement -------------------------------------------------------------

  function openCloneModal() {
    if (!selectedProject) return;
    setCloneForm({
      ...initialCloneForm,
      name: `${selectedProject.name} (Copy)`,
    });
    setShowCloneModal(true);
  }

  async function handleCloneProject(e) {
    e.preventDefault();
    if (!selectedProject) return;
    try {
      setCloning(true);
      setError("");
      const result = await cloneProject(selectedProject.id, {
        name: cloneForm.name || undefined,
        start_date: cloneForm.start_date ? new Date(cloneForm.start_date).toISOString() : undefined,
        end_date: cloneForm.end_date ? new Date(cloneForm.end_date).toISOString() : undefined,
        include_team: cloneForm.include_team,
        include_milestones: cloneForm.include_milestones,
        include_tasks: cloneForm.include_tasks,
      });
      setShowCloneModal(false);
      setCloneForm(initialCloneForm);
      await loadProjects();
      if (result?.project) await loadProjectDetail(result.project);
    } catch (err) {
      setError(err.message || "Failed to clone engagement");
    } finally {
      setCloning(false);
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
      { id: "timeline", label: "Timeline" },
      { id: "milestones", label: `Milestones (${milestones.length})` },
      { id: "contracts", label: `Contracts (${contracts.length})` },
      { id: "changeOrders", label: `Change Orders (${changeOrders.length})` },
      { id: "time", label: `Time (${timeEntries.length})` },
      { id: "risk", label: "Risk Forecast" },
      { id: "template", label: "Apply Template" },
      { id: "history", label: "History" },
    ],
    [assignments.length, milestones.length, contracts.length, timeEntries.length, changeOrders.length]
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
                <div className="flex shrink-0 items-center gap-2">
                  {health ? (
                    <span
                      title={health.reasons?.join("; ")}
                      className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${HEALTH_STYLES[health.health] || HEALTH_STYLES.green}`}
                    >
                      {health.health}
                    </span>
                  ) : null}
                  <button
                    onClick={openCloneModal}
                    className="rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                  >
                    Clone Engagement
                  </button>
                </div>
              </div>

              <div className="mt-4 flex flex-wrap gap-2 border-b border-slate-200 pb-3">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => {
                      setActiveTab(tab.id);
                      if (tab.id === "risk" && !riskForecast && !riskForecastLoading) {
                        loadRiskForecast();
                      }
                    }}
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
                  {budgetBurn ? (
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                      <div className="flex items-center justify-between text-xs">
                        <p className="font-semibold uppercase tracking-wide text-slate-400">
                          Budget Burn
                        </p>
                        <p
                          className={`rounded-full px-2 py-0.5 font-semibold capitalize ${
                            budgetBurn.alert ? "bg-rose-100 text-rose-700" : "bg-emerald-100 text-emerald-700"
                          }`}
                        >
                          {budgetBurn.status.replace("_", " ")}
                        </p>
                      </div>
                      {budgetBurn.percent_consumed !== null && budgetBurn.percent_consumed !== undefined ? (
                        <>
                          <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-200">
                            <div
                              className={`h-2 rounded-full ${BUDGET_STATUS_STYLES[budgetBurn.status] || BUDGET_STATUS_STYLES.on_track}`}
                              style={{ width: `${Math.min(100, budgetBurn.percent_consumed)}%` }}
                            />
                          </div>
                          <p className="mt-1 text-xs text-slate-600">
                            {budgetBurn.percent_consumed.toFixed(1)}% of budget consumed
                            {budgetBurn.cost_to_date !== null ? ` (${formatMoney(budgetBurn.cost_to_date)} to date)` : ""}
                          </p>
                        </>
                      ) : (
                        <p className="mt-1 text-xs text-slate-500">
                          {budgetBurn.status === "no_budget"
                            ? "No budget set on this engagement."
                            : "Logged hours don't yet have an hourly rate to translate into cost."}
                        </p>
                      )}
                    </div>
                  ) : null}
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
                  {selectedProject.status === "completed" || selectedProject.close_out_notes ? (
                    <div className="rounded-xl border border-blue-200 bg-blue-50 p-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-blue-500">
                        Close-out Notes
                      </p>
                      <p className="mt-1 whitespace-pre-wrap text-sm text-slate-800">
                        {selectedProject.close_out_notes || "No retrospective notes recorded yet — add them via Edit."}
                      </p>
                    </div>
                  ) : null}
                </div>
              ) : null}

              {activeTab === "timeline" ? (
                <div className="mt-4 space-y-4">
                  {(() => {
                    const startMs = selectedProject.start_date ? new Date(selectedProject.start_date).getTime() : null;
                    const endMs = selectedProject.end_date ? new Date(selectedProject.end_date).getTime() : null;
                    if (!startMs || !endMs || endMs <= startMs) {
                      return (
                        <p className="text-sm text-slate-400">
                          Set a start and end date on this engagement to see a timeline.
                        </p>
                      );
                    }
                    const span = endMs - startMs;
                    const pct = (ms) => Math.min(100, Math.max(0, ((ms - startMs) / span) * 100));
                    const todayPct = pct(Date.now());
                    const rows = [
                      ...milestones.map((m) => ({
                        kind: "milestone",
                        key: `m-${m.id}`,
                        label: m.name,
                        status: m.status,
                        at: m.due_date ? new Date(m.due_date).getTime() : null,
                      })),
                      ...projectTasks.map((t) => ({
                        kind: "task",
                        key: `t-${t.id}`,
                        label: t.title,
                        status: t.status,
                        startAt: t.created_at ? new Date(t.created_at).getTime() : startMs,
                        at: t.due_date ? new Date(t.due_date).getTime() : null,
                      })),
                    ].filter((r) => r.at !== null);

                    return (
                      <div className="space-y-2">
                        <div className="relative h-8 rounded-xl bg-slate-100">
                          <div className="absolute inset-y-0 left-0 flex items-center pl-2 text-[10px] font-semibold text-slate-400">
                            {formatDate(selectedProject.start_date)}
                          </div>
                          <div className="absolute inset-y-0 right-0 flex items-center pr-2 text-[10px] font-semibold text-slate-400">
                            {formatDate(selectedProject.end_date)}
                          </div>
                          {todayPct >= 0 && todayPct <= 100 ? (
                            <div
                              className="absolute inset-y-0 w-0.5 bg-slate-900"
                              style={{ left: `${todayPct}%` }}
                              title="Today"
                            />
                          ) : null}
                        </div>
                        <div className="max-h-80 space-y-1.5 overflow-y-auto">
                          {rows.length === 0 ? (
                            <p className="text-sm text-slate-400">
                              No dated milestones or tasks to plot on the timeline yet.
                            </p>
                          ) : (
                            rows
                              .sort((a, b) => a.at - b.at)
                              .map((r) => (
                                <div key={r.key} className="flex items-center gap-2">
                                  <span
                                    className={`w-24 shrink-0 truncate text-xs ${r.kind === "milestone" ? "font-semibold text-slate-700" : "text-slate-500"}`}
                                    title={r.label}
                                  >
                                    {r.label}
                                  </span>
                                  <div className="relative h-4 flex-1 rounded-full bg-slate-50">
                                    {r.kind === "task" ? (
                                      <div
                                        className={`absolute inset-y-0 rounded-full ${r.status === "done" ? "bg-emerald-300" : "bg-blue-300"}`}
                                        style={{
                                          left: `${pct(Math.min(r.startAt, r.at))}%`,
                                          width: `${Math.max(1.5, pct(r.at) - pct(Math.min(r.startAt, r.at)))}%`,
                                        }}
                                        title={`${r.label} — due ${formatDate(r.at)}`}
                                      />
                                    ) : (
                                      <div
                                        className={`absolute top-1/2 h-3 w-3 -translate-y-1/2 rotate-45 ${
                                          r.status === "achieved"
                                            ? "bg-emerald-500"
                                            : r.status === "missed"
                                            ? "bg-rose-500"
                                            : "bg-slate-400"
                                        }`}
                                        style={{ left: `calc(${pct(r.at)}% - 6px)` }}
                                        title={`${r.label} — due ${formatDate(r.at)}`}
                                      />
                                    )}
                                  </div>
                                </div>
                              ))
                          )}
                        </div>
                        <p className="text-xs text-slate-400">
                          Diamonds are milestones; bars are tasks (created date → due date). Vertical line marks today.
                        </p>
                      </div>
                    );
                  })()}
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
                          <div className="flex shrink-0 items-center gap-3">
                            {a.user_id ? (
                              <label className="flex items-center gap-1 text-xs text-slate-500">
                                Alloc:
                                <input
                                  type="number"
                                  min="1"
                                  max="100"
                                  defaultValue={a.allocation_percent ?? ""}
                                  onBlur={(e) => {
                                    if (e.target.value !== String(a.allocation_percent ?? "")) {
                                      handleUpdateAssignmentAllocation(a, e.target.value);
                                    }
                                  }}
                                  placeholder="—"
                                  className="w-14 rounded-lg border border-slate-300 px-1.5 py-1 text-xs outline-none focus:border-slate-900"
                                />
                                %
                              </label>
                            ) : null}
                            <button
                              onClick={() => handleRemoveAssignment(a)}
                              className="text-xs font-semibold text-rose-500 hover:underline"
                            >
                              Remove
                            </button>
                          </div>
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
                    {assignmentForm.target_type === "user" ? (
                      <input
                        name="allocation_percent"
                        type="number"
                        min="1"
                        max="100"
                        value={assignmentForm.allocation_percent}
                        onChange={handleAssignmentFormChange}
                        placeholder="Allocation % of their time (optional)"
                        className="w-full rounded-lg border border-slate-300 px-2 py-2 text-xs outline-none focus:border-slate-900"
                      />
                    ) : null}
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
                          <div className="mt-2 flex flex-wrap items-center gap-2">
                            <select
                              value={m.status}
                              onChange={(e) => handleMilestoneStatus(m, e.target.value)}
                              className="rounded-lg border border-slate-300 px-2 py-1 text-xs outline-none focus:border-slate-900"
                            >
                              <option value="pending">Pending</option>
                              <option value="achieved">Achieved</option>
                              <option value="missed">Missed</option>
                            </select>
                            <span
                              className={`rounded-full px-2 py-1 text-[10px] font-semibold capitalize ${APPROVAL_STATUS_STYLES[m.approval_status] || APPROVAL_STATUS_STYLES.pending}`}
                            >
                              Client sign-off: {m.approval_status || "pending"}
                            </span>
                          </div>
                          {m.approval_status === "rejected" && m.rejection_reason ? (
                            <p className="mt-1 text-xs text-rose-600">Reason: {m.rejection_reason}</p>
                          ) : null}
                          <div className="mt-2 flex gap-2">
                            <button
                              onClick={() => handleMilestoneSignoff(m, "approved")}
                              disabled={m.approval_status === "approved"}
                              className="text-xs font-semibold text-emerald-600 hover:underline disabled:opacity-40"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => handleMilestoneSignoff(m, "rejected")}
                              disabled={m.approval_status === "rejected"}
                              className="text-xs font-semibold text-rose-600 hover:underline disabled:opacity-40"
                            >
                              Reject
                            </button>
                            {m.approval_status && m.approval_status !== "pending" ? (
                              <button
                                onClick={() => handleMilestoneSignoff(m, "pending")}
                                className="text-xs font-semibold text-slate-500 hover:underline"
                              >
                                Reset
                              </button>
                            ) : null}
                          </div>
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

              {activeTab === "changeOrders" ? (
                <div className="mt-4 space-y-3">
                  {contracts.length === 0 ? (
                    <p className="text-sm text-slate-400">
                      Add a contract first — change orders are scoped to a contract.
                    </p>
                  ) : (
                    <button
                      onClick={openChangeOrderModal}
                      className="rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                    >
                      + Add Change Order
                    </button>
                  )}
                  <div className="max-h-72 space-y-2 overflow-y-auto">
                    {changeOrders.length === 0 ? (
                      <p className="text-sm text-slate-400">No change orders yet.</p>
                    ) : (
                      changeOrders.map((co) => (
                        <div key={co.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <p className="text-sm font-medium text-slate-800">{co.title}</p>
                              <p className="text-xs capitalize text-slate-500">
                                {co.change_type.replace("_", " ")}
                                {co.requested_date ? ` · requested ${formatDate(co.requested_date)}` : ""}
                              </p>
                            </div>
                            <span
                              className={`shrink-0 rounded-full px-2 py-1 text-[10px] font-semibold capitalize ${CHANGE_ORDER_STATUS_STYLES[co.status] || CHANGE_ORDER_STATUS_STYLES.pending}`}
                            >
                              {co.status}
                            </span>
                          </div>
                          {co.description ? (
                            <p className="mt-1 text-xs text-slate-600">{co.description}</p>
                          ) : null}
                          <p className="mt-1 text-xs text-slate-700">
                            {co.amount_delta !== null && co.amount_delta !== undefined
                              ? `${Number(co.amount_delta) >= 0 ? "+" : ""}${formatMoney(co.amount_delta)}`
                              : ""}
                            {co.hours_delta !== null && co.hours_delta !== undefined
                              ? ` · ${Number(co.hours_delta) >= 0 ? "+" : ""}${co.hours_delta}h`
                              : ""}
                          </p>
                          {co.status === "pending" ? (
                            <div className="mt-2 flex gap-3">
                              <button
                                onClick={() => handleApproveChangeOrder(co)}
                                className="text-xs font-semibold text-emerald-600 hover:underline"
                              >
                                Approve
                              </button>
                              <button
                                onClick={() => handleRejectChangeOrder(co)}
                                className="text-xs font-semibold text-rose-600 hover:underline"
                              >
                                Reject
                              </button>
                              <button
                                onClick={() => handleDeleteChangeOrder(co)}
                                className="text-xs font-semibold text-slate-500 hover:underline"
                              >
                                Delete
                              </button>
                            </div>
                          ) : (
                            <p className="mt-2 text-[11px] text-slate-400">
                              Decided by {co.decided_by_name || co.decided_by_email || "—"} on {formatDate(co.decided_at)}
                            </p>
                          )}
                        </div>
                      ))
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
                  {timeAnomalies.length > 0 ? (
                    <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
                      {timeAnomalies.length} entr{timeAnomalies.length === 1 ? "y" : "ies"} flagged for review below
                      — not an accusation, just worth a second look.
                    </p>
                  ) : null}
                  <div className="max-h-72 space-y-2 overflow-y-auto">
                    {timeEntries.length === 0 ? (
                      <p className="text-sm text-slate-400">No time logged yet.</p>
                    ) : (
                      timeEntries.map((t) => {
                        const anomaly = timeAnomalies.find((a) => a.time_entry_id === t.id);
                        return (
                          <div
                            key={t.id}
                            className={`rounded-xl border p-3 ${
                              anomaly ? "border-amber-300 bg-amber-50" : "border-slate-200 bg-slate-50"
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="text-sm text-slate-800">
                                  {t.hours}h · {t.user_name} · {formatDate(t.entry_date)}
                                  {!t.billable ? (
                                    <span className="ml-2 text-xs text-slate-400">(non-billable)</span>
                                  ) : null}
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
                            {anomaly ? (
                              <div className="mt-2 flex flex-wrap gap-1">
                                {anomaly.flags.map((flag, idx) => (
                                  <span
                                    key={flag}
                                    title={anomaly.reasons[idx]}
                                    className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-800"
                                  >
                                    {ANOMALY_LABELS[flag] || flag}
                                  </span>
                                ))}
                              </div>
                            ) : null}
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              ) : null}

              {activeTab === "risk" ? (
                <div className="mt-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-slate-500">
                      A leading-indicator score built from budget-burn velocity, overdue work, and timeline
                      slippage — can flag trouble before the health badge above turns amber/red.
                    </p>
                    <button
                      onClick={loadRiskForecast}
                      disabled={riskForecastLoading}
                      className="shrink-0 rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-50"
                    >
                      {riskForecastLoading ? "Refreshing..." : "Refresh"}
                    </button>
                  </div>

                  {riskForecastError ? (
                    <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
                      {riskForecastError}
                    </div>
                  ) : null}

                  {riskForecastLoading && !riskForecast ? (
                    <p className="text-sm text-slate-500">Loading...</p>
                  ) : riskForecast ? (
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                          <p className="text-xs text-slate-500">Risk Score</p>
                          <p className="mt-1 text-2xl font-bold text-slate-900">{riskForecast.risk_score}</p>
                        </div>
                        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                          <p className="text-xs text-slate-500">Current Health</p>
                          <span
                            className={`mt-1 inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${
                              HEALTH_STYLES[riskForecast.current_health] || HEALTH_STYLES.green
                            }`}
                          >
                            {riskForecast.current_health}
                          </span>
                        </div>
                        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                          <p className="text-xs text-slate-500">Predicted Health</p>
                          <span
                            className={`mt-1 inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${
                              HEALTH_STYLES[riskForecast.predicted_health] || HEALTH_STYLES.green
                            }`}
                          >
                            {riskForecast.predicted_health}
                          </span>
                        </div>
                        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                          <p className="text-xs text-slate-500">Trend ({riskForecast.lookback_days}d)</p>
                          <span
                            className={`mt-1 inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${
                              TREND_STYLES[riskForecast.trend] || TREND_STYLES.stable
                            }`}
                          >
                            {riskForecast.trend.replace("_", " ")}
                            {riskForecast.score_delta != null
                              ? ` (${riskForecast.score_delta > 0 ? "+" : ""}${riskForecast.score_delta})`
                              : ""}
                          </span>
                        </div>
                      </div>

                      {riskForecast.leading_indicator ? (
                        <div className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
                          Leading indicator: the forecast is already worse than today&apos;s health badge —
                          worth a look before it catches up.
                        </div>
                      ) : null}

                      <div>
                        <p className="mb-2 text-sm font-semibold text-slate-700">Contributing Signals</p>
                        <ul className="space-y-1">
                          {riskForecast.signals.map((s, idx) => (
                            <li key={idx} className="text-sm text-slate-600">
                              • {s}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  ) : null}
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

              {activeTab === "history" ? (
                <div className="mt-4 space-y-3">
                  <p className="text-sm text-slate-500">
                    Audit trail of status, risk-level and compliance-flag changes for this
                    engagement, newest first.
                  </p>
                  {historyLoading ? (
                    <p className="text-sm text-slate-400">Loading history...</p>
                  ) : history.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500">
                      No activity recorded yet.
                    </div>
                  ) : (
                    <ul className="space-y-2">
                      {history.map((entry) => (
                        <li
                          key={entry.id}
                          className="rounded-2xl border border-slate-200 bg-white px-4 py-3"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <span
                                className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${
                                  entry.action === "project_risk_changed"
                                    ? "bg-amber-100 text-amber-700"
                                    : "bg-slate-100 text-slate-600"
                                }`}
                              >
                                {entry.action?.replaceAll("_", " ")}
                              </span>
                              <p className="mt-1 text-sm text-slate-700">{entry.description}</p>
                            </div>
                            <div className="shrink-0 text-right text-xs text-slate-400">
                              <p>{new Date(entry.created_at).toLocaleString()}</p>
                              <p>{entry.user_name || entry.user_email}</p>
                            </div>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
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
                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Close-out Notes</label>
                    <textarea
                      name="close_out_notes"
                      value={projectForm.close_out_notes}
                      onChange={handleProjectFormChange}
                      rows={3}
                      placeholder="Retrospective — what went well, what to change next time"
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

      {showChangeOrderModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-4">
              <h2 className="text-xl font-bold text-slate-900">Add Change Order</h2>
              <button
                onClick={() => setShowChangeOrderModal(false)}
                className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
              >
                Close
              </button>
            </div>
            <form onSubmit={handleCreateChangeOrder} className="space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Contract</label>
                <select
                  value={changeOrderForm.contract_id}
                  onChange={(e) => setChangeOrderForm((p) => ({ ...p, contract_id: e.target.value }))}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  required
                >
                  <option value="" disabled>
                    Select a contract
                  </option>
                  {contracts.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name || `Contract #${c.id}`} — {formatMoney(c.value)}
                    </option>
                  ))}
                </select>
              </div>
              <input
                type="text"
                placeholder="Title"
                value={changeOrderForm.title}
                onChange={(e) => setChangeOrderForm((p) => ({ ...p, title: e.target.value }))}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                required
              />
              <textarea
                placeholder="Description (optional)"
                value={changeOrderForm.description}
                onChange={(e) => setChangeOrderForm((p) => ({ ...p, description: e.target.value }))}
                rows={2}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
              />
              <select
                value={changeOrderForm.change_type}
                onChange={(e) => setChangeOrderForm((p) => ({ ...p, change_type: e.target.value }))}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
              >
                {CHANGE_ORDER_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t.replace("_", " ")}
                  </option>
                ))}
              </select>
              <div className="grid grid-cols-2 gap-3">
                <input
                  type="number"
                  step="0.01"
                  placeholder="Amount delta ($)"
                  value={changeOrderForm.amount_delta}
                  onChange={(e) => setChangeOrderForm((p) => ({ ...p, amount_delta: e.target.value }))}
                  className="rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
                <input
                  type="number"
                  step="0.25"
                  placeholder="Hours delta"
                  value={changeOrderForm.hours_delta}
                  onChange={(e) => setChangeOrderForm((p) => ({ ...p, hours_delta: e.target.value }))}
                  className="rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Requested Date</label>
                <input
                  type="date"
                  value={changeOrderForm.requested_date}
                  onChange={(e) => setChangeOrderForm((p) => ({ ...p, requested_date: e.target.value }))}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                />
              </div>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowChangeOrderModal(false)}
                  className="rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-70"
                >
                  {saving ? "Saving..." : "Add Change Order"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {showCloneModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-4">
              <h2 className="text-xl font-bold text-slate-900">Clone Engagement</h2>
              <button
                onClick={() => setShowCloneModal(false)}
                className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
              >
                Close
              </button>
            </div>
            <p className="mb-4 text-xs text-slate-500">
              Useful for recurring work like an annual audit — copies the engagement setup with new dates.
            </p>
            <form onSubmit={handleCloneProject} className="space-y-4">
              <input
                type="text"
                placeholder="New engagement name"
                value={cloneForm.name}
                onChange={(e) => setCloneForm((p) => ({ ...p, name: e.target.value }))}
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
              />
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Start Date</label>
                  <input
                    type="date"
                    value={cloneForm.start_date}
                    onChange={(e) => setCloneForm((p) => ({ ...p, start_date: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">End Date</label>
                  <input
                    type="date"
                    value={cloneForm.end_date}
                    onChange={(e) => setCloneForm((p) => ({ ...p, end_date: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={cloneForm.include_team}
                    onChange={(e) => setCloneForm((p) => ({ ...p, include_team: e.target.checked }))}
                  />
                  Copy team assignments
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={cloneForm.include_milestones}
                    onChange={(e) => setCloneForm((p) => ({ ...p, include_milestones: e.target.checked }))}
                  />
                  Copy milestones
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={cloneForm.include_tasks}
                    onChange={(e) => setCloneForm((p) => ({ ...p, include_tasks: e.target.checked }))}
                  />
                  Copy open tasks
                </label>
              </div>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowCloneModal(false)}
                  className="rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={cloning}
                  className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-70"
                >
                  {cloning ? "Cloning..." : "Clone Engagement"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
