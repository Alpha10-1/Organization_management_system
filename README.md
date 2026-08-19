# Organization Management System

A full-stack **Organization Management System** built with **Next.js (frontend)** and **FastAPI (backend)**.

This system helps organizations manage:
- 👥 Clients
- 📁 Secure Files
- 📊 Dashboard Analytics
- 🧾 Activity Logs
- 🔐 Role-Based User Management

---

## Features

### Authentication & Roles
- JWT-based authentication
- Role-based access:
  - **Admin**
  - **Staff**
- Secure route protection on both frontend and backend

### Client Management
- Create, edit, delete clients
- Search and filter clients
- Client detail panel
- Status tracking (Active, Pending, Closed)

### File Management (Secure)
- Upload files linked to clients
- Pluggable storage backend: local disk by default, S3-compatible
  (AWS S3, MinIO, R2, etc) via `STORAGE_BACKEND=s3` — see `.env.example`
- JWT-protected file access
- Authenticated file download
- File preview for:
  - Images
  - PDFs
- File search and filtering:
  - by name
  - by type
  - by client
  - “My uploads only”

### Dashboard
- Real-time stats:
  - Total clients
  - Active / Pending / Closed clients
  - Files count
- Charts for client distribution
- Recent clients
- Recent activity feed

### Activity Logging
All important actions are logged:
- Login
- Client created / updated / deleted
- File uploaded / downloaded / deleted
- User management actions

### User Management (Admin Only)
- Create users
- Assign roles (admin / staff)
- Enable / disable users
- Update roles dynamically

---

## Tech Stack

### Frontend
- Next.js
- React
- Tailwind CSS
- Recharts

### Backend
- FastAPI
- SQLite
- SQLAlchemy
- JWT Authentication

---

## Project Structure

```text
Organization_management_system/
│
├── backend/
│   ├── app/
│   │   ├── models/
│   │   ├── routes/
│   │   ├── schemas/
│   │   ├── core/
│   │   └── db/
│   ├── alembic/           # database migrations
│   ├── tests/             # pytest suite
│   ├── uploads/
│   └── main.py
│
├── src/                   # Next.js frontend (at repo root, not frontend/)
│   ├── app/
│   │   ├── dashboard/
│   │   ├── login/
│   ├── lib/
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

---

## API Endpoints Overview

### Auth
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

### Clients
- `GET /clients`
- `POST /clients`
- `PUT /clients/{id}`
- `DELETE /clients/{id}`

### Files
- `POST /files/upload`
- `GET /files`
- `GET /files/{id}/download`
- `DELETE /files/{id}`

### Activity
- `GET /activity-logs`

### Users (Admin)
- `GET /users`
- `POST /users`
- `PATCH /users/{email}/role`
- `PATCH /users/{email}/status`

---

## Security Features

- JWT authentication stored in an `httpOnly`, `SameSite=Lax` cookie (not
  readable from JS, mitigating token theft via XSS), with `Authorization:
  Bearer` header support retained for API clients
- Per-account and per-IP login rate limiting
- Backend-enforced file access control
- Role-based permissions
- Secure file download via authenticated requests
- Soft delete for clients and files (rows are kept for audit/recovery,
  just hidden from normal queries)
- Activity audit logging

---

## Current Limitations

- No email verification or password reset flow yet
- Login rate limiting is in-memory and per-process — fine for a single
  uvicorn worker, but needs a shared store (e.g. Redis) before running
  with multiple workers/replicas

---

## Future Improvements

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
