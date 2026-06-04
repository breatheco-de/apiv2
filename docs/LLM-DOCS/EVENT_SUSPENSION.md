# Event Suspension API Documentation

This document provides comprehensive information about suspending events in the BreatheCode platform - how to suspend events, what happens when an event is suspended, and how the system handles suspended events.

## Overview

**Event Suspension** allows academy staff to temporarily suspend an event, preventing users from joining and automatically notifying all registered attendees. When an event is suspended, the system performs several actions to ensure attendees are informed and access is restricted.

### Key Concepts

- **Suspended Status**: Events can have a status of `SUSPENDED`, which prevents users from joining
- **Automatic Notifications**: All registered attendees receive email notifications when an event is suspended
- **Live Stream URL Removal**: The `live_stream_url` is set to `null` when an event is suspended
- **Join Restrictions**: Users attempting to join a suspended event will see a suspension message instead of being redirected to the meeting

### Event Status Values

Events can have the following status values:
- `ACTIVE` - Event is active and available
- `DRAFT` - Event is in draft state (not published)
- `DELETED` - Event has been deleted
- `SUSPENDED` - Event has been suspended (cannot be joined)
- `FINISHED` - Event has finished

---

## Suspend Event Endpoint

### Endpoint

**`PUT /v1/events/academy/event/{event_id}/suspend`**

### Purpose

Suspend an event that has not yet started, which:
1. Sets the event status to `SUSPENDED`
2. Removes the live stream URL (sets to `null`)
3. Sends email notifications to all registered attendees asynchronously
4. Prevents users from joining the event (shows suspension message instead)

**Important:** Only events that have not yet started and are scheduled for the future can be suspended. Events that have already started (where `starting_at` is in the past) cannot be suspended.

### Authentication

**Required:** `crud_event` capability in the academy

### Headers

```http
Authorization: Token {your-token}
Academy: {academy_id}
Content-Type: application/json
```

### URL Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `event_id` | integer | ✅ Yes | The ID of the event to suspend |

### Request Body

No request body required. The endpoint uses a PUT method but does not accept any body parameters.

### Response (200 OK)

Returns the updated event object with the status set to `SUSPENDED` and `live_stream_url` set to `null`.

```json
{
  "id": 123,
  "slug": "python-workshop-2025",
  "title": "Introduction to Python Workshop",
  "status": "SUSPENDED",
  "live_stream_url": null,
  "starting_at": "2025-11-15T18:00:00Z",
  "ending_at": "2025-11-15T20:00:00Z",
  "academy": {
    "id": 1,
    "slug": "downtown-miami",
    "name": "4Geeks Downtown Miami"
  },
  "event_type": {
    "id": 5,
    "slug": "workshop",
    "name": "Workshop"
  },
  "created_at": "2025-10-01T10:00:00Z",
  "updated_at": "2025-11-10T14:30:00Z"
}
```

### Error Responses

#### 400 Bad Request - Event Already Started

Event has already started or is in the past. Only future events that haven't started can be suspended.

```json
{
  "detail": "Only events that have not yet started and are scheduled for the future can be suspended",
  "status_code": 400,
  "slug": "event-already-started"
}
```

#### 404 Not Found

Event does not exist or does not belong to the specified academy.

```json
{
  "detail": "Event not found for this academy {academy_id}",
  "status_code": 404,
  "slug": "event-not-found"
}
```

#### 403 Forbidden

User does not have the required `crud_event` capability.

```json
{
  "detail": "You don't have permission to perform this action",
  "status_code": 403
}
```

### Example Request

```bash
curl -X PUT \
  'https://breathecode.herokuapp.com/v1/events/academy/event/123/suspend' \
  -H 'Authorization: Token your-auth-token' \
  -H 'Academy: 1' \
  -H 'Content-Type: application/json'
```

### Example Response

```json
{
  "id": 123,
  "slug": "python-workshop-2025",
  "title": "Introduction to Python Workshop",
  "status": "SUSPENDED",
  "live_stream_url": null,
  "description": "Learn Python fundamentals...",
  "starting_at": "2025-11-15T18:00:00Z",
  "ending_at": "2025-11-15T20:00:00Z",
  "capacity": 50,
  "banner": "https://example.com/banner.jpg",
  "online_event": true,
  "free_for_all": false,
  "free_for_bootcamps": true,
  "academy": {
    "id": 1,
    "slug": "downtown-miami",
    "name": "4Geeks Downtown Miami"
  },
  "event_type": {
    "id": 5,
    "slug": "workshop",
    "name": "Workshop"
  },
  "created_at": "2025-10-01T10:00:00Z",
  "updated_at": "2025-11-10T14:30:00Z"
}
```

---

## What Happens When an Event is Suspended

### Pre-Suspension Validation

Before suspending an event, the system validates that:
- The event's `starting_at` datetime is in the future (has not started yet)
- If the event has already started, the suspension will be rejected with a 400 error

### 1. Status Update

The event's `status` field is immediately changed to `SUSPENDED`.

### 2. Live Stream URL Removal

The event's `live_stream_url` is set to `null`, preventing users from accessing the meeting room.

### 3. Email Notifications

An asynchronous Celery task (`send_event_suspended_notification`) is queued to send email notifications to all registered attendees. The task:

- Fetches all `EventCheckin` records for the event that have valid email addresses
- Sends personalized email notifications using the "message" template
- Supports bilingual content (English and Spanish) based on the event's language setting
- Includes the event title and a suspension message in the email

#### Email Content

**English:**
- **Subject**: `Event Suspended: {event_title}`
- **Message**: 
  ```
  We regret to inform you that the event '{event_title}' has been suspended for reasons that are out of our hands.

  If you have any questions or concerns, please contact support for assistance.

  We apologize for any inconvenience this may cause.
  ```

**Spanish:**
- **Subject**: `Evento Suspendido: {event_title}`
- **Message**:
  ```
  Lamentamos informarle que el evento '{event_title}' ha sido suspendido por razones fuera de nuestro control.

  Si tiene alguna pregunta o inquietud, por favor contacte a soporte para asistencia.

  Nos disculpamos por cualquier inconveniente que esto pueda causar.
  ```

### 4. Event Status Updated Signal

The `event_status_updated` signal is automatically triggered when the event status changes, which can be used by other parts of the system to handle the suspension (e.g., webhooks, notifications).

---

## User-Facing Behavior

### Join Event Attempts

When users attempt to join a suspended event through either endpoint below, they will see a suspension message instead of being redirected to the meeting:

1. **Public Join**: `GET /v1/events/me/event/{event_id}/join`
2. **Academy Join**: `GET /v1/events/academy/event/{event_id}/join`

### Suspension Message

Users will see the following message (translated based on their language preference):

**English:**
```
This event was suspended for reasons that are out of our hands, contact support if you have any further questions
```

**Spanish:**
```
Este evento fue suspendido por razones fuera de nuestro control, contacte a soporte si tiene alguna pregunta adicional
```

The message is displayed using the standard message template with academy branding.

---

## Related Endpoints

### Update Event (Cannot Suspend)

**Endpoint:** `PUT /v1/events/academy/event/{event_id}`

This general update endpoint **cannot be used to suspend events**. If you attempt to set `status: "SUSPENDED"` via this endpoint, you will receive a 400 error:

```json
{
  "detail": "Cannot set event status to SUSPENDED using this endpoint. Please use PUT /v1/events/academy/event/{event_id}/suspend instead.",
  "status_code": 400,
  "slug": "use-suspend-endpoint"
}
```

**Important:** 
- To **suspend** an event, you **must** use the dedicated suspend endpoint: `PUT /v1/events/academy/event/{event_id}/suspend`
- To **unsuspend** an event (change from `SUSPENDED` to `ACTIVE`), you can use this general PUT endpoint with `status: "ACTIVE"` and restore the `live_stream_url` if needed
- You can set other status values (`ACTIVE`, `DRAFT`, `FINISHED`) using this endpoint without restrictions

### Check Event Status

To check if an event is suspended, use the standard event retrieval endpoints:

**Get Single Event:**
```
GET /v1/events/academy/event/{event_id}
```

The response will include the `status` field which will be `"SUSPENDED"` for suspended events.

### List Events (Filter by Status)

**List Academy Events:**
```
GET /v1/events/academy/event?status=SUSPENDED
```

Query parameters:
- `status=SUSPENDED` - Filter to show only suspended events
- `status=ACTIVE` - Filter to show only active events

---

## Workflow Examples

### Example 1: Suspend a Future Event

```bash
# 1. Suspend the event (only works for events that haven't started)
curl -X PUT \
  'https://breathecode.herokuapp.com/v1/events/academy/event/123/suspend' \
  -H 'Authorization: Token your-token' \
  -H 'Academy: 1'

# 2. Verify the suspension
curl -X GET \
  'https://breathecode.herokuapp.com/v1/events/academy/event/123' \
  -H 'Authorization: Token your-token' \
  -H 'Academy: 1'

# Response will show:
# - status: "SUSPENDED"
# - live_stream_url: null
```

### Example 1b: Attempt to Suspend an Event That Has Started (Will Fail)

```bash
# This will fail with 400 error if event.starting_at <= current_time
curl -X PUT \
  'https://breathecode.herokuapp.com/v1/events/academy/event/123/suspend' \
  -H 'Authorization: Token your-token' \
  -H 'Academy: 1'

# Response (400 Bad Request):
# {
#   "detail": "Only events that have not yet started and are scheduled for the future can be suspended",
#   "status_code": 400,
#   "slug": "event-already-started"
# }
```

### Example 2: Check for Suspended Events

```bash
# List all suspended events
curl -X GET \
  'https://breathecode.herokuapp.com/v1/events/academy/event?status=SUSPENDED' \
  -H 'Authorization: Token your-token' \
  -H 'Academy: 1'
```

### Example 3: Attempt to Suspend via General PUT Endpoint (Will Fail)

```bash
# This will fail with 400 error
curl -X PUT \
  'https://breathecode.herokuapp.com/v1/events/academy/event/123' \
  -H 'Authorization: Token your-token' \
  -H 'Academy: 1' \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "SUSPENDED"
  }'

# Response (400 Bad Request):
# {
#   "detail": "Cannot set event status to SUSPENDED using this endpoint. Please use PUT /v1/events/academy/event/{event_id}/suspend instead.",
#   "status_code": 400,
#   "slug": "use-suspend-endpoint"
# }
```

### Example 4: Unsuspend an Event (Change Status Back to ACTIVE)

```bash
# Use the general PUT endpoint to change status from SUSPENDED to ACTIVE
curl -X PUT \
  'https://breathecode.herokuapp.com/v1/events/academy/event/123' \
  -H 'Authorization: Token your-token' \
  -H 'Academy: 1' \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "ACTIVE",
    "live_stream_url": "https://meet.example.com/room123"
  }'
```

---

## Implementation Details

### Asynchronous Email Processing

The email notification task runs asynchronously using Celery with `TaskPriority.NOTIFICATION` priority. This ensures:

- The API response is not delayed by email sending
- Multiple emails can be sent in parallel
- Email failures don't block the suspension action

### Error Handling

If email sending fails for individual attendees, the errors are logged but do not prevent the suspension from completing. The suspension is successful even if some email notifications fail.

### Database Changes

When an event is suspended:
- `event.status` → `"SUSPENDED"`
- `event.live_stream_url` → `null`
- `event.updated_at` → Current timestamp

---

## Security Considerations

1. **Permission Check**: Only users with `crud_event` capability can suspend events
2. **Academy Validation**: Events must belong to the academy specified in the `Academy` header
3. **Idempotency**: Suspending an already suspended event will still update the timestamp but won't send duplicate emails (email task checks if event is suspended)

---

## Best Practices

1. **Timing**: Only suspend events before they start. Once an event has begun (`starting_at` is in the past), it cannot be suspended
2. **Notify Users Beforehand**: If possible, notify users before suspending an event
3. **Provide Context**: Include a reason in your internal records for why the event was suspended
4. **Monitor Email Deliverability**: Check email delivery logs to ensure attendees are notified
5. **Resume Events**: To resume an event, use the standard event update endpoint to change status back to `ACTIVE` and restore the `live_stream_url` if needed
6. **Check Event Timing**: Before attempting to suspend, verify the event's `starting_at` date to ensure it's in the future

---

## Troubleshooting

### Cannot Suspend Event - "event-already-started" Error

**Error:** `400 Bad Request - Only events that have not yet started and are scheduled for the future can be suspended`

**Cause:** The event's `starting_at` datetime is in the past (event has already started or started in the past).

**Solution:**
- Check the event's `starting_at` field to confirm it's in the past
- Only events scheduled for the future can be suspended
- If the event has started, you cannot suspend it through this endpoint

### Emails Not Being Sent

- Check that `EMAIL_NOTIFICATIONS_ENABLED` environment variable is set to `"TRUE"`
- Verify that attendees have valid email addresses in their `EventCheckin` records
- Check Celery worker logs for email sending errors

### Event Still Accessible After Suspension

- Verify the event status was successfully updated to `SUSPENDED`
- Check that `live_stream_url` is set to `null`
- Ensure the user is accessing through the correct endpoint (join endpoints check for suspension status)

### Permission Errors

- Verify the user has `crud_event` capability for the academy
- Check that the `Academy` header matches the event's academy
- Ensure the authentication token is valid and not expired

