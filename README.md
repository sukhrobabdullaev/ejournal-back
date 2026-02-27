# Ejournal - Manuscript Submission & Peer Review Platform

Django + DRF backend for a single-journal manuscript submission and peer review system.  
On-premise deployment: local storage, no AWS required.

## Docker (recommended)

1. Copy env and run:
   ```bash
   cp .env.docker.example .env
   docker compose up -d
   ```
2. API: http://localhost:8000/api/  
   Admin: http://localhost:8000/admin/ — login: `admin@ejournal.local` / `admin123`

Services: `web` (Django/Gunicorn), `db` (PostgreSQL), `redis`, `celery` (worker).  
Seed runs on startup. Manual: `python manage.py seed_db` or `seed_db --sample-users`

## Local Setup

1. Create virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

3. Create PostgreSQL database `ejournal` and set `DATABASE_URL` in `.env`.

4. Run migrations:
   ```bash
   python manage.py migrate
   ```

5. Run dev server:
   ```bash
   python manage.py runserver
   ```

6. Run Celery worker (separate terminal; required for email reminders):
   ```bash
   celery -A ejournal worker -l info
   ```

## API

### Auth & Account
- `POST /api/auth/signup` - Create account (roles: author, reviewer, editor; why_to_be required for reviewer/editor)
- `POST /api/auth/login` - Get JWT access + refresh tokens
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/me` - Current user profile
- `PATCH /api/me` - Update profile
### Integrations
- `POST /api/orcid/connect` - Connect ORCID (stub; send `orcid_id` in body)

### Submissions (Author)
- `GET /api/topic-areas` - List topic areas
- `POST /api/submissions` - Create draft
- `GET /api/submissions` - List own submissions
- `GET /api/submissions/{id}` - Get submission
- `PATCH /api/submissions/{id}` - Save step fields (agreements, metadata)
- `POST /api/submissions/{id}/upload-manuscript` - Attach manuscript PDF (multipart, `file`)
- `POST /api/submissions/{id}/upload-supplementary` - Attach supplementary file (multipart, `file`, optional `name`)
- `POST /api/submissions/{id}/submit` - Submit for review (draft -> submitted)

### Reviewer
- `GET /api/reviewer/assignments` - List my review assignments
- `GET /api/reviewer/assignments/{id}` - Get assignment detail
- `POST /api/reviewer/assignments/{id}/accept` - Accept invitation
- `POST /api/reviewer/assignments/{id}/decline` - Decline invitation
- `POST /api/reviewer/assignments/{id}/submit-review` - Submit structured review
- `GET /api/reviewer/accept-by-token/?token=xxx` - Get assignment info by invite token
- `POST /api/reviewer/accept-by-token` - Accept by token (body: `{token: "..."}`)

### Editorial
- `GET /api/editor/submissions?status=` - List submissions
- `GET /api/editor/submissions/{id}` - Get submission
- `POST /api/editor/submissions/{id}/start-screening` - submitted -> screening
- `POST /api/editor/submissions/{id}/desk-reject` - screening -> desk_rejected (body: `{reason: "..."}`)
- `POST /api/editor/submissions/{id}/send-to-review` - screening -> under_review
- `POST /api/editor/submissions/{id}/invite-reviewer` - Invite (body: `{reviewer_user_id? OR reviewer_email, due_date?}`)
- `POST /api/editor/review-assignments/{id}/remind` - Queue review reminder email
- `POST /api/editor/submissions/{id}/move-to-decision` - under_review -> decision_pending
- `POST /api/editor/submissions/{id}/decision` - Decision (body: `{decision: accept|reject|revision_required, decision_letter}`)
- `POST /api/editor/submissions/{id}/publish` - accepted -> published

### Admin (staff only)
- `POST /api/admin/users/{id}/approve-reviewer` - Approve reviewer role
- `POST /api/admin/users/{id}/approve-editor` - Approve editor role
- `POST /api/admin/users/{id}/reject-reviewer` - Reject (body: `{reason}`)
- `POST /api/admin/users/{id}/reject-editor` - Reject (body: `{reason}`)

## Settings

- Dev: `ejournal.settings.dev` (default in manage.py)
- Prod: `DJANGO_SETTINGS_MODULE=ejournal.settings.prod`

### Email
- On-premise: SMTP (set EMAIL_HOST, EMAIL_PORT, etc. in .env)
- Dev: console backend. No AWS/SES needed.

### Tests
```bash
python manage.py test tests --settings=ejournal.settings.test
# or
pytest tests/
```
# ejournal-back
