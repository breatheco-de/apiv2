---
name: bc-payments-read-active-users-bills
description: Use when academy staff need to read daily active-users billing snapshots or the month high-water-mark invoice; do NOT use for student checkout, AcademyService pricing, Stripe charges, or provisioning/GitHub bills.
requires:
  - bc-authenticate-staff-authentication
---

# Skill: Read Active Users Bills

## When to Use

- Use when staff need the **month invoice** (peak-day charge and cohort line items) for platform active-user billing.
- Use when staff need to list or inspect **daily** active-users bill snapshots for an academy.
- Do NOT use for student plan checkout, `AcademyService` prices, subscription cancel/refund, or provisioning (`ProvisioningBill`) GitHub consumption bills.
- Do NOT use to charge Stripe or POST-generate bills from the academy API (generation is ops/cron).

## Concepts

- **Active users billing** = 4Geeks charging the academy for enrolled students (internal), not the academy charging learners.
- **Daily bill** = one snapshot per academy per calendar day (`billing_date`): who was billable that day, with one **item per cohort** after dedupe.
- **Month invoice** = high-water mark: `amount = peak day's unique_user_count × that day's price_per_user`. Month response **`items`** are the **peak day's cohort lines**, not one row per date. Optional **`days`** is audit only.
- **Capability:** `read_active_users_bill`. All `/academy/` routes require header **`Academy: <academy_id>`**. Send **`Accept-Language: en|es`** for translated errors.
- **Who counts as billable (generation rules):** student `CohortUser` with `ACTIVE` or `NOT_COMPLETING`, not `LATE`, cohort not `ENDED`/`DELETED`, student `ProfileAcademy` (by user or email), no non-student ProfileAcademy role at that academy, slug not matching exclude patterns.
- **Config** lives on academy payment settings field **`internal_billing`** (Django admin PrettyJSON). `PUT /v1/payments/academy/paymentsettings` does **not** accept `internal_billing` today (Stripe/Coinbase only — see `bc-payments-configure-academy-stripe` for those keys only).
- Daily rows appear after ops runs generation (e.g. management command / scheduled job). If month has no peak, do not invent a charge.

### `internal_billing` JSON (admin)

Set on **Academy payment settings → `internal_billing`**. Example:

```json
{
  "active_users_billing": {
    "enabled": true,
    "price_per_user": 4.36,
    "currency": "USD",
    "exclude_cohort_slug_patterns": [
      ".*land-a-job-in-tech.*",
      ".*building-your-tech-profile.*",
      ".*-general.*",
      ".*pt-content.*",
      ".*career-support-"
    ]
  }
}
```

| Field | Meaning |
| --- | --- |
| `enabled` | Must be `true` or daily generation skips the academy |
| `price_per_user` | Required when enabled; snapshotted onto each daily bill |
| `currency` | Optional; default `USD` |
| `exclude_cohort_slug_patterns` | **Regex** list (`re.search` on `cohort.slug`). Use `.*foo.*`, not glob `*foo*`. Invalid patterns are skipped |

## Workflow

1. Authenticate staff per [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md). Confirm `read_active_users_bill` and send **`Academy`**.
2. Confirm billing config: `internal_billing.active_users_billing.enabled` is `true` and `price_per_user` is set (admin). Use the JSON example above if configuring patterns.
3. For an invoice UI, call month summary: `GET /v1/payments/academy/active-users-bill/month?year=<Y>&month=<M>`. Use `amount`, `price_per_user`, `unique_user_count`, `peak_date`, and cohort **`items`**.
4. Optionally list daily bills: `GET /v1/payments/academy/active-users-bill?year=<Y>&month=<M>` (paginated), or open detail with `peak_bill_id`: `GET /v1/payments/academy/active-users-bill/<id>`.
5. If `peak_date` / `peak_bill_id` is null or `items` is empty: report that no usable daily snapshots exist (disabled config, exclusions, or generation not run). Do not fabricate amounts.

## Endpoints

### List daily bills

- **Method / path:** `GET /v1/payments/academy/active-users-bill`
- **Headers:** `Authorization: Token <token>`, **`Academy: <academy_id>`**, optional `Accept-Language: en|es`
- **Permissions:** `read_active_users_bill`
- **Query:** optional `year`, `month`, `status` (comma-separated, e.g. `DUE,PAID`), `sort` (default `-billing_date`)
- **Pagination:** yes (standard list pagination)

**Response `200` (array of daily bills; shape of one element):**

```json
{
  "id": 128,
  "academy": {
    "id": 4,
    "name": "Downtown Miami",
    "slug": "downtown-miami"
  },
  "billing_date": "2026-08-14",
  "title": "2026-08-14 active users",
  "status": "DUE",
  "currency_code": "USD",
  "price_per_user": "4.36",
  "unique_user_count": 42,
  "duplicate_user_count": 7,
  "total_amount": "183.12",
  "notes": "7 duplicate enrollment(s) disregarded. 2 cohort(s) skipped by exclude_cohort_slug_patterns: land-a-job-in-tech-miami, building-your-tech-profile-spain",
  "created_at": "2026-08-14T06:00:00Z"
}
```

### Daily bill detail

- **Method / path:** `GET /v1/payments/academy/active-users-bill/<bill_id>`
- **Headers:** `Authorization: Token <token>`, **`Academy: <academy_id>`**, optional `Accept-Language`
- **Permissions:** `read_active_users_bill`
- **Pagination:** N/A

**Response `200`:**

```json
{
  "id": 128,
  "academy": {
    "id": 4,
    "name": "Downtown Miami",
    "slug": "downtown-miami"
  },
  "billing_date": "2026-08-14",
  "title": "2026-08-14 active users",
  "status": "DUE",
  "currency_code": "USD",
  "price_per_user": "4.36",
  "unique_user_count": 42,
  "duplicate_user_count": 7,
  "total_amount": "183.12",
  "notes": "7 duplicate enrollment(s) disregarded",
  "created_at": "2026-08-14T06:00:00Z",
  "items": [
    {
      "id": 901,
      "cohort": {
        "id": 55,
        "slug": "web-dev-pt-01",
        "name": "Web Development Part-Time 01"
      },
      "user_count": 25,
      "amount": "109.00",
      "user_ids": [101, 102, 103],
      "notes": ""
    },
    {
      "id": 902,
      "cohort": {
        "id": 56,
        "slug": "data-science-ft-02",
        "name": "Data Science Full-Time 02"
      },
      "user_count": 17,
      "amount": "74.12",
      "user_ids": [201, 202],
      "notes": "3 student(s) on this cohort already billed on another cohort"
    }
  ]
}
```

### Month invoice (high-water mark)

- **Method / path:** `GET /v1/payments/academy/active-users-bill/month?year=<Y>&month=<M>`
- **Headers:** `Authorization: Token <token>`, **`Academy: <academy_id>`**, optional `Accept-Language`
- **Permissions:** `read_active_users_bill`
- **Query:** `year` and `month` required (integers)
- **Pagination:** N/A (single invoice object)
- **Note:** `items` = peak day's cohort lines; `days` = optional audit of daily counts (not invoice lines). Days with status `IGNORED` or `ERROR` are excluded from peak selection.

**Response `200`:**

```json
{
  "academy": {
    "id": 4,
    "slug": "downtown-miami",
    "name": "Downtown Miami"
  },
  "year": 2026,
  "month": 8,
  "peak_date": "2026-08-14",
  "peak_bill_id": 128,
  "unique_user_count": 42,
  "price_per_user": "4.36",
  "currency_code": "USD",
  "amount": "183.12",
  "notes": "Month charge based on peak day 2026-08-14. 7 duplicate enrollment(s) disregarded",
  "items": [
    {
      "id": 901,
      "cohort": {
        "id": 55,
        "slug": "web-dev-pt-01",
        "name": "Web Development Part-Time 01"
      },
      "user_count": 25,
      "amount": "109.00",
      "user_ids": [101, 102, 103],
      "notes": ""
    },
    {
      "id": 902,
      "cohort": {
        "id": 56,
        "slug": "data-science-ft-02",
        "name": "Data Science Full-Time 02"
      },
      "user_count": 17,
      "amount": "74.12",
      "user_ids": [201, 202],
      "notes": "3 student(s) on this cohort already billed on another cohort"
    }
  ],
  "days": [
    {
      "id": 115,
      "billing_date": "2026-08-01",
      "unique_user_count": 38,
      "status": "DUE"
    },
    {
      "id": 128,
      "billing_date": "2026-08-14",
      "unique_user_count": 42,
      "status": "DUE"
    }
  ]
}
```

Empty month (no daily bills):

```json
{
  "academy": { "id": 4, "slug": "downtown-miami", "name": "Downtown Miami" },
  "year": 2026,
  "month": 8,
  "peak_date": null,
  "peak_bill_id": null,
  "unique_user_count": 0,
  "price_per_user": "0.00",
  "currency_code": "USD",
  "amount": "0.00",
  "notes": "No daily active users bills found for this month.",
  "items": [],
  "days": []
}
```

## Edge Cases

- **403 missing capability / Academy header:** Load staff auth skill; ensure `read_active_users_bill` and `Academy` header.
- **404 on detail:** Bill id belongs to another academy or does not exist — do not retry other academies without permission.
- **400 on month:** Missing/invalid `year` or `month` — fix query params.
- **Empty month / null peak:** Billing disabled, exclude patterns removed everyone, or daily job not run — tell the user; do not invent charges.
- **Glob patterns in config (`*foo*`):** Do not use; generation expects regex (`.*foo.*`). Misconfigured patterns are skipped or fail to match.
- **Month `items` vs `days`:** Never treat `days` as invoice line items; cohort breakdown is only in `items` (peak day).

## Checklist

1. Staff token and **`Academy`** header present; capability `read_active_users_bill` confirmed.
2. `internal_billing.active_users_billing` shape understood (enabled, price, regex excludes) if diagnosing empty data.
3. Month invoice fetched with `year` and `month`; `amount` and peak-day cohort `items` used for the invoice UI.
4. Optional daily list/detail used only for audit or drill-down via `peak_bill_id`.
5. Empty peak / empty items handled with a clear message — no fabricated totals.
