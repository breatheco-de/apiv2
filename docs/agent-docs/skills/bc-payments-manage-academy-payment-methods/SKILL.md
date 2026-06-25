---
name: bc-payments-manage-academy-payment-methods
description: Use when academy staff need to set main currency and create, list, update, or deprecate checkout payment methods; do NOT use for Stripe credential setup when is_credit_card is true (use bc-payments-configure-academy-stripe first), student card save, or subscription cancel/refund.
requires: []
---

# Skill: Manage Academy Payment Methods

## When to Use

- Use when staff must set the academy's `main_currency` or manage checkout **payment method catalog** entries (credit card, bank transfer, manual, etc.).
- Use Path A when adding a **credit card** option (`is_credit_card: true`) — requires Stripe connected first.
- Use Path B for **bank transfer, manual, or other non-card** methods.
- Do NOT use for Stripe API keys or webhooks — use `bc-payments-configure-academy-stripe` before Path A.
- Do NOT use for saving a student's card on file (`POST /v2/payments/card`) or cancel/refund flows.

## Concepts

- **Payment method catalog** = checkout option shown to customers (`title`, `visibility`, country filters). It is **not** a stored card.
- **`main_currency`** on the academy must be set before payment methods and before many billing flows. Set via admissions `PUT /v1/admissions/academy/me`; list valid codes via public `GET /v1/payments/currency`.
- **Credit card setup order:** (1) `main_currency`, (2) Stripe via `bc-payments-configure-academy-stripe`, (3) catalog entry with `is_credit_card: true` and `currency` matching `main_currency`.
- **Academy-owned vs global:** staff can CRUD only methods owned by their academy (`academy` set). Global methods (`academy=null`) are visible on GET but cannot be updated or deleted by academy staff.
- **`is_crypto`** is not writable via the payment method API — crypto catalog entries are outside this skill's create/update body.
- **Capabilities:** `read_paymentmethod` (list/get), `crud_paymentmethod` (create/update/delete). **`Academy`** header required on all `/academy/` routes.
- **Staff manual deposits** require a non-card, non-crypto payment method.

## Workflow

### Step 0: Set academy main currency (both paths — run first)

1. Call `GET /v1/admissions/academy/me` with `Authorization`, **`Academy: <academy_id>`**, capability `read_my_academy`. Read `main_currency` (`{"code": "USD", "name": "US Dollar"}` or `null`).
2. If `main_currency` is null, call `GET /v1/payments/currency` (public, paginated) and pick a code (e.g. `USD`, `EUR`, `PEN`).
3. Set it: `PUT /v1/admissions/academy/me` with `{"main_currency": "USD"}` (code or numeric id), capability `crud_my_academy`. Confirm with another `GET /v1/admissions/academy/me`.
4. Use that currency code on new `PaymentMethod` rows in Path A or B.

### Path A: Credit card (Stripe required — after Step 0)

1. **Connect Stripe.** Load `bc-payments-configure-academy-stripe` and complete all its steps. Do not continue until `GET /v1/payments/academy/publishable-key?academy=<id>` returns `200` with a non-empty `stripe_publishable_key`.
2. List existing methods: `GET /v1/payments/academy/paymentmethod`. If a non-deprecated credit-card method exists, `PUT` to update it instead of creating a duplicate.
3. Create catalog entry: `POST /v1/payments/academy/paymentmethod` with `is_credit_card: true`, `is_backed: true`, `visibility: PUBLIC`, `currency` matching academy `main_currency`, and appropriate `lang` / `included_country_codes`. Save returned `id`.
4. Verify public checkout: `GET /v1/payments/methods?academy_id=<id>&country_code=<cc>` includes the new method.

### Path B: Bank transfer / manual / non-card (Step 0 only — no Stripe)

1. List methods: `GET /v1/payments/academy/paymentmethod` (paginated; optional filters `visibility`, `currency_code`, `lang`, `deprecated`).
2. Create method: `POST /v1/payments/academy/paymentmethod` with `is_credit_card: false`, `currency` matching `main_currency` (or intentional regional currency), detailed `description`, optional `included_country_codes`. Save returned `id`.
3. Verify public checkout: `GET /v1/payments/methods?academy_id=<id>&country_code=<cc>` (no auth, paginated).

### Shared maintenance (both paths)

4. Update: `PUT /v1/payments/academy/paymentmethod/<paymentmethod_id>` (partial OK; academy-owned only).
5. Retire: prefer `PUT` with `deprecated: true` and `visibility: HIDDEN` over `DELETE`.

## Endpoints

### Read academy (main currency)

- **Method / path:** `GET /v1/admissions/academy/me`
- **Headers:** `Authorization`, **`Academy: <academy_id>`**, optional `Accept-Language: en|es`
- **Permissions:** `read_my_academy`
- **Pagination:** N/A (single academy object)

**Response `200` (subset):**

```json
{
  "id": 55,
  "slug": "miami",
  "name": "Miami Academy",
  "main_currency": {
    "code": "USD",
    "name": "US Dollar"
  }
}
```

`main_currency` may be `null` if Step 0 is still required.

### Set academy main currency

- **Method / path:** `PUT /v1/admissions/academy/me`
- **Headers:** `Authorization`, **`Academy: <academy_id>`**, optional `Accept-Language: en|es`
- **Permissions:** `crud_my_academy`
- **Pagination:** N/A

**Request:**

```json
{
  "main_currency": "USD"
}
```

**Response `200`:** full academy object (same shape as GET); `main_currency` reflects the saved currency.

### List currencies (public)

- **Method / path:** `GET /v1/payments/currency`
- **Headers:** none required
- **Pagination:** yes — `limit`, `offset` (and optional `code`, `name` filters)

**Response `200` (subset):**

```json
[
  {
    "code": "USD",
    "name": "US Dollar",
    "countries": []
  },
  {
    "code": "EUR",
    "name": "Euro",
    "countries": []
  }
]
```

### List payment methods (staff)

- **Method / path:** `GET /v1/payments/academy/paymentmethod`
- **Headers:** `Authorization`, **`Academy: <academy_id>`**, optional `Accept-Language: en|es`
- **Permissions:** `read_paymentmethod`
- **Pagination:** yes — `limit`, `offset`; optional query `visibility`, `currency_code`, `lang`, `deprecated`
- **Scope:** returns academy-owned methods **and** global methods (`academy=null`)

**Response `200` (subset):**

```json
[
  {
    "id": 1,
    "title": "Credit Card",
    "description": "Pay securely with Visa, Mastercard, or American Express",
    "is_backed": true,
    "lang": "en-US",
    "is_credit_card": true,
    "is_crypto": false,
    "third_party_link": null,
    "academy": {
      "id": 55,
      "name": "Miami Academy",
      "slug": "miami"
    },
    "currency": {
      "code": "USD",
      "name": "US Dollar"
    },
    "included_country_codes": "US,CA,MX",
    "visibility": "PUBLIC",
    "deprecated": false
  }
]
```

### Get single payment method (staff)

- **Method / path:** `GET /v1/payments/academy/paymentmethod/<paymentmethod_id>`
- **Headers:** `Authorization`, **`Academy: <academy_id>`**
- **Permissions:** `read_paymentmethod`
- **Pagination:** N/A

**Response `200`:** same object shape as one list item above.

### Create payment method (staff)

- **Method / path:** `POST /v1/payments/academy/paymentmethod`
- **Headers:** `Authorization`, **`Academy: <academy_id>`**, optional `Accept-Language: en|es`
- **Permissions:** `crud_paymentmethod`
- **Note:** `academy` is set from the `Academy` header automatically

**Request — credit card (Path A):**

```json
{
  "title": "Credit Card",
  "description": "Pay securely with Visa, Mastercard, American Express, or Discover",
  "is_backed": true,
  "is_credit_card": true,
  "currency": "USD",
  "lang": "en-US",
  "included_country_codes": "US,CA,MX,BR",
  "visibility": "PUBLIC",
  "deprecated": false
}
```

**Request — bank transfer (Path B):**

```json
{
  "title": "Bank Transfer - BCP",
  "description": "Wire transfer to Banco de Crédito del Perú. Account: 193-123456789-0-00. CCI: 002-193-123456789000-00",
  "is_backed": true,
  "is_credit_card": false,
  "currency": "PEN",
  "lang": "es-PE",
  "included_country_codes": "PE",
  "visibility": "PUBLIC",
  "deprecated": false
}
```

**Response `201`:**

```json
{
  "id": 123,
  "title": "Bank Transfer - BCP",
  "description": "Wire transfer to Banco de Crédito del Perú. Account: 193-123456789-0-00. CCI: 002-193-123456789000-00",
  "is_backed": true,
  "lang": "es-PE",
  "is_credit_card": false,
  "currency": "PEN",
  "academy": 55,
  "included_country_codes": "PE",
  "visibility": "PUBLIC",
  "deprecated": false
}
```

Required on create: `title`, `description`, `lang`.

### Update payment method (staff)

- **Method / path:** `PUT /v1/payments/academy/paymentmethod/<paymentmethod_id>`
- **Headers:** `Authorization`, **`Academy: <academy_id>`**
- **Permissions:** `crud_paymentmethod`
- **Restriction:** only academy-owned methods; global methods return 404

**Request (deprecate example):**

```json
{
  "deprecated": true,
  "visibility": "HIDDEN"
}
```

**Response `200`:** updated payment method object (create response shape).

### Delete payment method (staff)

- **Method / path:** `DELETE /v1/payments/academy/paymentmethod/<paymentmethod_id>`
- **Headers:** `Authorization`, **`Academy: <academy_id>`**
- **Permissions:** `crud_paymentmethod`
- **Response:** `204 No Content`

### List payment methods (public checkout)

- **Method / path:** `GET /v1/payments/methods?academy_id=<academy_id>&country_code=<cc>`
- **Headers:** none required
- **Pagination:** yes — `limit`, `offset`; optional `currency_code`, `lang`, `visibility`
- **Purpose:** checkout UI for unauthenticated or student users

**Response `200`:** same item shape as staff list (subset of fields).

## Edge Cases

- **`main_currency` null:** complete Step 0 before creating payment methods; staff deposit flows may return `currency-not-found` if neither payment method nor academy has currency.
- **Invalid currency on academy PUT:** `400` slug `currency-not-found` — pick a code from `GET /v1/payments/currency`.
- **Credit card without Stripe:** `GET /v1/payments/academy/publishable-key` returns `404` — load `bc-payments-configure-academy-stripe` before `POST` with `is_credit_card: true`.
- **Skip Stripe for credit card:** do not create the catalog entry; charges and checkout will fail without academy Stripe keys.
- **Update/delete global method:** `404` `payment-method-not-found` — only academy-owned rows are mutable.
- **Empty public list after create:** check `visibility`, `deprecated`, `included_country_codes`, and `country_code` / `currency_code` filters on `GET /v1/payments/methods`.
- **`is_crypto`:** not accepted on create/update via this API.

## Checklist

1. `main_currency` set and confirmed on academy (Step 0).
2. Path A only: publishable-key GET passed **before** credit-card `POST`.
3. Payment method created with expected `is_credit_card` flag and matching `currency`.
4. Method appears on staff list and on public `GET /v1/payments/methods` with appropriate filters.
5. If retiring a method, `deprecated` + `HIDDEN` applied (or delete if appropriate).

## Next steps

Payment setup is the **billing rail** layer. To sell at checkout, staff still need catalog layers. Recommend this **skill order** — do not skip ahead (plans depend on services; courses depend on plans):

1. **Services** — load `bc-payments-manage-services` when available. Defines what the academy sells; must exist before plans.
2. **Plans** — load [`bc-payments-manage-plans`](../bc-payments-manage-plans/SKILL.md). Bundles services into sellable packages priced in `main_currency`.
3. **Courses** — load `bc-marketing-create-or-clone-course`. Marketing catalog linked to the plan from step 2.

If the services skill is not published yet, staff may still create service items via `POST /v1/payments/academy/serviceitem` as documented in `bc-payments-manage-plans` Path A Phase 2.

**Closing message for staff:** "Payment setup is complete. Next steps: manage academy services, then plans (`bc-payments-manage-plans`), then create a marketing course — load the skills above in that order."
