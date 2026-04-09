---
name: bc-marketing-inbound-leads-attribution-and-acquisition
description: Use when implementing or analyzing inbound signups, attribution, and acquisition across marketing FormEntry and auth UserInvite flows; do NOT use for generic student login/session troubleshooting or post-enrollment academic operations.
requires:
  - breathecode-api-index
---

# Skill: Inbound Leads, Attribution, and Acquisition

## When to Use

- Use this skill for end-to-end inbound analysis: lead capture, partner integrations, invite-based signup capture, attribution fields, and referral outcomes.
- Use this when the request mixes `/v1/marketing/...` and `/v1/auth/...` data sources.
- Use this when you need to explain partner lead ingestion (`app/lead`) defaults and webhook ingestion.
- Do NOT use this for generic authentication login/token issues.
- Do NOT use this for post-enrollment operations (cohort management, grading, certificates).

## Concepts

- **Two inbound channels**
  - **FormEntry (marketing):** lead forms and ad-platform events (`/v1/marketing/...`).
  - **UserInvite (auth):** waitlist/invite signups and conversion metadata (`/v1/auth/...`).
- **Attribution fields**
  - `utm_*`, `gclid` (v1), `ppc_tracking_id` (v2), `referral_key`, and `custom_fields` (opaque JSON; numeric keys often mean **ActiveCampaign** field ids when that integration is in use — see decoding below; **other CRMs use different `custom_fields` shapes**).
  - `conversion_info` on `UserInvite` for signup context payloads (not a fixed schema — may include **UTM-style keys**, **landing/conversion paths**, **internal CTA labels**, or vendor-specific ids such as Brevo/campaign object ids).
- **Lead generation apps**
  - `LeadGenerationApp` stores per-partner defaults (`utm_*`, `location`, `language`, tags, automations, academy).
  - `app/lead` endpoints merge defaults first, then overwrite with request body values.
- **Referrals vs affiliate outcomes**
  - `FormEntry.referral_key` = lead-level referrer marker at capture time.
  - Coupon/commission outcomes are tracked later in payments/commission flows.
- **Unified inbound “Leads” list (merge pattern, not a single API)**
  - Many products want **one** list of **inbound interest**: combine **marketing `FormEntry`** records with **`UserInvite`** records for the same academy.
  - **Include `UserInvite` only when `author` is null** — treat these as **self-serve** capture (public subscribe/waitlist-style flows). **Exclude** invites where **`author` is set** — those are **staff-created** (outbound/onboarding), not the same bucket as organic leads.
  - **Dedup:** the same person may appear as both a `FormEntry` and a `UserInvite` (same email); define **dedup rules** (e.g. email + date window) when merging.
  - **API gap:** `GET /v1/auth/academy/user/invite` uses `UserInviteSerializer`, which **does not currently expose `author`** in the JSON. To filter **client-side** by `author`, either **extend the serializer** to include `author` / `author_id`, or **merge in a backend job** that reads the model field directly.

### Example `conversion_info` payloads

**Shape A — product CTAs + referrer URL (e.g. LearnPack-style):**

```json
{
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0",
  "landing_url": "/signup",
  "utm_referrer": "https://learn.learnpack.co/?error=google-user-not-found",
  "conversion_url": "https://learn.learnpack.co/signup",
  "internal_cta_content": "learnpack-signup",
  "internal_cta_placement": "signup-form"
}
```

**Shape B — UTM dimensions + Brevo-style campaign ids (numeric strings on `utm_*` fields are common for ad/CRM systems):**

```json
{
  "utm_term": "120225055241440575",
  "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
  "utm_medium": "ppc",
  "utm_source": "brevo",
  "landing_url": "/beyondtheresume",
  "utm_content": "120225059437650575",
  "utm_campaign": "120225055241360575",
  "conversion_url": "/es/bootcamp/change-your-career-in-15-days-self-paced",
  "internal_cta_placement": "navbar-career-booster-cambia-tu-carrera-en-15-días"
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

**Decoding numeric keys (ActiveCampaign only):** The **`acp_ids`** dictionary applies **only to the ActiveCampaign integration**. It maps **ActiveCampaign custom field id strings** (what you often see as keys like `"4"`, `"5"` in stored `FormEntry.custom_fields`) to **stable internal slugs** used in this codebase. Other CRMs (and raw Facebook Lead Ads or partner payloads) store **`custom_fields` as their own opaque key/value bags** — different id schemes, different semantics — and **are not decoded by `acp_ids`**.

- **`acp_ids`** in [`breathecode/services/activecampaign/client.py`](../../../../breathecode/services/activecampaign/client.py) (ActiveCampaign only):
  - **Contact-level** fields (e.g. `referral_key` → `"27"`, `gclid` → `"26"`).
  - **`acp_ids["deal"]`**: maps **human-readable keys** to **ActiveCampaign deal custom field id strings** (e.g. `gclid` → `"4"`, `utm_url` → `"5"`, `utm_campaign` → `"7"`, `utm_source` → `"8"`, `utm_medium` → `"9"`, `utm_location` → `"16"`, `Deal_Phone` → `"65"`, `utm_content` → `"70"`, `referral_key` → `"34"`, …).
- When a lead is serialized with **`FormEntryBigSerializer`**, `get_custom_fields` **inverts** `acp_ids["deal"]` so API responses can show **slug keys** instead of ActiveCampaign numeric ids **where that serializer path and mapping apply** ([`breathecode/marketing/serializers.py`](../../../../breathecode/marketing/serializers.py) — `FormEntryBigSerializer.get_custom_fields`).
- **Keys with no entry** in `acp_ids["deal"]` (e.g. `"103"`, `"104"` in the sample) stay **opaque** until mapped, or belong to **another vendor/CRM** with its own field catalog.
- **Brevo** (separate from ActiveCampaign’s `acp_ids`) uses **`AC_MAPS`** in [`breathecode/services/brevo.py`](../../../../breathecode/services/brevo.py) for that integration’s field labels.

## Workflow

1. **Pick the correct inbound write path.**
   - Use `POST /v1/marketing/lead` (or captcha/app variants) for direct marketing lead capture.
   - Use `POST /v1/auth/subscribe/` for invite/waitlist style signup capture.
2. **Prefer partner-safe ingestion when integrations are external.**
   - For partner systems, use `app/lead` endpoints with `app_id` so defaults are enforced per integration.
3. **Store attribution at write time.**
   - Populate `utm_*`, `referral_key`, and `custom_fields` (FormEntry) or `conversion_info` (UserInvite).
4. **Read and segment inbound data for academy operations.**
   - Staff uses `/academy/...` endpoints with `Academy` header for leads, apps, utm catalog, and invite stats.
   - For a **single merged Leads view**, combine `FormEntry` (e.g. `GET /v1/marketing/academy/lead`) with **self-serve** `UserInvite` rows only (`author` null — see Concepts). Apply **dedup** if the same email exists in both sources.
5. **Add webhook context for server-to-server ingestion.**
   - Facebook and ActiveCampaign webhooks are part of acquisition intake, not only dashboard reads.
6. **Separate lead attribution from commercial referral payouts.**
   - Lead marker (`referral_key`) belongs here.
   - Coupon/commission payouts are verified via payments/commission endpoints.

## Endpoints

### Marketing lead capture

| Action | Method | Path | Required headers | Body | Notes |
|---|---|---|---|---|---|
| Create lead (v1) | POST | `/v1/marketing/lead` | `Content-Type: application/json` | Lead payload | Uses `gclid` for paid tracking. |
| Create lead with captcha (v1) | POST | `/v1/marketing/lead-captcha` | `Content-Type: application/json` | Lead payload + captcha fields | Public endpoint. |
| Create lead from app (v1) | POST | `/v1/marketing/app/lead?app_id=<slug_or_token>` | `Content-Type: application/json` | Lead payload (partial allowed) | Merges defaults from `LeadGenerationApp`. |
| Create lead from app slug (v1) | POST | `/v1/marketing/app/<app_slug>/lead?app_id=<app_id>` | `Content-Type: application/json` | Lead payload (partial allowed) | Requires valid slug + app credential. |
| Create lead (v2) | POST | `/v2/marketing/lead` | `Content-Type: application/json` | Lead payload | Uses `ppc_tracking_id` (no backward compatibility with `gclid`). |
| Create lead with captcha (v2) | POST | `/v2/marketing/lead-captcha` | `Content-Type: application/json` | Lead payload + captcha fields | Public endpoint. |
| Create lead from app (v2) | POST | `/v2/marketing/app/lead?app_id=<slug_or_token>` | `Content-Type: application/json` | Lead payload | Same app-default merge behavior as v1. |

#### Example request (v1 marketing lead)

```json
{
  "first_name": "Lucia",
  "last_name": "Mendez",
  "email": "lucia@example.com",
  "phone": "+34600000000",
  "utm_url": "https://learn.example.com/signup",
  "utm_medium": "paid-social",
  "utm_campaign": "barcelona-bootcamp-q2",
  "utm_source": "facebook",
  "utm_plan": "freemium",
  "referral_key": "partner-acme-01",
  "custom_fields": {
    "4": "1650742692601910",
    "5": "facebook_form_3538488439623664",
    "9": "ppc"
  }
}
```

#### Example response (marketing lead created)

```json
{
  "id": 219384,
  "first_name": "Lucia",
  "last_name": "Mendez",
  "email": "lucia@example.com",
  "phone": "+34600000000",
  "utm_medium": "paid-social",
  "utm_campaign": "barcelona-bootcamp-q2",
  "utm_source": "facebook",
  "referral_key": "partner-acme-01",
  "custom_fields": {
    "4": "1650742692601910",
    "5": "facebook_form_3538488439623664",
    "9": "ppc"
  },
  "storage_status": "PENDING",
  "created_at": "2026-04-03T15:29:11.532Z"
}
```

### Marketing staff reads and controls

All endpoints below include `/academy/`, so requests must include `Academy: <academy_id>`.

| Action | Method | Path | Required headers | Notes |
|---|---|---|---|---|
| List lead generation apps | GET | `/v1/marketing/academy/app` | `Authorization`, `Academy` | Shows configured `LeadGenerationApp` integrations. |
| List leads | GET | `/v1/marketing/academy/lead` | `Authorization`, `Academy` | Supports filtering/sorting in view logic. |
| Get/update/delete one lead | GET/PUT/PATCH/DELETE | `/v1/marketing/academy/lead/<lead_id>` | `Authorization`, `Academy` | Staff-only operations. |
| List UTM values | GET | `/v1/marketing/academy/utm` | `Authorization`, `Academy` | UTM catalog for attribution filters. |
| List/create short links | GET/POST | `/v1/marketing/academy/short` | `Authorization`, `Academy` | URL attribution helper. |
| Get/update/delete short link | GET/PUT/PATCH/DELETE | `/v1/marketing/academy/short/<short_slug>` | `Authorization`, `Academy` | Staff-only short-link management. |
| Lead report | GET | `/v1/marketing/report/lead` | `Authorization`, `Academy` | Reporting endpoint used by staff dashboards. |

#### Example response (lead generation app list)

```json
[
  {
    "id": 13,
    "slug": "acme-partner",
    "name": "Acme Partner Engine",
    "app_id": "f8R9nA...token",
    "hits": 2093,
    "academy": {
      "id": 55,
      "slug": "barcelona"
    }
  }
]
```

### Auth signup capture and invite attribution

All `/academy/...` auth endpoints also require `Academy: <academy_id>`.

| Action | Method | Path | Required headers | Body | Notes |
|---|---|---|---|---|---|
| Create/update waitlist invite | POST | `/v1/auth/subscribe/` | `Content-Type: application/json` | Invite/waitlist payload | Public signup ingestion into `UserInvite`. |
| List academy invites | GET | `/v1/auth/academy/user/invite` | `Authorization`, `Academy` | Filters: `status`, `role`, `like`, `user_id`, `invite_id`, `profile_academy_id`, `sort`. |
| Get invite stats | GET | `/v1/auth/academy/user/invite/stats` | `Authorization`, `Academy` | Aggregated status/open/click metrics; supports `clean_cache=true`. |

#### Example request (`/v1/auth/subscribe/`)

```json
{
  "email": "lucia@example.com",
  "first_name": "Lucia",
  "last_name": "Mendez",
  "academy": "barcelona",
  "course": "full-stack-pt",
  "asset_slug": "intro-to-python",
  "event_slug": "open-house-apr",
  "has_marketing_consent": true,
  "conversion_info": {
    "landing_url": "/signup",
    "utm_referrer": "https://learn.learnpack.co/?error=google-user-not-found",
    "conversion_url": "https://learn.learnpack.co/signup",
    "internal_cta_content": "learnpack-signup",
    "internal_cta_placement": "signup-form"
  }
}
```

#### Example response (academy invite list item)

```json
{
  "id": 9921,
  "status": "WAITING_LIST",
  "email": "lucia@example.com",
  "first_name": "Lucia",
  "last_name": "Mendez",
  "event_slug": "open-house-apr",
  "asset_slug": "intro-to-python",
  "course": {
    "id": 17,
    "slug": "full-stack-pt"
  },
  "conversion_info": {
    "landing_url": "/signup",
    "utm_referrer": "https://learn.learnpack.co/?error=google-user-not-found",
    "conversion_url": "https://learn.learnpack.co/signup"
  },
  "opened_at": null,
  "clicked_at": null,
  "created_at": "2026-04-03T15:55:01.299Z"
}
```

### Acquisition webhooks and integrations

| Area | Method | Path | Role in acquisition |
|---|---|---|---|
| Meta/Facebook Lead Ads verify + ingest | GET + POST | `/v1/marketing/facebook/lead` | GET verifies webhook subscription challenge; POST ingests `leadgen` payload into FormEntry fields. |
| ActiveCampaign webhook ingest | POST | `/v1/marketing/activecampaign/webhook/<ac_academy_id>` or `/v1/marketing/activecampaign/webhook/<academy_slug>` | Logs payload and dispatches async processing. |
| Google Ads enrollment export | GET | `/v1/marketing/googleads/enrollments/<academy_slugs>` | CSV export for attribution workflows using `gclid`. |

### Referral and affiliate outcomes (commercial layer)

| Action | Method | Path | Notes |
|---|---|---|---|
| Referral commissions list | GET | `/v1/commission/academy/<academy_id>/referral-commissions` | Post-purchase referral outcomes for the influencer/geek creator program. |
| Referral commissions detail | GET | `/v1/commission/academy/<academy_id>/referral-commissions/<commission_id>` | Detailed record per commission item. |
| Influencer payout report | GET | `/v1/commission/academy/<academy_id>/report` | Aggregate report including referral/usage dimensions. |

## Edge Cases

- **Development URL safeguard:** marketing lead creation ignores `utm_url` values containing localhost/gitpod and returns 201 without persistence side effects.
- **App credential mismatch:** `app/lead` fails if `app_id` is missing or does not match slug/token.
- **Default merge behavior:** partner defaults are applied first; request payload can still overwrite provided fields.
- **Invite list default status filter:** if `status` is omitted, academy invite list defaults to pending-only behavior in the view.
- **Invite stats cache:** `/academy/user/invite/stats` may return cached values unless `clean_cache=true`.
- **Legacy tracking field mismatch:** v2 endpoints expect `ppc_tracking_id`; sending only legacy `gclid` can break intended attribution.
- **Referrals are multi-layered:** `referral_key` tracks capture source, but payouts depend on coupon and commission flows.
- **Merged Leads + `author` filter:** excluding staff-created invites requires the **`author`** field; it may not be present on invite list API responses — see Concepts.
- **Heuristic limits:** `author is null` is a strong signal for self-serve, but confirm with your deployment that no staff flow leaves `author` unset.

## Checklist

1. [ ] Selected the correct write path (`/v1|v2/marketing/lead*`, `app/lead`, or `/v1/auth/subscribe/`).
2. [ ] Included attribution payload (`utm_*`, `custom_fields`, `referral_key`, or `conversion_info`) in requests.
3. [ ] Used `Academy` header on all `/academy/` routes.
4. [ ] Queried staff read endpoints for analytics (`academy/lead`, `academy/utm`, invite list/stats).
5. [ ] Considered webhook ingestion (Facebook, ActiveCampaign, Google Ads export) where integration is server-to-server.
6. [ ] If asked about affiliate performance, checked both lead-level referral markers and commission endpoints.
7. [ ] If building a merged Leads list, included only **self-serve** `UserInvite` rows (`author` null) and planned **dedup** + **author visibility** (serializer or backend) as needed.
