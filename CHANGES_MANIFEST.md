# File manifest — Contacts, Contracts, Task Enhancements, Documents & Dashboards

Extract this zip into the root of `Organization_management_system/`, preserving
the folder structure — every path below is relative to the repo root.

This session picked up from the last push (`feat: add project and time entry
management`), which already covered the Project/Engagement model and Time
Tracking. This pass adds everything else from the brief: client contacts &
hierarchy, contracts/SOWs with margin visibility, task subtasks/dependencies/
recurrence/templates, project milestones, client relationship health,
project-scoped documents, and per-partner/per-client reporting dashboards.

One file was **deleted**, not included here: `backend/organization.db`
(already gitignored — remove it if it's still sitting in your working copy).

## New files

**Models**
- `backend/app/models/client_contact.py` — `ClientContact` (name, role, email, phone, is_primary)
- `backend/app/models/contract.py` — `Contract`/SOW (billing_type, value, hourly_rate, dates, status)
- `backend/app/models/task_dependency.py` — `TaskDependency` (blocked_by/blocks edges)
- `backend/app/models/task_template.py` — `TaskTemplate` + `TaskTemplateItem` (cloneable checklists)
- `backend/app/models/milestone.py` — `Milestone` (project-level checkpoints)

**Core logic**
- `backend/app/core/client_health.py` — green/amber/red relationship-health computation

**Routes**
- `backend/app/routes/contracts.py` — Contract CRUD + `/contracts/{id}/margin`
- `backend/app/routes/milestones.py` — Milestone CRUD
- `backend/app/routes/task_templates.py` — Template CRUD + `/task-templates/{id}/apply`

**Schemas**
- `backend/app/schemas/client_contact.py`
- `backend/app/schemas/contract.py`
- `backend/app/schemas/milestone.py`
- `backend/app/schemas/task_dependency.py`
- `backend/app/schemas/task_template.py`

**Migration**
- `backend/alembic/versions/dd16b268bb45_add_contacts_contracts_task_.py`

**Tests** (46 new tests, 124 total passing)
- `backend/tests/test_client_contacts.py` — contacts CRUD, hierarchy, relationship health
- `backend/tests/test_contracts.py` — contract CRUD, margin visibility
- `backend/tests/test_task_enhancements.py` — subtasks, dependencies (incl. cycle detection), recurrence, milestones, templates
- `backend/tests/test_documents_and_dashboards.py` — project-scoped files, partner/client dashboards

## Modified files

- `backend/app/db/base.py` — registers all new models with `Base.metadata`
- `backend/app/main.py` — wires up the three new routers
- `backend/app/models/client.py` — adds `parent_client_id` (group structures) and `relationship_health` (manual override)
- `backend/app/models/file_record.py` — adds `project_id` (documents scoped to an engagement, not just a client)
- `backend/app/models/task.py` — adds `parent_task_id` (subtasks), `recurrence_rule`/`recurrence_end_date`/`recurrence_parent_id`
- `backend/app/routes/clients.py` — parent-client validation, `/clients/{id}/health`, full contacts CRUD nested under `/clients/{id}/contacts`
- `backend/app/routes/files.py` — `project_id` accepted on upload, filterable on list
- `backend/app/routes/reports.py` — `/reports/dashboard/partner` and `/reports/dashboard/client/{id}`
- `backend/app/routes/tasks.py` — subtask validation, recurrence auto-cloning on completion, dependency endpoints with cycle detection, `/tasks/{id}/detail` rollup
- `backend/app/schemas/client.py` — `parent_client_id`, `relationship_health`, new `ClientHealth` schema
- `backend/app/schemas/file_record.py` — `project_id`
- `backend/app/schemas/task.py` — subtask/recurrence fields, new `TaskDetail` schema

## New API surface at a glance

```
GET/POST          /clients/{id}/contacts
PUT/DELETE        /clients/{id}/contacts/{contact_id}
GET               /clients/{id}/health

GET/POST          /contracts/
GET/PUT/DELETE    /contracts/{id}
GET               /contracts/{id}/margin

GET/POST          /milestones/
GET/PUT/DELETE    /milestones/{id}

GET/POST          /task-templates/
GET/PUT/DELETE    /task-templates/{id}
POST              /task-templates/{id}/apply

GET/POST          /tasks/{id}/dependencies
DELETE            /tasks/{id}/dependencies/{dependency_id}
GET               /tasks/{id}/detail

GET               /reports/dashboard/partner?partner_email=...
GET               /reports/dashboard/client/{id}
```

## After extracting

```bash
cd backend
rm -f organization.db          # if present — start clean or keep your existing data
alembic upgrade head           # applies the new migration (safe on a create_all'd DB too)
pytest                         # 124 tests should pass
```

### A note on the migration if `alembic upgrade head` errors
This repo's baseline migration assumes the schema already exists (it was
originally built via `Base.metadata.create_all`, not tracked from an empty
DB — see the "Schema-ahead-of-Alembic" note in your own key-learnings).
If you're starting from a totally empty `organization.db` and `alembic
upgrade head` fails on the *first* migration, build the schema and stamp it
first:
```bash
rm -f organization.db
python -c "from app.db.session import Base, engine; import app.db.base; Base.metadata.create_all(bind=engine)"
alembic stamp head
```
If you already have a working DB from the last session (Projects/Time
Tracking in place), just run `alembic upgrade head` directly — it'll apply
cleanly on top.
