# Payment Report API Documentation

Guide to API endpoints and activity data used for payment reports, sales dashboards, and sales activity.

## Overview

Payment and sales reporting uses:

- **Payments API** – Invoices, subscriptions, plan financing, bags (completed and recurring sales).
- **Commission API** – Creator/influencer payments and commission reports (payouts, not customer sales).
- **Activity API (V2/V3)** – Sales-related activity events (e.g. bag created, checkout completed).

**Base URLs:**

- Payments: `/v1/payments/` (academy-scoped paths use `Academy` header)
- Commission: `/v1/commission/`
- Activity: `/v2/activity/`, `/v3/activity/`

---

## Authentication & Headers

All requests require:

```http
Authorization: Token {your-token}
```

Academy-scoped endpoints (payments academy/*, activity academy/*) also require:

```http
Academy: {academy_id}
```

Commission URLs include the academy in the path: `academy/<academy_id>/...`.

---

## Payments API – Sales Data

Base: **`/v1/payments/`**

### Invoices (completed sales)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `academy/invoice` | List invoices. Sorted by `-id` by default, paginated. |
| GET | `academy/invoice/<invoice_id>` | Single invoice. |
| POST | `academy/invoice/<invoice_id>/refund` | Refund (for activity/history). |

**Query parameters (list):**

- `status` – Comma-separated (e.g. `FULFILLED`, `PENDING`, `REFUNDED`).
- **`date_start`** – Optional. ISO 8601 datetime (or date). Filter by `paid_at >= date_start`.
- **`date_end`** – Optional. ISO 8601 datetime (or date). Filter by `paid_at <= date_end`.
- Pagination: `limit`, `offset` (via API view extensions).

**Capability:** `read_invoice` (list/detail), `crud_invoice` (refund).

### Subscriptions (recurring sales)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `academy/subscription` | List subscriptions. Sorted `-id`, paginated, cached. |
| GET | `academy/subscription/<subscription_id>` | Single subscription. |
| PUT | `academy/subscription/<subscription_id>` | Update subscription. |

**Query parameters (list):**

- `status`, `users`, `plan`, `service`, `invoice` (comma-separated).
- **`date_start`** – Optional. Filter by `paid_at >= date_start`. Bypasses cache when used.
- **`date_end`** – Optional. Filter by `paid_at <= date_end`. Bypasses cache when used.

**Capability:** `read_subscription`.

### Plan financing (installments)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `academy/planfinancing` | List plan financings. Sorted `-id`, paginated, cached. |
| GET | `academy/planfinancing/<financing_id>` | Single plan financing. |
| PUT | `academy/planfinancing/<financing_id>` | Update plan financing. |

**Query parameters (list):**

- `users`, `plan`, `invoice` (comma-separated).
- **`date_start`** – Optional. Filter by `created_at >= date_start`. Bypasses cache when used.
- **`date_end`** – Optional. Filter by `created_at <= date_end`. Bypasses cache when used.

### Bags (carts / orders)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `academy/bag/<bag_id>` | Single bag by ID. No list endpoint. |

**Capability:** `read_subscription`.

### Coupons (search & manage)

See [COUPONS.md](COUPONS.md) for full details. Summary: `GET/POST academy/coupon`, `GET/PUT/DELETE academy/coupon/<slug>`, `GET academy/coupon/<slug>/exists`, `GET coupon?coupons=...&plan=...`, `GET me/coupon`, `GET/PUT me/user/coupons`, `PUT bag/<id>/coupon`.

---

## Commission API – Payouts & Reports

Base: **`/v1/commission/`**. Academy in path: `academy/<academy_id>/...`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `academy/<academy_id>/report` | Commission report. Query: `creator_id`, `month` (YYYY-MM), `preview`, `async`, `include_plans`, `exclude_plans`. |
| GET | `academy/<academy_id>/report.<extension>` | Export report (e.g. CSV). |
| GET | `academy/<academy_id>/payments` | List creator payments. |
| GET | `academy/<academy_id>/payments/<payment_id>` | Single payment. |
| GET | `academy/<academy_id>/commissions` | List commissions. |
| GET | `academy/<academy_id>/usage-commissions` | Usage commissions. |
| GET | `academy/<academy_id>/referral-commissions` | Referral commissions. |
| GET | `academy/<academy_id>/referral-commissions/<commission_id>` | Single referral commission. |

**Capability:** `crud_commission` (report).

---

## Activity API – Sales Activity Events

Sales-related activity kinds: `bag_created`, `checkout_completed` (for Subscription, PlanFinancing, Invoice). Queried via **V2** or **V3** activity endpoints (BigQuery).

### V3 Activity – `/v3/activity/` (recommended for date range)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `kinds` | All activity kinds by `related_type`. |
| GET | `academy/activity` | List activity. Query: `kind` (comma-separated), `user_id`, **`date_start`**, **`date_end`**, `cohort_id`, `limit`, `page`. |

**Example – sales activity in date range:**  
`GET /v3/activity/academy/activity?kind=bag_created,checkout_completed&date_start=2025-02-01&date_end=2025-02-09&limit=50`

**Capability:** `read_activity`.

---

## Timeframe (start / end datetimes)

| Area | Timeframe support | Notes |
|------|--------------------|--------|
| **Payments – invoices** | **Yes** | `date_start`, `date_end` filter by **`paid_at`**. |
| **Payments – subscriptions** | **Yes** | `date_start`, `date_end` filter by **`paid_at`**. Cache bypassed when either param is present. |
| **Payments – plan financing** | **Yes** | `date_start`, `date_end` filter by **`created_at`**. Cache bypassed when either param is present. |
| **Activity V3** | Yes | `date_start`, `date_end` on `academy/activity`. |
| **Commission report** | By month only | `month` (YYYY-MM), not arbitrary start/end. |

**Format:** ISO 8601 datetime or date (e.g. `2025-02-01T00:00:00Z` or `2025-02-01`). Invalid values return 400 with slug `invalid-datetime`.

---

## Pagination & sort

- **Payments** list views: default sort `-id`, query params `limit`, `offset`.
- **Activity** V2/V3: `limit`, `page`.

---

## Summary for dashboards

| Goal | Primary endpoints |
|------|-------------------|
| Latest completed sales | `GET /v1/payments/academy/invoice?limit=20&status=FULFILLED` |
| Revenue in timeframe | `GET /v1/payments/academy/invoice?date_start=...&date_end=...` (and/or subscription / planfinancing) |
| Recurring / installments | `GET /v1/payments/academy/subscription`, `GET /v1/payments/academy/planfinancing` |
| Sales activity feed | `GET /v3/activity/academy/activity?kind=bag_created,checkout_completed&limit=20` |
| Commission / payouts | `GET /v1/commission/academy/<academy_id>/payments`, `.../report` |
| Coupons | `GET /v1/payments/academy/coupon?like=...`, CRUD `academy/coupon`, `academy/coupon/<slug>/exists` |

---

## Related docs

- [COUPONS.md](COUPONS.md) – Coupon API, fields, validation, and examples.
- [BC_INVOICE.md](BC_INVOICE.md) – Invoice handling.
- [BC_REFUNDS.md](BC_REFUNDS.md) – Refunds.
- [BC_CHECKOUT.md](BC_CHECKOUT.md) – Checkout flow.
- [Student_Activity.md](Student_Activity.md) – Full activity API.
