---
name: bc-marketing-debug-form-entry
description: Use when diagnosing FormEntry CRM sync failures, stuck storage_status, or ActiveCampaign double-sync issues; do NOT use for creating leads or routine list/update/delete operations.
requires:
  - bc-marketing-create-form-entry
  - bc-marketing-manage-form-entries
  - breathecode-staff-api-index
---

# Skill: Debug FormEntry CRM Sync

## When to Use

- `storage_status` is `ERROR`, stuck `PENDING`, or unexpected `DUPLICATED` / `REJECTED`.
- Lead never appeared in CRM after create.
- Salesperson updated deal in ActiveCampaign but `FormEntry` fields (`deal_status`, `ac_deal_*`) did not update.
- `form_entry.added` platform webhook fired but CRM sync failed.
- Bulk CSV upload rows are missing or failed silently.

Do NOT use for: creating leads (create skill), routine list/update without a failure (manage skill), acquisition analytics (monitoring/inbound skills), Facebook intake failures (inbound skill), or referral commission payouts (inbound + commission).

## Concepts

### Outbound vs reverse sync

| Symptom | Likely layer |
|---|---|
| `storage_status=ERROR` | **Outbound** — BreatheCode → CRM (`persist_single_lead`) |
| `storage_status=PERSISTED` but `deal_status` / `ac_deal_*` stale | **Reverse** — ActiveCampaign → BreatheCode (webhooks `deal_add` / `deal_update`) |
| `form_entry.added` received but CRM empty | Outbound failed **independently** of platform webhook |

### ActiveCampaign double sync

- **Outbound:** create or `process` pushes contact + automation/tags to ActiveCampaign. Failures appear in `storage_status_text`.
- **Reverse (optional):** ActiveCampaign webhooks POST to `/v1/marketing/activecampaign/webhook/<academy_slug>` or `/v1/marketing/activecampaign/webhook/<ac_academy_id>` and update `deal_status`, `ac_deal_id`, `ac_deal_*`, `won_at`, etc.
- **Brevo:** no reverse deal webhooks in the current API.
- UTMs are **never overwritten** on reverse sync.

### `storage_status` reference

| Status | Meaning | Action |
|---|---|---|
| `PENDING` | Queued, in flight, or Celery retry | Wait briefly; then `process` via manage skill |
| `PERSISTED` | Outbound CRM OK | Outbound done; check reverse sync separately if deal fields stale |
| `ERROR` | Outbound failed | Read `storage_status_text`, fix lead, `process` |
| `DUPLICATED` | Intentional dedup (~30 min window) | **Do not** `process` |
| `REJECTED` | Business rejection (manual/admin) | Read `storage_status_text`; not auto-set by CRM pipeline |
| `MANUALLY_PERSISTED` | Legacy/manual CRM paste marker | Used in reverse-sync email matching; not a normal automated outcome |

### Platform webhooks vs CRM

- `form_entry.added` fires on **database save** (`post_save`), before async CRM completes.
- `form_entry.changed` fires on staff `PUT`; does **not** re-push to CRM.
- CRM retry requires `PUT /v1/marketing/academy/lead/process?id=`.

## Workflow

1. **Identify the lead.** `GET /v1/marketing/academy/lead/<id>` or list with `?storage_status=ERROR` / `?storage_status=PENDING` (manage skill). Save `id`, `storage_status`, `storage_status_text`, `ac_contact_id`, `ac_deal_id`, `deal_status`.

2. **Classify the problem.** Use the tables below:
   - `ERROR` or stuck `PENDING` → outbound CRM (Steps 3–8).
   - `PERSISTED` but deal fields stale → reverse sync (Step 9).
   - Bulk upload missing rows → Step 10.
   - Webhook received but CRM failed → outbound (Steps 3–8); explain webhook ≠ CRM to the user.

3. **Check CRM config.** `GET /v1/marketing/crmacademy` — verify `crm_vendor` (`ACTIVE_CAMPAIGN` or `BREVO`), credentials, `sync_status`, `sync_message`.

4. **Validate lead payload** against create-skill requirements: `location`, `first_name`, `last_name`, `phone`, `course`, `tags` (AC) or `automations` (both vendors; Brevo: one only).

5. **Verify tag/automation slugs.** `GET /v1/marketing/academy/tag`, `GET /v1/marketing/academy/automation`. Refresh from CRM if stale: `GET /v1/marketing/academy/<academy_id>/tag/sync`, `GET /v1/marketing/academy/<academy_id>/automation/sync`.

6. **Fix lead data.** `PUT /v1/marketing/academy/lead/<id>` (manage skill).

7. **Retry outbound.** `PUT /v1/marketing/academy/lead/process?id=<id>` — add `sync=true` when you need the final `storage_status` in the same response. **Skip if `DUPLICATED`**.

8. **Poll outcome.** Re-read lead until `PERSISTED`, `DUPLICATED`, or stable `ERROR`. Match `storage_status_text` to lookup table below if still failing.

9. **Reverse sync (ActiveCampaign only).** If outbound is `PERSISTED` but `deal_status` / `ac_deal_*` never update after salesperson CRM action:
   - Confirm AC webhooks target `/v1/marketing/activecampaign/webhook/...`.
   - Confirm `ac_contact_id` is set on the lead (outbound must have succeeded).
   - Webhook matching uses `ac_deal_id`, then `ac_contact_id`, then email.
   - Staff `PUT` on `deal_status` may be overwritten by the next AC webhook when double sync is on.
   - **API gap:** no staff GET endpoint for `ActiveCampaignWebhook` logs (`status`, `status_text`).

10. **Bulk CSV debug.** Upload returns `PENDING` immediately. If rows are missing, search `GET /v1/marketing/academy/lead?like=<name>` or filter by email + `created_at`. **API gap:** no staff GET for `CSVUpload` job log.

## Endpoints

All staff endpoints require `Authorization`, `Academy`, optional `Accept-Language`.

| Purpose | Method | Path | Capability |
|---|---|---|---|
| Read lead diagnostics | GET | `/v1/marketing/academy/lead/<id>` | `read_lead` |
| List failed leads | GET | `/v1/marketing/academy/lead?storage_status=ERROR` | `read_lead` |
| List stuck leads | GET | `/v1/marketing/academy/lead?storage_status=PENDING` | `read_lead` |
| CRM config health | GET | `/v1/marketing/crmacademy` | `read_lead` |
| Tag catalog | GET | `/v1/marketing/academy/tag` | `read_lead` |
| Automation catalog | GET | `/v1/marketing/academy/automation` | `read_lead` |
| Sync tags from AC | GET | `/v1/marketing/academy/<academy_id>/tag/sync` | `crud_lead` |
| Sync automations from AC | GET | `/v1/marketing/academy/<academy_id>/automation/sync` | `crud_lead` |
| Fix lead fields | PUT | `/v1/marketing/academy/lead/<id>` | `crud_lead` |
| Retry CRM outbound | PUT | `/v1/marketing/academy/lead/process?id=<id>` | `crud_lead` | Optional `sync=true` for inline processing |

#### Example — read failing lead

```http
GET /v1/marketing/academy/lead/219384
Authorization: Token <token>
Academy: 4
```

```json
{
  "id": 219384,
  "email": "lucia@example.com",
  "location": "barcelona-spain",
  "tags": "",
  "storage_status": "ERROR",
  "storage_status_text": "You need to specify tags for this entry",
  "ac_contact_id": null,
  "deal_status": null
}
```

#### Example — CRM config check

```http
GET /v1/marketing/crmacademy
Authorization: Token <token>
Academy: 4
```

```json
[
  {
    "id": 12,
    "crm_vendor": "ACTIVE_CAMPAIGN",
    "sync_status": "OK",
    "sync_message": "",
    "academy": {
      "id": 4,
      "slug": "barcelona"
    }
  }
]
```

#### Example — retry after fix

```http
PUT /v1/marketing/academy/lead/process?id=219384
Authorization: Token <token>
Academy: 4
```

```json
{
  "details": "1 leads added to the processing queue"
}
```

## `storage_status_text` lookup table (outbound CRM)

| `storage_status_text` | Root cause | Fix | Retry `process`? |
|---|---|---|---|
| `Missing location information` | No/invalid `location`; `academy=null` on public create | Set valid `location` or use staff create (overrides location) | Yes |
| `No CRM vendor information for academy with slug …` | No CRM config for location slug | Configure CRM via `crmacademy`; verify `active_campaign_slug` | Yes |
| `You need to specify tags for this entry` | ActiveCampaign; missing `tags` | Add valid tag slugs | Yes |
| `The contact tags are empty` | `tags` field blank after parse | Set non-empty comma-separated slugs | Yes |
| `Some tag applied to the contact not found or have tag_type different than…` | Invalid tag slug or wrong type | Fix slug; sync tag catalog from AC | Yes |
| `The specified automation … was not found for this AC Academy …` | Invalid automation slug | Fix slug; sync automation catalog | Yes |
| `No automation was specified and the specified tag (if any) has no automation either` | No automations and first tag has no linked automation | Add `automations` or tag with automation | Yes |
| `Brevo CRM does not support tags, please remove them from the contact payload` | Tags on Brevo academy | Remove `tags` from lead | Yes |
| `Only one automation at a time is allowed for Brevo` | Multiple automation slugs on Brevo | Keep one automation | Yes |
| `The email doesn't exist` | Missing email in processed payload | Set `email` | Yes |
| `The first name doesn't exist` | Missing `first_name` | Set `first_name` | Yes |
| `The last name doesn't exist` | Missing `last_name` | Set `last_name` | Yes |
| `The phone doesn't exist` | Missing `phone` | Set `phone` | Yes |
| `The course doesn't exist` | Missing `course` | Set `course` | Yes |
| `The id doesn't exist` | Internal task payload missing id | Re-queue `process` | Yes |
| `FormEntry not found (id: …)` | Race or bad id | Wait and re-queue `process` | Yes |
| `Could not save contact in CRM` / `Subscriber_id not found` | AC contact API failure | Check credentials, AC outage, payload | Yes |
| `Could not add contact to Automation` | AC automation enrollment failed | Verify automation `acp_id`; sync catalog | Yes |
| *(empty text)* + `DUPLICATED` | Same email+course within dedup window (default 30 min) | Expected — not a bug | **No** |
| `Saved but not send to CRM because SAVE_LEADS is FALSE` | Env disables CRM (`PERSISTED`) | Ops environment note | No |

### Stuck / transient outbound

| Symptom | Root cause | Action |
|---|---|---|
| `PENDING` + timeout text | Celery timeout during CRM call | Wait; `process` retry |
| `PENDING` indefinitely | Staff create without `process` | Call `process` |
| `PENDING` (initial) | Task not yet consumed | Wait 1–2 minutes, then investigate |

## Reverse sync troubleshooting (ActiveCampaign)

| Symptom | Root cause | What to do |
|---|---|---|
| `deal_status` never updates after AC salesperson action | Webhooks not configured to `/v1/marketing/activecampaign/webhook/...` | Configure AC webhooks; verify academy slug or id in URL |
| Webhook cannot match lead | No `ac_contact_id`, `ac_deal_id`, or matching email on `FormEntry` | Ensure outbound `PERSISTED` first; check email match |
| Staff `PUT deal_status` reverts | AC webhook overwrites on next sync | Prefer AC as source of truth when double sync on |
| Brevo academy | No reverse deal webhooks | Deal fields only update via staff `PUT` or outbound |
| Secondary custom-field sync fails | `async_update_deal_custom_fields` after `deal_add` | Does not change `storage_status`; deal core fields may still update |

Webhook processing errors use messages like `Impossible to find formentry for webhook …` or `Impossible to find formentry with deal …` — there is **no staff API** to read these logs.

## Side effects that do not change `storage_status`

| Failure | What you observe | What to do |
|---|---|---|
| API create `400` (bad phone, language >2 chars) | No `FormEntry` created | Fix payload; use create skill |
| Public empty POST → `201` then CRM `ERROR: Missing location` | Record exists, CRM failed | Fix `location`; `process` |
| `contact-us` tag internal email fails | CRM may abort before `PERSISTED` | Rare; check `storage_status_text`; fix email config |
| Geolocation after `PERSISTED` | `city`/`country` empty; status stays `PERSISTED` | Non-blocking; Maps API or missing lat/long |
| `REJECTED` status | Manual/admin only; never auto-set by CRM pipeline | Read `storage_status_text` if present |
| `MANUALLY_PERSISTED` | Used for reverse-sync email matching | Not an automated CRM outcome |

## Bulk CSV debug path

| Symptom | Root cause | What to do |
|---|---|---|
| Upload `400` | Missing required CSV column | Add `first_name`, `last_name`, `email`, `location`, `phone`, `language` |
| Row skipped | `No location or academy`, bad email, missing names, unknown slug | Fix row; re-upload or create lead manually |
| Upload `PENDING`, leads missing | Per-row errors logged server-side only | Search leads by email + `created_at` |
| Extra CSV columns ignored | `referral_key`, `tags` not mapped by bulk task | Set fields via staff `PUT` or use non-bulk create |

## Integration confusion (webhooks ≠ CRM)

| Symptom | Explanation |
|---|---|
| n8n/Zapier got `form_entry.added` but `storage_status=ERROR` | Platform webhook fires on save; CRM is async and independent |
| Staff `PUT` but CRM contact unchanged | `form_entry.changed` only; call `process` to re-push |

## API limitations

- No staff GET for `ActiveCampaignWebhook` error logs.
- No staff GET for `CSVUpload` job status or per-row log.
- Do not reference management commands — use API endpoints only.

## Cross-references (do not deep-dive here)

- Facebook inbound intake failures → [`bc-marketing-inbound-leads-attribution-and-acquisition`](../bc-marketing-inbound-leads-attribution-and-acquisition/SKILL.md)
- Attribution / `custom_fields` decoding → inbound skill
- Referral commission payouts → inbound skill + `/v1/commission/...`
- Acquisition funnel drill-down → [`bc-monitoring-read-report-acquisition`](../bc-monitoring-read-report-acquisition/SKILL.md) + manage skill

## Edge Cases

- **`DUPLICATED` after legitimate re-submit:** same person submitted the same course within the dedup window — expected; do not `process`.
- **`PERSISTED` + empty `ac_deal_id`:** outbound contact may exist without a deal yet; reverse `deal_add` webhook sets deal fields.
- **Staff create never processed:** `PENDING` forever until `process` — not a CRM failure.
- **`SAVE_LEADS=FALSE`:** looks like success (`PERSISTED`) but CRM was skipped — check `storage_status_text`.
- **Race: `process` before DB visible:** rare `FormEntry not found` — retry `process`.

## Checklist

1. [ ] Retrieved lead by `id` and recorded `storage_status`, `storage_status_text`, `ac_contact_id`, `ac_deal_id`, `deal_status`.
2. [ ] Classified outbound vs reverse vs bulk vs webhook-confusion problem.
3. [ ] Checked `GET /v1/marketing/crmacademy` for vendor and sync health.
4. [ ] Matched `storage_status_text` to lookup table and applied fix via `PUT`.
5. [ ] Called `process` unless status is `DUPLICATED`.
6. [ ] Polled until terminal state (`PERSISTED`, `DUPLICATED`, or stable `ERROR`).
7. [ ] If outbound OK but deal fields stale, verified AC reverse webhook configuration.
8. [ ] Documented API gaps when webhook or CSV upload logs are needed.
