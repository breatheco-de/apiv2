---
name: bc-events-post-event
description: Use when staff wrap up a finished academy workshop—confirm the event has ended, reconcile attendance (platform join, Luma off-platform guests, or bulk import), publish the recording URL (emails checkins with attended_at), and know what runs automatically (AI recap, NPS survey); do NOT use for creating events (bc-events-create-and-edit-event), operating while scheduled/live (bc-events-during-event), or initial Luma webhook setup (bc-events-configure-luma-webhooks).
requires:
  - bc-events-create-and-edit-event
---

# Skill: Post-Event Workshop Wrap-Up

## When to Use

Use when a workshop has ended and staff need to close the loop: verify finish state, ensure attendance is recorded, publish the recording, and confirm automatic follow-ups fired.

Do NOT use for:

- Creating or editing event details before/during the live session (`bc-events-create-and-edit-event`)
- Operating on a scheduled or live event (`bc-events-during-event`)
- Initial Luma webhook credential setup (`bc-events-configure-luma-webhooks`)

## Concepts

- **Finished event:** `status == FINISHED`, or `ending_at` is in the past. Past `ACTIVE` events are auto-marked `FINISHED` by the `garbage_collect_events` management command (sets `ended_at`).
- **Attended checkin:** `EventCheckin` with `attended_at` set (usually `status=DONE`). Set live via join/Luma, or imported via bulk check-in skill.
- **Luma off-platform guests:** guests who registered on Luma (not on 4Geeks) get checkins with `utm_source=luma` and `luma_guest_id`; `guest.updated` webhooks may set attendance.
- **Publish recording:** `PUT .../recording` saves `recording_url` and asynchronously emails every attended checkin with a valid email. Only the first time a URL goes from empty to set.
- **Automatic on FINISHED (no staff call):** AI event recap is generated; NPS survey emails go to attended checkins that have a linked platform user (`attendee`).

## Workflow

1. Set headers: `Authorization`, `Academy: <academy_id>`, optional `Accept-Language`.

2. Load and verify the event.
   - `GET /v1/events/academy/event/<event_id>` (or list with filters).
   - Confirm `status == FINISHED` or `ending_at < now`.
   - If still `ACTIVE` but `ending_at` passed, either wait for auto-finish or set `status: FINISHED` via `PUT /v1/events/academy/event/<event_id>`.

3. Finalize attendance before publishing the recording.
   - `GET /v1/events/academy/checkin?event=<event_id>&status=DONE`
   - **Platform join:** checkins with `attended_at` from live consumption.
   - **Luma (guests who registered outside the platform):** if the event uses Luma, load [`bc-events-configure-luma-webhooks`](../bc-events-configure-luma-webhooks/SKILL.md)—reconcile checkins with `utm_source=luma` and `luma_guest_id`; `guest.updated` may have set `attended_at`.
   - **Manual outside guests:** use [`bc-events-bulk-import-checkins`](../bc-events-bulk-import-checkins/SKILL.md) with `attended: true`.

4. Publish the recording (preferred path).
   - `PUT /v1/events/academy/event/<event_id>/recording`
   - Body: `{ "recording_url": "https://..." }` (http/https required).
   - Returns `200` with updated event; emails queued for checkins with `attended_at`.

5. Verify outcome.
   - Re-fetch event and confirm `recording_url` is set.
   - Optional: confirm check-in count matches expected attendees.
   - Note: recap and NPS survey are triggered automatically when status becomes `FINISHED`—staff do not call those endpoints.

## Endpoints

| Action | Method | Path | Capability | Body | Notes |
|---|---|---|---|---|---|
| Get event | GET | `/v1/events/academy/event/<event_id>` | `read_event` | — | Verify `status`, `ending_at`, `recording_url` |
| Mark finished | PUT | `/v1/events/academy/event/<event_id>` | `crud_event` | `{ "id": <id>, "status": "FINISHED", ... }` | Triggers recap + NPS automatically |
| List check-ins | GET | `/v1/events/academy/checkin?event=<event_id>` | `read_eventcheckin` | — | Filter `status=DONE` for attendees |
| Publish recording | PUT | `/v1/events/academy/event/<event_id>/recording` | `crud_event` | `{ "recording_url": "https://..." }` | `400` if event not finished; emails attended checkins |

**Publish recording request**
```json
{
  "recording_url": "https://cdn.example.com/workshops/intro-python-recording.mp4"
}
```

**Publish recording response (200)** — same shape as other event GET/PUT responses; includes `recording_url`.

## Edge Cases

- `event-not-finished` — recording endpoint rejects if event has not ended yet.
- `invalid-recording-url` — URL must start with `http://` or `https://`.
- No attended checkins — recording saves but no emails are sent.
- RSVP-only checkins (`attended_at` null) — not emailed; import or mark attendance first.
- Luma guests without `attended_at` — check Luma webhook sync or bulk-import with `attended: true`.
- Recording URL already set — updating to a new URL does not re-notify (only first publish triggers emails).
- NPS survey audience is narrower than recording emails — requires `attendee` user linked, not just email.
- Setting `recording_url` via general `PUT /v1/events/academy/event/<event_id>` also notifies if event is finished; prefer `.../recording` for explicit validation.

## Checklist

1. Headers set (`Authorization`, `Academy`).
2. Event loaded and confirmed finished.
3. Attendance verified or imported (`attended_at` on expected checkins, including Luma/off-platform guests).
4. Recording published via `PUT .../recording`.
5. Event re-fetched to confirm `recording_url`.
6. Staff aware recap/NPS already ran on `FINISHED` (no extra step).
