---
name: bc-marketing-manage-form-entries
description: Use when staff search, filter, update, delete, or re-process existing academy FormEntry leads; do NOT use for creating leads, debugging storage_status failures, or public capture flows.
requires:
  - breathecode-staff-api-index
---

# Skill: Manage FormEntry Leads (Staff)

## When to Use

- Use for searching, reading, updating, deleting, or re-processing **existing** academy `FormEntry` records.
- Use for listing won deals (`GET /v1/marketing/academy/lead/won`).
- Do NOT use for creating new leads — load [`bc-marketing-create-form-entry`](../bc-marketing-create-form-entry/SKILL.md).
- Do NOT use for diagnosing `storage_status` / CRM failures — load [`bc-marketing-debug-form-entry`](../bc-marketing-debug-form-entry/SKILL.md).
- Do NOT use for attribution funnel analytics — load [`bc-monitoring-read-report-acquisition`](../bc-monitoring-read-report-acquisition/SKILL.md).

## Concepts

- Field semantics (`location`, `tags`, `automations`, `custom_fields`, CRM requirements) live in [`bc-marketing-create-form-entry`](../bc-marketing-create-form-entry/SKILL.md).
- `storage_status` diagnosis and retry guidance live in [`bc-marketing-debug-form-entry`](../bc-marketing-debug-form-entry/SKILL.md).
- When ActiveCampaign double sync is enabled, `deal_status` and `ac_deal_*` fields on GET may reflect salesperson CRM activity via reverse webhooks — not only staff `PUT` updates.
- Staff `PUT` triggers `form_entry.changed` platform webhook but does **not** auto re-push to CRM. Use `process` to retry CRM sync.

## Workflow

1. Set headers on all `/academy/` routes: `Authorization: Token <token>`, `Academy: <academy_id>`, optional `Accept-Language` (`en`, `es`) for translated errors.

2. Search or list leads with filters (`GET /v1/marketing/academy/lead`). Use `start` and `end` for date windows on `created_at`. Save lead `id` values from results.

3. Get one lead by id (`GET /v1/marketing/academy/lead/<id>`). Use `FormEntryBigSerializer` response for full diagnostics (`storage_status`, `storage_status_text`, `ac_contact_id`, `ac_deal_*`, `deal_status`).

4. Update lead fields (`PUT /v1/marketing/academy/lead/<id>` or `PUT /v1/marketing/academy/lead?id=<id>`). Does not auto-call CRM. If `storage_status=ERROR`, fix fields then go to Step 5.

5. Re-process CRM sync (`PUT /v1/marketing/academy/lead/process?id=<id>`). Use after fixing data or for staff-created leads that were never processed. See debug skill for when **not** to call `process` (`DUPLICATED`).

6. Delete leads in bulk (`DELETE /v1/marketing/academy/lead?id=<id1>,<id2>`). Requires `id` query param.

7. List won leads (`GET /v1/marketing/academy/lead/won`) with `read_won_lead` capability. Supports same date and filter params as the main list.

## Endpoints

All endpoints below require `Authorization`, `Academy`, and optional `Accept-Language`. Paths contain `/academy/`.

| Action | Method | Path | Capability | Notes |
|---|---|---|---|---|
| List / filter leads | GET | `/v1/marketing/academy/lead` | `read_lead` | Paginated (`limit`, `offset`). Default sort `-created_at`. |
| Get one lead | GET | `/v1/marketing/academy/lead/<id>` | `read_lead` | Returns full lead detail. |
| Update one lead | PUT | `/v1/marketing/academy/lead/<id>` | `crud_lead` | Triggers `form_entry.changed`. |
| Update multiple leads | PUT | `/v1/marketing/academy/lead?id=<ids>` | `crud_lead` | Comma-separated ids in query. |
| Delete leads | DELETE | `/v1/marketing/academy/lead?id=<ids>` | `crud_lead` | Bulk only via `?id=` query. |
| Re-process CRM | PUT | `/v1/marketing/academy/lead/process?id=<ids>` | `crud_lead` | Queues `persist_single_lead` per lead. |
| List won leads | GET | `/v1/marketing/academy/lead/won` | `read_won_lead` | Filters `deal_status=WON`. Paginated. |

### List filters

| Query param | Filters on | Notes |
|---|---|---|
| `start` | `created_at >=` | `YYYY-MM-DD` |
| `end` | `created_at <=` | `YYYY-MM-DD` at **midnight start-of-day** — use the **next calendar day** to include the full last day |
| `storage_status` | `storage_status` | e.g. `ERROR`, `PENDING`, `PERSISTED`, `DUPLICATED` |
| `deal_status` | `deal_status` | Uppercased in lookup (`WON`, `LOST`) |
| `course` | `course` | Comma-separated |
| `location` / `location_alias` | `location` | Comma-separated |
| `deal_location` | `ac_deal_location` | Comma-separated |
| `deal_course` | `ac_deal_course` | Comma-separated |
| `ac_deal_id` | `ac_deal_id` | Exact match |
| `utm_medium` | `utm_medium` | `icontains` |
| `utm_url` | `utm_url` | `icontains` |
| `utm_campaign` | `utm_campaign` | `icontains` |
| `utm_source` | `utm_source` | `icontains` |
| `utm_term` | `utm_term` | `icontains` |
| `tags` | tag slugs | Comma-separated |
| `like` | name search | Full-name fuzzy match |
| `only_first` | — | `true` returns first match only (hook-oriented shape) |
| `limit`, `offset` | pagination | Default limit 20 |

#### Example request — list leads by date and status

```http
GET /v1/marketing/academy/lead?start=2026-04-01&end=2026-04-08&storage_status=ERROR&limit=20&offset=0
Authorization: Token <token>
Academy: 4
```

#### Example response — paginated list (subset)

```json
{
  "count": 3,
  "first": null,
  "next": null,
  "previous": null,
  "last": null,
  "results": [
    {
      "id": 219384,
      "first_name": "Lucia",
      "last_name": "Mendez",
      "email": "lucia@example.com",
      "phone": "+34600000000",
      "course": "full-stack",
      "location": "barcelona-spain",
      "storage_status": "ERROR",
      "storage_status_text": "You need to specify tags for this entry",
      "deal_status": null,
      "created_at": "2026-04-03T15:29:11.532Z"
    }
  ]
}
```

#### Example request — get one lead

```http
GET /v1/marketing/academy/lead/219384
Authorization: Token <token>
Academy: 4
```

#### Example response — single lead (subset)

```json
{
  "id": 219384,
  "first_name": "Lucia",
  "last_name": "Mendez",
  "email": "lucia@example.com",
  "phone": "+34600000000",
  "course": "full-stack",
  "location": "barcelona-spain",
  "tags": "website-lead",
  "storage_status": "ERROR",
  "storage_status_text": "You need to specify tags for this entry",
  "ac_contact_id": null,
  "ac_deal_id": null,
  "deal_status": null,
  "won_at": null,
  "referral_key": "partner-acme-01",
  "utm_source": "facebook",
  "utm_campaign": "barcelona-bootcamp-q2",
  "custom_fields": {},
  "created_at": "2026-04-03T15:29:11.532Z",
  "updated_at": "2026-04-03T15:29:12.100Z"
}
```

#### Example request — update lead (fix tags before retry)

```http
PUT /v1/marketing/academy/lead/219384
Authorization: Token <token>
Academy: 4
Content-Type: application/json
```

```json
{
  "tags": "website-lead",
  "course": "full-stack"
}
```

#### Example response — update

Same shape as get-one response with updated fields.

#### Example request — re-process CRM

```http
PUT /v1/marketing/academy/lead/process?id=219384
Authorization: Token <token>
Academy: 4
```

#### Example response — process queued

```json
{
  "details": "1 leads added to the processing queue"
}
```

Poll `GET /v1/marketing/academy/lead/219384` until `storage_status` is `PERSISTED`, `DUPLICATED`, or stable `ERROR`.

#### Example request — delete leads

```http
DELETE /v1/marketing/academy/lead?id=219384,219385
Authorization: Token <token>
Academy: 4
```

Returns `204 No Content` on success.

#### Example request — list won leads

```http
GET /v1/marketing/academy/lead/won?start=2026-04-01&end=2026-04-30
Authorization: Token <token>
Academy: 4
```

Paginated list of leads with `deal_status=WON`.

## Edge Cases

- **Invalid filter values:** returns empty `results` — do not assume a bug; verify filter spelling and academy scope.
- **GET one wrong id:** returns `404` with `lead-not-found`.
- **PUT wrong id in bulk:** returns `400` with `lead-not-found` if no matches.
- **Delete without `?id=`:** returns `400` — bulk delete requires query param ids.
- **`storage_status=ERROR`:** load debug skill; read `storage_status_text`, fix fields, then `process`.
- **`storage_status=DUPLICATED`:** do not call `process` — intentional dedup within ~30 minutes.
- **Date filter `end` caveat:** `end=2026-04-07` excludes leads created after midnight on April 7; use `end=2026-04-08` to include all of April 7.

## Checklist

1. [ ] Sent `Authorization` and `Academy` headers on every request.
2. [ ] Used correct date params (`start`/`end`, not `started_at`/`ended_at`).
3. [ ] Applied `end` date midnight caveat when filtering by last day.
4. [ ] Retrieved lead `id` before update, process, or delete.
5. [ ] Called `process` after staff create or after fixing `ERROR` leads (unless `DUPLICATED`).
6. [ ] Loaded debug skill if `storage_status` did not reach expected terminal state after `process`.
