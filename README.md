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
- Secure file storage (local disk for development)
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

`CORS_ORIGINS`, `COOKIE_SECURE`, `UPLOAD_DIR`, and `DATABASE_URL` are also
configurable — see the comments in `.env.example` for details. All default
to sensible values for local development if left unset.

### Apply database migrations

Schema changes are managed with Alembic rather than by hand-editing the
database.

```bash
alembic upgrade head
```

This is safe to run on a brand-new database (it creates the schema from
scratch) or an existing one (it applies only what's missing).

### Run backend

```bash
uvicorn app.main:app --reload
```

Open:
`http://127.0.0.1:8000/docs`

### Run tests

```bash
pip install -r requirements-dev.txt
pytest
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

- Files are stored locally instead of cloud storage
- No email verification or password reset flow yet
- Login rate limiting is in-memory and per-process — fine for a single
  uvicorn worker, but needs a shared store (e.g. Redis) before running
  with multiple workers/replicas

---

## Future Improvements

- Cloud file storage (AWS S3 / Firebase)
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
