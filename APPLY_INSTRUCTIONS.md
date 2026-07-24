# How to apply these changes

This folder mirrors the repo's directory structure. Copy each file into the
matching path in your local clone (overwriting the existing ones), then:

## 1. Delete one obsolete file
```
backend/app/core/fake_db.py
```
It's replaced by `backend/app/models/user.py` + `backend/app/core/seed.py`.

## 2. New files (no existing counterpart to overwrite)
- backend/app/models/user.py
- backend/app/core/seed.py
- backend/app/core/rate_limit.py
- backend/app/requirements.txt
- backend/.env.example

## 3. Modified files (overwrite existing)
- .gitignore
- README.md
- backend/app/core/config.py
- backend/app/core/deps.py
- backend/app/db/base.py
- backend/app/main.py
- backend/app/routes/auth.py
- backend/app/routes/clients.py
- backend/app/routes/files.py
- backend/app/routes/protected.py
- backend/app/routes/users.py
- backend/app/schemas/user_management.py

## 4. Set up your environment
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"   # paste into .env as SECRET_KEY
```

## 5. Also worth doing before you commit
`__pycache__/*.pyc` files were previously committed to the repo (the new
.gitignore now excludes them going forward, but git won't remove
already-tracked files on its own). Run:
```bash
git rm -r --cached '**/__pycache__' 2>/dev/null
```
from the repo root to stop tracking them.
