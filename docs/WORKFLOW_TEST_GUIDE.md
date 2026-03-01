# Ejournal — Step-by-Step Workflow Test Guide

End-to-end process from draft to published, role by role. Test each step in order.

**Base URL:** `http://localhost:8000` (or `http://127.0.0.1:8000`)  
**Auth:** `Authorization: Bearer <access_token>` for all protected endpoints.

---

## Prerequisites

```bash
docker compose up -d
docker compose exec web python manage.py seed_db --sample-users
```

| Email | Password | Role |
|-------|----------|------|
| admin@ejournal.local | admin123 | Admin |
| author@test.com | author123 | Author |
| reviewer@test.com | reviewer123 | Reviewer (pre-approved) |
| editor@test.com | editor123 | Editor (pre-approved) |

---

## Role 1: Author — Submit Manuscript

### Step 1.1 — Login as Author

```
POST /api/auth/login
Content-Type: application/json
```

```json
{
  "email": "author@test.com",
  "password": "author123"
}
```

**Save:** `access` token for later requests.

---

### Step 1.2 — Get Topic Areas

```
GET /api/topic-areas
Authorization: Bearer <access_token>
```

**Note:** Topic area IDs (e.g. 1 = AI, 2 = Software Engineering). You need one for metadata.  
ORCID iD (optional) can be typed and saved via `PATCH /api/me`.

---

### Step 1.3 — Create Draft

```
POST /api/submissions/
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Minimal (empty body):**
```json
{}
```

**Or with metadata (optional):**
```json
{
  "title": "My Manuscript Title",
  "abstract": "Abstract text here.",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "topic_area_id": 1,
  "originality_confirmation": true,
  "plagiarism_agreement": true,
  "ethics_compliance": true,
  "copyright_agreement": true
}
```

**Save:** `id` from response → this is `<submission_id>`.

---

### Step 1.4 — Fill Metadata

```
PATCH /api/submissions/<submission_id>/
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "title": "My Manuscript Title",
  "abstract": "Abstract text here.",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "topic_area_id": 1,
  "originality_confirmation": true,
  "plagiarism_agreement": true,
  "ethics_compliance": true,
  "copyright_agreement": true
}
```

**Required:** Title, abstract, 3+ keywords, topic_area_id, all agreements `true`.

---

### Step 1.5 — Upload Manuscript PDF

```
POST /api/submissions/<submission_id>/upload-file/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

- `file`: select PDF file  
- `file_type`: `manuscript`

---

### Step 1.6 — Submit for Review

```
POST /api/submissions/<submission_id>/submit/
Authorization: Bearer <access_token>
```

Body: `{}` (empty)

**Result:** Status changes from `draft` → `submitted`.

---

## Role 2: Admin — Approve Reviewer/Editor (if using new users)

Skip if using seeded users (reviewer@test.com and editor@test.com are pre-approved).

### Step 2.1 — Login as Admin

```
POST /api/auth/login
Content-Type: application/json
```

```json
{
  "email": "admin@ejournal.local",
  "password": "admin123"
}
```

---

### Step 2.2 — Approve Reviewer

```
POST /api/admin/users/<user_id>/approve-reviewer
Authorization: Bearer <admin_access_token>
```

Replace `<user_id>` with the reviewer's user ID (e.g. from Django admin or GET /api/me for that user).

---

### Step 2.3 — Approve Editor

```
POST /api/admin/users/<user_id>/approve-editor
Authorization: Bearer <admin_access_token>
```

---

## Role 3: Editor — Screening & Peer Review

### Step 3.1 — Login as Editor

```
POST /api/auth/login
Content-Type: application/json
```

```json
{
  "email": "editor@test.com",
  "password": "editor123"
}
```

---

### Step 3.2 — List Submitted Manuscripts

```
GET /api/editor/submissions?status=submitted
Authorization: Bearer <editor_access_token>
```

**Save:** `id` of the submission you want to process.

---

### Step 3.3 — Start Screening

```
POST /api/editor/submissions/<submission_id>/start-screening/
Authorization: Bearer <editor_access_token>
```

**Result:** Status changes `submitted` → `screening`.

---

### Step 3.4 — Send to Review (skip desk-reject path)

```
POST /api/editor/submissions/<submission_id>/send-to-review/
Authorization: Bearer <editor_access_token>
```

**Result:** Status changes `screening` → `under_review`.

---

### Step 3.5 — Invite Reviewer

```
POST /api/editor/submissions/<submission_id>/invite-reviewer/
Authorization: Bearer <editor_access_token>
Content-Type: application/json
```

```json
{
  "reviewer_user_id": 3,
  "due_date": "2025-04-15"
}
```

Replace `reviewer_user_id` with the reviewer's user ID (e.g. 3 for reviewer@test.com if that's their ID).  
Or use email:

```json
{
  "reviewer_email": "reviewer@test.com",
  "due_date": "2025-04-15"
}
```

**Save:** `id` from response → this is `<assignment_id>` (for reviewer flow).

---

## Role 4: Reviewer — Accept & Submit Review

### Step 4.1 — Login as Reviewer

```
POST /api/auth/login
Content-Type: application/json
```

```json
{
  "email": "reviewer@test.com",
  "password": "reviewer123"
}
```

---

### Step 4.2 — List Assignments

```
GET /api/reviewer/assignments
Authorization: Bearer <reviewer_access_token>
```

**Save:** `id` of the assignment with status `invited`.

---

### Step 4.3 — Accept Invitation

```
POST /api/reviewer/assignments/<assignment_id>/accept/
Authorization: Bearer <reviewer_access_token>
```

**Result:** Assignment status → `accepted`.

---

### Step 4.4 — Submit Review

```
POST /api/reviewer/assignments/<assignment_id>/submit-review/
Authorization: Bearer <reviewer_access_token>
Content-Type: application/json
```

```json
{
  "summary": "Overall assessment of the manuscript.",
  "strengths": "Clear methodology, good structure.",
  "weaknesses": "Limited sample size.",
  "confidential_to_editor": "No conflicts of interest.",
  "recommendation": "accept"
}
```

`recommendation`: `accept` | `minor_revision` | `major_revision` | `reject`

**Result:** Review submitted, assignment status → `review_submitted`.

---

## Role 3 (Editor) — Decision & Publish

### Step 3.6 — Move to Decision

```
POST /api/editor/submissions/<submission_id>/move-to-decision/
Authorization: Bearer <editor_access_token>
```

**Result:** Status changes `under_review` → `decision_pending`.

---

### Step 3.7 — Make Decision (Accept)

```
POST /api/editor/submissions/<submission_id>/decision/
Authorization: Bearer <editor_access_token>
Content-Type: application/json
```

```json
{
  "decision": "accept",
  "decision_letter": "We are pleased to accept your manuscript for publication."
}
```

`decision`: `accept` | `reject` | `revision_required`

**Result:** Status changes → `accepted`.

---

### Step 3.8 — Publish

```
POST /api/editor/submissions/<submission_id>/publish/
Authorization: Bearer <editor_access_token>
```

**Result:** Status changes `accepted` → `published`.

---

## Status Flow Summary

```
draft → submitted → screening → under_review → decision_pending → accepted → published
                ↘ desk_rejected                                          ↘ revision_required
                ↘ rejected (after decision)                                    ↓
                                                                          resubmitted → under_review (loop)
```

---

## Alternative Paths

### Desk Reject (Editor, after start-screening)

```
POST /api/editor/submissions/<submission_id>/desk-reject/
Content-Type: application/json
```

```json
{ "reason": "Out of scope for this journal." }
```

### Reject (Editor, at decision step)

```json
{
  "decision": "reject",
  "decision_letter": "We regret to inform you..."
}
```

### Decline Invitation (Reviewer)

```
POST /api/reviewer/assignments/<assignment_id>/decline/
Authorization: Bearer <reviewer_access_token>
```

---

## Revision Required Path (Author updates & resubmits)

When the editor decides **revision_required**, the author can update the manuscript and resubmit.

### Editor — Request Revision

At the decision step, use:

```json
{
  "decision": "revision_required",
  "decision_letter": "Please address the reviewers' comments and resubmit."
}
```

**Result:** Status → `revision_required`.

---

### Author — Update & Resubmit

**1. Update metadata (if needed):**

```
PATCH /api/submissions/<submission_id>/
Authorization: Bearer <author_access_token>
Content-Type: application/json
```

```json
{
  "title": "Revised Title",
  "abstract": "Updated abstract...",
  "keywords": ["kw1", "kw2", "kw3"]
}
```

**2. Upload revised manuscript (form-data):**

```
POST /api/submissions/<submission_id>/upload-file/
Authorization: Bearer <author_access_token>
```

- `file`: new PDF
- `file_type`: `manuscript`

**3. Resubmit:**

```
POST /api/submissions/<submission_id>/resubmit/
Authorization: Bearer <author_access_token>
```

**Result:** Status → `resubmitted`. A new version is created.

---

### Editor — Send Resubmission Back to Review

```
POST /api/editor/submissions/<submission_id>/send-to-review/
Authorization: Bearer <editor_access_token>
```

**Result:** Status `resubmitted` → `under_review`. Flow continues (invite reviewers, move to decision, etc.).

---

## Quick Checklist

| # | Role   | Action                    | Endpoint                                      |
|---|--------|---------------------------|-----------------------------------------------|
| 1 | Author | Login                     | POST /api/auth/login                          |
| 2 | Author | Create draft              | POST /api/submissions/                        |
| 3 | Author | Fill metadata             | PATCH /api/submissions/{id}/                  |
| 4 | Author | Upload manuscript         | POST /api/submissions/{id}/upload-file/       |
| 5 | Author | Submit                    | POST /api/submissions/{id}/submit/            |
| 5b | Author | Resubmit (after revision) | POST /api/submissions/{id}/resubmit/          |
| 6 | Editor | Login                     | POST /api/auth/login                          |
| 7 | Editor | List submissions          | GET /api/editor/submissions?status=submitted  |
| 8 | Editor | Start screening           | POST /api/editor/submissions/{id}/start-screening/ |
| 9 | Editor | Send to review            | POST /api/editor/submissions/{id}/send-to-review/ |
|10 | Editor | Invite reviewer           | POST /api/editor/submissions/{id}/invite-reviewer/ |
|11 | Reviewer | Login                   | POST /api/auth/login                          |
|12 | Reviewer | List assignments        | GET /api/reviewer/assignments                 |
|13 | Reviewer | Accept                  | POST /api/reviewer/assignments/{id}/accept/   |
|14 | Reviewer | Submit review           | POST /api/reviewer/assignments/{id}/submit-review/ |
|15 | Editor | Move to decision          | POST /api/editor/submissions/{id}/move-to-decision/ |
|16 | Editor | Decision (accept)         | POST /api/editor/submissions/{id}/decision/   |
|17 | Editor | Publish                   | POST /api/editor/submissions/{id}/publish/    |
