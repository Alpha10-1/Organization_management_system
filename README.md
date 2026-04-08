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
│   ├── uploads/
│   └── main.py
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── dashboard/
│   │   │   ├── login/
│   │   ├── lib/
│   │   └── components/
│   └── package.json
│
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
```

If you do not have a requirements file yet:

```bash
pip install fastapi uvicorn sqlalchemy python-multipart passlib[bcrypt] python-jose
```

### Run backend

```bash
uvicorn app.main:app --reload
```

Open:
`http://127.0.0.1:8000/docs`

---

## Frontend Setup (Next.js)

```bash
cd frontend
npm install
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

- JWT authentication for protected routes
- Backend-enforced file access control
- Role-based permissions
- Secure file download via authenticated requests
- Activity audit logging

---

## Current Limitations

- Users are currently stored in memory and are not persistent after backend restart
- Files are stored locally instead of cloud storage
- No email verification yet

---

## Future Improvements

- Move users to database
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
