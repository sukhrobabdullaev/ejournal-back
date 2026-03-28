# Ejournal - Manuscript Submission & Peer Review Platform

Django + DRF backend for a single-journal manuscript submission and peer review system. On-premise deployment: local storage, no AWS required.

---

## Quick Start (Docker)

```bash
cp .env.docker.example .env
docker compose up -d
```

- **API**: http://localhost:8000/api/
- **Admin**: http://localhost:8000/admin/ вЂ” `admin@ejournal.local` / `admin123`

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

1. **Sign up** в†’ `POST /api/auth/signup` (roles: `["author"]`)
2. **Login** в†’ `POST /api/auth/login` в†’ receive `access` + `refresh` tokens
3. **Create submission** в†’ `POST /api/submissions` в†’ returns `{ id }`
4. **Fill metadata** в†’ `PATCH /api/submissions/{id}` with `title`, `abstract`, `keywords`, `topic_area_id`, agreements
5. **Upload file** в†’ `POST /api/upload-file` (form-data: `file`) в†’ returns `{ url }`; for submission manuscript/supplementary use `POST /api/submissions/{id}/upload-file` (form-data: `file`, `file_type`)
6. **Submit** в†’ `POST /api/submissions/{id}/submit` (requires all agreements, title, abstract, 3+ keywords, topic, manuscript)

**If revision required:** Update metadata (`PATCH`), upload revised manuscript (`POST .../upload-file`), then **Resubmit** в†’ `POST /api/submissions/{id}/resubmit`

### 2. Reviewer role (must be approved by admin)

1. **Sign up** with `roles: ["reviewer"]` and `why_to_be` (required)
2. **Admin approves** в†’ `POST /api/admin/users/{id}/approve-reviewer` (staff only)
3. **Editor invites** в†’ `POST /api/editor/submissions/{id}/invite-reviewer` with `reviewer_user_id` or `reviewer_email`
4. **Reviewer accepts** via:
   - `POST /api/reviewer/assignments/{id}/accept`, or
   - `GET /api/reviewer/accept-by-token/?token=xxx` then `POST /api/reviewer/accept-by-token` with `{ "token": "..." }`
5. **Submit review** в†’ `POST /api/reviewer/assignments/{id}/submit-review` with `summary`, `strengths`, `weaknesses`, `confidential_to_editor`, `recommendation` (`accept`|`minor_revision`|`major_revision`|`reject`)

### 3. Editor workflow

1. **Sign up** with `roles: ["editor"]` and `why_to_be`
2. **Admin approves** в†’ `POST /api/admin/users/{id}/approve-editor`
3. **List submissions** в†’ `GET /api/editor/submissions?status=submitted` (or `screening`, `under_review`, etc.)
4. **Start screening** в†’ `POST /api/editor/submissions/{id}/start-screening` (submitted в†’ screening)
5. **Desk reject** в†’ `POST /api/editor/submissions/{id}/desk-reject` with `{ "reason": "..." }`
6. **Send to review** в†’ `POST /api/editor/submissions/{id}/send-to-review` (screening в†’ under_review)
7. **Invite reviewer** в†’ `POST /api/editor/submissions/{id}/invite-reviewer` with `{ "reviewer_user_id": N }` or `{ "reviewer_email": "r@example.com", "due_date": "2025-03-15" }`
8. **Remind reviewer** в†’ `POST /api/editor/review-assignments/{id}/remind`
9. **Move to decision** в†’ `POST /api/editor/submissions/{id}/move-to-decision` (under_review в†’ decision_pending)
10. **Decision** в†’ `POST /api/editor/submissions/{id}/decision` with `{ "decision": "accept"|"reject"|"revision_required", "decision_letter": "..." }`
11. **Publish** в†’ `POST /api/editor/submissions/{id}/publish` (accepted в†’ published)

### 4. Admin (staff)

- Approve/reject reviewer: `POST /api/admin/users/{id}/approve-reviewer`, `reject-reviewer` (body: `{ "reason": "..." }`)
- Approve/reject editor: `POST /api/admin/users/{id}/approve-editor`, `reject-editor` (body: `{ "reason": "..." }`)

---

## API Reference

**Frontend devs:** see [docs/API_FRONTEND.md](docs/API_FRONTEND.md) for full request/response shapes, TypeScript types, and workflow.

All auth-protected endpoints use JWT: `Authorization: Bearer <access_token>`.

| Method    | Endpoint                                      | Auth       | Description                                         |
| --------- | --------------------------------------------- | ---------- | --------------------------------------------------- |
| GET       | /api/                                         | -          | API info                                            |
| POST      | /api/auth/signup                              | -          | Create account                                      |
| POST      | /api/auth/login                               | -          | Get JWT tokens                                      |
| POST      | /api/auth/refresh                             | -          | Refresh access token                                |
| GET/PATCH | /api/me                                       | вњ“          | Current user profile                                |
| POST      | /api/upload-file                              | вњ“          | Upload file (form-data). Returns `{ url }`          |
| GET       | /api/topic-areas                              | вњ“          | List topic areas                                    |
| GET       | /api/editorial-board                          | -          | List board members (`?role=editor_in_chief|managing_editor|associate_editor`) |
| POST      | /api/submissions                              | вњ“          | Create submission                                        |
| GET       | /api/submissions                              | вњ“          | List own submissions                                |
| GET       | /api/submissions/{id}                         | вњ“          | Get submission                                      |
| PATCH     | /api/submissions/{id}                         | вњ“          | Save metadata/agreements                            |
| POST      | /api/submissions/{id}/upload-file             | вњ“          | Upload file (form-data). Returns `{ url }`          |
| POST      | /api/submissions/{id}/submit                  | вњ“          | Submit for review                                   |
| POST      | /api/submissions/{id}/resubmit                | вњ“          | Resubmit after revision_required                    |
| GET       | /api/reviewer/assignments                     | вњ“ reviewer | List assignments                                    |
| GET       | /api/reviewer/assignments/{id}                | вњ“ reviewer | Assignment detail                                   |
| POST      | /api/reviewer/assignments/{id}/accept         | вњ“ reviewer | Accept invitation                                   |
| POST      | /api/reviewer/assignments/{id}/decline        | вњ“ reviewer | Decline invitation                                  |
| POST      | /api/reviewer/assignments/{id}/submit-review  | вњ“ reviewer | Submit review                                       |
| GET       | /api/reviewer/accept-by-token/?token=xxx      | вњ“ reviewer | Get assignment by token                             |
| POST      | /api/reviewer/accept-by-token                 | вњ“ reviewer | Accept by token (body: `{ "token": "..." }`)        |
| GET       | /api/editor/submissions                       | вњ“ editor   | List submissions (query: `?status=`)                |
| GET       | /api/editor/submissions/{id}                  | вњ“ editor   | Submission detail                                   |
| POST      | /api/editor/submissions/{id}/start-screening  | вњ“ editor   | submitted в†’ screening                               |
| POST      | /api/editor/submissions/{id}/desk-reject      | вњ“ editor   | screening в†’ desk_rejected                           |
| POST      | /api/editor/submissions/{id}/send-to-review   | вњ“ editor   | screening в†’ under_review                            |
| POST      | /api/editor/submissions/{id}/invite-reviewer  | вњ“ editor   | Invite reviewer                                     |
| POST      | /api/editor/submissions/{id}/move-to-decision | вњ“ editor   | under_review в†’ decision_pending                     |
| POST      | /api/editor/submissions/{id}/decision         | вњ“ editor   | Accept/reject/revision                              |
| POST      | /api/editor/submissions/{id}/publish          | вњ“ editor   | accepted в†’ published                                |
| POST      | /api/editor/review-assignments/{id}/remind    | вњ“ editor   | Queue reminder email                                |
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
{ "full_name": "New Name", "affiliation": "...", "country": "...", "orcid_id": "0000-0002-1234-5678" }
```

**POST /api/upload-file** вЂ” upload file, get URL

Form-data: key `file` (select file). Response: `{ "url": "http://..." }`

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

Form-data: `file` (file), `file_type` (`manuscript` or `supplementary`).  
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
