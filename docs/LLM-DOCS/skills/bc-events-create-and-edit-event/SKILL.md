---
name: bc-events-create-and-edit-event
description: Use when staff need to create or edit academy events end-to-end (event type, tags, optional workshop asset, host, and meeting setup); do NOT use for attendee checkin/join-only tasks without event authoring.
requires: []
---

# Skill: Create and Edit Academy Events

## When to Use

Use this skill when the user needs to create or edit an event through the academy API workflow, including selecting/creating event type, selecting tags, linking workshop assets, assigning hosts, and setting meeting provider behavior. Do NOT use this skill for attendee-only tasks (join/checkin) or for public event browsing without editing.

## Concepts

- `is_public` controls visibility/discoverability of the event.
- `free_for_all` affects the `event_join` consumption price path. When `true`, join is treated as price `0` (no consumable spend path), but non-saas financial-status checks can still block access.
- `free_for_bootcamps` applies when `free_for_all=false`. Eligible bootcamp users can still join through the price `0` path without spending an `event_join` consumable.
- When neither host nor free path applies, join requires an `event_join` consumable compatible with the event type.
- `tags` are validated against marketing tags of type `DISCOVERY` for the academy.
- `asset_slug` is optional workshop linkage. Only use assets with `asset_type` `PROJECT` or `EXERCISE`.
- For online events, room automation is controlled by `create_meet` and optional `meeting_provider` (`daily` or `livekit`). A custom provider is handled by passing `live_stream_url` directly.

## Workflow

1. Set request context first. Send `Authorization` and `Academy: <academy_id>` headers on all `/academy/` endpoints. Send `Accept-Language` (for example `en` or `es`) if translated errors are needed.

2. Resolve event type before creating or publishing an event.
   - Call `GET /v1/events/academy/eventype` and pick an existing `id`.
   - If no option is suitable, create one with `POST /v1/events/academy/eventype`.
   - If an academy event type needs refinement, update it with `PUT /v1/events/academy/eventype/<event_type_slug>`.

3. Resolve allowed event tags.
   - Call `GET /v1/marketing/academy/tag?type=DISCOVERY`.
   - Use returned tag `slug` values to build the event `tags` CSV string.
   - If you send unknown slugs or wrong tag types, event create/update fails with `tag-not-exist`.

4. Resolve optional workshop asset.
   - Call `GET /v1/registry/academy/asset` with `like=<title|slug|url>` to search candidates.
   - Query `asset_type=PROJECT` and `asset_type=EXERCISE` separately (filter is exact).
   - Optionally validate a specific slug with `slug=<asset_slug>&asset_type=<PROJECT|EXERCISE>`.
   - Only set `asset_slug` in event payload if the selected asset type is `PROJECT` or `EXERCISE`.

5. Resolve optional venue for in-person events.
   - Call `GET /v1/events/academy/venues` and pick `venue` id when `online_event=false`.

6. Create the event.
   - Call `POST /v1/events/academy/event`.
   - Include required fields: `banner`, `capacity`, `starting_at`, `ending_at`.
   - Include `event_type`, `tags`, and (for online non-draft) `live_stream_url` or `create_meet=true`.
   - For room automation, set `create_meet=true` and optionally `meeting_provider` (`daily`/`livekit`).
   - If `meeting_provider` is omitted, backend uses academy default provider, then env default (`daily`).

7. Add or update host after creation.
   - Assign host and send invite via `POST /v1/events/academy/event/<event_id>/host`.
   - If profile details need adjustment, call `PUT /v1/events/academy/event/<event_id>/host/<user_id>`.

8. Edit event details.
   - Single event: `PUT /v1/events/academy/event/<event_id>`.
   - Bulk: `PUT /v1/events/academy/event` with list payload; each item must contain `id`.
   - Do not try to update `slug` on PUT (`try-update-slug`).
   - If host ownership changes, re-run Step 7.

9. Use specialized lifecycle operations when needed.
   - Suspend event with `PUT /v1/events/academy/event/<event_id>/suspend` (do not set `SUSPENDED` in normal PUT).
   - Delete only draft events with `DELETE /v1/events/academy/event/<event_id>`.

## Endpoints

| Action | Method | Path | Headers | Body | Response |
|---|---|---|---|---|---|
| List event types | GET | `/v1/events/academy/eventype` | `Authorization`, `Academy`, optional `Accept-Language` | Optional query filters | Non-paginated list of event types |
| Create event type | POST | `/v1/events/academy/eventype` | `Authorization`, `Academy`, optional `Accept-Language` | Event type payload | `201` event type object |
| Update event type | PUT | `/v1/events/academy/eventype/<event_type_slug>` | `Authorization`, `Academy`, optional `Accept-Language` | Event type update payload | `200` event type object |
| List selectable tags | GET | `/v1/marketing/academy/tag?type=DISCOVERY` | `Authorization`, `Academy`, optional `Accept-Language` | Optional pagination/query filters | Paginated tags (`results`) |
| Search workshop assets | GET | `/v1/registry/academy/asset` | `Authorization`, `Academy`, optional `Accept-Language` | Query examples below | Paginated assets (`results`) |
| List venues | GET | `/v1/events/academy/venues` | `Authorization`, `Academy`, optional `Accept-Language` | — | Non-paginated venue list |
| Create event | POST | `/v1/events/academy/event` | `Authorization`, `Academy`, optional `Accept-Language` | Event payload | `201` event object |
| Update one event | PUT | `/v1/events/academy/event/<event_id>` | `Authorization`, `Academy`, optional `Accept-Language` | Event update payload | `200` event object |
| Bulk update events | PUT | `/v1/events/academy/event` | `Authorization`, `Academy`, optional `Accept-Language` | List of event updates | `200` list of event objects |
| Assign host + invite | POST | `/v1/events/academy/event/<event_id>/host` | `Authorization`, `Academy`, optional `Accept-Language` | Host payload | `201` with `user`, `invite`, `event_id` |
| Update host profile | PUT | `/v1/events/academy/event/<event_id>/host/<user_id>` | `Authorization`, `Academy`, optional `Accept-Language` | Partial profile payload | `200` updated profile |
| Suspend event | PUT | `/v1/events/academy/event/<event_id>/suspend` | `Authorization`, `Academy`, optional `Accept-Language` | Optional suspension reason | `200` event object |
| Delete draft event | DELETE | `/v1/events/academy/event/<event_id>` | `Authorization`, `Academy`, optional `Accept-Language` | — | `204` |

**List event types response example (GET `/v1/events/academy/eventype`)**
```json
[
  {
    "id": 12,
    "slug": "coding-workshop",
    "name": "Coding Workshop",
    "technologies": "python,flask",
    "description": "Live coding session",
    "icon_url": "https://cdn.example.com/icons/workshop.png",
    "lang": "en",
    "academy": {
      "id": 1,
      "slug": "miami",
      "name": "4Geeks Miami",
      "city": {"name": "Miami"}
    }
  }
]
```

**Create event type request (POST `/v1/events/academy/eventype`)**
```json
{
  "name": "AI Workshop",
  "slug": "ai-workshop",
  "description": "Hands-on AI workshop",
  "icon_url": "https://cdn.example.com/icons/ai-workshop.png",
  "lang": "en",
  "allow_shared_creation": false,
  "technologies": "python,llm"
}
```

**Update event type request (PUT `/v1/events/academy/eventype/ai-workshop`)**
```json
{
  "name": "AI Workshop Updated",
  "description": "Updated workshop description",
  "icon_url": "https://cdn.example.com/icons/ai-workshop-v2.png",
  "lang": "en",
  "allow_shared_creation": false
}
```

**Tag lookup response example (GET `/v1/marketing/academy/tag?type=DISCOVERY`)**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {"id": 41, "slug": "intro-webinar", "tag_type": "DISCOVERY", "subscribers": 120},
    {"id": 42, "slug": "python-beginner", "tag_type": "DISCOVERY", "subscribers": 89}
  ]
}
```

**Asset search request examples (GET `/v1/registry/academy/asset`)**
- `/v1/registry/academy/asset?like=javascript&asset_type=PROJECT`
- `/v1/registry/academy/asset?like=https://github.com/acme/repo&asset_type=EXERCISE`
- `/v1/registry/academy/asset?slug=react-todo&asset_type=PROJECT`

**Asset search response example**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 55,
      "slug": "react-todo",
      "title": "React Todo Project",
      "asset_type": "PROJECT",
      "url": "https://github.com/acme/react-todo",
      "readme_url": "https://github.com/acme/react-todo/blob/main/README.md"
    }
  ]
}
```

**Venue list response example (GET `/v1/events/academy/venues`)**
```json
[
  {
    "id": 7,
    "title": "Main Campus Auditorium",
    "street_address": "123 NE 1st St",
    "city": "Miami",
    "zip_code": "33132",
    "state": "FL",
    "updated_at": "2026-03-31T14:00:00Z"
  }
]
```

**Create event request (POST `/v1/events/academy/event`)**
```json
{
  "title": "Intro to Python Live Workshop",
  "banner": "https://cdn.example.com/banners/python-workshop.png",
  "capacity": 80,
  "starting_at": "2026-04-21T22:00:00Z",
  "ending_at": "2026-04-22T00:00:00Z",
  "status": "DRAFT",
  "description": "Beginner-friendly workshop",
  "excerpt": "Start coding with Python",
  "url": "https://4geeks.com/workshops/intro-python",
  "tags": "intro-webinar,python-beginner",
  "lang": "en",
  "event_type": 12,
  "online_event": true,
  "live_stream_url": "",
  "create_meet": true,
  "meeting_provider": "daily",
  "is_public": true,
  "free_for_all": true,
  "free_for_bootcamps": true,
  "asset_slug": "react-todo"
}
```

**Create event response (201)**
```json
{
  "id": 101,
  "academy": 1,
  "title": "Intro to Python Live Workshop",
  "slug": "intro-to-python-live-workshop",
  "banner": "https://cdn.example.com/banners/python-workshop.png",
  "capacity": 80,
  "starting_at": "2026-04-21T22:00:00Z",
  "ending_at": "2026-04-22T00:00:00Z",
  "status": "DRAFT",
  "tags": "intro-webinar,python-beginner",
  "lang": "en",
  "event_type": 12,
  "online_event": true,
  "live_stream_url": "https://your-room.daily.co/event-101",
  "is_public": true,
  "free_for_all": true,
  "free_for_bootcamps": true,
  "asset_slug": "react-todo",
  "eventbrite_sync_status": "PENDING",
  "created_at": "2026-03-31T14:05:00Z",
  "updated_at": "2026-03-31T14:05:00Z"
}
```

**Update event request (PUT `/v1/events/academy/event/101`)**
```json
{
  "id": 101,
  "title": "Intro to Python Workshop (Updated)",
  "banner": "https://cdn.example.com/banners/python-workshop-v2.png",
  "capacity": 120,
  "starting_at": "2026-04-21T22:00:00Z",
  "ending_at": "2026-04-22T00:30:00Z",
  "tags": "intro-webinar,python-beginner",
  "status": "ACTIVE",
  "event_type": 12,
  "online_event": true,
  "free_for_all": false,
  "free_for_bootcamps": true
}
```

`slug` is read-only on PUT. Do not include it in update payloads.

**Bulk update request (PUT `/v1/events/academy/event`)**
```json
[
  {
    "id": 101,
    "title": "Python Workshop A",
    "starting_at": "2026-04-21T22:00:00Z",
    "ending_at": "2026-04-21T23:30:00Z"
  },
  {
    "id": 102,
    "status": "DRAFT"
  }
]
```

**Assign host request (POST `/v1/events/academy/event/101/host`)**
```json
{
  "host": "Alex Johnson",
  "host_email": "alex.johnson@example.com",
  "avatar_url": "https://cdn.example.com/hosts/alex.png",
  "bio": "Senior instructor and open-source contributor",
  "github_username": "alexj",
  "linkedin_url": "https://www.linkedin.com/in/alexj/"
}
```

**Assign host response (201)**
```json
{
  "user": {
    "id": 9001,
    "first_name": "Alex",
    "last_name": "Johnson",
    "email": "alex.johnson@example.com",
    "is_active": false
  },
  "invite": {
    "id": 300,
    "status": "PENDING",
    "event_slug": "intro-to-python-live-workshop",
    "email": "alex.johnson@example.com"
  },
  "event_id": 101,
  "message": "Host user created and invitation sent"
}
```

**Update host profile request (PUT `/v1/events/academy/event/101/host/9001`)**
```json
{
  "bio": "Lead instructor for Python track",
  "portfolio_url": "https://alex.dev",
  "twitter_username": "alexcodes"
}
```

**Suspend event request (PUT `/v1/events/academy/event/101/suspend`)**
```json
{
  "suspension_reason": "Speaker unavailable"
}
```

## Edge Cases

- Missing required event create fields (`banner`, `capacity`, `starting_at`, `ending_at`) returns field-level `400` validation errors.
- Slug collision on create returns `slug-taken`.
- Attempting to update `slug` on PUT returns `try-update-slug`.
- Non-draft event without tags returns `empty-tags`.
- Non-draft event without `event_type` returns `no-event-type`.
- Event language mismatching selected event type language returns `event-type-lang-mismatch`.
- Online non-draft event without `live_stream_url` and without `create_meet=true` returns `live-stream-url-empty`.
- Setting `status=SUSPENDED` through normal event PUT returns `use-suspend-endpoint`.
- Deleting non-draft event returns `non-draft-event`.
- `free_for_all=true` does not bypass all checks: users can still be blocked by financial-status validation (`cohort-user-status-later`) in join flow.
- `free_for_all=false` does not always mean consumable is required: host users and eligible bootcamp users may still join via price `0` path.
- Tag slugs not available for academy `DISCOVERY` tags return `tag-not-exist`.
- Invalid tags CSV formatting (spaces, duplicate commas, leading/trailing commas) fails validation.
- Host assignment without `host` returns `host-name-required`.
- Host assignment without `host_email` returns `host-email-required`.
- Host update for user not assigned as event host returns `user-not-event-host`.
- Host update for user outside academy membership or invitation state returns `user-not-in-academy` or `user-not-accepted-invitation`.
- Event type update for missing slug returns `event-type-not-found`.
- If selected workshop asset is not `PROJECT` or `EXERCISE`, do not assign it as `asset_slug`.

## Checklist

1. Confirm headers are set: `Authorization`, `Academy`, and optional `Accept-Language`.
2. Resolve event type (`GET`, then optional `POST`/`PUT`) and save valid `event_type` id.
3. Resolve tags via `GET /v1/marketing/academy/tag?type=DISCOVERY` and build valid `tags` CSV.
4. If workshop asset is needed, search and validate via `GET /v1/registry/academy/asset` and only use `PROJECT`/`EXERCISE`.
5. If in-person event, pick `venue` from `GET /v1/events/academy/venues`.
6. Create event with `POST /v1/events/academy/event` including required fields and access flags (`is_public`, `free_for_all`, `free_for_bootcamps`).
7. For online meeting automation, use `create_meet=true` and optional `meeting_provider` (`daily`/`livekit`), or provide `live_stream_url` for custom provider.
8. Assign/update host with host endpoints after create and after any host ownership change.
9. Use normal PUT for event edits, suspend endpoint for suspension, and delete only when event is draft.
