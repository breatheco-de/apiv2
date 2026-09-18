---
name: bc-mentorship-book-and-join-session
description: Use when directing students or mentors to book or join a mentorship via /mentor short links (Calendly book, meet URL, session close); do NOT use for creating mentors, reviewing session logs, or configuring payment plans.
requires:
  - bc-authenticate-student-authentication
---

# Skill: Book and Join Mentorship Sessions

## When to Use

Use when the user asks **what URL to open to book a mentor**, **how a student joins a meeting**, or **how a mentor joins/closes a session**. Do NOT use to create or activate mentors (load `bc-mentorship-create-manage-mentor`), to list session history (load `bc-mentorship-review-session-activity`), or to set up plans/consumables from scratch (load `bc-payments-*` only when join fails for credits).

## Concepts

- **Book ≠ join.** Booking opens Calendly. Joining starts or enters the video session.
- **Short links live on the API host** under `/mentor/...` (HTML pages), not under `/v1/mentorship/`. Auth is the query param `?token=<auth_token>`.
- **Same meet URL for student and mentor.** Role is determined by whose token is used. Do not invent a separate mentor-only meet API.
- **Mentors close** the session at `/mentor/session/{session_id}?token=...`.
- **Calendly-only self-serve booking.** Non-Calendly schedulers are unsupported for the student booking flow. Staff may create a one-off session with `POST /v1/mentorship/academy/session` as an exception — not a substitute for student self-booking.
- **Join consumes `join_mentorship`.** Students need that permission/consumable (often from a plan with a mentorship service set). Mentors joining with their own token follow the mentor path on the same URL.
- **Live room:** service `video_provider` `GOOGLE_MEET` may redirect to Meet; `DAILY` renders an in-app room and shows the mentor backup URL as fallback.

## Workflow

### Step 1 — Obtain a token

1. Load `bc-authenticate-student-authentication` (or staff auth if generating a token for a known user).
2. Obtain an auth token for the **student** (to book/join as mentee) or the **mentor user** (to join/close as mentor).
3. Confirm the mentor profile is `ACTIVE` or `UNLISTED` and has a Calendly `booking_url`. If not, stop and use `bc-mentorship-create-manage-mentor`.

### Step 2 — Student books a meeting

Give the student one of:

- All mentor services: `{API_BASE}/mentor/{mentor_slug}?token={token}`
- Specific service: `{API_BASE}/mentor/{mentor_slug}/service/{service_slug}?token={token}`

The page embeds Calendly from the mentor’s `booking_url`. Service-specific booking should pass tracking so Calendly webhooks receive the service slug (`utm_campaign` = service slug). After booking, Calendly’s webhook creates/updates the session — do not invent webhook payloads.

### Step 3 — Student joins the meeting

1. Prefer the direct join URL:  
   `{API_BASE}/mentor/meet/{mentor_slug}/service/{service_slug}?token={token}`
2. If the service is unknown, use the picker first:  
   `{API_BASE}/mentor/meet/{mentor_slug}?token={token}`  
   then continue to `/service/{service_slug}`.
3. Optional query params: `redirect=true` (proceed into the room), `session={id}` (open a specific session), `extend=true` (extend when allowed).
4. If join fails for missing `join_mentorship` permission or consumable credits, **stop**. Load `bc-authenticate-student-authentication` to verify permissions and `bc-payments-manage-plans` (or related payments skills) to fix plan/mentorship service set access. Do not duplicate plan setup inside this skill.

### Step 4 — Mentor joins and closes

1. Mentor opens the **same** meet URL with the **mentor’s** token:  
   `{API_BASE}/mentor/meet/{mentor_slug}/service/{service_slug}?token={mentor_token}`
2. After the meeting, mentor closes / leaves feedback at:  
   `{API_BASE}/mentor/session/{session_id}?token={mentor_token}`
3. Do not invent alternate mentor dashboard meet endpoints.

### Step 5 — Staff one-off session (exception only)

When self-serve Calendly booking is impossible and staff must schedule manually:

1. Staff auth + `Academy` header + `crud_mentorship_session`.
2. `POST /v1/mentorship/academy/session` with `mentor` and `service` (ids or resolvable identifiers).
3. Tell student and mentor to use the meet short links in Steps 3–4.

This is not the default student booking path.

## Endpoints

### Short links (primary — browser GET)

Base: API host (e.g. `https://breathecode.herokuapp.com`). All require `?token=`.

| Purpose | Method | Path |
|---------|--------|------|
| Book (any service) | GET | `/mentor/{mentor_slug}?token={token}` |
| Book (one service) | GET | `/mentor/{mentor_slug}/service/{service_slug}?token={token}` |
| Pick service to join | GET | `/mentor/meet/{mentor_slug}?token={token}` |
| Join session | GET | `/mentor/meet/{mentor_slug}/service/{service_slug}?token={token}` |
| Close session (mentor) | GET | `/mentor/session/{session_id}?token={token}` |

These return HTML (booking embed, start/join UI, Daily room, or redirect to Google Meet). There is no JSON body.

**Example student join URL:**

```text
https://breathecode.herokuapp.com/mentor/meet/jane-mentor/service/career-coaching?token=abc123token
```

**Example mentor close URL:**

```text
https://breathecode.herokuapp.com/mentor/session/401?token=mentorTokenHere
```

### System Calendly webhook (do not call as an agent)

- **POST** `/v1/mentorship/calendly/webhook/{org_hash}` — owned by Calendly; creates sessions from bookings. Do not craft payloads.

### Staff manual session (exception)

**POST** `/v1/mentorship/academy/session`

Headers: `Authorization`, `Academy: 4`, `Content-Type: application/json`, `Accept-Language: en`

Capability: `crud_mentorship_session`

Request:

```json
{
  "mentor": 55,
  "service": 12,
  "mentee": 90,
  "agenda": "Resume review"
}
```

`mentor` and `service` are required (numeric id or resolvable slug/email per API rules).

Response `201` (relevant fields):

```json
{
  "id": 401,
  "status": "PENDING",
  "agenda": "Resume review",
  "allow_billing": false,
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
  },
  "mentee": {
    "id": 90,
    "first_name": "Alex",
    "last_name": "Student",
    "email": "alex@example.com"
  },
  "online_meeting_url": null,
  "started_at": null,
  "ended_at": null
}
```

## Edge Cases

| Observation | What to do |
|-------------|------------|
| User asks for Cal.com / HubSpot booking | Refuse for self-serve: only Calendly-backed mentor profiles work. Point staff at mentor setup skill to fix `booking_url`, or use the staff one-off session exception. |
| Join denied / no `join_mentorship` | Load student auth to confirm permission; load payments skills to attach mentorship service set / consumables. Do not invent bypass URLs. |
| Mentor asks for a different meet URL than the student | Give the same `/mentor/meet/.../service/...` URL with the mentor’s token; close via `/mentor/session/{id}`. |
| Mentor not ACTIVE/UNLISTED | Booking/meet short links fail readiness checks — fix mentor via `bc-mentorship-create-manage-mentor`. |
| Google Meet vs Daily | Meet may hard-redirect to `online_meeting_url`; Daily keeps the user on API-hosted UI with room + backup link. |
| No prior Calendly booking | Ad-hoc join can still create/reuse a pending session on the meet URL — that is expected. |
| Agent tries to POST to `/mentor/...` as JSON API | Correct: short links are browser GETs with `token`, not REST JSON resources. |

## Checklist

1. Token obtained for the correct role (student vs mentor).
2. Mentor is ACTIVE/UNLISTED with Calendly booking URL.
3. Student book URL provided (`/mentor/{slug}` or with `/service/{service_slug}`).
4. Student join URL provided (`/mentor/meet/{slug}/service/{service_slug}?token=...`).
5. Mentor given the same meet URL (mentor token) and session close URL.
6. If join failed on credits/permission, payments + auth skills loaded instead of guessing.
7. No non-Calendly scheduler recommended for self-serve booking.
