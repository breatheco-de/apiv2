---
name: bc-monitoring-read-reports-api
description: Use when retrieving monitoring report data for dashboards or frontend report screens via `/v1/monitoring/report*`; do NOT use for creating new report generators or running `generate_report`.
requires: []
---

# Skill: Read Monitoring Reports API

## When to Use

Use this skill when the task is to fetch monitoring report metadata, list rows, row detail, or summary metrics from the monitoring report endpoints.
Use it when frontend code needs filter/sort/pagination behavior for monitoring reports.
If the request is specifically about acquisition report interpretation (funnel tiers, top assets/workshops, attribution patterns), prefer `bc-monitoring-read-report-acquisition`.
Do NOT use this skill to build a new report type or modify report generation logic.
Do NOT use this skill for non-monitoring report domains such as admissions, commission, or marketing report endpoints.

## Concepts

- Monitoring report retrieval is registry-driven: the client calls one route pattern with `report_type` instead of one endpoint per report.
- Access is academy-scoped and requires capability `read_monitoring_report`.
- List retrieval defaults to the latest report date when `date` is not provided (for report types that define a date field).

## Workflow

1. Resolve scope and auth before calling any endpoint.
   - Send `Authorization: Token <token>`.
   - Send `Academy: <academy_id>` because these endpoints enforce academy capability scope.

2. Discover available report types.
   - Call `GET /v1/monitoring/report`.
   - Use returned `filters` and `sort_fields` for dynamic UI query builders.

3. Fetch report rows for a selected type.
   - Call `GET /v1/monitoring/report/{report_type}`.
   - Apply only allowed filters and sort values to avoid validation errors.

4. Fetch summary metrics when needed by widgets/cards.
   - Call `GET /v1/monitoring/report/{report_type}/summary`.
   - Keep list and summary filters consistent so numbers match the table scope.

5. Fetch one row detail for drill-down panels.
   - Call `GET /v1/monitoring/report/{report_type}/{report_id}`.
   - Use `report_id` returned from Step 3.

6. Trigger async generation only when explicitly requested.
   - Call `POST /v1/monitoring/report/{report_type}/generate`.
   - Use one date strategy per request (`date`, range, or `days_back`).
   - Requests are deduplicated by report/date scope unless `force=true`.

7. Poll generation job state and queue health.
   - Call `GET /v1/monitoring/report/{report_type}/generate/{job_id}` for one job.
   - Call `GET /v1/monitoring/report/generate-jobs` for pending/running/completed lists.

8. Handle validation failures predictably.
   - If filters/sort are rejected, rebuild query using only discovery metadata from Step 2.
   - If report type is unknown, refresh type list from Step 2 before retrying.

## Endpoints

### 1) Discover report types

- **Method:** `GET`
- **Path:** `/v1/monitoring/report`
- **Required headers:** `Authorization`, `Academy`
- **Required capability:** `read_monitoring_report`
- **Required body fields:** none
- **Pagination:** Not paginated
- **Translated errors:** optional `Accept-Language: en|es`
- **Response that matters:** `slug`, `filters`, `sort_fields`, `supports_detail`, `supports_summary`

**Request context example**
```json
{
  "headers": {
    "Authorization": "Token 4f8f5b2d8e4a",
    "Academy": "1",
    "Accept-Language": "en"
  },
  "query": {}
}
```

**Response example**
```json
[
  {
    "slug": "churn",
    "label": "Churn Risk Report",
    "description": "Daily user churn risk scores and alert signals",
    "filters": ["academy", "date", "risk_level", "user", "min_score", "max_score"],
    "sort_fields": ["report_date", "-report_date", "churn_risk_score", "-churn_risk_score", "risk_level", "-risk_level", "created_at", "-created_at", "user_id", "-user_id"],
    "supports_detail": true,
    "supports_summary": true
  },
  {
    "slug": "acquisition",
    "label": "Acquisition Report",
    "description": "Daily lead and invite acquisition snapshots with funnel tiers",
    "filters": ["academy", "date", "date_start", "date_end", "source_type", "user", "utm_source", "utm_campaign", "deal_status", "asset_slug", "event_slug", "funnel_tier"],
    "sort_fields": ["report_date", "-report_date", "created_at", "-created_at", "source_type", "-source_type", "funnel_tier", "-funnel_tier", "user_id", "-user_id"],
    "supports_detail": true,
    "supports_summary": true
  }
]
```

### 2) List report rows

- **Method:** `GET`
- **Path:** `/v1/monitoring/report/{report_type}`
- **Required headers:** `Authorization`, `Academy`
- **Required capability:** `read_monitoring_report`
- **Required body fields:** none
- **Pagination:** Paginated (supports `limit`, `offset`)
- **Current filters for `churn`:** `academy`, `date`, `risk_level`, `user`, `min_score`, `max_score`
- **Current filters for `acquisition`:** `academy`, `date`, `date_start`, `date_end`, `source_type`, `user`, `utm_source`, `utm_campaign`, `deal_status`, `asset_slug`, `event_slug`, `funnel_tier`
- **Sort:** use only values declared in discovery response `sort_fields`
- **Translated errors:** optional `Accept-Language: en|es`

**Request context example**
```json
{
  "path_params": {
    "report_type": "churn"
  },
  "headers": {
    "Authorization": "Token 4f8f5b2d8e4a",
    "Academy": "1"
  },
  "query": {
    "risk_level": "CRITICAL",
    "min_score": "70",
    "sort": "-churn_risk_score",
    "limit": "20",
    "offset": "0"
  }
}
```

**Response example**
```json
[
  {
    "id": 118,
    "user_id": 2033,
    "user_email": "student@example.com",
    "academy_id": 1,
    "report_date": "2026-04-13",
    "churn_risk_score": 82.5,
    "risk_level": "CRITICAL",
    "days_since_last_activity": 11,
    "login_count_7d": 1,
    "assignments_completed_7d": 0,
    "has_payment_issues": true,
    "subscription_status": "PAYMENT_ISSUE"
  }
]
```

### 3) Get report summary

- **Method:** `GET`
- **Path:** `/v1/monitoring/report/{report_type}/summary`
- **Required headers:** `Authorization`, `Academy`
- **Required capability:** `read_monitoring_report`
- **Required body fields:** none
- **Pagination:** Not paginated
- **Filters:** same filter set as list endpoint for that report type
- **Translated errors:** optional `Accept-Language: en|es`

**Request context example**
```json
{
  "path_params": {
    "report_type": "churn"
  },
  "headers": {
    "Authorization": "Token 4f8f5b2d8e4a",
    "Academy": "1"
  },
  "query": {
    "date": "2026-04-13"
  }
}
```

**Response example**
```json
{
  "total": 142,
  "average_score": 38.4,
  "payment_risk_count": 9,
  "unresolved_alert_count": 16,
  "risk_levels": {
    "LOW": 74,
    "MEDIUM": 41,
    "HIGH": 19,
    "CRITICAL": 8
  }
}
```

**Acquisition summary example**
```json
{
  "total": 72,
  "by_source_type": {
    "FORM_ENTRY": 18,
    "USER_INVITE": 54
  },
  "by_funnel_tier": {
    "1": 6,
    "2": 14,
    "3": 10,
    "4": 42
  },
  "by_funnel_tier_label": {
    "won_or_sale": 6,
    "strong_lead": 14,
    "soft_lead": 10,
    "nurture_invite": 42
  },
  "top_asset_slugs": [{"asset_slug": "interactive-python", "count": 19}],
  "top_event_slugs": [{"event_slug": "full-stack-with-ai-workshop-part-2-copy", "count": 12}],
  "top_utm_sources": [{"utm_source": "an", "count": 17}],
  "top_utm_campaigns": [{"utm_campaign": "120239918684820575", "count": 11}],
  "top_conversion_urls": [{"conversion_url": "/es/bootcamp/change-your-career-in-15-days-self-paced", "count": 8}],
  "by_deal_status": {"WON": 4},
  "team_seat_invite_count": 3
}
```

### 4) Get one report row detail

- **Method:** `GET`
- **Path:** `/v1/monitoring/report/{report_type}/{report_id}`
- **Required headers:** `Authorization`, `Academy`
- **Required capability:** `read_monitoring_report`
- **Required body fields:** none
- **Pagination:** Not paginated
- **Translated errors:** optional `Accept-Language: en|es`
- **Response that matters:** full row detail including report-specific payloads like `details`

**Request context example**
```json
{
  "path_params": {
    "report_type": "churn",
    "report_id": 118
  },
  "headers": {
    "Authorization": "Token 4f8f5b2d8e4a",
    "Academy": "1"
  },
  "query": {}
}
```

### 5) Trigger report generation job

- **Method:** `POST`
- **Path:** `/v1/monitoring/report/{report_type}/generate`
- **Required headers:** `Authorization`, `Academy`
- **Required capability:** `read_monitoring_report`
- **Body rules:** send exactly one strategy:
  - `date`
  - `date_start` + `date_end`
  - `days_back`
- **Optional body field:** `force` (bool) to bypass dedup and create a new job.
- **Behavior:** returns queued job payload with progress fields.

**Request context example**
```json
{
  "path_params": {
    "report_type": "acquisition"
  },
  "headers": {
    "Authorization": "Token 4f8f5b2d8e4a",
    "Academy": "1"
  },
  "body": {
    "date_start": "2026-04-01",
    "date_end": "2026-04-30"
  }
}
```

**Response example**
```json
{
  "id": 42,
  "report_type": "acquisition",
  "status": "PENDING",
  "status_message": "Queued",
  "academy_id": 1,
  "date_start": "2026-04-01",
  "date_end": "2026-04-30",
  "progress_current": 0,
  "progress_total": 0,
  "generated_rows": 0
}
```

### 6) Poll one generation job

- **Method:** `GET`
- **Path:** `/v1/monitoring/report/{report_type}/generate/{job_id}`
- **Required headers:** `Authorization`, `Academy`
- **Required capability:** `read_monitoring_report`
- **Status values:** `PENDING`, `RUNNING`, `DONE`, `PARTIAL`, `ERROR`, `CANCELLED`

### 7) List generation jobs queue

- **Method:** `GET`
- **Path:** `/v1/monitoring/report/generate-jobs`
- **Required headers:** `Authorization`, `Academy`
- **Required capability:** `read_monitoring_report`
- **Supported filters:** `status` (comma-separated), `report_type`
- **Primary use case:** list pending/running generation jobs in dashboards.

**Response example**
```json
{
  "id": 118,
  "user_id": 2033,
  "user_email": "student@example.com",
  "academy_id": 1,
  "report_date": "2026-04-13",
  "churn_risk_score": 82.5,
  "risk_level": "CRITICAL",
  "days_since_last_activity": 11,
  "login_count_7d": 1,
  "login_trend": -75.0,
  "assignments_completed_7d": 0,
  "assignment_trend": -100.0,
  "avg_frustration_score": 72.0,
  "avg_engagement_score": 21.0,
  "has_payment_issues": true,
  "subscription_status": "PAYMENT_ISSUE",
  "days_until_renewal": 2,
  "details": {
    "academy_id": 1,
    "subscription_status": "PAYMENT_ISSUE",
    "days_since_last_activity": 11
  },
  "created_at": "2026-04-14T08:15:21Z"
}
```

## Edge Cases

- **Missing academy scope header:** API returns `403` with missing academy message. Send `Academy` header and retry.
- **Missing capability:** API returns `403` capability error. Use a user/role with `read_monitoring_report`.
- **Unknown report type:** API returns `404` with `report-type-not-found`. Re-run discovery endpoint and use a supported `slug`.
- **Unsupported filters:** API returns `400` with `unsupported-filter`. Remove unknown query params and retry with allowed keys only.
- **Invalid sort value:** API returns `400` with `invalid-sort-field`. Use one of `sort_fields` from discovery response.
- **Academy filter mismatch:** API returns `400` with `academy-filter-mismatch` if query `academy` differs from scoped academy. Keep them aligned.
- **Invalid date strategy on generation:** API returns `400` with date-combination/range slugs. Send only one strategy and valid ranges.

## Checklist

1. [ ] Called `GET /v1/monitoring/report` and selected a valid `report_type`.
2. [ ] Sent `Authorization` and `Academy` headers on every request.
3. [ ] Used only allowed filters and sort fields from discovery metadata.
4. [ ] Queried list and summary with the same filter scope when showing one dashboard view.
5. [ ] Used detail endpoint only after obtaining `report_id` from list results.
6. [ ] Handled 400/403/404 errors with explicit retry behavior.
7. [ ] For generation, used exactly one strategy (`date`, range, or `days_back`).
8. [ ] Used `force=true` only when intentionally creating a duplicate regeneration job.
