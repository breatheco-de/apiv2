---
name: bc-events-bulk-import-checkins
description: Use when staff bulk-import event attendees (RSVP and optional attended) for an existing academy event via async job; do NOT use for creating/editing events, Luma webhooks, or learner self-service check-in.
requires:
  - bc-events-create-and-edit-event
---

# Skill: Bulk Import Event Check-ins

## When to Use

Use when staff need to import many RSVPs or attendance records for **one existing event** (CSV parsed to JSON on the client, or API payload).

Do NOT use for:

- Creating or editing events (`bc-events-create-and-edit-event`)
- Real-time Luma guest sync (`bc-events-configure-luma-webhooks`)
- Learner self-service (`POST /v1/events/me/event/<event_id>/checkin`)

## Concepts

- Each row is keyed by **email + event** (one `EventCheckin` per pair).
- **RSVP:** `attended: false` → `status=PENDING`, no `attended_at`.
- **Attended:** `attended: true` → `status=DONE` and `attended_at` (defaults to now if omitted).
- **`run_marketing`:** default `false`. When `true`, enqueues ActiveCampaign per row after DB upsert; import job completes before emails/automations finish.
- Jobs live in **Redis** (~24h); poll by `job_id`. No DB job model.
- Recommended **≤500 rows** per request.

## Workflow

1. Set headers: `Authorization`, `Academy: <academy_id>`, optional `Accept-Language`.
2. Confirm the event exists and note `event_id` (from `bc-events-create-and-edit-event`).
3. Optional: export current check-ins as a template — `GET /v1/events/academy/checkin?event=<event_id>` or `GET /v1/events/academy/checkin.csv` (`read_eventcheckin`).
4. Preview without writes: `POST /v1/events/academy/event/<event_id>/checkin/bulk?soft=true` with body below.
5. Run import: `POST /v1/events/academy/event/<event_id>/checkin/bulk` → **202** with `job_id`.
6. Poll: `GET /v1/events/academy/event/<event_id>/checkin/bulk/<job_id>` until `status` is `completed` (`crud_eventcheckin`).
7. Review `results[]` per row (`created`, `updated`, `skipped`, `failed`).

## Endpoints

| Action | Method | Path | Capability |
|--------|--------|------|------------|
| Soft validate | POST | `/v1/events/academy/event/<event_id>/checkin/bulk?soft=true` | `crud_eventcheckin` |
| Start import | POST | `/v1/events/academy/event/<event_id>/checkin/bulk` | `crud_eventcheckin` |
| Poll job | GET | `/v1/events/academy/event/<event_id>/checkin/bulk/<job_id>` | `crud_eventcheckin` |
| List check-ins | GET | `/v1/events/academy/checkin?event=<event_id>` | `read_eventcheckin` |
| Export CSV | GET | `/v1/events/academy/checkin.csv?event=<event_id>` | `read_eventcheckin` |

**POST body:**

```json
{
  "run_marketing": false,
  "checkins": [
    {
      "email": "guest@example.com",
      "first_name": "Guest",
      "last_name": "One",
      "attended": true,
      "attended_at": "2026-06-01T18:30:00Z",
      "utm_source": "import"
    }
  ]
}
```

Query `?run_marketing=true` mirrors body flag (body wins if both set).

**Per-row result fields:** `index`, `email`, `classification` (`NEW_CHECKIN`, `ALREADY_REGISTERED`, `ALREADY_ATTENDED`), `status`, `event_checkin_id`, `message`, `slug`, optional `marketing_status: "queued"`.

## Edge Cases

- Duplicate email in the same event: second import without `attended` → `skipped` (`ALREADY_REGISTERED`).
- Already attended: `skipped` unless you only need idempotent re-import with `attended: false`.
- `run_marketing=true` on large batches: marketing runs in Celery after job `completed`; do not use job status as “all emails sent.”
- Wrong `event_id` on poll → 404 `job-not-found`.

## Checklist

- [ ] Event exists and belongs to academy in `Academy` header
- [ ] Staff has `crud_eventcheckin`
- [ ] Soft run reviewed for `failed` rows
- [ ] Batch ≤500 rows (split larger lists)
- [ ] `run_marketing` only when automations/tags are intended
