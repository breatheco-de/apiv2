# Event Recording Notification

When staff publish a workshop recording after the event has finished, the API emails attendees who actually attended.

## Trigger

Notification fires when `recording_url` changes from empty to a non-empty URL **and** the event is finished (`status == FINISHED` or `ending_at` is in the past).

Entry points:

| Path | Behavior |
|---|---|
| `PUT /v1/events/academy/event/<event_id>/recording` | Preferred — validates event is finished before save |
| `PUT /v1/events/academy/event/<event_id>` with `recording_url` | Also triggers notification if event is finished at save time |
| Django admin | Same model trigger |

The dedicated endpoint saves `recording_url` via `Event.save()`; the model trigger queues the Celery task (no duplicate emails).

## Recipients

- `EventCheckin` rows with `attended_at` set and a valid `email`
- RSVP-only checkins (`attended_at` null) are **not** emailed
- Luma/off-platform guests count if their checkin has `attended_at` (see [`bc-events-configure-luma-webhooks`](skills/bc-events-configure-luma-webhooks/SKILL.md))

## Celery task

`send_event_recording_notification(event_id)` in `breathecode/events/tasks.py`:

- Uses the generic `message` email template with `BUTTON` / `LINK` pointing to `recording_url`
- Bilingual subject/body from `event.lang` (en/es)
- Priority: `NOTIFICATION`

## API: Publish recording

**`PUT /v1/events/academy/event/{event_id}/recording`**

- Capability: `crud_event`
- Headers: `Authorization`, `Academy`

**Request**
```json
{
  "recording_url": "https://cdn.example.com/workshops/recording.mp4"
}
```

**Errors**

| Slug | When |
|---|---|
| `event-not-found` | Event not in academy |
| `event-not-finished` | Event has not ended yet |
| `invalid-recording-url` | URL does not start with `http://` or `https://` |

## Related automation (no staff action)

When `status` becomes `FINISHED`:

- `generate_event_recap` — AI recap on `EventContext`
- `send_event_survey` — NPS to attended checkins with linked `attendee` user (narrower audience than recording emails)

## Agent skills

- Post-event workflow: [`bc-events-post-event`](skills/bc-events-post-event/SKILL.md)
- During-event operations: [`bc-events-during-event`](skills/bc-events-during-event/SKILL.md)
