---
name: bc-monitoring-read-report-acquisition
description: Use when reading and interpreting the acquisition monitoring report via `/v1/monitoring/report/acquisition*`; do NOT use for report generation or acquisition report implementation changes.
requires: []
---

# Skill: Read Acquisition Monitoring Report

## When to Use

Use this skill when the task is to query, interpret, or explain acquisition report data for dashboards, PM analysis, or agent investigations.
Use it for list/detail/summary reads of `report_type=acquisition`.
Do NOT use this skill to implement report models, generators, serializers, registry entries, or `generate_report` command behavior.
Do NOT use this skill for non-monitoring report domains.
If you need to trigger regeneration jobs, use `bc-monitoring-read-reports-api` generation endpoints (`POST /v1/monitoring/report/acquisition/generate` + polling).

## Core Concepts

- `source_type`:
  - `FORM_ENTRY`: Marketing/CRM lead path; row is for the lead’s **creation** day (`FormEntry.created_at` date in the generator). Drill down to lead detail: `source_id` is the FormEntry id — use [`bc-marketing-manage-form-entries`](../bc-marketing-manage-form-entries/SKILL.md) (`GET /v1/marketing/academy/lead/<id>`). If CRM sync looks wrong on that lead, load [`bc-marketing-debug-form-entry`](../bc-marketing-debug-form-entry/SKILL.md).
  - `FORM_ENTRY_WON`: Same form lead when the deal was **won**; row is for **`won_at` date** (requires `deal_status=WON` and `won_at` set on `FormEntry`). Pairs with `FORM_ENTRY` for the same `source_id` (form entry id) on different `report_date`s when creation and win fall on different days. Use `by_source_type` for both; do not use win-only filters for a full-funnel story in one period.
  - `USER_INVITE`: Invite/self-serve onboarding path (not only staff-invited users).
  - `EVENT_RSVP`: Event/workshop registration from `events.EventCheckin` on the **RSVP day** (`created_at` date). Funnel tier **nurture_invite** (`4`).
  - `EVENT_ATTENDED`: Same check-in when the person **attended**; row is written on **`attended_at` date** with funnel tier **soft_lead** (`3`). RSVP and attendance are **two rows** (same `source_id`, different `source_type`) when both apply, so stage-flow is visible (same calendar day can have both).
- This report is **time-window / activity** style: `report_date` is the day the event is counted, not a full cohort engine. Cohort questions (e.g. “leads from March who ever won”) need joining `FORM_ENTRY` and `FORM_ENTRY_WON` on `source_id` or analytics outside this summary.
- `funnel_tier` (required contract):
  - `1 = won_or_sale`
  - `2 = strong_lead`
  - `3 = soft_lead`
  - `4 = nurture_invite`
- `asset_slug` and `event_slug`: invite path plus **event check-ins** (slug from `Event.slug`). Check-in rows copy UTMs from `EventCheckin` and use `utm_url` as `landing_url`.
- Attribution fields can come from two shapes:
  - Form entries: first-class `utm_*` and `utm_url`.
  - User invites: `conversion_info` with `utm_*`, `landing_url`, `conversion_url`, and optional `sale`.

## Required Scope and Headers

- `Authorization: Token <token>`
- `Academy: <academy_id>` or comma-separated list for multi-academy scope (`1,2,3`)
- Capability: `read_monitoring_report`

## Endpoint Workflow

1. Discover supported reports and filters:
   - `GET /v1/monitoring/report`
2. List acquisition rows:
   - `GET /v1/monitoring/report/acquisition`
3. Get one row detail:
   - `GET /v1/monitoring/report/acquisition/{report_id}`
4. Get acquisition summary:
   - `GET /v1/monitoring/report/acquisition/summary`

## Allowed Filters and Period Handling

Supported filters for acquisition:
- `academy`
- `date`
- `date_start`
- `date_end`
- `source_type`
- `user`
- `utm_source`
- `utm_campaign`
- `deal_status`
- `asset_slug`
- `event_slug`
- `funnel_tier`

Period behavior:
- If no `date`/range filters are sent, list/summary default to latest `report_date`.
- Use `date_start` + `date_end` for windows like last 30 days.

Example last 30 days query:
```http
GET /v1/monitoring/report/acquisition/summary?date_start=2026-03-23&date_end=2026-04-21
```

## Summary Keys and Meaning

- `report_row_count`: number of `AcquisitionReport` rows matching filters (all source types); not “unique leads” — use `unique_identities` for people-level dedup.
- `unique_identities`: deduped identities in filter scope (`user_id`, fallback normalized `email`).
- `cross_academy_identities`: deduped identities seen in more than one academy in the same query scope.
- `by_source_type`: distribution by `FORM_ENTRY`, `FORM_ENTRY_WON`, `USER_INVITE`, `EVENT_RSVP`, and `EVENT_ATTENDED`.
- `by_funnel_tier`: counts by tier number (`"1"`..`"4"`).
- `by_funnel_tier_label`: counts by tier label (`won_or_sale`, `strong_lead`, `soft_lead`, `nurture_invite`).
- `by_funnel_tier_identities`: deduped identity counts by best tier (best tier wins: `1` > `2` > `3` > `4`).
- `by_funnel_tier_label_identities`: deduped identity counts by label.
- `top_asset_slugs`: top invite asset slugs.
- `top_event_slugs`: top event/workshop slugs from invites **and** event RSVP/attendance rows (`event_slug`).
- `top_utm_sources`: top sources.
- `top_utm_campaigns`: top campaigns.
- `top_conversion_urls`: top invite conversion pages.
- `by_deal_status`: deal status breakdown for lead rows.
- `team_seat_invite_count`: invite rows linked to subscription/financing seats.

## Question Catalog (Question -> Request Pattern)

For every query below, include:
- `Authorization` and `Academy` headers.
- Same date/filter scope between list and summary when comparing widgets.
- If using multi-academy (`Academy: 1,2,3`), interpret `by_funnel_tier` as event-level and `by_funnel_tier_identities` as deduped person-level.

1. Top assets in a period
   - Endpoint: `summary`
   - Query: `?date_start=YYYY-MM-DD&date_end=YYYY-MM-DD&source_type=USER_INVITE`
   - Read: use `top_asset_slugs`.

2. Top workshops/events in a period
   - Endpoint: `summary`
   - Query: `?date_start=YYYY-MM-DD&date_end=YYYY-MM-DD&source_type=USER_INVITE`
   - Read: use `top_event_slugs`.

3. Funnel mix for last 30 days
   - Endpoint: `summary`
   - Query: `?date_start=<today-30d>&date_end=<today>`
   - Read: use `by_funnel_tier` + `by_funnel_tier_label`.

4. Won/sale volume in a period
   - Endpoint: `list` or `summary`
   - Query: `?date_start=YYYY-MM-DD&date_end=YYYY-MM-DD&funnel_tier=1`
   - Read: row count/list size or `by_funnel_tier["1"]`.

5. Strong vs soft lead comparison
   - Endpoint: `summary`
   - Query: `?date_start=YYYY-MM-DD&date_end=YYYY-MM-DD`
   - Read: compare `by_funnel_tier["2"]` and `by_funnel_tier["3"]`.

6. Top UTM source in a period
   - Endpoint: `summary`
   - Query: `?date_start=YYYY-MM-DD&date_end=YYYY-MM-DD`
   - Read: first element of `top_utm_sources`.

7. Top UTM campaign in a period
   - Endpoint: `summary`
   - Query: `?date_start=YYYY-MM-DD&date_end=YYYY-MM-DD`
   - Read: first element of `top_utm_campaigns`.

8. Top conversion URLs for invite-heavy traffic
   - Endpoint: `summary`
   - Query: `?date_start=YYYY-MM-DD&date_end=YYYY-MM-DD&source_type=USER_INVITE`
   - Read: `top_conversion_urls`.

9. Team-seat invite count in a period
   - Endpoint: `summary`
   - Query: `?date_start=YYYY-MM-DD&date_end=YYYY-MM-DD&source_type=USER_INVITE`
   - Read: `team_seat_invite_count`.

10. Drill-down rows for one asset
    - Endpoint: `list`
    - Query: `?date_start=YYYY-MM-DD&date_end=YYYY-MM-DD&source_type=USER_INVITE&asset_slug=<slug>`
    - Read: rows are the detailed sample behind the asset leaderboard.

11. Drill-down rows for one workshop/event
    - Endpoint: `list`
    - Query: `?date_start=YYYY-MM-DD&date_end=YYYY-MM-DD&source_type=USER_INVITE&event_slug=<slug>`
    - Read: rows are the detailed sample behind workshop leaderboard.

## Error and Edge Handling

- Unsupported query params -> `400` (`unsupported-filter`).
- Invalid sort field -> `400` (`invalid-sort-field`).
- Academy mismatch in query/header scope -> `400` (`academy-filter-mismatch`).
- Missing auth/capability/scope -> `401/403`.
- Unknown report type or record -> `404`.
- Snapshot caveat: data freshness depends on report generation cadence; missing days can appear if generation/backfill did not run.

## Checklist

1. [ ] Confirmed `acquisition` exists via `GET /v1/monitoring/report`.
2. [ ] Sent `Authorization` and `Academy` headers.
3. [ ] Used only allowed filters from discovery.
4. [ ] Kept list and summary filter scope identical when comparing values.
5. [ ] Used detail endpoint only after obtaining `report_id` from list.
6. [ ] Interpreted funnel tiers with locked labels (`won_or_sale`, `strong_lead`, `soft_lead`, `nurture_invite`).
