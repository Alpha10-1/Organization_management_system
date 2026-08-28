# Organization Management System

A full-stack **Organization Management System** for a professional
services firm (audit / tax / advisory), built with **Next.js**
(frontend) and **FastAPI** (backend). The reference model throughout is
a Deloitte-style firm: engagements rather than generic "projects,"
partners and managers rather than generic "staff," workpaper review
chains, independence checks, and a client who is a first-class actor in
the system, not just a record.

It covers the full lifecycle of client work:
- 🤝 **CRM & pipeline** — prospects → proposals → won engagements
- 📁 **Engagement management** — tasks, milestones, staffing, capacity
- 🧾 **Billing** — time entries → WIP → invoices → realization rate
- 🛡️ **Compliance** — independence/conflict checks, workpaper review
  chains, audit trail
- 🌐 **Client portal** — a scoped client-facing app for milestone
  sign-off and document requests
- ✍️ **E-signature** — pluggable engagement-letter / change-order signing
- 🧠 **Intelligence layer** — engagement risk prediction, time-entry
  anomaly detection, natural-language engagement search, document
  intelligence
- 🔐 **RBAC** — a delegated permission catalog on top of admin/staff,
  plus department-scoped writes

---

## Features

### Authentication & Roles
- JWT-based authentication, stored in an `httpOnly` cookie
- Email verification and self-service password reset (staff)
- Role-based access: **Admin** / **Staff**, plus admin-defined **custom
  roles** built from a 10-key permission catalog (see RBAC below)
- Department-scoped writes: staff can be restricted to acting only
  within their own department
- Secure route protection on both frontend and backend

### RBAC (Role-Based Access Control)
- Three seeded system roles (Partner, Manager, Engagement Quality
  Reviewer) plus admin-defined custom roles
- A 10-key permission catalog admins assign per role
- Privilege-escalation guard: a user with `users.manage` cannot use it
  to create an admin account

### Client Management
- Business/individual clients, contacts, notes, tags
- Client relationship health tracking
- Client hierarchy (parent/subsidiary clients)
- Search and filter; soft delete (records are kept for audit/recovery)

### Engagement / Project Management
- Engagements (audit, tax, advisory, etc.) with status and type
- Tasks, task dependencies, and reusable task templates
- Milestones with client-facing sign-off (approve / request changes)
- Staffing via resource requests, with independence/conflict-of-interest
  checks before someone is staffed on an engagement
- Capacity forecasting: rolling utilization view across users and
  departments

### Billing & Invoicing
- Time entries roll up into work-in-progress (WIP)
- Invoice generation from WIP
- Realization rate reporting (billed vs. worked) per engagement, per
  partner, per department
- Contracts / SOWs and change orders, with a full audit trail

### Compliance
- **Independence & conflict-of-interest checks**: run a conflict check
  before staffing, log disclosures, and record documented overrides
- **Workpaper review chains**: preparer → reviewer → partner sign-off,
  with a per-workpaper status and full review-event history

### Client Portal
A scoped-down, client-facing application (`/portal/*` on the frontend,
`/portal/*` on the API) — separate login, separate cookie, separate
`actor="client"` JWT claim from the staff app:
- Clients see their own engagements only
- **Milestones**: view status, approve or request changes — real
  client sign-off, not staff recording it on the client's behalf
- **PBC (prepared-by-client) requests**: a structured, due-dated
  checklist of documents needed from the client, with upload
- **Shared files**: browse and download files staff have shared on the
  engagement
- Staff manage portal access (invite, disable/enable, revoke) from the
  client detail view in the dashboard

### E-Signature
Pluggable engagement-letter and change-order signing (mock provider by
default, DocuSign-shaped webhook contract) — a signed change order
triggers the same e-sign flow as the original contract.

### CRM / Pipeline
Prospects → proposals → won engagements, so the system covers the full
client lifecycle, not just active engagement work.

### Intelligence Layer
- **Engagement risk prediction**: heuristic scoring over budget-burn
  trajectory, overdue tasks, and historical health scores, flagging
  engagements trending toward trouble before the health score turns red
- **Time-entry anomaly detection**: flags suspicious patterns (e.g.
  large late-logged entries, patterns resembling WIP padding)
- **Natural-language engagement search**: plain-language search across
  engagement notes, close-out notes, and the risk audit trail
- **Document intelligence**: extracts key figures/dates from uploaded
  client documents to help pre-populate engagement data

### Knowledge Base
Aggregates close-out notes and engagement retrospectives across the
firm into a searchable "how did we handle this before" resource.

### File Management (Secure)
- Upload files linked to clients/engagements
- Pluggable storage backend: local disk by default, S3-compatible
  (AWS S3, MinIO, R2, etc) via `STORAGE_BACKEND=s3` — see `.env.example`
- JWT-protected file access, authenticated download, preview for
  images/PDFs
- Search and filter by name, type, client, or "my uploads only"

### Dashboard & Reporting
- Real-time stats, charts, recent activity feed
- Realization, capacity, and risk reporting views

### Activity Logging
Every significant action (login, engagement/client/file/user changes,
milestone sign-offs, PBC submissions, invoicing, portal activity, etc.)
is written to an audit trail.

### User Management (Admin Only)
- Create users, assign system or custom roles, enable/disable accounts

---

## Tech Stack

### Frontend
- Next.js
- React
- Tailwind CSS
- Recharts
- Lucide React (icons)

### Backend
- FastAPI
- SQLAlchemy + Alembic (migrations)
- SQLite by default, Postgres-swappable via `DATABASE_URL`
- JWT authentication
- boto3 (pluggable S3-compatible storage)

---

## Project Structure

```text
Organization_management_system/
│
├── backend/
│   ├── app/
│   │   ├── models/        # ~30 SQLAlchemy models: engagements, billing,
│   │   │                  #   compliance, portal, CRM, intelligence layer
│   │   ├── routes/        # ~30 route modules, grouped by domain
│   │   ├── schemas/
│   │   ├── core/          # auth, RBAC, storage backend, activity log, etc.
│   │   └── db/
│   ├── alembic/           # database migrations
│   ├── tests/             # pytest suite (500+ tests)
│   └── main.py
│
├── src/                   # Next.js frontend (at repo root, not frontend/)
│   ├── app/
│   │   ├── dashboard/     # staff-facing app (engagements, billing, RBAC, ...)
│   │   ├── portal/        # client-facing app (separate auth/session)
│   │   ├── login/, forgot-password/, reset-password/, verify-email/
│   ├── lib/                # api.js (staff) + portal-api.js (client portal)
│   └── components/
│
├── .github/workflows/     # CI: backend tests + frontend build
└── README.md
```

---

## Setup Instructions

### 1. Clone Repository

```bash
git clone https://github.com/Alpha10-1/Organization_management_system.git
cd Organization_management_system
```

---

## Backend Setup (FastAPI)

### Install dependencies

```bash
cd backend
pip install -r requirements.txt
# or, to also run the test suite: pip install -r requirements-dev.txt
```

### Configure environment

```bash
cp .env.example .env
# then set SECRET_KEY in .env, e.g.:
python -c "import secrets; print(secrets.token_hex(32))"
```

Without a `SECRET_KEY`, the app still runs in development (it generates a
temporary one and warns you), but every restart invalidates existing logins.
Setting `ENVIRONMENT=production` without a real `SECRET_KEY` will refuse to
start at all.

`CORS_ORIGINS`, `COOKIE_SECURE`, `UPLOAD_DIR`, `STORAGE_BACKEND`, and
`DATABASE_URL` are also configurable — see the comments in `.env.example`
for details. All default to sensible values for local development if left
unset.

### Apply database migrations

Schema changes are managed with Alembic rather than by hand-editing the
database.

```bash
alembic upgrade head
```

**Note:** the baseline migration assumes the schema already exists — it was
originally captured from a database built via `Base.metadata.create_all`,
not from empty tables, so `alembic upgrade head` alone will fail against a
truly empty `organization.db` (`no such table: clients`). Starting the
app once (`uvicorn app.main:app`) runs `create_all` automatically, so the
usual flow is:

```bash
rm -f organization.db          # optional: start clean
python -c "from app.db.session import Base, engine; import app.db.base; Base.metadata.create_all(bind=engine)"
alembic stamp head              # mark the create_all'd schema as up to date
```

If you're picking up an *existing* database that was already tracked by
Alembic (e.g. from a previous session), just run `alembic upgrade head`
directly — it applies cleanly on top.

### Run backend

```bash
uvicorn app.main:app --reload
```

Open:
`http://localhost:8000/docs`

### Run tests

```bash
pip install -r requirements-dev.txt
pytest
```

### Optional: local S3-compatible storage (MinIO)

File uploads default to local disk (`STORAGE_BACKEND=local`, the
zero-config path — nothing below is required to run the app). To develop
or test against the S3 code path without touching a real AWS bucket, this
repo ships a `docker-compose.yml` that runs [MinIO](https://min.io/), an
S3-compatible object store, plus a one-shot job that creates the bucket
the backend expects.

```bash
docker compose up -d
```

- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001` (login `minioadmin` / `minioadmin`)

The `createbuckets` container exits right after creating the bucket —
`docker compose ps` showing it as `Exited (0)` is expected, not a failure.

Then point the backend at it (uncomment the "Local MinIO quickstart"
block at the bottom of `backend/.env.example`, or set directly):

```bash
STORAGE_BACKEND=s3
S3_BUCKET=oms-uploads
S3_ENDPOINT_URL=http://localhost:9000
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
```

Restart the backend and uploads now go to MinIO — visible in the console
at `localhost:9001`. Switching back to local disk is just deleting/
commenting those env vars (or setting `STORAGE_BACKEND=local`) and
restarting; no code or data-model changes either way.

To wipe the dev bucket and start over:

```bash
docker compose down -v
```

---

## Frontend Setup (Next.js)

```bash
npm install
cp .env.example .env.local   # set NEXT_PUBLIC_API_URL if not using the default
npm run dev
```

Open:
`http://localhost:3000`

---

## Troubleshooting: logged in but every request 401s

If `POST /auth/login` returns `200` but `GET /auth/me` (and everything else)
immediately returns `401`, this is almost always a **hostname mismatch**
between frontend and backend. Browsers treat `localhost` and `127.0.0.1` as
different sites, so the login cookie (`SameSite=Lax`) gets set but never
sent back if, say, you open the frontend at `localhost:3000` while
`NEXT_PUBLIC_API_URL` points at `127.0.0.1:8000` (or vice versa).

Fix: make sure the URL you use in your browser for the frontend and the
`NEXT_PUBLIC_API_URL` value both use the **same hostname** (both
`localhost`, or both `127.0.0.1`), then restart `npm run dev` so the env
change takes effect.

---

## Demo Accounts

| Role  | Email          | Password   |
|-------|----------------|------------|
| Admin | admin@org.com  | Admin123!  |
| Staff | staff@org.com  | Staff123!  |

There is no seeded client-portal demo account — a portal account only
exists once a staff user invites one. To try the client portal:
1. Log in to the dashboard as admin, open **Clients**, select a client
   (create one first if needed, and give it at least one engagement)
2. In the client detail panel, use **Portal Access → Invite user**
3. In development, the invite/reset email is written to the backend
   console/log rather than actually sent — copy the `token=...` value
   from there
4. Visit `/portal/set-password?token=<that token>` on the frontend to
   set a password, then sign in at `/portal/login`

---

## API Endpoints Overview

The API is organized into ~30 route modules under `backend/app/routes/`.
Full request/response schemas are always available at `/docs`
(Swagger UI) once the backend is running — the list below is a map of
what exists, not the full contract.

### Auth (staff)
`POST /auth/login` · `POST /auth/logout` · `GET /auth/me` ·
`POST /auth/request-password-reset` · `POST /auth/reset-password` ·
`POST /auth/request-verification` · `POST /auth/verify-email`

### Client Portal (client-facing, separate cookie/session)
`POST /portal/auth/login` · `POST /portal/auth/logout` ·
`GET /portal/auth/me` · `POST /portal/auth/request-password-reset` ·
`POST /portal/auth/reset-password` ·
`GET /portal/engagements` · `GET /portal/engagements/{id}` ·
`GET /portal/engagements/{id}/milestones` ·
`PUT /portal/engagements/{id}/milestones/{id}/signoff` ·
`GET /portal/engagements/{id}/pbc-requests` ·
`POST /portal/pbc-requests/{id}/upload` ·
`GET /portal/engagements/{id}/files` ·
`GET /portal/files/{id}/download`

### Client Portal Access (staff-managed)
`GET/POST /clients/{id}/portal-users` ·
`PUT/DELETE /clients/{id}/portal-users/{id}`

### Clients
`GET/POST /clients` · `PUT/DELETE /clients/{id}` ·
contacts, notes, tags, and health sub-resources under `/clients/{id}/*`

### Engagements / Projects
`GET/POST /projects` · `PUT/DELETE /projects/{id}` ·
tasks, task templates, milestones, staffing (resource requests)

### Billing
`GET/POST /contracts` · `POST /change-orders` ·
`GET/POST /time-entries` · `GET/POST /invoices`
(realization-rate figures surface via `/reports`)

### Compliance
`GET/POST /independence/disclosures` · `GET /independence/check` ·
`GET/POST /independence/overrides` ·
`GET/POST /workpapers` · `PUT /workpapers/{id}/submit` ·
`PUT /workpapers/{id}/review` · `PUT /workpapers/{id}/partner-signoff`

### E-Signature
`POST /esign/webhook` (provider-driven; clients sign through the
provider's hosted UI, this closes the loop back into the contract)

### CRM / Pipeline
`GET/POST /prospects` · `GET/POST /proposals`

### Intelligence Layer
`GET /search` (natural-language engagement search) ·
risk and anomaly signals surface via `/reports` and on engagement
records (see `app/core/engagement_health.py`,
`app/core/risk_prediction.py`, `app/core/time_anomaly.py`,
`app/core/document_intelligence.py`)

### Knowledge Base
`GET/POST /knowledge-base`

### Capacity
`GET /capacity/forecast` · `GET /capacity/forecast/summary`

### Files
`POST /files/upload` · `GET /files` · `GET /files/{id}/download` ·
`DELETE /files/{id}` · `POST /files/bulk/download`

### Activity
`GET /activity-logs`

### Users & RBAC (Admin)
`GET/POST /users` · `PATCH /users/{email}/role` ·
`PATCH /users/{email}/status` · `GET/POST /roles`

---

## Security Features

- JWT authentication stored in an `httpOnly`, `SameSite=Lax` cookie (not
  readable from JS, mitigating token theft via XSS), with `Authorization:
  Bearer` header support retained for API clients
- The client portal uses a separate cookie (`portal_access_token`) and a
  separate `actor="client"` JWT claim, so a staff session and a client
  session can coexist in the same browser without crossing over
- Email verification and self-service password reset for staff accounts
  (and the equivalent invite/reset flow for portal accounts)
- Per-account and per-IP login rate limiting
- Backend-enforced file access control, scoped per actor (staff vs.
  client) and, for clients, to their own engagements only
- Role-based permissions: admin/staff plus a delegated RBAC permission
  catalog, with a privilege-escalation guard on role management
- Department-scoped writes
- Secure file download via authenticated requests
- Soft delete for clients and files (rows are kept for audit/recovery,
  just hidden from normal queries)
- Activity audit logging across staff and client-portal actions

---

## Current Limitations

- SSO (SAML/OIDC) is not implemented — RBAC covers fine-grained
  permissions, but there's no external identity-provider integration yet
- E-signature is backend-only (provider-webhook driven); there's no
  staff-side UI yet for tracking/initiating envelopes
- Login rate limiting is in-memory and per-process — fine for a single
  uvicorn worker, but needs a shared store (e.g. Redis) before running
  with multiple workers/replicas
- `npm audit` currently reports high-severity advisories against
  upstream Next.js/transitive packages at their latest available
  versions — worth periodically rechecking as upstream patches land

---

## Future Improvements

- SSO (SAML/OIDC) integration
- Staff-side e-signature envelope tracking UI
- Notifications system
- Real-time updates (WebSockets)
- Advanced reporting and exports
- Mobile PWA support

---

## Author

**Alfah Lubisi**

- GitHub: https://github.com/Alpha10-1
- Email: lubisialpha@gmail.com

---

## License

This project is open-source and available under the MIT License.
