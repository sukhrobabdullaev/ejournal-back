# Ejournal API — Frontend Developer Guide

Complete API reference for building the journal frontend.

---

## Base URL

```
https://api.yourdomain.com/api/
```

Example: `https://api.uzfintex.uz/api/`

---

## Authentication

All protected endpoints require a JWT access token:

```
Authorization: Bearer <access_token>
```

Requests use `Content-Type: application/json` except for file uploads (`multipart/form-data`).

---

## Auth Flow

1. **Signup** → `POST /api/auth/signup`
2. **Login** → `POST /api/auth/login` → receive `access` and `refresh`
3. Store `access` in memory (or secure storage)
4. On 401, call **Refresh** → `POST /api/auth/refresh` with `refresh` token
5. If refresh fails, redirect to login

---

## Error Responses

| Status | Format |
|--------|--------|
| 400 | `{ "detail": "Error message" }` or `{ "field": ["error"] }` |
| 401 | `{ "detail": "..." }` — token invalid/expired |
| 403 | `{ "detail": "..." }` — permission denied |
| 404 | `{ "detail": "Not found." }` |

---

## Enums & Constants

### Submission status

```ts
type SubmissionStatus =
  | "draft"
  | "submitted"
  | "screening"
  | "desk_rejected"
  | "under_review"
  | "revision_required"
  | "resubmitted"
  | "decision_pending"
  | "accepted"
  | "rejected"
  | "published"
  | "withdrawn";
```

### Review assignment status

```ts
type AssignmentStatus =
  | "invited"
  | "accepted"
  | "declined"
  | "review_submitted"
  | "expired";
```

### Recommendation

```ts
type Recommendation = "accept" | "minor_revision" | "major_revision" | "reject";
```

### Editorial decision

```ts
type EditorialDecision = "accept" | "reject" | "revision_required";
```

### Role approval status

```ts
type ApprovalStatus = "pending" | "approved" | "rejected" | null;
```

---

## Endpoints

### Public (no auth)

#### GET /api/

API info.

**Response:** `{ "message": "Ejournal API", "version": "1.0" }`

---

#### POST /api/auth/signup

Create account.

**Request:**
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

- `roles`: `["author"]`, `["reviewer"]`, `["editor"]` or combinations
- `why_to_be`: **required** if `reviewer` or `editor` in roles

**Response 201:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "Full Name",
  "roles": ["author"],
  "reviewer_status": null,
  "editor_status": null,
  "message": "Account created. Use /api/auth/login to obtain tokens."
}
```

---

#### POST /api/auth/login

Get tokens.

**Request:**
```json
{ "email": "user@example.com", "password": "password123" }
```

**Response 200:**
```json
{
  "access": "eyJ...",
  "refresh": "eyJ..."
}
```

---

#### POST /api/auth/refresh

Refresh access token.

**Request:**
```json
{ "refresh": "<refresh_token>" }
```

**Response 200:**
```json
{ "access": "eyJ..." }
```

---

#### GET /api/editorial-board

List editorial board members (no auth).

**Query:** `?role=editor_in_chief|managing_editor|associate_editor` (optional)

**Response 200:**
```json
[
  {
    "id": 1,
    "name": "Dr. Sarah Mitchell",
    "affiliation": "Stanford University",
    "expertise": ["AI", "ML"],
    "email": "s.mitchell@example.com",
    "linkedin_url": "https://linkedin.com/...",
    "profile_image_url": "https://api.example.com/media/editorial_board/photo.jpg",
    "role": "editor_in_chief"
  }
]
```

---

### Authenticated (any role)

#### GET /api/me

Current user profile.

**Response 200:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "Full Name",
  "affiliation": "University",
  "country": "USA",
  "orcid_id": "",
  "is_email_verified": true,
  "roles": ["author"],
  "reviewer_status": null,
  "editor_status": null,
  "date_joined": "2025-01-01T00:00:00Z"
}
```

---

#### PATCH /api/me

Update profile (writable: `full_name`, `affiliation`, `country`, `orcid_id`).

**Request:**
```json
{ "full_name": "New Name", "affiliation": "...", "orcid_id": "0000-0002-1234-5678" }
```

---

#### GET /api/topic-areas

List topic areas for submission form.

**Response 200:**
```json
[
  { "id": 1, "name": "Artificial Intelligence", "slug": "ai" },
  { "id": 2, "name": "Software Engineering", "slug": "swe" }
]
```

---

#### POST /api/upload-file

Upload file (returns URL). Form-data: `file`.

**Response 201:** `{ "url": "https://..." }`

---

### Author (role: author, is_email_verified)

#### POST /api/submissions

Create draft. Body optional; can include metadata.

**Request (optional):**
```json
{
  "title": "Manuscript Title",
  "abstract": "Abstract...",
  "keywords": ["kw1", "kw2", "kw3"],
  "topic_area_id": 1,
  "originality_confirmation": true,
  "plagiarism_agreement": true,
  "ethics_compliance": true,
  "copyright_agreement": true
}
```

**Response 201:** Submission object (see below)

---

#### GET /api/submissions

List own submissions.

**Response 200:** `[{ ...submission }]`

---

#### GET /api/submissions/{id}

Get submission.

**Response 200:**
```json
{
  "id": 1,
  "status": "draft",
  "title": "...",
  "abstract": "...",
  "keywords": ["kw1", "kw2", "kw3"],
  "topic_area": { "id": 1, "name": "AI", "slug": "ai" },
  "topic_area_id": 1,
  "originality_confirmation": true,
  "plagiarism_agreement": true,
  "ethics_compliance": true,
  "copyright_agreement": true,
  "manuscript_pdf": "https://.../media/submissions/1/manuscripts/xxx.pdf",
  "supplementary_files": [
    { "id": 1, "file": "https://...", "name": "file.pdf", "created_at": "..." }
  ],
  "created_at": "...",
  "updated_at": "..."
}
```

---

#### PATCH /api/submissions/{id}

Update metadata/agreements.

**Request:**
```json
{
  "title": "...",
  "abstract": "...",
  "keywords": ["kw1", "kw2", "kw3"],
  "topic_area_id": 1,
  "originality_confirmation": true,
  "plagiarism_agreement": true,
  "ethics_compliance": true,
  "copyright_agreement": true
}
```

---

#### POST /api/submissions/{id}/upload-file

Upload manuscript or supplementary. Form-data: `file`, `file_type` (`manuscript` \| `supplementary`).

**Response 200:** `{ "url": "...", "file_type": "manuscript" }`

---

#### POST /api/submissions/{id}/submit

Submit for review. Requires: title, abstract, 3+ keywords, topic_area_id, all agreements true, manuscript.

**Response 200:** Submission object

---

#### POST /api/submissions/{id}/resubmit

Resubmit after revision_required.

**Response 200:** Submission object

---

#### DELETE /api/submissions/{id}

Delete draft only.

---

### Reviewer (role: reviewer, reviewer_status: approved, is_email_verified)

#### GET /api/reviewer/assignments

List my assignments.

**Response 200:**
```json
[
  {
    "id": 1,
    "submission": 5,
    "submission_title": "...",
    "submission_abstract": "...",
    "submission_version": { "id": 1, "version_number": 1 },
    "manuscript_url": "https://...",
    "status": "invited",
    "due_date": "2025-04-15",
    "invited_at": "...",
    "responded_at": null
  }
]
```

---

#### GET /api/reviewer/assignments/{id}

Assignment detail.

---

#### POST /api/reviewer/assignments/{id}/accept

Accept invitation.

**Response 200:** Assignment object

---

#### POST /api/reviewer/assignments/{id}/decline

Decline invitation.

**Response 200:** Assignment object

---

#### POST /api/reviewer/assignments/{id}/submit-review

Submit review.

**Request:**
```json
{
  "summary": "Overall assessment...",
  "strengths": "...",
  "weaknesses": "...",
  "confidential_to_editor": "...",
  "recommendation": "accept"
}
```

`recommendation`: `accept` | `minor_revision` | `major_revision` | `reject`

**Response 200:** Assignment object

---

#### GET /api/reviewer/accept-by-token/?token=xxx

Get assignment by email token. No auth required if token valid.

---

#### POST /api/reviewer/accept-by-token

Accept by token. **Request:** `{ "token": "..." }`

---

### Editor (role: editor, editor_status: approved, is_email_verified)

#### GET /api/editor/submissions

List submissions. **Query:** `?status=submitted|screening|under_review|...`

**Response 200:**
```json
[
  {
    "id": 5,
    "status": "under_review",
    "title": "...",
    "abstract": "...",
    "keywords": [...],
    "topic_area": { "id": 1, "name": "AI", "slug": "ai" },
    "author": 11,
    "desk_reject_reason": "",
    "editorial_decision": "",
    "decision_letter": "",
    "manuscript_pdf": "https://...",
    "supplementary_files": [...],
    "created_at": "...",
    "updated_at": "...",
    "review_assignments": [
      {
        "id": 2,
        "reviewer": 12,
        "reviewer_email": "r@example.com",
        "status": "review_submitted",
        "due_date": "2025-04-15",
        "invited_at": "...",
        "review": {
          "summary": "...",
          "strengths": "...",
          "weaknesses": "...",
          "confidential_to_editor": "...",
          "recommendation": "minor_revision",
          "submitted_at": "..."
        }
      },
      {
        "id": 3,
        "reviewer": null,
        "reviewer_email": "r2@example.com",
        "status": "invited",
        "review": null
      }
    ]
  }
]
```

---

#### GET /api/editor/submissions/{id}

Submission detail (same shape).

---

#### POST /api/editor/submissions/{id}/start-screening

submitted → screening. Body: `{}`

---

#### POST /api/editor/submissions/{id}/desk-reject

screening → desk_rejected.

**Request:** `{ "reason": "Out of scope." }`

---

#### POST /api/editor/submissions/{id}/send-to-review

screening → under_review. Body: `{}`

---

#### POST /api/editor/submissions/{id}/invite-reviewer

**Request (by user id):**
```json
{ "reviewer_user_id": 3, "due_date": "2025-04-15" }
```

**Request (by email):**
```json
{ "reviewer_email": "r@example.com", "due_date": "2025-04-15" }
```

---

#### POST /api/editor/submissions/{id}/move-to-decision

under_review → decision_pending. Body: `{}`

---

#### POST /api/editor/submissions/{id}/decision

**Request:**
```json
{
  "decision": "accept",
  "decision_letter": "We are pleased to accept..."
}
```

`decision`: `accept` | `reject` | `revision_required`

---

#### POST /api/editor/submissions/{id}/publish

accepted → published. Body: `{}`

---

#### POST /api/editor/review-assignments/{id}/remind

Send reminder email to reviewer. Body: `{}`

---

### Admin (is_staff)

#### POST /api/admin/users/{id}/approve-reviewer

Approve reviewer. Body: `{}`

---

#### POST /api/admin/users/{id}/approve-editor

Approve editor. Body: `{}`

---

#### POST /api/admin/users/{id}/reject-reviewer

**Request:** `{ "reason": "..." }`

---

#### POST /api/admin/users/{id}/reject-editor

**Request:** `{ "reason": "..." }`

---

## Status Flow

```
draft → submitted → screening → under_review → decision_pending → accepted → published
                ↘ desk_rejected        ↘ revision_required → resubmitted → under_review
                                       ↘ rejected
```

---

## Permission Summary

| Endpoint / Area    | Auth          | Role / condition                          |
|--------------------|---------------|-------------------------------------------|
| /api/editorial-board | None        | Public                                    |
| /api/auth/*        | None          | Public                                    |
| /api/me            | JWT           | Any authenticated                         |
| /api/topic-areas   | JWT + verified| Any                                        |
| /api/submissions   | JWT + verified| author                                     |
| /api/reviewer/*    | JWT + verified| reviewer + reviewer_status=approved       |
| /api/editor/*      | JWT + verified| editor + editor_status=approved           |
| /api/admin/*       | JWT           | is_staff                                  |

**Note:** Users with `is_email_verified: false` cannot access submissions, topic-areas, reviewer, or editor endpoints. They can still use `/api/me`.

---

## File URLs

- **Manuscript:** `manuscript_pdf` in submission — full URL
- **Supplementary:** `supplementary_files[].file` — full URL
- **Media base:** `https://api.yourdomain.com/media/`
- **Static:** `https://api.yourdomain.com/static/`

---

## Postman

Import `postman/Ejournal.postman_collection.json`. Set `base_url` and `access_token` in collection variables.
