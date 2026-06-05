---
name: bc-marketing-create-form-entry
description: Use when creating FormEntry leads via public capture, partner app, staff POST, or CSV bulk upload, including CRM and webhook side effects; do NOT use for listing, editing, deleting, or analyzing existing leads.
requires:
  - breathecode-staff-api-index
---

# Skill: Create FormEntry Leads

## When to Use

- Use for `POST /v1/marketing/lead*`, `POST /v2/marketing/lead*`, `POST /v1/marketing/app/lead`, staff `POST /v1/marketing/academy/lead`, or bulk `PUT /v1/marketing/academy/upload`.
- Use when explaining what happens **after** a lead is submitted (CRM queue, platform webhooks, `storage_status`).
- Do NOT use for list/filter/update/delete existing leads — load [`bc-marketing-manage-form-entries`](../bc-marketing-manage-form-entries/SKILL.md).
- Do NOT use for debugging `storage_status` failures — load [`bc-marketing-debug-form-entry`](../bc-marketing-debug-form-entry/SKILL.md).
- Do NOT use for acquisition funnel analytics — load [`bc-monitoring-read-report-acquisition`](../bc-monitoring-read-report-acquisition/SKILL.md).
- Do NOT use for referral commission payouts — load [`bc-marketing-inbound-leads-attribution-and-acquisition`](../bc-marketing-inbound-leads-attribution-and-acquisition/SKILL.md).

## Concepts

### Two-layer field model

| Layer | Rule |
|---|---|
| **API create** | Permissive serializer; **`email` is the only business-mandatory field**. An empty public POST can still return `201`. |
| **CRM process** | Async `persist_single_lead` requires `location`, `first_name`, `last_name`, `phone`, `course`, and (for ActiveCampaign) `tags` or valid `automations` for successful CRM sync. |

A lead can exist in the database with `storage_status=ERROR` even when create returned `201`. Diagnose with the debug skill.

### `location` and academy resolution

- Routes the lead to an academy and CRM vendor via academy alias slugs and `active_campaign_slug` values.
- Staff `POST /v1/marketing/academy/lead` **overrides** any client `location` with the session academy's `active_campaign_slug`.
- The canonical slug sent to CRM as `utm_location` may differ from the raw `location` when aliases are configured.

### `tags` and `automations`

- Comma-separated **slugs**, scoped to the academy's CRM configuration.
- **ActiveCampaign:** tags are required unless `automations` is provided. Tag types must be `STRONG`, `SOFT`, `DISCOVERY`, or `OTHER`. Tags enroll contacts and can link to automations.
- **Brevo:** tags are **not supported**. Only **one** automation slug is allowed.
- Fallback: if `automations` is empty, the first tag's linked automation is used (ActiveCampaign only).
- `app/lead` merges defaults from `LeadGenerationApp` before applying the request body.
- Discover valid slugs: `GET /v1/marketing/academy/tag`, `GET /v1/marketing/academy/automation`.

### `referral_key`

- Capture-time marker (referrer, partner, influencer code) stored on `FormEntry` and forwarded to CRM.
- Set at create time. Filterable on staff list (manage skill).
- **Not** the same as affiliate commission payouts (`/v1/commission/...` — inbound skill).

### `custom_fields` — why it exists

- `custom_fields` is a **JSON catch-all** for partner-specific, campaign, or telemetry data that does not warrant a dedicated `FormEntry` column.
- Many values are stored and forwarded (CRM, webhooks) but are **not** used for platform filtering or reporting logic.
- **Prefer `custom_fields`** for new partner-specific or experimental capture data instead of proposing new schema columns.
- **First-class fields** (`utm_*`, `email`, `course`, `referral_key`, `deal_status`, etc.) are reserved for values the platform filters, reports, or syncs with defined semantics.
- On ActiveCampaign academies, numeric keys often map to CRM custom field ids; slug-key decoding on read is documented in the inbound skill.
- **Pass through** unknown inbound keys into `custom_fields` rather than dropping them.

### Other sensible create fields

`utm_*`, `gclid` (v1), `ppc_tracking_id` (v2), `lead_type`, `language`, `course`, `phone`, `current_download`, `client_comments`. `lead_generation_app` is set automatically on `app/lead`.

### Create side effects

| Side effect | Public / app / bulk CSV | Staff `POST /academy/lead` |
|---|---|---|
| `form_entry.added` platform webhook | Yes (on save) | Yes (on save) |
| CRM outbound (`persist_single_lead`) | **Auto** after save | **No** — call `PUT .../lead/process` via manage skill |
| Geolocation enrichment | After CRM if `city` missing | Same if processed |
| Initial `storage_status` | `PENDING` → `PERSISTED` / `ERROR` / `DUPLICATED` | Stays `PENDING` until `process` |

CRM vendor routing (`ACTIVE_CAMPAIGN` vs `BREVO`) is automatic per academy CRM config (`GET /v1/marketing/crmacademy`).

**Outbound CRM sync:** create/process pushes leads **to** the CRM. Reverse sync (salesperson updates deal in ActiveCampaign reflected on `FormEntry`) is documented in [`bc-marketing-debug-form-entry`](../bc-marketing-debug-form-entry/SKILL.md).

**Later platform webhook events** (on update or deal change): `form_entry.changed`, `form_entry.won_or_lost`, `form_entry.new_deal`. Subscribe via `POST /v1/notify/hook/subscribe` (see [`HOOKS_MANAGEMENT.md`](../../HOOKS_MANAGEMENT.md)).

## Workflow

1. Set context headers. Staff and bulk paths require `Authorization: Token <token>` and `Academy: <academy_id>`. Send `Accept-Language` (e.g. `en`, `es`) for translated errors.

2. Pick the create path:
   - **Public v1:** `POST /v1/marketing/lead` or `POST /v1/marketing/lead-captcha` (uses `gclid`).
   - **Public v2:** `POST /v2/marketing/lead` or `POST /v2/marketing/lead-captcha` (uses `ppc_tracking_id`, not `gclid`).
   - **Partner app:** `POST /v1/marketing/app/lead?app_id=<slug_or_token>` — defaults merged from `LeadGenerationApp`.
   - **Staff manual:** `POST /v1/marketing/academy/lead` — then `PUT /v1/marketing/academy/lead/process?id=<id>` if CRM sync is needed (manage skill).
   - **Bulk CSV:** `PUT /v1/marketing/academy/upload` with multipart `file`.

3. Build the payload. Minimum: `email`. For successful CRM sync also include `first_name`, `last_name`, `phone`, `course`, `location` (except staff POST, which overrides location), `tags` or `automations` (per vendor rules), and attribution fields (`utm_*`, `referral_key`, `custom_fields`).

4. On `201`, save the returned `id`. For public/app/bulk paths, CRM runs asynchronously. Poll with `GET /v1/marketing/academy/lead/<id>` (manage skill) or load the debug skill if `storage_status` is `ERROR` or stuck `PENDING`.

5. If integrations need real-time fan-out, confirm a `form_entry.added` hook subscription exists (`POST /v1/notify/hook/subscribe`).

## Endpoints

### Public lead capture

| Action | Method | Path | Auth | Notes |
|---|---|---|---|---|
| Create lead (v1) | POST | `/v1/marketing/lead` | Public | Uses `gclid` for paid tracking. |
| Create with captcha (v1) | POST | `/v1/marketing/lead-captcha` | Public | Captcha fields required. |
| Create lead (v2) | POST | `/v2/marketing/lead` | Public | Uses `ppc_tracking_id`. |
| Create with captcha (v2) | POST | `/v2/marketing/lead-captcha` | Public | Captcha fields required. |
| Create from app | POST | `/v1/marketing/app/lead?app_id=<slug_or_token>` | Public | Merges `LeadGenerationApp` defaults. |
| Create from app (slug path) | POST | `/v1/marketing/app/<app_slug>/lead?app_id=<app_id>` | Public | Requires valid slug + app credential. |
| Create from app (v2) | POST | `/v2/marketing/app/lead?app_id=<slug_or_token>` | Public | Same merge behavior as v1. |

#### Example request — public create (CRM-ready)

```json
{
  "first_name": "Lucia",
  "last_name": "Mendez",
  "email": "lucia@example.com",
  "phone": "+34600000000",
  "course": "full-stack",
  "location": "barcelona-spain",
  "language": "en",
  "tags": "website-lead",
  "utm_url": "https://learn.4geeks.com/signup",
  "utm_medium": "paid-social",
  "utm_campaign": "barcelona-bootcamp-q2",
  "utm_source": "facebook",
  "referral_key": "partner-acme-01",
  "custom_fields": {
    "4": "1650742692601910",
    "9": "ppc"
  }
}
```

#### Example response — public create

```json
{
  "id": 219384,
  "first_name": "Lucia",
  "last_name": "Mendez",
  "email": "lucia@example.com",
  "phone": "+34600000000",
  "course": "full-stack",
  "location": "barcelona-spain",
  "language": "en",
  "tags": "website-lead",
  "utm_medium": "paid-social",
  "utm_campaign": "barcelona-bootcamp-q2",
  "utm_source": "facebook",
  "referral_key": "partner-acme-01",
  "custom_fields": {
    "4": "1650742692601910",
    "9": "ppc"
  },
  "storage_status": "PENDING",
  "storage_status_text": "",
  "created_at": "2026-04-03T15:29:11.532Z",
  "updated_at": "2026-04-03T15:29:11.532Z"
}
```

### Partner app create

`POST /v1/marketing/app/lead?app_id=acme-partner` merges `LeadGenerationApp` defaults (`utm_*`, `location`, `language`, `tags`, `automations`, academy) then overwrites with request body fields.

#### Example request — partial app payload

```json
{
  "email": "partner-lead@example.com",
  "first_name": "Ana",
  "last_name": "Ruiz",
  "phone": "+14155550100",
  "course": "data-science-pt"
}
```

#### Example response

Same shape as public create. `storage_status` starts as `PENDING`; CRM runs automatically.

### Staff manual create

| Action | Method | Path | Headers | Capability |
|---|---|---|---|---|
| Staff create | POST | `/v1/marketing/academy/lead` | `Authorization`, `Academy`, optional `Accept-Language` | `crud_lead` |

`location` in the request body is **ignored** and replaced with the session academy's `active_campaign_slug`.

#### Example request — minimal staff create

```json
{
  "email": "manual-lead@example.com",
  "first_name": "Carlos",
  "last_name": "Perez",
  "phone": "+34600111222",
  "course": "full-stack",
  "tags": "staff-import"
}
```

#### Example request — CRM-ready staff create

```json
{
  "email": "manual-lead@example.com",
  "first_name": "Carlos",
  "last_name": "Perez",
  "phone": "+34600111222",
  "course": "full-stack",
  "tags": "website-lead",
  "automations": "welcome-sequence",
  "utm_source": "referral",
  "utm_campaign": "open-house-apr",
  "referral_key": "staff-booth-01"
}
```

#### Example response — staff create

Returns `FormEntryBigSerializer` shape (more fields than public create). Key fields:

```json
{
  "id": 219401,
  "first_name": "Carlos",
  "last_name": "Perez",
  "email": "manual-lead@example.com",
  "phone": "+34600111222",
  "course": "full-stack",
  "location": "barcelona-spain",
  "tags": "website-lead",
  "storage_status": "PENDING",
  "storage_status_text": "",
  "ac_contact_id": null,
  "deal_status": null,
  "created_at": "2026-04-03T16:10:00.000Z"
}
```

After staff create, call `PUT /v1/marketing/academy/lead/process?id=219401` (manage skill) to push to CRM.

### Bulk CSV upload

| Action | Method | Path | Headers | Capability |
|---|---|---|---|---|
| Bulk CSV upload | PUT | `/v1/marketing/academy/upload` | `Authorization`, `Academy`, `Content-Type: multipart/form-data` | `crud_media` |

**Required CSV columns:** `first_name`, `last_name`, `email`, `location`, `phone`, `language`.

**Optional column:** `academy` (academy slug) helps resolve `FormEntry.academy`.

Each row runs asynchronously: save → `persist_single_lead` (auto CRM, same as public capture).

**Current behavior:** the bulk task maps `first_name`, `last_name`, `email`, `location`, `academy` only. Extra columns (`referral_key`, `tags`, `utm_*`) are **not** applied today.

#### Example response — bulk upload accepted

```json
[
  {
    "file_name": "leads-april.csv",
    "status": "PENDING",
    "message": "Despues"
  }
]
```

There is **no staff GET API** to poll `CSVUpload` job status. Find imported leads by email and `created_at` (debug skill).

### Platform webhook subscription (optional)

Subscribe to `form_entry.added` so n8n/Zapier receives new leads in real time.

```http
POST /v1/notify/hook/subscribe
Authorization: Token <academy_token>
Content-Type: application/json
```

```json
{
  "event": "form_entry.added",
  "target": "https://hooks.example.com/form-entry-added"
}
```

Full hook catalog and auth rules: [`HOOKS_MANAGEMENT.md`](../../HOOKS_MANAGEMENT.md).

## Edge Cases

- **Empty public POST:** returns `201` with minimal record; CRM fails with `storage_status=ERROR`, `storage_status_text=Missing location information`. Load debug skill.
- **Invalid phone or language on create:** returns `400` before any record is saved (phone regex `^\+?1?\d{8,15}$`; language max 2 chars).
- **Development URL safeguard:** if `utm_url` contains `//localhost:` or `gitpod.io`, public create returns `201` without persisting side effects.
- **Brevo academy + tags:** CRM error — remove tags from payload.
- **Brevo academy + multiple automations:** CRM error — keep one automation slug.
- **Duplicate email+course within 30 minutes:** `storage_status=DUPLICATED`; lead is not re-sent to CRM. Do not call `process`.
- **Staff create without `process`:** record exists but no CRM contact (`ac_contact_id` null, `storage_status=PENDING`).
- **Bulk row missing location/academy:** row error logged server-side; lead not created for that row.
- **`SAVE_LEADS=FALSE` environment:** CRM is skipped; `storage_status=PERSISTED` with explanatory `storage_status_text` (ops environments only).
- **App credential mismatch:** `app/lead` fails if `app_id` is missing or invalid.

## Checklist

1. [ ] Picked the correct create path (public, app, staff POST, or bulk CSV).
2. [ ] Included `email` at minimum; added CRM-ready fields (`location`, names, phone, course, tags/automations) when CRM sync is required.
3. [ ] Used `Academy` header on staff POST and bulk upload.
4. [ ] Saved returned `id` from `201` response.
5. [ ] For staff create, called `PUT .../lead/process?id=` when CRM contact is needed.
6. [ ] For public/app/bulk, checked `storage_status` after async processing; loaded debug skill if `ERROR` or stuck `PENDING`.
7. [ ] Confirmed `form_entry.added` hook subscription if external integrations need real-time fan-out.
