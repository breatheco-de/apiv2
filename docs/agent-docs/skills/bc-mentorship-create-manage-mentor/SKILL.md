---
name: bc-mentorship-create-manage-mentor
description: Use when creating or activating an academy mentorship service and mentor profile (Calendly booking, backup meeting URL, syllabus, ACTIVE/UNLISTED); do NOT use for student booking/join URLs, session activity review, or mentorship billing.
requires:
  - bc-authenticate-staff-authentication
  - bc-authenticate-staff-invites
---

# Skill: Create and Manage Mentorship Mentors

## When to Use

Use when staff need to **create a mentorship service**, **create a mentor for an academy**, **attach services/syllabus**, or **activate** a mentor (`ACTIVE` / `UNLISTED`). Do NOT use for student book/join short links (load `bc-mentorship-book-and-join-session`), session logs (load `bc-mentorship-review-session-activity`), or plan/consumable setup (load `bc-payments-*`).

## Concepts

- **One mentor profile = one academy.** The `Academy` header sets academy on create. The same user may have another profile in a different academy; each profile needs a **unique** public `slug`.
- **Services** are academy-owned offerings (e.g. career coaching). Mentors offer services via a list of service IDs.
- **Calendly-only booking.** `booking_url` must contain `https://calendly.com` before status can become `ACTIVE` or `UNLISTED`. Other schedulers are not supported for self-serve booking.
- **Backup vs live room.** `online_meeting_url` on the mentor is a **backup** (any reachable URL: Meet, Zoom, etc.). The live room for a session comes from the service `video_provider` (`GOOGLE_MEET` or `DAILY`), or from Calendly’s join URL when present. Do not treat the backup URL as the primary room source.
- **Multi-academy Calendly.** Reusing the same Calendly URL across **different** academies is allowed. Never create two profiles in the **same** academy that share the same Calendly URL or mentor email — webhook mentor matching uses `.first()` and can attach sessions to the wrong profile. Prefer distinct Calendly URLs per profile when practical.
- **ProfileAcademy required.** The mentor’s user must have a ProfileAcademy in that academy (name/email resolution and updates depend on it).
- **Activation also needs** at least one syllabus and a healthy availability report (no failing booking/meeting URL checks).

## Workflow

### Step 0 — Auth and ProfileAcademy

1. Load `bc-authenticate-staff-authentication`. Confirm staff token and capabilities `crud_mentorship_service` and `crud_mentorship_mentor` for the target academy.
2. Send **`Academy: <academy_id>`** on every `/v1/mentorship/academy/...` call. Send **`Accept-Language`** (`en` or `es`) for translated errors.
3. Confirm the future mentor user has a **ProfileAcademy** in that academy. If missing, load `bc-authenticate-staff-invites`, invite/accept them into the academy, then continue. Do not create the mentor until ProfileAcademy exists (PUT/activate will fail later).

### Step 1 — Ensure a mentorship service

1. Optionally list existing services: `GET /v1/mentorship/academy/service` (paginated; capability `read_mentorship_service`).
2. If none fits, create one: `POST /v1/mentorship/academy/service` with at least `slug` and `name`. Set `status` to `ACTIVE` when ready to offer. Set `video_provider` to `GOOGLE_MEET` or `DAILY`.
3. Save the returned service `id` and `slug`.

### Step 2 — Create the mentor profile

1. `POST /v1/mentorship/academy/mentor` with required fields: `slug`, `user` (user id), `price_per_hour`, `services` (array of service ids). Academy is forced from the `Academy` header — do not rely on a client-supplied academy override.
2. Save returned mentor `id`, `slug`, and `status` (starts as `INVITED`).

### Step 3 — Configure and activate

1. `PUT /v1/mentorship/academy/mentor/{mentor_id}` with:
   - `booking_url`: Calendly URL containing `https://calendly.com`
   - `online_meeting_url`: backup meeting URL
   - `syllabus`: array of syllabus ids (at least one)
   - `services`: service ids if changing
2. Then set `status` to `ACTIVE` (public) or `UNLISTED` (bookable but not listed on public mentor catalog). Activation runs readiness checks; if they fail, fix the fields and retry.
3. Do not send `user` or `token` on PUT — those fields are read-only.

### Step 4 — Verify

Call `GET /v1/mentorship/academy/mentor/{mentor_id}` and confirm `status`, `booking_url`, `online_meeting_url`, `services`, and `syllabus` match intent.

For student book/join URLs after activation, load [`bc-mentorship-book-and-join-session`](../bc-mentorship-book-and-join-session/SKILL.md).

## Endpoints

All `/academy/` endpoints require the **`Academy`** header. List endpoints support pagination (`limit`, `offset`; response may include `count` / `results` when paginated). Send **`Accept-Language`** for translated errors.

| Action | Method | Path | Capability |
|--------|--------|------|------------|
| List services | GET | `/v1/mentorship/academy/service` | `read_mentorship_service` |
| Create service | POST | `/v1/mentorship/academy/service` | `crud_mentorship_service` |
| Update service | PUT | `/v1/mentorship/academy/service/{service_id}` | `crud_mentorship_service` |
| List mentors | GET | `/v1/mentorship/academy/mentor` | `read_mentorship_mentor` |
| Create mentor | POST | `/v1/mentorship/academy/mentor` | `crud_mentorship_mentor` |
| Get mentor | GET | `/v1/mentorship/academy/mentor/{mentor_id}` | `read_mentorship_mentor` |
| Update mentor | PUT | `/v1/mentorship/academy/mentor/{mentor_id}` | `crud_mentorship_mentor` |

### Create service

**POST** `/v1/mentorship/academy/service`

Headers: `Authorization`, `Academy: 4`, `Content-Type: application/json`, `Accept-Language: en`

Request:

```json
{
  "slug": "career-coaching",
  "name": "Career Coaching",
  "status": "ACTIVE",
  "video_provider": "GOOGLE_MEET",
  "description": "One-hour career mentoring sessions",
  "language": "en"
}
```

Response `201` (relevant fields):

```json
{
  "id": 12,
  "slug": "career-coaching",
  "name": "Career Coaching",
  "status": "ACTIVE",
  "video_provider": "GOOGLE_MEET",
  "duration": "01:00:00",
  "max_duration": "02:00:00",
  "missed_meeting_duration": "00:10:00",
  "language": "en",
  "allow_mentee_to_extend": true,
  "allow_mentors_to_extend": true,
  "description": "One-hour career mentoring sessions",
  "logo_url": null
}
```

Unset duration/language/extend/video fields inherit academy mentorship settings or platform defaults (1h duration, Google Meet).

### Create mentor

**POST** `/v1/mentorship/academy/mentor`

Request:

```json
{
  "slug": "jane-mentor",
  "user": 87,
  "price_per_hour": 40,
  "services": [12],
  "name": "Jane Mentor"
}
```

Required: `slug`, `user`, `price_per_hour`, `services`. Name/email are filled from ProfileAcademy or User when omitted.

Response `201` (relevant fields):

```json
{
  "id": 55,
  "slug": "jane-mentor",
  "status": "INVITED",
  "price_per_hour": 40.0,
  "booking_url": null,
  "online_meeting_url": null,
  "email": "jane@example.com",
  "syllabus": [],
  "user": {
    "id": 87,
    "first_name": "Jane",
    "last_name": "Mentor",
    "email": "jane@example.com"
  },
  "services": [
    {
      "id": 12,
      "slug": "career-coaching",
      "name": "Career Coaching",
      "status": "ACTIVE"
    }
  ]
}
```

### Update and activate mentor

**PUT** `/v1/mentorship/academy/mentor/55`

Request:

```json
{
  "booking_url": "https://calendly.com/jane-mentor/career-coaching",
  "online_meeting_url": "https://meet.google.com/abc-defg-hij",
  "syllabus": [3],
  "services": [12],
  "status": "ACTIVE",
  "timezone": "America/New_York"
}
```

Response `200` includes the same shape as create, with updated fields and `status: "ACTIVE"`.

Mentor list query filters (optional): `services` (service slugs, comma-separated), `status`, `syllabus` (syllabus slugs), `like` (name search).

## Edge Cases

| Observation | What to do |
|-------------|------------|
| Activation error: booking_url must point to calendly | Set `booking_url` to a URL containing `https://calendly.com`. Do not use Cal.com or other schedulers for activation. |
| Activation error: missing online_meeting_url | Set any reachable backup meeting URL, then retry ACTIVE/UNLISTED. |
| Activation error: no syllabus | Attach at least one syllabus id on PUT, then retry. |
| Activation error: booking/meeting URL failing | Fix the URL so it responds successfully to health checks; clear bad availability report by correcting URLs and re-checking. |
| `profile-academy-not-found` on PUT | Load `bc-authenticate-staff-invites`, create ProfileAcademy for the mentor user, ensure first/last name are set, retry PUT. |
| `missing-slug-field` on POST | Always send `slug` in the create body. |
| User wants the same person in two academies | Create a **second** mentor profile under the other academy’s `Academy` header with a **different** `slug`. Do not reuse one profile across academies. |
| Same Calendly on two profiles in one academy | Refuse / warn — create distinct Calendly event URLs or keep a single profile per academy. |
| Agent assumes backup Meet link is always the live room | Correct them: live room follows service `video_provider` (or Calendly join URL); mentor URL is backup only. |
| Service slug change on PUT | Service slug cannot be updated; create a new service if a new slug is required. |

## Checklist

1. Staff auth loaded; `Academy` header set; capabilities confirmed.
2. Mentor user has ProfileAcademy in the academy (invited if needed).
3. Mentorship service exists (`id` saved); `video_provider` is `GOOGLE_MEET` or `DAILY`.
4. Mentor created with unique `slug`, `user`, `price_per_hour`, `services`.
5. PUT set Calendly `booking_url`, backup `online_meeting_url`, and ≥1 syllabus.
6. Status set to `ACTIVE` or `UNLISTED` without readiness errors.
7. GET mentor confirms configuration; no duplicate same-academy Calendly identity.
