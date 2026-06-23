---
name: bc-payments-manage-plans
description: Use when academy staff need to list, create, update, or retire payment plans, configure resource sets, consumables, financing, country pricing, or plan upgrade offers; do NOT use for payment method setup, Stripe credentials, subscription cancel/refund, or marketing course creation.
requires:
  - bc-payments-manage-academy-payment-methods
---

# Skill: Manage Academy Payment Plans

## When to Use

- Use when staff must create or update **sellable plans** (bootcamp financing, subscriptions, onboarding packages).
- Use Path A for end-to-end plan setup (cohort/event/mentorship sets, consumables, pricing, financing, activation).
- Use Path B to configure **plan upgrade offers** (original plan → suggested plan).
- Use Path C to unlist, discontinue, or delete plans and related offers.
- Do NOT use for `main_currency` or checkout payment methods — use `bc-payments-manage-academy-payment-methods`.
- Do NOT use for Stripe keys, subscription cancel/refund, or marketing course pages.

## Concepts

- **Resource sets** — bundles sold through the plan: `cohort_set`, `mentorship_service_set`, `event_type_set` (FK ids on the plan).
- **Consumables** — quotas students spend (`service_items` on the plan). `how_many: -1` = unlimited.
- **Pricing** — `price_per_month`, `price_per_quarter`, `price_per_half`, `price_per_year` in plan `currency`.
- **Country adjustments** — `pricing_ratio_exceptions` on the plan (and on financing options). Keys are lowercase country codes. Each entry may use `ratio`, direct `price_per_*` overrides, and optional `currency`.
- **Financing** — installment options (`financing_options` ids) when `is_renewable: false`.
- **Billing model** — `is_renewable: true` → subscription; `false` → plan financing (requires `time_of_life` + `time_of_life_unit`).
- **Capabilities** — plan CRUD: `read_subscription` / `crud_subscription`; sets + service-item link: `crud_plan`. **`Academy` header** required on all `/academy/` routes.

## Workflow

### Phase 0 — Prerequisites

1. Load `bc-payments-manage-academy-payment-methods` and complete Step 0 (`main_currency` set).
2. Configure checkout payment methods if customers will pay online (same skill).

### Path A — Create and activate a sellable plan

Order matters: create sets and service items **before** referencing them on the plan.

**Phase 1 — Resource sets** (`crud_plan`)

1. Cohort set (if selling cohort access): `POST /v1/payments/academy/cohortset` → save `id`.
2. Add cohorts: `PUT /v1/payments/academy/cohortset/{slug}/cohort?id=123,456` — pass cohort ids or slugs as **query params** (`id` or `slug`, comma-separated).
3. Mentorship set (optional): `POST /v1/payments/academy/mentorshipserviceset` with `slug` and `mentorship_service_ids`.
4. Event type set (optional): `POST /v1/payments/academy/eventtypeset` with `slug` and `event_type_ids`.

**Phase 2 — Consumables** (`crud_service` to create, `crud_plan` to link)

1. Create service items: `POST /v1/payments/academy/serviceitem` per consumable (`service` id, `how_many`, optional `is_renewable`).
2. Or list existing: `GET /v1/payments/serviceitem` (paginated).

**Phase 3 — Financing options** (optional, bootcamps)

1. `POST /v1/payments/academy/financingoption` with `monthly_price`, `how_many_months`, `currency`, optional `pricing_ratio_exceptions`.
2. Save returned ids for Phase 4.

**Phase 4 — Create plan** (`crud_subscription`)

`POST /v1/payments/academy/plan` with `status: DRAFT`, set FKs from Phase 1, pricing, `pricing_ratio_exceptions`, and `financing_options` ids.

**Phase 5 — Link consumables** (`crud_plan`)

`POST /v1/payments/academy/plan/serviceitem` with `plan` (slug or id) and `service_item` (id or array).

**Phase 6 — Activate and verify**

1. `PUT /v1/payments/academy/plan/{slug}` → `{"status": "ACTIVE"}`.
2. Staff: `GET /v1/payments/academy/plan/{slug}?country_code=ES`.
3. Public: `GET /v1/payments/plan/{slug}?country_code=ES`.

**Phase 7 — Marketing**

Load `bc-marketing-create-or-clone-course` with `plan_slug` from Phase 4.

### Path B — Configure upgrade / upsell offer

1. `GET /v1/payments/academy/plan` — pick `original_plan` (academy-owned) and `suggested_plan`.
2. `POST /v1/payments/academy/planoffer` with both plans and `translations[]` (at least one).
3. Verify: `GET /v1/payments/planoffer?original_plan={slug}` (public, no auth).

### Path C — Retire or discontinue

1. `PUT` plan `status: UNLISTED` or `DISCONTINUED` (`discontinued_reason` required for `DISCONTINUED`).
2. Or `DELETE /v1/payments/academy/plan/{slug}` (soft delete → `status: DELETED`).
3. `PUT` plan offer with past `expires_at`, or `DELETE /v1/payments/academy/planoffer/{id}`.

## Endpoints

### Create cohort set

- **POST** `/v1/payments/academy/cohortset`
- **Headers:** `Authorization`, **`Academy: <academy_id>`**
- **Permissions:** `crud_plan`

**Request:**

```json
{
  "slug": "full-stack-bootcamp-2025"
}
```

**Response `201`:** `{ "id": 5, "slug": "full-stack-bootcamp-2025", "cohorts": [] }`

### Add cohorts to cohort set

- **PUT** `/v1/payments/academy/cohortset/{cohort_set_slug}/cohort?id=123,456`
- **Query params:** `id` (comma-separated cohort ids) **or** `slug` (comma-separated cohort slugs)
- **Permissions:** `crud_plan`

**Response `200` or `201`:** `{ "status": "ok" }`

### Create mentorship service set

- **POST** `/v1/payments/academy/mentorshipserviceset`
- **Permissions:** `crud_plan`

**Request:**

```json
{
  "slug": "premium-mentorship",
  "mentorship_service_ids": [1, 2]
}
```

### Create event type set

- **POST** `/v1/payments/academy/eventtypeset`
- **Permissions:** `crud_plan`

**Request:**

```json
{
  "slug": "workshops-2025",
  "event_type_ids": [3, 4]
}
```

### Create service item (consumable)

- **POST** `/v1/payments/academy/serviceitem`
- **Permissions:** `crud_service`

**Request:**

```json
{
  "service": 12,
  "how_many": -1,
  "sort_priority": 1
}
```

**Response `201`:** includes `id` — use in plan serviceitem link.

### Create financing option

- **POST** `/v1/payments/academy/financingoption`
- **Permissions:** `crud_subscription`

**Request:**

```json
{
  "monthly_price": 299.0,
  "how_many_months": 12,
  "currency": "USD",
  "pricing_ratio_exceptions": {
    "mx": { "ratio": 0.7 },
    "es": { "ratio": 0.85 }
  }
}
```

### Create plan

- **POST** `/v1/payments/academy/plan`
- **Permissions:** `crud_subscription`
- **Pagination:** N/A

**Request:**

```json
{
  "slug": "web-dev-bootcamp-2025",
  "title": "Web Development Bootcamp 2025",
  "currency": "USD",
  "status": "DRAFT",
  "is_renewable": false,
  "is_onboarding": true,
  "time_of_life": 6,
  "time_of_life_unit": "MONTH",
  "trial_duration": 0,
  "trial_duration_unit": "DAY",
  "price_per_month": 299.0,
  "price_per_quarter": 799.0,
  "price_per_half": 1499.0,
  "price_per_year": 2499.0,
  "pricing_ratio_exceptions": {
    "es": { "ratio": 0.85 },
    "mx": { "ratio": 0.7 },
    "pe": { "price_per_month": 199.0, "currency": "USD" }
  },
  "cohort_set": 5,
  "mentorship_service_set": 2,
  "event_type_set": 3,
  "financing_options": [10, 11],
  "consumption_strategy": "PER_SEAT"
}
```

`owner` is set from the `Academy` header. Non-renewable plans require `time_of_life` + `time_of_life_unit`.

### Link service items to plan

- **POST** `/v1/payments/academy/plan/serviceitem`
- **Permissions:** `crud_plan`

**Request:**

```json
{
  "plan": "web-dev-bootcamp-2025",
  "service_item": [456, 52, 93]
}
```

### Unlink service item

- **DELETE** `/v1/payments/academy/plan/{plan_id}/serviceitem/{service_item_id}`
- **Permissions:** `crud_plan`

### List / get plans (staff)

- **GET** `/v1/payments/academy/plan` (paginated)
- **GET** `/v1/payments/academy/plan/{id_or_slug}`
- **Permissions:** `read_subscription`
- **Query:** `country_code`, `like`, `cohort`, `status`, etc.

Use `country_code` to verify regional pricing adjustments on GET.

### Update / activate plan

- **PUT** `/v1/payments/academy/plan/{id_or_slug}` (partial OK)
- **Permissions:** `crud_subscription`

**Request (activate):**

```json
{
  "status": "ACTIVE"
}
```

**Request (attach financing):**

```json
{
  "financing_options": [10, 11]
}
```

### Create plan offer

- **POST** `/v1/payments/academy/planoffer`
- **Permissions:** `crud_subscription`

**Request:**

```json
{
  "original_plan": "basic-bootcamp",
  "suggested_plan": "premium-bootcamp",
  "show_modal": true,
  "expires_at": null,
  "translations": [
    {
      "lang": "en",
      "title": "Upgrade to Premium",
      "description": "Get mentorship and career support.",
      "short_description": "Unlock premium features"
    },
    {
      "lang": "es",
      "title": "Mejora a Premium",
      "description": "Obtén mentoría y apoyo profesional.",
      "short_description": "Desbloquea funciones premium"
    }
  ]
}
```

**Response `201`:** includes `id`, nested `original_plan`, `suggested_plan`, and `translations[]`.

- `original_plan` must be owned by the academy.
- `suggested_plan` may be academy-owned or global (`owner=null`).
- Only one **active** offer per `original_plan` (slug `active-plan-offer-exists` on conflict).

### List / update / delete plan offers (staff)

- **GET** `/v1/payments/academy/planoffer` (paginated; filters `original_plan`, `suggested_plan`)
- **GET** `/v1/payments/academy/planoffer/{id}`
- **PUT** `/v1/payments/academy/planoffer/{id}` — upserts `translations` by `lang`
- **DELETE** `/v1/payments/academy/planoffer/{id}`
- **Permissions:** `read_subscription` (GET), `crud_subscription` (write)

### Verify public catalog

- **GET** `/v1/payments/plan/{slug}?country_code=ES` — no auth
- **GET** `/v1/payments/planoffer?original_plan={slug}` — no auth

## Edge Cases

- **`main_currency` null:** stop and complete `bc-payments-manage-academy-payment-methods` Step 0.
- **Cohort add fails:** cohorts must belong to the same academy; use `id`/`slug` query params on PUT, not JSON body.
- **Plan validation on renewable vs financing:** do not set `time_of_life` on priced renewable subscriptions; financing plans need `time_of_life`.
- **DISCONTINUED plan:** `discontinued_reason` is required (slug `discontinued-reason-required`).
- **Duplicate plan offer:** only one active offer per original plan — update existing offer or expire/delete before creating another.
- **Foreign original plan on offer:** returns `403` slug `plan-not-belonging-to-academy`.
- **Empty translations on POST offer:** returns `400` slug `translations-required`.

## Checklist

1. `main_currency` confirmed.
2. Resource sets created and populated (if needed).
3. Service items created and linked to plan.
4. Financing options created and attached (if bootcamp installments).
5. Plan created in `DRAFT`, then `ACTIVE`.
6. Country pricing verified with `?country_code=` on staff and public GET.
7. Plan offer created (Path B) and verified on public `GET /planoffer` (if upsell configured).
8. Marketing course linked via `bc-marketing-create-or-clone-course` (Path A Phase 7).

## Next steps

After plans are active, load **`bc-marketing-create-or-clone-course`** to publish the course catalog entry with `plan_slug`.

For checkout issues, confirm payment methods via **`bc-payments-manage-academy-payment-methods`**.
