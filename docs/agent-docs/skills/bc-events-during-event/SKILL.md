---
name: bc-events-during-event
description: Use when staff operate on a scheduled or live academy workshop before it finishes—reschedule dates, suspend an upcoming event, export the guest list, import outside registrations, or create promo short links with UTM; do NOT use for initial event creation (bc-events-create-and-edit-event), post-event wrap-up (bc-events-post-event), or Luma webhook credential setup (bc-events-configure-luma-webhooks—load only when wiring Luma).
requires:
  - bc-events-create-and-edit-event
---

# Skill: During-Event Operations

## When to Use

Use when an event is scheduled or live (not finished) and staff need to manage guests, dates, registrations, or promotional links.

Do NOT use for:

- Creating or setting up a new event (`bc-events-create-and-edit-event`)
- Post-event wrap-up: attendance reconciliation, recording publish (`bc-events-post-event`)
- Initial Luma webhook credential setup (`bc-events-configure-luma-webhooks`)

## Concepts

- **Scheduled/live event:** `status` is not `FINISHED` and `ending_at` is in the future (or the session is currently running).
- **Outside registrations:** guests who RSVP outside 4Geeks—import via bulk check-in, sync via Luma (`utm_source=luma`), or Eventbrite webhooks (`utm_source=eventbrite`).
- **Guest list export:** async CSV via monitoring downloads (`202` response).
- **Custom broadcast message:** there is **no** staff API to send an ad-hoc email to all guests. Alternatives: suspend email (upcoming only), or `event_rescheduled` webhook for external automation (n8n/Zapier).

## Workflow

1. Set headers: `Authorization`, `Academy: <academy_id>`, optional `Accept-Language`.

2. Load the event.
   - `GET /v1/events/academy/event/<event_id>`
   - Confirm the event is not finished (`status != FINISHED`, `ending_at >= now`).

3. Reschedule (if dates change).
   - `PUT /v1/events/academy/event/<event_id>` with updated `starting_at` / `ending_at`.
   - Fires `event_rescheduled` webhook with pending attendees who have linked platform users—external systems can send emails.

4. Cancel an upcoming event (if needed).
   - `PUT /v1/events/academy/event/<event_id>/suspend` with optional `suspension_reason`.
   - Only works **before** `starting_at`; emails all checkin emails automatically.
   - Cannot suspend an event that has already started.

5. Export or review the guest list.
   - JSON: `GET /v1/events/academy/checkin?event=<event_id>`
   - CSV (async): `GET /v1/events/academy/checkin.csv?event=<event_id>` → poll `GET /v1/monitoring/download/<download_id>?raw=true`

6. Import outside registrations.
   - Manual/batch: [`bc-events-bulk-import-checkins`](../bc-events-bulk-import-checkins/SKILL.md) with `attended: false` for RSVPs or `attended: true` if they already joined.
   - Luma (real-time off-platform guests): [`bc-events-configure-luma-webhooks`](../bc-events-configure-luma-webhooks/SKILL.md)—guests appear as checkins with `utm_source=luma`.
   - Eventbrite: inbound webhook on organization (no staff pull endpoint).

7. Create promotional URLs with UTM attribution.
   - `POST /v1/marketing/academy/short` with `destination` (event landing `url`), UTM fields, and `event: "<id:slug>"` for traceability.
   - List existing links: `GET /v1/marketing/academy/short?event=<event_id>`
   - UTM preset catalog: `GET /v1/marketing/academy/utm?type=SOURCE,MEDIUM,CAMPAIGN`
   - See [`MARKETING_SHORTCUTS.md`](../../MARKETING_SHORTCUTS.md).

8. Staff join the live session (if needed).
   - `GET /v1/events/academy/event/<event_id>/join` (`start_or_end_event` capability).

## Endpoints

| Action | Method | Path | Capability | Notes |
|---|---|---|---|---|
| Get event | GET | `/v1/events/academy/event/<event_id>` | `read_event` | Verify status and dates |
| Reschedule | PUT | `/v1/events/academy/event/<event_id>` | `crud_event` | Update `starting_at`, `ending_at` |
| Suspend upcoming | PUT | `/v1/events/academy/event/<event_id>/suspend` | `crud_event` | Optional `suspension_reason`; emails all guests |
| List check-ins | GET | `/v1/events/academy/checkin?event=<event_id>` | `read_eventcheckin` | Filter `status`, `like`, dates |
| Export check-ins CSV | GET | `/v1/events/academy/checkin.csv?event=<event_id>` | `read_eventcheckin` | Async — poll monitoring download |
| Bulk import check-ins | POST | `/v1/events/academy/event/<event_id>/checkin/bulk` | `crud_eventcheckin` | See bulk-import skill |
| Create promo short link | POST | `/v1/marketing/academy/short` | `crud_shortlink` | Tie to event via `event` field |
| List promo short links | GET | `/v1/marketing/academy/short?event=<event_id>` | `read_shortlink` | Filter by event |
| Staff join live | GET | `/v1/events/academy/event/<event_id>/join` | `start_or_end_event` | Redirects to live stream |

**Suspend request**
```json
{
  "suspension_reason": "Speaker unavailable"
}
```

**Promo short link request**
```json
{
  "destination": "https://4geeks.com/workshops/intro-python",
  "slug": "intro-python-ig",
  "event": "101:intro-python-workshop",
  "utm_source": "instagram",
  "utm_medium": "social",
  "utm_campaign": "intro-python-apr"
}
```

## Edge Cases

- `event-already-started` — suspend rejected if `starting_at <= now`.
- `use-suspend-endpoint` — cannot set `SUSPENDED` via normal event PUT.
- No custom broadcast API — use suspend (upcoming only) or reschedule webhook integrations.
- Reschedule webhook recipients — only `PENDING` checkins with linked `attendee` user; email-only guests need external handling.
- CSV export is async — not an immediate file download.
- Luma guests register off-platform — checkins have `utm_source=luma`; attendance may update via `guest.updated` webhook.

## Checklist

1. Headers set (`Authorization`, `Academy`).
2. Event loaded and confirmed not finished.
3. Chosen action: reschedule, suspend, export guests, import registrations, or promo link.
4. If importing outside guests: bulk import or confirm Luma webhook is configured.
5. If promo link needed: short link created with `event` traceability and UTM fields.
6. For post-event tasks after the session ends, switch to [`bc-events-post-event`](../bc-events-post-event/SKILL.md).
