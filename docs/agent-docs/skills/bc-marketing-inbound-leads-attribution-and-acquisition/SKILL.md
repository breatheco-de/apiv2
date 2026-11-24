---
name: bc-marketing-inbound-leads-attribution-and-acquisition
description: Use when implementing or analyzing inbound signups, attribution, and acquisition across marketing FormEntry and auth UserInvite flows; do NOT use for creating leads, staff lead CRUD, CRM sync debugging, or generic student login troubleshooting.
requires:
  - breathecode-staff-api-index
  - bc-marketing-create-form-entry
  - bc-marketing-manage-form-entries
  - bc-marketing-debug-form-entry
---

# Skill: Inbound Leads, Attribution, and Acquisition

## When to Use

- Use for end-to-end **inbound analysis**: attribution fields, acquisition funnel architecture, partner ingestion overview, invite-based signup capture, and referral **commercial** outcomes.
- Use when the request mixes `/v1/marketing/...` and `/v1/auth/...` data sources for a unified inbound picture.
- Do NOT use for creating leads — load [`bc-marketing-create-form-entry`](../bc-marketing-create-form-entry/SKILL.md).
- Do NOT use for searching/editing/deleting leads — load [`bc-marketing-manage-form-entries`](../bc-marketing-manage-form-entries/SKILL.md).
- Do NOT use for debugging `storage_status` or CRM sync — load [`bc-marketing-debug-form-entry`](../bc-marketing-debug-form-entry/SKILL.md).
- Do NOT use for generic authentication login/token issues or post-enrollment academic operations.

## Concepts

### Two inbound channels

- **FormEntry (marketing):** lead forms, partner apps, ad-platform webhooks (`/v1/marketing/...`). Create mechanics → create skill.
- **UserInvite (auth):** waitlist/invite signups with `conversion_info` (`/v1/auth/...`).

### Attribution fields

- **FormEntry:** `utm_*`, `gclid` (v1), `ppc_tracking_id` (v2), `referral_key`, `custom_fields`.
- **UserInvite:** `conversion_info` (not a fixed schema — UTMs, landing paths, internal CTA labels, vendor ids).
- **Why `custom_fields` exists** (capture rationale) → [`bc-marketing-create-form-entry`](../bc-marketing-create-form-entry/SKILL.md). **Decoding numeric keys** (ActiveCampaign) → below.

### Lead generation apps (overview)

- `LeadGenerationApp` stores per-partner defaults (`utm_*`, `location`, `language`, tags, automations, academy).
- `app/lead` merges defaults then overwrites with request body. Full create workflow → create skill.

### Referrals vs affiliate outcomes

- `FormEntry.referral_key` = lead-level referrer marker at **capture** time (set via create skill).
- Coupon/commission **payouts** are tracked later in `/v1/commission/...` — not the same as `referral_key`.

### Unified inbound "Leads" list (merge pattern, not one API)

- Combine **marketing `FormEntry`** with **`UserInvite`** for the same academy.
- **Include `UserInvite` only when `author` is null** (self-serve capture). **Exclude** staff-created invites (`author` set).
- **Dedup:** same email may appear in both sources — define rules (email + date window).
- **API gap:** `GET /v1/auth/academy/user/invite` may not expose `author` in JSON — extend serializer or merge in a backend job to filter client-side.

### Acquisition funnel architecture

Monitoring report `source_type` values (see [`bc-monitoring-read-report-acquisition`](../bc-monitoring-read-report-acquisition/SKILL.md)):

| `source_type` | Meaning |
|---|---|
| `FORM_ENTRY` | Lead created (`FormEntry.created_at` date) |
| `FORM_ENTRY_WON` | Same lead when deal won (`won_at` date; requires `deal_status=WON`) |
| `USER_INVITE` | Self-serve invite path |
| `EVENT_RSVP` / `EVENT_ATTENDED` | Event check-in funnel tiers |

Drill down from acquisition report to lead detail → manage skill (`GET /v1/marketing/academy/lead/<id>`).

### Example `conversion_info` payloads

**Shape A — product CTAs + referrer URL:**

```json
{
  "user_agent": "Mozilla/5.0 ...",
  "landing_url": "/signup",
  "utm_referrer": "https://learn.learnpack.co/?error=google-user-not-found",
  "conversion_url": "https://learn.learnpack.co/signup",
  "internal_cta_content": "learnpack-signup",
  "internal_cta_placement": "signup-form"
}
```

**Shape B — UTM dimensions + campaign ids:**

```json
{
  "utm_term": "120225055241440575",
  "utm_medium": "ppc",
  "utm_source": "brevo",
  "landing_url": "/beyondtheresume",
  "utm_content": "120225059437650575",
  "utm_campaign": "120225055241360575",
  "conversion_url": "/es/bootcamp/change-your-career-in-15-days-self-paced"
}
```

### Example `FormEntry.custom_fields` payload

```json
{
  "4": "1650742692601910",
  "5": "facebook_form_3538488439623664",
  "7": "120208243666950073",
  "8": "PR+q3Czf(p$285[W($4(bK(c",
  "9": "ppc",
  "16": "barcelona-spain",
  "65": "+34639709613",
  "70": "120241983817670073",
  "103": "0.075",
  "104": "MEDIO"
}
```

**Decoding numeric keys (ActiveCampaign only):** maps ActiveCampaign custom field id strings to internal slugs. Other CRMs and raw partner payloads keep opaque key/value shapes.

- Contact-level examples: `referral_key`, `gclid`.
- Deal-level examples: `gclid` → `"4"`, `utm_url` → `"5"`, `utm_campaign` → `"7"`, `utm_source` → `"8"`, `utm_medium` → `"9"`, `utm_location` → `"16"`, `Deal_Phone` → `"65"`, `utm_content` → `"70"`, `referral_key` → `"34"`.
- `FormEntryBigSerializer` inverts deal mappings on read where applicable — slug keys instead of numeric ids.
- Unmapped keys (e.g. `"103"`, `"104"`) stay opaque.
- **Brevo** uses its own field map (`AC_MAPS`) — separate from ActiveCampaign decoding.

## Workflow

1. **Capture** → [`bc-marketing-create-form-entry`](../bc-marketing-create-form-entry/SKILL.md) for `POST /v1|v2/marketing/lead*`, `app/lead`, staff POST, bulk CSV. Use `POST /v1/auth/subscribe/` for invite/waitlist capture ([`bc-authenticate-signup-user`](../bc-authenticate-signup-user/SKILL.md)).

2. **Store attribution at write time.** Populate `utm_*`, `referral_key`, `custom_fields` (FormEntry) or `conversion_info` (UserInvite).

3. **Partner-safe ingestion.** Prefer `app/lead` with `app_id` for external integrations (defaults enforced per `LeadGenerationApp`).

4. **Staff read/edit** → [`bc-marketing-manage-form-entries`](../bc-marketing-manage-form-entries/SKILL.md) for `GET/PUT/DELETE /v1/marketing/academy/lead`, `process`, won list. Use `start`/`end` date filters (not `started_at`/`ended_at`).

5. **CRM sync failed or lead stuck** → [`bc-marketing-debug-form-entry`](../bc-marketing-debug-form-entry/SKILL.md).

6. **Webhook subscriptions for n8n/Zapier** → create skill + [`HOOKS_MANAGEMENT.md`](../../HOOKS_MANAGEMENT.md) (`form_entry.added`, `form_entry.changed`, `form_entry.won_or_lost`, `form_entry.new_deal`).

7. **Merged Leads view.** Combine `GET /v1/marketing/academy/lead` with self-serve `UserInvite` rows (`author` null). Apply dedup. Load manage skill for FormEntry reads.

8. **Acquisition analytics.** Funnel tiers and attribution across forms, invites, and events → `GET /v1/monitoring/report/acquisition*` (monitoring skill). Live `FormEntry` counts grouped by status, course, location, UTM, or date → `GET /v1/marketing/report/lead` with the `Academy` header (see [Lead report](#lead-report)). Cross-academy raw lead reads: `GET /v1/marketing/lead/all`.

9. **Referral payouts.** Check commission endpoints separately from `referral_key` capture markers.

## Endpoints

### Auth signup capture

| Action | Method | Path | Auth | Notes |
|---|---|---|---|---|
| Create/update waitlist invite | POST | `/v1/auth/subscribe/` | Public | Ingests `UserInvite` with `conversion_info`. |
| List academy invites | GET | `/v1/auth/academy/user/invite` | `Authorization`, `Academy` | Filters: `status`, `role`, `like`, etc. |
| Invite stats | GET | `/v1/auth/academy/user/invite/stats` | `Authorization`, `Academy` | `clean_cache=true` for fresh data. |

#### Example request — subscribe

```json
{
  "email": "lucia@example.com",
  "first_name": "Lucia",
  "last_name": "Mendez",
  "academy": "barcelona",
  "course": "full-stack-pt",
  "has_marketing_consent": true,
  "conversion_info": {
    "landing_url": "/signup",
    "utm_referrer": "https://learn.learnpack.co/signup",
    "conversion_url": "https://learn.learnpack.co/signup",
    "internal_cta_content": "learnpack-signup"
  }
}
```

### Marketing reads (attribution / reporting — not CRUD)

| Action | Method | Path | Headers | Notes |
|---|---|---|---|---|
| Cross-academy leads | GET | `/v1/marketing/lead/all` | `Authorization` | Staff cross-academy read. |
| Lead report | GET | `/v1/marketing/report/lead` | `Authorization`, `Academy` | Live lead counts grouped by allowlisted fields. Requires `read_lead` when `Academy` is sent. See [Lead report](#lead-report). |
| List lead generation apps | GET | `/v1/marketing/academy/app` | `Authorization`, `Academy` | Partner integration config. |
| UTM catalog | GET | `/v1/marketing/academy/utm` | `Authorization`, `Academy` | Attribution filter values. |

Staff lead CRUD (`GET/PUT/DELETE /academy/lead`, `process`, won list) → **manage skill**.

Lead create (`POST /lead*`, `app/lead`, bulk upload) → **create skill**.

### Lead report

`GET /v1/marketing/report/lead` counts `FormEntry` rows per group. Use it for live breakdowns such as "ERROR leads by course" or "leads per week by UTM source". Use the acquisition monitoring report for funnel tiers and cross-source attribution.

**Headers:** `Authorization: Token <token>` and `Academy: <academy_id>`. With the `Academy` header the user needs the `read_lead` capability in that academy and results are limited to that academy. Calls without the header are deprecated: they fall back to every academy the user belongs to and the `academy` parameter filters on `location`.

**Rate limits:** 30 requests per minute and 300 per hour per user. Over the limit the API answers `429` with `{"detail": "rate-limit-exceeded"}` and a `Retry-After` header (seconds). Wait for `Retry-After` before retrying; do not loop.

**Query parameters:**

| Param | Values | Notes |
|---|---|---|
| `by` | Comma-separated: `location`, `course`, `created_at__date`, `storage_status`, `deal_status`, `utm_source`, `utm_medium`, `utm_campaign`, `lead_type` | Default `location,created_at__date,course`. Any other field → `400 invalid-group-by`. |
| `start` / `end` | `YYYY-MM-DD` | Both inclusive. `end` defaults to today, `start` to `end` minus 365 days. Max window 366 days. |
| `interval` | `day` (default), `week`, `month` | Only applies when `by` includes `created_at__date`. |
| `storage_status` | `PENDING`, `PERSISTED`, `REJECTED`, `DUPLICATED`, `ERROR`, `MANUALLY_PERSISTED` | Comma-separated, case-insensitive. |
| `deal_status` | `WON`, `LOST` | Comma-separated, case-insensitive. |
| `lead_type` | `STRONG`, `SOFT`, `DISCOVERY` | Comma-separated, case-insensitive. |
| `location`, `utm_source`, `utm_campaign` | Free text | Comma-separated, exact match. |
| `limit` | `1`–`5000` | Default `1000`. Max number of rows returned. |

**Response:** a JSON list. Each row has the `by` fields plus `total_leads`. Leads with a null value in a grouped field (e.g. no `location`) are still counted, in a row where that field is `null`.

- `interval=day` with `created_at__date`: rows include `created_at__date` (`YYYY-MM-DD`) and `created_date` (`YYYYMMDD`).
- `interval=week` or `month`: the date column is returned as `period` (first day of the week, Monday, or of the month).
- Rows are sorted by date (when grouped by date), then by `total_leads` descending.

**Response headers:** `X-Total-Count` (number of groups before `limit`) and `X-Truncated` (`true` when rows were cut by `limit`). When truncated, narrow the date window, add filters, or use a coarser `interval`.

#### Example request — ERROR leads by course, last month

```http
GET /v1/marketing/report/lead?by=course&storage_status=ERROR&start=2026-10-01&end=2026-10-31
Authorization: Token <token>
Academy: 1
```

```json
[
  {"course": "full-stack", "total_leads": 12},
  {"course": "data-science", "total_leads": 4},
  {"course": null, "total_leads": 2}
]
```

#### Example request — weekly leads per UTM source

```http
GET /v1/marketing/report/lead?by=created_at__date,utm_source&interval=week&start=2026-09-01&end=2026-10-31
Authorization: Token <token>
Academy: 1
```

```json
[
  {"period": "2026-08-31", "utm_source": "google", "total_leads": 40},
  {"period": "2026-08-31", "utm_source": "facebook", "total_leads": 18}
]
```

**Errors (`400`):** `invalid-group-by`, `invalid-filter-value`, `invalid-date-format`, `invalid-date-range` (`start` after `end`), `date-range-too-long`, `invalid-interval`, `invalid-limit`. `403` when the user lacks `read_lead` in the `Academy` sent.

### Acquisition webhooks (intake sources)

| Area | Method | Path | Role |
|---|---|---|---|
| Meta/Facebook Lead Ads | GET + POST | `/v1/marketing/facebook/lead` | GET verifies subscription; POST ingests `leadgen` into FormEntry. |
| ActiveCampaign reverse sync | POST | `/v1/marketing/activecampaign/webhook/<ac_academy_id>` or `.../<academy_slug>` | **Optional reverse-sync channel** (`deal_add`, `deal_update`) — updates `deal_status`, `ac_deal_*` on existing leads. **Not** Facebook-style intake. Activation and troubleshooting → debug skill. |
| Google Ads enrollment export | GET | `/v1/marketing/googleads/enrollments/<academy_slugs>` | CSV export using `gclid`. |

### Referral and affiliate outcomes (commercial layer)

| Action | Method | Path | Notes |
|---|---|---|---|
| Referral commissions list | GET | `/v1/commission/academy/<academy_id>/referral-commissions` | Post-purchase outcomes. |
| Referral commission detail | GET | `/v1/commission/academy/<academy_id>/referral-commissions/<commission_id>` | Per-item detail. |
| Influencer payout report | GET | `/v1/commission/academy/<academy_id>/report` | Aggregate referral/usage report. |

## Edge Cases

- **Development URL safeguard:** public lead create ignores `utm_url` with localhost/gitpod (create skill).
- **App credential mismatch:** `app/lead` fails without valid `app_id` (create skill).
- **Default merge:** partner defaults applied first; request body overwrites (create skill).
- **Invite list default status:** omits `status` → pending-only behavior in view.
- **Invite stats cache:** use `clean_cache=true` on stats endpoint.
- **v2 tracking:** v2 expects `ppc_tracking_id`; legacy `gclid` alone may break attribution intent.
- **Merged Leads + `author`:** serializer may not expose `author` — see Concepts.
- **AC webhook ≠ intake:** AC webhook is reverse deal sync, not a new-lead intake path like Facebook.
- **Referrals are multi-layered:** `referral_key` at capture vs commission payouts later.
- **Lead report window:** omitting `start`/`end` covers only the last 366 days, not all time. Longer analyses need several calls.
- **Lead report truncation:** check `X-Truncated` before presenting totals; a truncated response does not include every group.

## Checklist

1. [ ] Identified inbound channel (FormEntry vs UserInvite vs event check-in).
2. [ ] Delegated create to create skill; CRUD to manage skill; CRM debug to debug skill.
3. [ ] Included attribution payload (`utm_*`, `custom_fields`, `referral_key`, or `conversion_info`).
4. [ ] Used `Academy` header on all `/academy/` routes.
5. [ ] Planned merged Leads view with self-serve invites only and dedup rules.
6. [ ] Used acquisition monitoring skill for funnel analysis; manage skill for lead drill-down.
7. [ ] For lead counts, called `report/lead` with the `Academy` header, an allowlisted `by`, and checked `X-Truncated`.
8. [ ] Separated `referral_key` capture from commission payout verification.
