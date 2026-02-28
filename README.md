# Ejournal - Manuscript Submission & Peer Review Platform

Django + DRF backend for a single-journal manuscript submission and peer review system. On-premise deployment: local storage, no AWS required.

---

## Quick Start (Docker)

```bash
cp .env.docker.example .env
docker compose up -d
```

- **API**: http://localhost:8000/api/
- **Admin**: http://localhost:8000/admin/ — `admin@ejournal.local` / `admin123`

**Optional sample users** (author, reviewer, editor):

```bash
docker compose exec web python manage.py seed_db --sample-users
```

| Email                | Password    | Role                    |
| -------------------- | ----------- | ----------------------- |
| admin@ejournal.local | admin123    | Superuser               |
| author@test.com      | author123   | Author                  |
| reviewer@test.com    | reviewer123 | Reviewer (pre-approved) |
| editor@test.com      | editor123   | Editor (pre-approved)   |

---

## End-to-End Workflow

### 1. Author submits manuscript

1. **Sign up** → `POST /api/auth/signup` (roles: `["author"]`)
2. **Login** → `POST /api/auth/login` → receive `access` + `refresh` tokens
3. **Create draft** → `POST /api/submissions` → returns `{ id }`
4. **Fill metadata** → `PATCH /api/submissions/{id}` with `title`, `abstract`, `keywords`, `topic_area_id`, agreements
5. **Upload file** → `POST /api/upload-file` (JSON, base64) → returns `{ url }`; for submission manuscript/supplementary use `POST /api/submissions/{id}/upload-file` (add `file_type`)
6. **Submit** → `POST /api/submissions/{id}/submit` (requires all agreements, title, abstract, 3+ keywords, topic, manuscript)

### 2. Reviewer role (must be approved by admin)

1. **Sign up** with `roles: ["reviewer"]` and `why_to_be` (required)
2. **Admin approves** → `POST /api/admin/users/{id}/approve-reviewer` (staff only)
3. **Editor invites** → `POST /api/editor/submissions/{id}/invite-reviewer` with `reviewer_user_id` or `reviewer_email`
4. **Reviewer accepts** via:
   - `POST /api/reviewer/assignments/{id}/accept`, or
   - `GET /api/reviewer/accept-by-token/?token=xxx` then `POST /api/reviewer/accept-by-token` with `{ "token": "..." }`
5. **Submit review** → `POST /api/reviewer/assignments/{id}/submit-review` with `summary`, `strengths`, `weaknesses`, `confidential_to_editor`, `recommendation` (`accept`|`minor_revision`|`major_revision`|`reject`)

### 3. Editor workflow

1. **Sign up** with `roles: ["editor"]` and `why_to_be`
2. **Admin approves** → `POST /api/admin/users/{id}/approve-editor`
3. **List submissions** → `GET /api/editor/submissions?status=submitted` (or `screening`, `under_review`, etc.)
4. **Start screening** → `POST /api/editor/submissions/{id}/start-screening` (submitted → screening)
5. **Desk reject** → `POST /api/editor/submissions/{id}/desk-reject` with `{ "reason": "..." }`
6. **Send to review** → `POST /api/editor/submissions/{id}/send-to-review` (screening → under_review)
7. **Invite reviewer** → `POST /api/editor/submissions/{id}/invite-reviewer` with `{ "reviewer_user_id": N }` or `{ "reviewer_email": "r@example.com", "due_date": "2025-03-15" }`
8. **Remind reviewer** → `POST /api/editor/review-assignments/{id}/remind`
9. **Move to decision** → `POST /api/editor/submissions/{id}/move-to-decision` (under_review → decision_pending)
10. **Decision** → `POST /api/editor/submissions/{id}/decision` with `{ "decision": "accept"|"reject"|"revision_required", "decision_letter": "..." }`
11. **Publish** → `POST /api/editor/submissions/{id}/publish` (accepted → published)

### 4. Admin (staff)

- Approve/reject reviewer: `POST /api/admin/users/{id}/approve-reviewer`, `reject-reviewer` (body: `{ "reason": "..." }`)
- Approve/reject editor: `POST /api/admin/users/{id}/approve-editor`, `reject-editor` (body: `{ "reason": "..." }`)

---

## API Reference

All auth-protected endpoints use JWT: `Authorization: Bearer <access_token>`.

| Method    | Endpoint                                      | Auth       | Description                                         |
| --------- | --------------------------------------------- | ---------- | --------------------------------------------------- |
| GET       | /api/                                         | -          | API info                                            |
| POST      | /api/auth/signup                              | -          | Create account                                      |
| POST      | /api/auth/login                               | -          | Get JWT tokens                                      |
| POST      | /api/auth/refresh                             | -          | Refresh access token                                |
| GET/PATCH | /api/me                                       | ✓          | Current user profile                                |
| POST      | /api/upload-file                              | ✓          | Upload file (JSON, base64). Returns `{ url }`       |
| POST      | /api/orcid/connect                            | ✓          | Connect ORCID (stub; body: `{ "orcid_id": "..." }`) |
| GET       | /api/topic-areas                              | ✓          | List topic areas                                    |
| POST      | /api/submissions                              | ✓          | Create draft                                        |
| GET       | /api/submissions                              | ✓          | List own submissions                                |
| GET       | /api/submissions/{id}                         | ✓          | Get submission                                      |
| PATCH     | /api/submissions/{id}                         | ✓          | Save metadata/agreements                            |
| POST      | /api/submissions/{id}/upload-file             | ✓          | Upload file (JSON, base64). Returns `{ url }`       |
| POST      | /api/submissions/{id}/submit                  | ✓          | Submit for review                                   |
| DELETE    | /api/submissions/{id}                         | ✓          | Delete draft                                        |
| GET       | /api/reviewer/assignments                     | ✓ reviewer | List assignments                                    |
| GET       | /api/reviewer/assignments/{id}                | ✓ reviewer | Assignment detail                                   |
| POST      | /api/reviewer/assignments/{id}/accept         | ✓ reviewer | Accept invitation                                   |
| POST      | /api/reviewer/assignments/{id}/decline        | ✓ reviewer | Decline invitation                                  |
| POST      | /api/reviewer/assignments/{id}/submit-review  | ✓ reviewer | Submit review                                       |
| GET       | /api/reviewer/accept-by-token/?token=xxx      | ✓ reviewer | Get assignment by token                             |
| POST      | /api/reviewer/accept-by-token                 | ✓ reviewer | Accept by token (body: `{ "token": "..." }`)        |
| GET       | /api/editor/submissions                       | ✓ editor   | List submissions (query: `?status=`)                |
| GET       | /api/editor/submissions/{id}                  | ✓ editor   | Submission detail                                   |
| POST      | /api/editor/submissions/{id}/start-screening  | ✓ editor   | submitted → screening                               |
| POST      | /api/editor/submissions/{id}/desk-reject      | ✓ editor   | screening → desk_rejected                           |
| POST      | /api/editor/submissions/{id}/send-to-review   | ✓ editor   | screening → under_review                            |
| POST      | /api/editor/submissions/{id}/invite-reviewer  | ✓ editor   | Invite reviewer                                     |
| POST      | /api/editor/submissions/{id}/move-to-decision | ✓ editor   | under_review → decision_pending                     |
| POST      | /api/editor/submissions/{id}/decision         | ✓ editor   | Accept/reject/revision                              |
| POST      | /api/editor/submissions/{id}/publish          | ✓ editor   | accepted → published                                |
| POST      | /api/editor/review-assignments/{id}/remind    | ✓ editor   | Queue reminder email                                |
| POST      | /api/admin/users/{id}/approve-reviewer        | staff      | Approve reviewer                                    |
| POST      | /api/admin/users/{id}/approve-editor          | staff      | Approve editor                                      |
| POST      | /api/admin/users/{id}/reject-reviewer         | staff      | Reject reviewer (body: `{ "reason" }`)              |
| POST      | /api/admin/users/{id}/reject-editor           | staff      | Reject editor (body: `{ "reason" }`)                |

---

## API Payloads (JSON)

All requests use `Content-Type: application/json`. Auth: `Authorization: Bearer <access_token>`.

**POST /api/auth/signup**

```json
{
  "email": "user@example.com",
  "password": "password123",
  "full_name": "Full Name",
  "affiliation": "University",
  "country": "USA",
  "roles": ["author"],
  "why_to_be": ""
}
```

`roles`: `["author"]`, `["reviewer"]`, `["editor"]` or combinations. `why_to_be` required if reviewer/editor.

**POST /api/auth/login**

```json
{ "email": "user@example.com", "password": "password123" }
```

**POST /api/auth/refresh**

```json
{ "refresh": "<refresh_token>" }![1772265646798](image/README/1772265646798.png)
```

**PATCH /api/me**

```json
{ "full_name": "New Name", "affiliation": "...", "country": "..." }
```

**POST /api/upload-file** — upload file, get URL

Form-data: key `file` (select file). Or JSON: `{ "file_base64": "...", "filename": "document.pdf" }`.  
Response: `{ "url": "http://..." }`

**POST /api/orcid/connect**

```json
{ "orcid_id": "0000-0002-1234-5678" }
```

**PATCH /api/submissions/{id}**

```json
{
  "title": "Manuscript Title",
  "abstract": "Abstract text...",
  "keywords": ["kw1", "kw2", "kw3"],
  "topic_area_id": 1,
  "originality_confirmation": true,
  "plagiarism_agreement": true,
  "ethics_compliance": true,
  "copyright_agreement": true
}
```

**POST /api/submissions/{id}/upload-file**

Form-data: `file` (file), `file_type` (`manuscript` or `supplementary`). Or JSON with `file_base64`, `filename`, `file_type`.  
Response: `{ "url": "http://...", "file_type": "manuscript" }`.

**POST /api/reviewer/assignments/{id}/submit-review**

```json
{
  "summary": "Overall assessment...",
  "strengths": "Strengths...",
  "weaknesses": "Weaknesses...",
  "confidential_to_editor": "Confidential notes",
  "recommendation": "accept"
}
```

`recommendation`: `accept` | `minor_revision` | `major_revision` | `reject`

**POST /api/reviewer/accept-by-token**

```json
{ "token": "token_from_email" }
```

**POST /api/editor/submissions/{id}/desk-reject**

```json
{ "reason": "Out of scope." }
```

**POST /api/editor/submissions/{id}/invite-reviewer**

```json
{ "reviewer_user_id": 3, "due_date": "2025-03-15" }
```

Or: `{ "reviewer_email": "r@example.com", "due_date": "2025-03-15" }`

**POST /api/editor/submissions/{id}/decision**

```json
{
  "decision": "accept",
  "decision_letter": "We are pleased to accept..."
}
```

`decision`: `accept` | `reject` | `revision_required`

**POST /api/admin/users/{id}/reject-reviewer** | **reject-editor**

```json
{ "reason": "Reason text." }
```

---

## Local Setup (without Docker)

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env
# Configure DATABASE_URL, etc.
python manage.py migrate
python manage.py seed_db --sample-users
python manage.py runserver
# Separate terminal for Celery:
celery -A ejournal worker -l info
```

---

## Tests

```bash
pytest tests/
# or
python manage.py test tests --settings=ejournal.settings.test
```

---

## Postman Collection

Import `postman/Ejournal.postman_collection.json` and set base URL in collection variables (default `http://localhost:8000`). Use **Login** request, copy `access` from response into the collection variable `access_token` for authenticated requests.
