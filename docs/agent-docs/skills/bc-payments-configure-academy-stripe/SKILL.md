---
name: bc-payments-configure-academy-stripe
description: Use when academy staff need to configure Stripe API keys and webhook secret for their academy; do NOT use for payment method catalog CRUD, subscription cancel/refund, or student card onboarding.
requires: []
---

# Skill: Configure Academy Stripe

## When to Use

- Use when staff must connect the academy's own Stripe account (secret key, publishable key, webhook signing secret).
- Use before creating a credit-card `PaymentMethod` (`is_credit_card: true`) or before card-based checkout can charge against academy-specific Stripe credentials.
- Do NOT use for listing or creating payment methods — use `bc-payments-manage-academy-payment-methods`.
- Do NOT use for canceling subscriptions, refunds, or saving a student's card (`/v2/payments/card`).

## Concepts

- **Academy payment settings** store per-academy Stripe credentials. A `PUT` auto-creates the row if it does not exist yet.
- **Three fields** for a fully independent Stripe setup: `stripe_api_key` (server charges), `stripe_publishable_key` (frontend Stripe.js), `stripe_webhook_secret` (signature verification on incoming events).
- **Capability:** `crud_academy_payment_settings` (typically Academy Admin / `country_manager`). All `/academy/` routes require the **`Academy`** header with the academy id.
- **Publishable key** is exposed on a separate public GET for checkout UIs; secret keys are only written via `PUT` and echoed in that response.
- **Webhook URL** BreatheCode receives: `POST /v1/monitoring/stripe/webhook`. Register this URL in the Stripe Dashboard (external step).
- **Fallback:** if academy keys are empty, the platform may use global Stripe env vars — reseller academies are expected to configure all three fields.

## Workflow

1. Authenticate staff with `crud_academy_payment_settings`. Send `Authorization` and **`Academy: <academy_id>`**.
2. Save Stripe keys via `PUT /v1/payments/academy/paymentsettings` with `stripe_api_key` and `stripe_publishable_key` (partial body OK).
3. In Stripe Dashboard, create a webhook endpoint pointing to `https://<api-host>/v1/monitoring/stripe/webhook` with payment lifecycle events (charges and payment intents at minimum).
4. Copy the signing secret (`whsec_...`) from Stripe and `PUT` it as `stripe_webhook_secret` on the same endpoint.
5. Verify publishable key exposure: `GET /v1/payments/academy/publishable-key?academy=<id>` must return `200` with a non-empty `stripe_publishable_key`.
6. If staff also need a credit-card checkout option, hand off to `bc-payments-manage-academy-payment-methods` (Path A) — only after Step 5 passes. Do not `POST` `is_credit_card: true` payment methods before publishable-key verification succeeds.

## Endpoints

### Update academy Stripe credentials

- **Method / path:** `PUT /v1/payments/academy/paymentsettings`
- **Headers:** `Authorization: Token <token>`, **`Academy: <academy_id>`**, optional `Accept-Language: en|es`
- **Permissions:** `crud_academy_payment_settings`
- **Pagination:** N/A (single resource update; no GET list on this route)
- **Body:** all fields optional; only send fields to change

**Request example (partial — Stripe only):**

```json
{
  "stripe_api_key": "sk_live_51PxAbCexampleSecretKey",
  "stripe_publishable_key": "pk_live_51PxAbCexamplePublishableKey",
  "stripe_webhook_secret": "whsec_exampleSigningSecretFromStripe"
}
```

**Response `200`:**

```json
{
  "stripe_api_key": "sk_live_51PxAbCexampleSecretKey",
  "stripe_webhook_secret": "whsec_exampleSigningSecretFromStripe",
  "stripe_publishable_key": "pk_live_51PxAbCexamplePublishableKey",
  "coinbase_api_key": null,
  "coinbase_webhook_secret": null
}
```

Optional body fields also accepted: `coinbase_api_key`, `coinbase_webhook_secret` (Coinbase Commerce; not required for Stripe-only setup).

### Verify publishable key (public)

- **Method / path:** `GET /v1/payments/academy/publishable-key?academy=<academy_id>`
- **Headers:** none required (`AllowAny`). Query parameter `academy` is required (or use `Academy` header per API convention).
- **Pagination:** N/A

**Response `200`:**

```json
{
  "academy_id": 55,
  "academy_name": "Miami Academy",
  "academy_slug": "miami",
  "stripe_publishable_key": "pk_live_51PxAbCexamplePublishableKey"
}
```

Use this response in Step 5 as the gate before credit-card payment method creation.

### Stripe webhook receiver (register in Stripe Dashboard)

- **Method / path:** `POST /v1/monitoring/stripe/webhook`
- **Configured in:** Stripe Dashboard → Developers → Webhooks (external; not a BreatheCode staff API call)
- **Purpose:** Stripe sends signed events; BreatheCode verifies using `stripe_webhook_secret` (academy-specific when identifiable from the charge, else global fallback)

## Edge Cases

- **403 missing capability or Academy header:** ensure `crud_academy_payment_settings` and `Academy: <id>` on `PUT`.
- **404 on publishable-key GET (`payment-settings-not-found` or `publishable-key-not-configured`):** settings row missing or `stripe_publishable_key` empty — complete Steps 2–4 before handing off to payment methods.
- **No GET for payment settings:** confirm saved values from the `PUT` response body only.
- **Translated errors:** send `Accept-Language: en` or `es` on staff endpoints for localized error messages.
- **Staff asks for credit card checkout but Stripe incomplete:** stop; finish this skill through Step 5, then load `bc-payments-manage-academy-payment-methods` Path A.

## Checklist

1. `stripe_api_key`, `stripe_publishable_key`, and `stripe_webhook_secret` saved via `PUT`.
2. Webhook endpoint registered in Stripe pointing to `/v1/monitoring/stripe/webhook`.
3. `GET /v1/payments/academy/publishable-key?academy=<id>` returns `200` with non-empty `stripe_publishable_key`.
4. If credit-card catalog is needed, hand off to `bc-payments-manage-academy-payment-methods` Path A.

## Next steps

After Stripe is connected, load **`bc-payments-manage-academy-payment-methods`** to set `main_currency` (if needed), create payment method catalog entries, and follow that skill's **Next steps** for services, plans, and courses.
