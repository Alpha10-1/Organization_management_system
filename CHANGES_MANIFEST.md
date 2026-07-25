# File manifest

Extract this zip into the root of `Organization_management_system/`, preserving
the folder structure — every path below is relative to the repo root.

One file was **deleted**, not included here: `backend/organization.db`
(it's no longer tracked in git — see #1 below).

## New files

- `.env.example` — frontend env template (`NEXT_PUBLIC_API_URL`)
- `.github/workflows/ci.yml` — CI: backend tests + frontend build
- `backend/alembic.ini`, `backend/alembic/**` — migrations setup + baseline migration
- `backend/app/core/time.py` — shared tz-aware `utcnow()` helper
- `backend/pytest.ini`, `backend/requirements-dev.txt`
- `backend/tests/**` — pytest suite (25 tests)

## Modified files

- `.gitignore` — ignore `*.db`/`*.sqlite*`
- `README.md` — corrected layout, added migration/test/env docs
- `backend/.env.example` — documented `CORS_ORIGINS`, `COOKIE_SECURE`, `UPLOAD_DIR`
- `backend/app/core/config.py` — configurable CORS origins + cookie security flag
- `backend/app/core/deps.py` — auth accepts cookie or Authorization header
- `backend/app/db/session.py` — absolute/configurable `DATABASE_URL`
- `backend/app/main.py` — CORS origins from settings
- `backend/app/models/{activity_log,client,file_record,user}.py` — tz-aware timestamps; `deleted_at` + indexes on `client.py`/`file_record.py`
- `backend/app/routes/auth.py` — httpOnly cookie login/logout
- `backend/app/routes/clients.py` — soft delete, filters everywhere
- `backend/app/routes/files.py` — soft delete, absolute upload dir, filters everywhere
- `backend/app/routes/protected.py` — dashboard stats exclude soft-deleted rows
- `src/lib/api.js` — cookie-based requests (`credentials: "include"`), no more token params
- `src/lib/auth.js` — replaced localStorage helpers with explanatory comment
- `src/components/auth/ProtectedRoute.js` — checks session via `/auth/me`, not localStorage
- `src/components/layout/AppHeader.js` — logout calls backend to clear cookie
- `src/app/login/page.js` — no client-side token storage
- `src/app/dashboard/layout.js`, `src/app/dashboard/{page,users/page,files/page,clients/page,reports/page}.js` — removed `getToken()`/token args; fixed a missing `fetchCurrentUser` import in `users/page.js`

## After extracting

```bash
cd backend
pip install -r requirements-dev.txt
alembic upgrade head        # apply schema changes (safe on new or existing DB)
pytest                      # 25 tests should pass

cd ..
npm install
cp .env.example .env.local  # set NEXT_PUBLIC_API_URL if needed
```
