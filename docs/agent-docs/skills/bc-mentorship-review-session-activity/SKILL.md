---
name: bc-mentorship-review-session-activity
description: Use when reviewing mentorship meeting history via academy or user/me session APIs (filters, notes, status); do NOT use for booking/join short links, creating mentors, generic activity feeds, or mentorship bill payout deep-dives.
requires:
  - bc-authenticate-staff-authentication
  - bc-authenticate-student-authentication
---

# Skill: Review Mentorship Session Activity

## When to Use

Use when staff or learners need to **see mentorship meetings**, **filter by mentor/student/status/dates**, or **update session notes/status**. The mentorship activity log **is the sessions API** — do NOT dig into generic activity-domain endpoints for this task, and do NOT use Admin. Do NOT use this skill to book/join (load `bc-mentorship-book-and-join-session`) or create mentors (load `bc-mentorship-create-manage-mentor`). Mentorship bills are out of scope beyond noting that sessions can be billed later.

## Concepts

- **Staff log:** `/v1/mentorship/academy/session` (and nested mentor/service session lists).
- **Learner log:** `/v1/mentorship/user/me/session` — sessions where the current user is mentor or mentee (`get_my_mentoring_sessions`).
- **Statuses:** `PENDING`, `STARTED`, `COMPLETED`, `FAILED`, `CANCELED`, `IGNORED` (ignored sessions are excluded from billing).
- **Useful fields for review:** `status`, `summary`, `agenda`, `started_at`, `ended_at`, `mentor_joined_at`, `mentee_left_at`, `online_meeting_url`, `allow_billing`, `bill`.

## Workflow

### Path A — Staff academy activity

1. Load `bc-authenticate-staff-authentication`. Confirm `read_mentorship_session` (and `crud_mentorship_session` if updating).
2. Set **`Academy: <academy_id>`** and **`Accept-Language`**.
3. List sessions: `GET /v1/mentorship/academy/session` with filters as needed:
   - `status` — comma-separated statuses
   - `mentor` — mentor id(s) or name-like search
   - `student` — mentee name-like search
   - `service` — service slug contains
   - `started_after` / `ended_before` — ISO datetimes
   - `billed` — `true` or `false`
   - `with_feedback` — `true` or `false`
4. Narrow by mentor: `GET /v1/mentorship/academy/mentor/{mentor_id}/session`.
5. Narrow by service: `GET /v1/mentorship/academy/service/{service_id}/session`.
6. Open one meeting: `GET /v1/mentorship/academy/session/{session_id}` for full notes, URLs, and timestamps.
7. If correcting the log: `PUT /v1/mentorship/academy/session/{session_id}` with `summary`, `status`, `agenda`, etc. Do not overwrite online join timestamps that the system owns when `is_online` is true.

### Path B — Learner “my sessions”

1. Load `bc-authenticate-student-authentication`. Confirm permission `get_my_mentoring_sessions`.
2. `GET /v1/mentorship/user/me/session` (no `Academy` header). Optional filters: `status`, `billed`, `started_after`, `ended_before`, `mentee`, `mentor`.
3. Present the list; for deeper staff investigation of one academy’s records, switch to Path A with staff credentials.

### Empty results

If the list is empty: widen or clear filters, confirm the mentor belongs to the `Academy` header academy, confirm the learner was mentee/mentor on sessions, and confirm dates are ISO and timezone-aware. Do not route to generic activity APIs.

## Endpoints

### Staff list sessions

**GET** `/v1/mentorship/academy/session`

Headers: `Authorization`, `Academy: 4`, `Accept-Language: en`

Capability: `read_mentorship_session`

List endpoints are **paginated** (`limit`, `offset`).

Example: `GET /v1/mentorship/academy/session?status=COMPLETED,STARTED&mentor=55&started_after=2026-01-01T00:00:00Z`

Response item shape (list; relevant fields):

```json
{
  "id": 401,
  "status": "COMPLETED",
  "summary": "Covered resume and LinkedIn profile",
  "started_at": "2026-03-10T15:00:00Z",
  "ended_at": "2026-03-10T16:05:00Z",
  "mentor_joined_at": "2026-03-10T14:58:00Z",
  "mentee_left_at": "2026-03-10T16:05:00Z",
  "allow_billing": true,
  "accounted_duration": "01:00:00",
  "rating": null,
  "bill": { "id": 22, "status": "DUE" },
  "mentee": {
    "id": 90,
    "first_name": "Alex",
    "last_name": "Student",
    "email": "alex@example.com"
  },
  "mentor": {
    "id": 55,
    "slug": "jane-mentor",
    "status": "ACTIVE",
    "booking_url": "https://calendly.com/jane-mentor/career-coaching",
    "user": {
      "id": 87,
      "first_name": "Jane",
      "last_name": "Mentor",
      "email": "jane@example.com"
    }
  },
  "service": {
    "id": 12,
    "name": "Career Coaching",
    "slug": "career-coaching",
    "duration": "3600.0"
  }
}
```

### Staff get one session

**GET** `/v1/mentorship/academy/session/401`

Response `200` (relevant fields):

```json
{
  "id": 401,
  "status": "COMPLETED",
  "name": null,
  "agenda": "Resume review",
  "summary": "Covered resume and LinkedIn profile",
  "is_online": true,
  "online_meeting_url": "https://meet.google.com/xyz-abcd-efg",
  "online_recording_url": null,
  "starts_at": "2026-03-10T15:00:00Z",
  "ends_at": "2026-03-10T16:00:00Z",
  "started_at": "2026-03-10T15:00:00Z",
  "ended_at": "2026-03-10T16:05:00Z",
  "mentor_joined_at": "2026-03-10T14:58:00Z",
  "mentor_left_at": "2026-03-10T16:06:00Z",
  "mentee_left_at": "2026-03-10T16:05:00Z",
  "allow_billing": true,
  "accounted_duration": "01:00:00",
  "bill": null,
  "mentee": {
    "id": 90,
    "first_name": "Alex",
    "last_name": "Student",
    "email": "alex@example.com"
  },
  "mentor": {
    "id": 55,
    "slug": "jane-mentor",
    "status": "ACTIVE",
    "user": {
      "id": 87,
      "first_name": "Jane",
      "last_name": "Mentor",
      "email": "jane@example.com"
    }
  },
  "service": {
    "id": 12,
    "name": "Career Coaching",
    "slug": "career-coaching"
  }
}
```

### Staff update session

**PUT** `/v1/mentorship/academy/session/401`

Capability: `crud_mentorship_session`

Request:

```json
{
  "mentor": 55,
  "summary": "Student will resubmit resume by Friday",
  "status": "COMPLETED",
  "agenda": "Resume review"
}
```

Bulk updates may send a JSON array of session objects (API supports list PUT). Response returns the updated session big serializer shape.

### Nested staff lists

| Action | Method | Path | Capability |
|--------|--------|------|------------|
| Sessions for mentor | GET | `/v1/mentorship/academy/mentor/{mentor_id}/session` | `read_mentorship_session` |
| Sessions for service | GET | `/v1/mentorship/academy/service/{service_id}/session` | `read_mentorship_session` |

Both are paginated academy-scoped lists.

### Learner my sessions

**GET** `/v1/mentorship/user/me/session`

Headers: `Authorization` (no `Academy` header)

Permission: `get_my_mentoring_sessions`

Paginated when `limit`/`offset` are used.

Response: array (or paginated wrapper) of session objects for the current user as mentor or mentee — same general fields as staff list items (`id`, `status`, `summary`, timestamps, mentor, mentee, service, bill).

## Edge Cases

| Observation | What to do |
|-------------|------------|
| Empty list | Clear filters; verify `Academy` header; verify mentor id; widen date range; for `/user/me/session` confirm the user was mentee or mentor. |
| Agent wants “activity log” from activity domain | Stay on mentorship session endpoints — that is the mentorship meeting log. |
| Need bill payout details | Out of scope here; sessions expose `bill` id/status only. Do not expand into full billing workflows in this skill. |
| PUT rejects online timestamp fields | Those fields are system-managed for online sessions — update `summary` / `status` / `agenda` instead. |
| Session `not-found` | Confirm session belongs to a mentor whose services are in the header academy. |
| Learner lacks `get_my_mentoring_sessions` | Fix permissions via auth skills; do not use academy session routes with a student token unless they are staff. |

## Checklist

1. Correct persona loaded (staff vs student auth).
2. Staff calls include `Academy` header; learner calls use `/user/me/session`.
3. Filters applied deliberately; empty results re-checked with wider filters.
4. Detail fetched for the session under review when notes/URLs matter.
5. Corrections done via PUT only when staff has `crud_mentorship_session`.
6. No generic activity-domain or Admin path used.
7. Book/join URL questions deferred to `bc-mentorship-book-and-join-session`.
