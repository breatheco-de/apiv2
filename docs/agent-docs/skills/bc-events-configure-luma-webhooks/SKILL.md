---
name: bc-events-configure-luma-webhooks
description: Use when staff need to connect a Luma calendar to BreatheCode for real-time guest registration and check-in via webhooks; do NOT use for Eventbrite sync, manual event check-in APIs only, or learner self-service join flows.
requires:
  - bc-events-create-and-edit-event
---

# Skill: Configure Luma Webhooks for Academy Events

## When to Use

Use this skill when you must:

- register a Luma webhook that posts to BreatheCode,
- store Luma calendar credentials on an academy organization,
- link a Luma event (`evt-…`) to a BreatheCode event (`luma_id`),
- verify guest registration/check-in webhooks are flowing.

Do NOT use for Eventbrite (`/v1/events/eventbrite/webhook/...`), creating/editing events without Luma (`bc-events-create-and-edit-event` only), or attendee join/check-in APIs that do not involve Luma webhooks.

## Concepts

- **Luma calendar**: every Luma API key and webhook belongs to one calendar. Webhooks require **Luma Plus**.
- **Organization**: each academy has one `events.Organization` record. Store `luma_calendar_id` and `luma_webhook_secret` (`whsec_…`) on it via the academy organization API.
- **Event linking**: set `luma_id` on the BreatheCode event to the Luma `event.id` (`evt-…`). Webhooks match guests using that field.
- **Webhook types (v1)**: subscribe to `guest.registered` and `guest.updated` only.

## Workflow

1. Confirm prerequisites: Luma Plus on the calendar, calendar **manage** access for target events, and BreatheCode Luma processing enabled (default; set `LUMA_EVENT_PROCESSING=0` only to disable globally).

2. Resolve the academy organization in BreatheCode.
   - Call `GET /v1/events/academy/organization` with `Authorization` and `Academy: <academy_id>`.
   - If missing, create it with `POST /v1/events/academy/organization` (requires `crud_organization`).

3. Create the BreatheCode event (or load an existing one) and note its internal `id`.
   - Use `bc-events-create-and-edit-event` if the event does not exist yet.

4. Create the event on Luma (outside BreatheCode) and copy its Luma event id (`evt-…`).

5. Link the events in BreatheCode.
   - Call `PUT /v1/events/academy/event/<event_id>` with `luma_id` set to the Luma `evt-…` value (and optional `luma_url` such as `https://lu.ma/your-event`).

6. Register the webhook in Luma (Luma API, not BreatheCode).
   - Call `POST https://api.lu.ma/v1/webhooks/create` with header `x-luma-api-key: <calendar_api_key>`.
   - Set `url` to `https://<api-host>/v1/events/luma/webhook/<organization_id>` where `<organization_id>` is the BreatheCode organization primary key from Step 2.
   - Set `event_types` to `["guest.registered", "guest.updated"]`.
   - Save the returned `webhook.secret` (`whsec_…`).

7. Persist Luma credentials on the organization.
   - Call `PUT /v1/events/academy/organization` with `luma_calendar_id` and `luma_webhook_secret` from Steps 2 and 6.

8. Send a test registration on Luma and confirm ingestion.
   - Luma sends `POST /v1/events/luma/webhook/<organization_id>` with signed body.
   - BreatheCode creates/updates `EventCheckin` and runs the same marketing automations as Eventbrite registrations when `approval_status` is `approved`.
   - `guest.updated` with `checked_in_at` marks the check-in `DONE`.

9. If deliveries fail, list webhooks in Luma (`GET /v1/webhooks/list`) and re-create or update the endpoint URL/event types as needed.

## Endpoints

### BreatheCode — organization (store Luma credentials)

**GET** `/v1/events/academy/organization`

Headers: `Authorization`, `Academy: 1`, optional `Accept-Language: en`

Response `200`:
```json
{
  "id": 1,
  "name": "Miami Events Org",
  "eventbrite_id": "",
  "eventbrite_key": null,
  "luma_calendar_id": "cal-abc123",
  "sync_status": "PENDING",
  "sync_desc": null,
  "academy": {
    "id": 1,
    "slug": "miami",
    "name": "4Geeks Miami"
  }
}
```

**PUT** `/v1/events/academy/organization`

Headers: `Authorization`, `Academy: 1`

Request:
```json
{
  "luma_calendar_id": "cal-abc123",
  "luma_webhook_secret": "whsec_xxxxxxxx"
}
```

Response `201` (same shape as GET; secret is writable but not returned on GET serializers for security in some deployments—re-store from Luma if lost).

### BreatheCode — link event

**PUT** `/v1/events/academy/event/42`

Headers: `Authorization`, `Academy: 1`

Request:
```json
{
  "luma_id": "evt-abc123xyz",
  "luma_url": "https://lu.ma/full-stack-workshop"
}
```

Response `200` (subset):
```json
{
  "id": 42,
  "slug": "full-stack-workshop-uuid",
  "title": "Full Stack Workshop",
  "luma_id": "evt-abc123xyz",
  "luma_url": "https://lu.ma/full-stack-workshop",
  "eventbrite_id": null,
  "status": "ACTIVE"
}
```

### BreatheCode — receive webhooks (Luma → BreatheCode)

**POST** `/v1/events/luma/webhook/<organization_id>`

- No auth headers; Luma signs the body.
- Luma processing is on by default; set `LUMA_EVENT_PROCESSING=0` on the API only to disable all orgs.
- Respond with `200` and body `ok` on success.
- Invalid signature → `403 Forbidden`.

Headers from Luma:
- `Webhook-Signature`: `t=<unix>,v1=<hex>`
- `Webhook-Id`: unique delivery id
- `Webhook-Timestamp`: unix seconds

Request body example (`guest.registered`):
```json
{
  "type": "guest.registered",
  "data": {
    "id": "gst-abc123",
    "user_email": "guest@example.com",
    "user_first_name": "Jane",
    "user_last_name": "Doe",
    "approval_status": "approved",
    "event": {
      "id": "evt-abc123xyz",
      "calendar_id": "cal-abc123",
      "name": "Full Stack Workshop"
    }
  }
}
```

Response `200`:
```
ok
```

Signature verification (implement in clients testing against staging):

1. Parse `t` and `v1` from `Webhook-Signature`.
2. Build `signed_payload = "{t}.{raw_json_body}"`.
3. `expected = HMAC_SHA256(luma_webhook_secret, signed_payload).hexdigest()`.
4. Compare `expected` to `v1` with a constant-time compare; reject if timestamp is older than ~5 minutes.

### Luma API — create webhook

**POST** `https://api.lu.ma/v1/webhooks/create`

Headers: `x-luma-api-key: <calendar_api_key>`, `Content-Type: application/json`

Request:
```json
{
  "url": "https://breathecode.herokuapp.com/v1/events/luma/webhook/1",
  "event_types": ["guest.registered", "guest.updated"]
}
```

Response `200`:
```json
{
  "webhook": {
    "id": "wh-abc123",
    "url": "https://breathecode.herokuapp.com/v1/events/luma/webhook/1",
    "event_types": ["guest.registered", "guest.updated"],
    "status": "active",
    "secret": "whsec_xxxxxxxx",
    "created_at": "2024-01-01T12:00:00.000Z"
  }
}
```

### Luma API — list webhooks

**GET** `https://api.lu.ma/v1/webhooks/list`

Headers: `x-luma-api-key: <calendar_api_key>`

Response `200` (non-paginated list in `webhooks` array):
```json
{
  "webhooks": [
    {
      "id": "wh-abc123",
      "url": "https://breathecode.herokuapp.com/v1/events/luma/webhook/1",
      "event_types": ["guest.registered", "guest.updated"],
      "status": "active",
      "created_at": "2024-01-01T12:00:00.000Z"
    }
  ]
}
```

### Luma API — update webhook

**POST** `https://api.lu.ma/v1/webhooks/update`

Headers: `x-luma-api-key: <calendar_api_key>`

Request:
```json
{
  "id": "wh-abc123",
  "event_types": ["guest.registered", "guest.updated"],
  "status": "active"
}
```

### Luma API — delete webhook

**POST** `https://api.lu.ma/v1/webhooks/delete`

Headers: `x-luma-api-key: <calendar_api_key>`

Request:
```json
{
  "id": "wh-abc123"
}
```

## Edge Cases

| Observation | Action |
|---|---|
| `403` on BreatheCode webhook | Verify `luma_webhook_secret` matches Luma, clock skew < 5 minutes, and raw body is used for HMAC (not re-serialized JSON). |
| Webhook `ERROR`: `event doesn't exist` | Set `luma_id` on the BreatheCode event to match `data.event.id` from the payload. |
| Webhook `DONE` with `skipped: approval_status=...` | Guest is not approved yet; wait for `guest.updated` when approved or approve in Luma first. |
| Duplicate deliveries | Safe to retry; check-ins dedupe by email + event and update by `luma_guest_id`. |
| Calendar mismatch | Set `luma_calendar_id` on the organization to match `data.event.calendar_id`. |
| `LUMA_EVENT_PROCESSING` disabled | API returns plain text; processing is on by default—remove `LUMA_EVENT_PROCESSING=0` or set `LUMA_EVENT_PROCESSING=1`. |
| No ActiveCampaign automation | Webhook errors like Eventbrite; configure `event_attendancy_automation` on `ActiveCampaignAcademy` first. |

## Checklist

1. [ ] Organization exists for the academy and `luma_calendar_id` + `luma_webhook_secret` are saved.
2. [ ] BreatheCode event has `luma_id` equal to the Luma `evt-…` id.
3. [ ] Luma webhook URL points to `/v1/events/luma/webhook/<organization_id>` with types `guest.registered` and `guest.updated`.
4. [ ] API deployment does not set `LUMA_EVENT_PROCESSING=0` (unless intentionally disabled).
5. [ ] Test guest receives `EventCheckin` with `utm_source=luma` after approved registration.
6. [ ] Check-in on Luma fires `guest.updated` and sets check-in `status` to `DONE` when `checked_in_at` is present.
