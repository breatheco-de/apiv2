---
name: bc-admissions-create-manage-syllabus-schedules
description: Use when staff need to create and manage syllabus schedule templates, schedule timeslots, and sync them into cohort timeslots; do NOT use for syllabus JSON/version authoring or macro override content workflows.
requires: []
---

# Skill: Create and Manage Syllabus Schedules

## When to Use

Use this skill when the user needs to manage class schedule templates under admissions: create/update schedule records, configure schedule timeslots, assign a schedule to cohorts, and sync those template timeslots into cohort timeslots. Do NOT use this skill for syllabus JSON content/versioning (`/syllabus/.../version`) or for macro-cohort overrides.

## Concepts

- A **syllabus schedule** is a reusable template linked to one academy and one syllabus.
- A **schedule timeslot** stores recurrent meeting windows for that template.
- A **cohort timeslot** is the concrete cohort schedule used by downstream flows.
- Syncing from schedule to cohort is a **replace** operation: existing cohort timeslots for target cohorts are deleted, then recreated from schedule timeslots.

## Workflow

1. Set request context first.
   - Send `Authorization: Token <token>` on protected endpoints.
   - Send `Academy: <academy_id>` on all `/academy/...` schedule endpoints.
   - Send optional `Accept-Language` (for example `en` or `es`) if translated error messages are needed.

2. Create or locate a schedule template for the target academy.
   - Create with `POST /v1/admissions/academy/schedule`.
   - Read academy-local templates with `GET /v1/admissions/academy/schedule`.

3. Configure schedule timeslots for that schedule.
   - Create with `POST /v1/admissions/academy/schedule/<schedule_id>/timeslot`.
   - Update with `PUT /v1/admissions/academy/schedule/<schedule_id>/timeslot/<timeslot_id>`.
   - Delete with `DELETE /v1/admissions/academy/schedule/<schedule_id>/timeslot/<timeslot_id>`.
   - Read list/detail using the same route family with `GET`.

4. Attach the schedule to cohorts.
   - On cohort create/update, set `schedule` to the schedule id.
   - Cohorts without `schedule` cannot be synced.

5. Sync schedule timeslots into one or more cohorts.
   - Call `POST /v1/admissions/academy/cohort/sync/timeslot?cohort=<id[,id2,...]>`.
   - This deletes existing `CohortTimeSlot` rows for those cohorts and recreates them from schedule timeslots.

6. Verify the resulting cohort timeslots.
   - Confirm sync response payload and then read cohort timeslots from cohort endpoints if needed.

## Endpoints

| Action | Method | Path | Headers | Body | Response |
|---|---|---|---|---|---|
| List public schedules | GET | `/v1/admissions/schedule` | `Authorization`, optional `Accept-Language` | Optional query filters (`syllabus_id`, `syllabus_slug`, `academy_id`, `academy_slug`) | Non-paginated array by default; supports pagination extension when pagination params are used |
| Get one public schedule | GET | `/v1/admissions/schedule/<schedule_id>/` | `Authorization`, optional `Accept-Language` | — | `200` schedule object (`id`, `name`, `description`, `syllabus`) |
| List academy schedules | GET | `/v1/admissions/academy/schedule` | `Authorization`, `Academy`, optional `Accept-Language` | Optional query filters (`syllabus_id`, `syllabus_slug`, `schedule_type`) | Non-paginated array by default; paginated response when pagination params are used |
| Create academy schedule | POST | `/v1/admissions/academy/schedule` | `Authorization`, `Academy`, optional `Accept-Language` | `academy`, `syllabus`, `name`, `description`, optional `schedule_type` | `201` schedule object including `created_at`, `updated_at` |
| Get one academy schedule | GET | `/v1/admissions/academy/schedule/<schedule_id>` | `Authorization`, `Academy`, optional `Accept-Language` | — | `200` schedule object (`id`, `name`, `description`, `syllabus`) |
| Update academy schedule | PUT | `/v1/admissions/academy/schedule/<schedule_id>` | `Authorization`, `Academy`, optional `Accept-Language` | Partial fields (`name`, `description`, `schedule_type`, `syllabus`) | `200` updated schedule object |
| Delete one academy schedule | DELETE | `/v1/admissions/academy/schedule/<schedule_id>` | `Authorization`, `Academy`, optional `Accept-Language` | — | `204` |
| Bulk delete academy schedules | DELETE | `/v1/admissions/academy/schedule?id=<id[,id2,...]>` | `Authorization`, `Academy`, optional `Accept-Language` | Querystring must include at least one lookup (`id`) | `204` |
| List schedule timeslots | GET | `/v1/admissions/academy/schedule/<schedule_id>/timeslot` | `Authorization`, `Academy`, optional `Accept-Language` | Optional `recurrency_type` query | `200` list with ISO `starting_at`/`ending_at` |
| Get schedule timeslot | GET | `/v1/admissions/academy/schedule/<schedule_id>/timeslot/<timeslot_id>` | `Authorization`, `Academy`, optional `Accept-Language` | — | `200` timeslot object |
| Create schedule timeslot | POST | `/v1/admissions/academy/schedule/<schedule_id>/timeslot` | `Authorization`, `Academy`, optional `Accept-Language` | `starting_at`, `ending_at` (ISO), optional `recurrent`, `recurrency_type` | `201` timeslot write serializer object |
| Update schedule timeslot | PUT | `/v1/admissions/academy/schedule/<schedule_id>/timeslot/<timeslot_id>` | `Authorization`, `Academy`, optional `Accept-Language` | `starting_at`, `ending_at` (ISO), optional `recurrent`, `recurrency_type` | `200` timeslot write serializer object |
| Delete schedule timeslot | DELETE | `/v1/admissions/academy/schedule/<schedule_id>/timeslot/<timeslot_id>` | `Authorization`, `Academy`, optional `Accept-Language` | — | `204` |
| Sync timeslots to cohorts | POST | `/v1/admissions/academy/cohort/sync/timeslot?cohort=<id[,id2,...]>` | `Authorization`, `Academy`, optional `Accept-Language` | Empty body | `201` list of created cohort timeslots |

**Create academy schedule request**
```json
{
  "academy": 1,
  "syllabus": 12,
  "name": "Full-Time Morning",
  "description": "Monday to Friday, 09:00 to 13:00",
  "schedule_type": "FULL-TIME"
}
```

**Create academy schedule response (201)**
```json
{
  "id": 44,
  "academy": 1,
  "syllabus": 12,
  "name": "Full-Time Morning",
  "description": "Monday to Friday, 09:00 to 13:00",
  "schedule_type": "FULL-TIME",
  "created_at": "2026-04-01T12:00:00Z",
  "updated_at": "2026-04-01T12:00:00Z"
}
```

**List academy schedules response (non-paginated default)**
```json
[
  {
    "id": 44,
    "name": "Full-Time Morning",
    "description": "Monday to Friday, 09:00 to 13:00",
    "syllabus": 12
  }
]
```

**Create schedule timeslot request**
```json
{
  "starting_at": "2026-05-04T13:00:00Z",
  "ending_at": "2026-05-04T17:00:00Z",
  "recurrent": true,
  "recurrency_type": "WEEKLY"
}
```

**Create schedule timeslot response (201)**
```json
{
  "id": 301,
  "schedule": 44,
  "recurrent": true,
  "recurrency_type": "WEEKLY",
  "timezone": "America/New_York"
}
```

**List schedule timeslots response**
```json
[
  {
    "id": 301,
    "schedule": 44,
    "starting_at": "2026-05-04T13:00:00Z",
    "ending_at": "2026-05-04T17:00:00Z",
    "recurrent": true,
    "recurrency_type": "WEEKLY",
    "created_at": "2026-04-01T12:15:00Z",
    "updated_at": "2026-04-01T12:15:00Z"
  }
]
```

**Sync schedule timeslots to cohorts request**
```json
{}
```

**Sync schedule timeslots to cohorts response (201)**
```json
[
  {
    "id": 801,
    "cohort": 1001,
    "recurrent": true,
    "recurrency_type": "WEEKLY",
    "timezone": "America/New_York"
  }
]
```

## Edge Cases

- Missing `Academy` header on `/academy/...` endpoints returns `403`.
- Missing capability returns `403`: schedule list/detail uses `read_certificate`; schedule create/update/delete uses `crud_certificate`; **schedule timeslot** create/update/delete uses `crud_cohort` (same scope as cohort edits); cohort timeslot sync uses `crud_cohort`.
- Creating a schedule without `syllabus` returns `missing-syllabus-in-request`.
- Creating a schedule without `academy` in body returns `missing-academy-in-request`.
- Timeslot create/update fails with `academy-without-timezone` when academy timezone is not configured.
- Timeslot create/update requires both `starting_at` and `ending_at`.
- Sync fails with `missing-cohort-in-querystring` if `cohort` query param is absent.
- Sync fails with `cohort-without-specialty-mode` if a target cohort has no assigned schedule.
- Sync fails with `without-timezone` when academy timezone is missing.
- Sync is destructive for target cohorts: existing cohort timeslots are removed before recreation.
- `schedule_type` and `recurrency_type` are normalized to uppercase accepted values.

## Checklist

1. Confirm headers are set correctly (`Authorization`, `Academy`, optional `Accept-Language`).
2. Create or select a valid schedule for the target `academy` + `syllabus`.
3. Create at least one schedule timeslot and verify it appears in timeslot GET.
4. Ensure target cohort(s) have `schedule` assigned.
5. Run sync endpoint with `cohort` querystring ids.
6. Verify sync response includes created cohort timeslots.
7. Re-check cohort timeslots and confirm they match schedule timeslot recurrence/timezone.
