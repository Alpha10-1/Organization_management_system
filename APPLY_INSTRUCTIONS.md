# How to apply these changes

This folder mirrors the repo's directory structure. Copy each file into the
matching path in your local clone (overwriting the existing ones).

## 1. New files (no existing counterpart to overwrite)
- backend/app/models/client_contact.py
- backend/app/models/contract.py
- backend/app/models/task_dependency.py
- backend/app/models/task_template.py
- backend/app/models/milestone.py
- backend/app/core/client_health.py
- backend/app/routes/contracts.py
- backend/app/routes/milestones.py
- backend/app/routes/task_templates.py
- backend/app/schemas/client_contact.py
- backend/app/schemas/contract.py
- backend/app/schemas/milestone.py
- backend/app/schemas/task_dependency.py
- backend/app/schemas/task_template.py
- backend/alembic/versions/dd16b268bb45_add_contacts_contracts_task_.py
- backend/tests/test_client_contacts.py
- backend/tests/test_contracts.py
- backend/tests/test_task_enhancements.py
- backend/tests/test_documents_and_dashboards.py

## 2. Modified files (overwrite existing)
- backend/app/db/base.py
- backend/app/main.py
- backend/app/models/client.py
- backend/app/models/file_record.py
- backend/app/models/task.py
- backend/app/routes/clients.py
- backend/app/routes/files.py
- backend/app/routes/reports.py
- backend/app/routes/tasks.py
- backend/app/schemas/client.py
- backend/app/schemas/file_record.py
- backend/app/schemas/task.py

## 3. Apply the migration and verify

```bash
cd backend
rm -f organization.db     # optional — start from a clean DB, or keep your existing one
alembic upgrade head
pytest                    # 124 tests should pass
```

See `CHANGES_MANIFEST.md` for what to do if `alembic upgrade head` errors on
a totally fresh/empty database, and for the full new API surface.

## 4. Nothing to change on the frontend yet
This pass is backend-only (models, routes, migration, tests). The new
endpoints — contacts, contracts, milestones, task templates, dependencies,
subtasks, recurrence, health, and the two dashboard endpoints — are all
live and ready for a frontend pass whenever you're ready for it.
