---
name: breathecode-staff-api-index
description: Load first for academy-scoped BreatheCode API work (/academy/, Academy header, staff capabilities). Maps requests to domain skills. Do NOT use for pure learner self-service without staff context — use breathecode-student-api-index instead.
requires: []
---

# BreatheCode Staff API Index

This skill is the entry point for **staff and academy-scoped** BreatheCode API work. Its only job is to help you identify which domain skill(s) to load before taking any action. Do not attempt to call the API using only this skill — always load the relevant domain skill(s) first.

## When to Use

- Load this skill at the start of tasks that involve **academy administration**, **`Academy` header**, paths under **`/academy/`**, or staff capabilities.
- Use it when the request is ambiguous and may span multiple **staff** domains.
- Do NOT use this as a substitute for the domain skill — always proceed to load the specific skill after consulting this index.

## Related index

If the session is **learner-only** (authenticated student using `me` / `user/me` flows, no staff capabilities), load [`breathecode-student-api-index`](../breathecode-student-api-index/SKILL.md) instead of this file.

---

## Workflow

1. Read the user's request.
2. Identify the domain(s) from the table below.
3. Load the corresponding skill(s) before proceeding.
4. If the task spans multiple domains, load all relevant skills and check each one for cross-domain instructions before calling any endpoint.

---

## Domain Map

| Domain | Covers | Skill to Load |
|---|---|---|
| **admissions** | Students, cohorts, syllabi, enrollments, cohort stages, micro/macro cohorts | `bc-admissions-*` |
| **activity** | User activity tracking, engagement stats, daily summaries, login streaks | `bc-activity-*` |
| **assessment** | Quizzes, tests, student quiz attempts, grading | `bc-assessment-*` |
| **assignment** | Student task deliveries, project submissions, revision requests; **PROJECT** teacher review (list → registry asset → `PUT` task; **ignore** = same `PUT` with `revision_status=IGNORED`, not a separate route) | `bc-assignment-*`, [`bc-assignment-review-submit-task-revision`](../bc-assignment-review-submit-task-revision/SKILL.md) |
| **authenticate** | Staff login, academy-scoped capabilities, integration token, staff-assisted reset; staff invites and member admin | `bc-authenticate-*`, [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md), [`bc-authenticate-staff-invites`](../bc-authenticate-staff-invites/SKILL.md) |
| **career** | Job listings, job applications post-graduation, employer connections | `bc-career-*` |
| **certificate** | Certificate emission, specialties, certificate-syllabus associations | `bc-certificate-*` |
| **events** | Workshops, live classes, RSVPs, check-ins, during-event ops, post-event wrap-up | `bc-events-*`, [`bc-events-during-event`](../bc-events-during-event/SKILL.md), [`bc-events-post-event`](../bc-events-post-event/SKILL.md), [`bc-events-bulk-import-checkins`](../bc-events-bulk-import-checkins/SKILL.md) |
| **feedback** | NPS surveys, student satisfaction studies, feedback forms | `bc-feedback-*` |
| **marketing** | URL shortener, **FormEntry create** (public, app, staff, bulk CSV), **FormEntry staff management**, UTM tracking, **academy-scoped marketing courses** (list/create/clone under `/v1/marketing/academy/course`) | `bc-marketing-*`, [`bc-marketing-create-form-entry`](../bc-marketing-create-form-entry/SKILL.md), [`bc-marketing-manage-form-entries`](../bc-marketing-manage-form-entries/SKILL.md), [`bc-marketing-debug-form-entry`](../bc-marketing-debug-form-entry/SKILL.md) |
| **media** | Images, videos, documents used in LMS content, asset management | `bc-media-*` |
| **mentorship** | Mentors, mentor availability, session scheduling, session notes | `bc-mentorship-*` |
| **monitoring** | Platform monitoring endpoints, report retrieval APIs, monitoring webhooks, and operational status resources | `bc-monitoring-*` |
| **notify** | Email, SMS, WhatsApp messaging, notification templates, delivery status | `bc-notify-*` |
| **payments** | Billing plans, invoices, subscriptions, shop items, payment history | `bc-payments-*` |
| **provisioning** | Student VPS servers, Codespaces containers, provisioning requests | `bc-provisioning-*` |
| **registry** | Learning assets — lessons, exercises, projects, asset versioning | `bc-registry-*` |
| **talent development** | Job families, job roles, career paths and stages, skill domains, global skills, competencies, stage-anchored skills (`/v1/talent/`) | `bc-talentdevelopment-*` |

---

## Common Cross-Domain Workflows

Some user requests touch multiple domains. Load ALL listed skills before proceeding.

| User Request | Skills to Load |
|---|---|
| Create a cohort | `bc-admissions-create-cohort` + `bc-certificate-manage-and-assign-specialties` (syllabus must have an associated specialty) |
| Create and apply syllabus schedule templates to cohorts | `bc-admissions-create-manage-syllabus-schedules` + `bc-admissions-create-cohort` (cohorts must have `schedule` assigned before sync) |
| Create a macro cohort | `bc-admissions-create-cohort` (Path B — macro) + `bc-certificate-manage-and-assign-specialties` (each micro syllabus must have a linked specialty) |
| Configure or fetch micro syllabus with macro-specific overrides | `bc-admissions-create-cohort` (Path B, optional overrides step) + [SYLLABUS.md — Macro cohort syllabus overrides](../../SYLLABUS.md#macro-cohort-syllabus-overrides) (supports `slug.vN` and ordered `N:slug.vN` keys) |
| Enroll a student in a cohort | `bc-admissions-enroll-student` + `bc-payments-*` (student must have a valid plan) |
| Issue a certificate to a student | `bc-certificate-*` + `bc-admissions-*` (verify cohort completion status) |
| Schedule a mentorship session | `bc-mentorship-*` + `bc-notify-*` (session confirmation messaging) |
| Send a notification | `bc-notify-*` + the domain that triggered the notification |
| Create a marketing lead (form, app, staff, or CSV bulk) | [`bc-marketing-create-form-entry`](../bc-marketing-create-form-entry/SKILL.md) |
| Bulk import leads from CSV | [`bc-marketing-create-form-entry`](../bc-marketing-create-form-entry/SKILL.md) (`PUT /v1/marketing/academy/upload`) |
| Search, update, delete, or re-process existing form entries | [`bc-marketing-manage-form-entries`](../bc-marketing-manage-form-entries/SKILL.md) |
| Understand ActiveCampaign double sync (salesperson CRM changes reflected on FormEntry) | [`bc-marketing-manage-form-entries`](../bc-marketing-manage-form-entries/SKILL.md) + [`bc-marketing-create-form-entry`](../bc-marketing-create-form-entry/SKILL.md) (outbound half) |
| Debug FormEntry CRM sync failure (`storage_status=ERROR` / stuck `PENDING`) | [`bc-marketing-debug-form-entry`](../bc-marketing-debug-form-entry/SKILL.md) + [`bc-marketing-create-form-entry`](../bc-marketing-create-form-entry/SKILL.md) (payload requirements) + [`bc-marketing-manage-form-entries`](../bc-marketing-manage-form-entries/SKILL.md) (retry via `process`) |
| ActiveCampaign double sync not updating FormEntry after salesperson CRM change | [`bc-marketing-debug-form-entry`](../bc-marketing-debug-form-entry/SKILL.md) |
| Inbound signups, attribution, and acquisition (forms + invites) | [`bc-marketing-inbound-leads-attribution-and-acquisition`](../bc-marketing-inbound-leads-attribution-and-acquisition/SKILL.md) + [`bc-marketing-create-form-entry`](../bc-marketing-create-form-entry/SKILL.md) + [`bc-marketing-manage-form-entries`](../bc-marketing-manage-form-entries/SKILL.md) |
| Wire lead events to n8n / Zapier | [`bc-marketing-create-form-entry`](../bc-marketing-create-form-entry/SKILL.md) + [`HOOKS_MANAGEMENT.md`](../../HOOKS_MANAGEMENT.md) |
| Acquisition funnel drill-down to lead detail | [`bc-monitoring-read-report-acquisition`](../bc-monitoring-read-report-acquisition/SKILL.md) + [`bc-marketing-manage-form-entries`](../bc-marketing-manage-form-entries/SKILL.md) |
| Referral performance (capture marker vs payouts) | [`bc-marketing-inbound-leads-attribution-and-acquisition`](../bc-marketing-inbound-leads-attribution-and-acquisition/SKILL.md) + `bc-payments-*` / commission endpoints |
| Onboard a new student | `bc-admissions-*` + `bc-payments-*` + `bc-authenticate-*` |
| Log in as staff and call academy-scoped endpoints | [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md) |
| Check whether a staff user can perform an action in an academy | [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md) (Track B — list or probe capabilities) |
| Invite a staff member to an academy | [`bc-authenticate-staff-invites`](../bc-authenticate-staff-invites/SKILL.md) + [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md) |
| Resend or manage pending staff invitations | [`bc-authenticate-staff-invites`](../bc-authenticate-staff-invites/SKILL.md) |
| Accept a staff invitation (first-time onboarding) | [`bc-authenticate-staff-invites`](../bc-authenticate-staff-invites/SKILL.md) + [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md) (post-accept session) |
| Authenticate staff via hosted login in an external admin app (redirect + callback token) | [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md) (Track A — universal hosted login) |
| Connect a third-party app to student authentication (hosted login redirect + callback token) | [`bc-authenticate-student-authentication`](../bc-authenticate-student-authentication/SKILL.md) |
| Provision a resource for a student | `bc-provisioning-*` + `bc-admissions-*` (verify enrollment status first) |
| Create and run an NPS-style cohort satisfaction study | `bc-feedback-create-manage-nps-survey` + `bc-admissions-*` (resolve target cohorts before configuration scope or `send_emails`) |
| Configure academy VPS provisioning (profiles, credentials, settings) | `bc-provisioning-settings-and-credentials` |
| Create or edit an academy event with tags and workshop asset selection | `bc-events-create-and-edit-event` + `bc-marketing-*` (fetch valid `DISCOVERY` tags) + `bc-registry-*` (search and validate workshop assets by type) |
| Connect Luma webhooks for real-time guest registration and check-in | `bc-events-configure-luma-webhooks` + `bc-events-create-and-edit-event` (set `luma_id` on the event) + `bc-marketing-*` (ActiveCampaign automation for registrations) |
| Bulk-import event attendees (RSVP + attended) after event exists | `bc-events-bulk-import-checkins` + `bc-events-create-and-edit-event` (resolve `event_id`) + optional `bc-marketing-*` if `run_marketing=true` |
| Reschedule, suspend, export guests, import outside registrations, or create promo UTM links for a scheduled/live workshop | [`bc-events-during-event`](../bc-events-during-event/SKILL.md) + `bc-events-create-and-edit-event` + optional `bc-events-bulk-import-checkins`, [`bc-events-configure-luma-webhooks`](../bc-events-configure-luma-webhooks/SKILL.md), `bc-marketing-*` |
| After a workshop ends: finalize attendance (incl. Luma guests), publish recording, verify follow-ups | [`bc-events-post-event`](../bc-events-post-event/SKILL.md) + `bc-events-create-and-edit-event` + optional `bc-events-bulk-import-checkins`, [`bc-events-configure-luma-webhooks`](../bc-events-configure-luma-webhooks/SKILL.md) |
| Configure academy Slack integration and manage sync health | `bc-notify-manage-academy-slackintegration` + `bc-admissions-*` (students/cohorts drive Slack mappings) + [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md) (Slack OAuth endpoints live in auth) |
| Build or debug a frontend dashboard that reads monitoring reports | `bc-monitoring-read-reports-api` + [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md) (academy-scoped capability and header requirements drive access outcomes) |
| Read acquisition monitoring insights (funnel tiers, top assets, top workshops, attribution mix) | [`bc-monitoring-read-report-acquisition`](../bc-monitoring-read-report-acquisition/SKILL.md) + [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md) (academy-scoped capability and `Academy` header drive access and scope) |
| Create a marketing course from scratch or by cloning another course | `bc-marketing-create-or-clone-course` + [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md) (staff list: `GET /v1/marketing/academy/course` with comma-separated numeric `Academy` ids and `crud_course` read-aggregate; create/clone: `POST` with `Academy` header; clone requires `crud_course` on source course academy too) |
| Diagnose why graduation/certificate auto-issuance did not happen for a student or cohort | `bc-certificate-manage-and-assign-specialties` + `bc-admissions-*` (use `GET /v1/certificate/diagnostic` with `kind=graduation|certificate`, plus academy-scoped capability/header) |
| Align or extend syllabus design with the school skills framework (job role stages, skills on the go) | `bc-admissions-*` (syllabus, cohorts) + `bc-talentdevelopment-manage-skills` (career path, stages, `stage_skill`, domains) |
| Cancel a user subscription and optionally issue a refund | `bc-payments-cancel-subscription-and-refund` + [`docs/llm-docs/BC_REFUNDS.md`](../../BC_REFUNDS.md) (use the skill for actor-specific flow and endpoint order, then use BC_REFUNDS for refund payload semantics and validations) |
| Configure academy Stripe payment gateway credentials | [`bc-payments-configure-academy-stripe`](../bc-payments-configure-academy-stripe/SKILL.md) |
| Create or manage checkout payment methods for an academy | [`bc-payments-manage-academy-payment-methods`](../bc-payments-manage-academy-payment-methods/SKILL.md) |
| Set academy main currency | [`bc-payments-manage-academy-payment-methods`](../bc-payments-manage-academy-payment-methods/SKILL.md) (Step 0 — `main_currency` via admissions academy/me) |
| Enable credit card payments for an academy | [`bc-payments-manage-academy-payment-methods`](../bc-payments-manage-academy-payment-methods/SKILL.md) Step 0 → [`bc-payments-configure-academy-stripe`](../bc-payments-configure-academy-stripe/SKILL.md) → Path A (main currency, then Stripe, then credit-card catalog entry) |
| Add bank transfer or manual payment option at checkout | [`bc-payments-manage-academy-payment-methods`](../bc-payments-manage-academy-payment-methods/SKILL.md) (Path B) |
| Set up academy commerce end-to-end (payments → services → plans → courses) | [`bc-payments-manage-academy-payment-methods`](../bc-payments-manage-academy-payment-methods/SKILL.md) → `bc-payments-manage-services` → `bc-payments-manage-plans` → [`bc-marketing-create-or-clone-course`](../bc-marketing-create-or-clone-course/SKILL.md) (services/plans skills future; course skill exists today) |
| Diagnose why an asset telemetry is missing for users/tasks | `bc-assignment-diagnose-asset-telemetry` + `bc-registry-*` (validate asset slug and translation/canonical context when telemetry appears split by locale) |
| Queue or interpret asset-level telemetry_stats (`telemetry_stats` JSON on assets) | `bc-assignment-diagnose-asset-telemetry` + `bc-registry-*` (registry asset action `sync_telemetry_stats` queues Celery recompute; read updated stats from asset) |
| Inspect incoming LearnPack telemetry webhook logs by student/event/asset/package filters | `bc-assignment-diagnose-asset-telemetry` + [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md) (academy capability/header scope and identity checks) |
| Delete LearnPack webhook logs (single or bulk cleanup) | `bc-assignment-diagnose-asset-telemetry` + [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md) (cleanup is academy-scoped and restricted to `ERROR` webhooks; bulk delete requires `status=ERROR`) |
| Configure per-academy LearnPack telemetry webhook ignore rules (by user, package, asset slug, or event) | `bc-assignment-diagnose-asset-telemetry` — use `GET`/`PUT /v1/assignment/academy/learnpack/telemetry-webhook-ignore` (rules are stored under `learnpack_features.telemetry_webhook_ignore` on academy auth settings) |
| Review **PROJECT** syllabus tasks (list pending **`DONE`** deliveries oldest-first, load asset **`config`**, submit **`PUT`** approval/rejection — **ignoring** uses the same **`PUT`** with **`revision_status=IGNORED`**, not a separate route) | [`bc-assignment-review-submit-task-revision`](../bc-assignment-review-submit-task-revision/SKILL.md) + registry asset read (`GET /v1/registry/asset/{slug}`) + [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md) (token / headers as needed) |

---

## Routing Rules

**When only one domain is involved:** Load the single matching skill and proceed.

**When multiple domains are involved:** Load all relevant skills, read each one fully, then identify any conflict or ordering constraint between them before calling any endpoint. Cross-domain ordering instructions will be in the use-case skill, not in the individual domain skills.

**When no skill exists yet for the task:** Fall back to the BreatheCode API documentation directly. Do not guess endpoint behavior — ask the user to confirm the correct endpoint or create a new skill for the use case.

**When unsure which domain applies:** Re-read the domain map above. If still ambiguous, ask the user to clarify before proceeding — do not assume.

---

## API Conventions

Assume these conventions for all BreatheCode API endpoints unless a domain skill or endpoint docs say otherwise.

### Pagination

- **Default:** List endpoints are paginated unless the domain skill or endpoint docs say otherwise.
- **Query params:** `limit` (default 20), `offset` (default 0).
- **Paginated response:** When envelope is used, the body has `count`, `first`, `next`, `previous`, `last`, and `results`; headers include `X-Total-Count` and `Link`.

### Academy (staff) endpoints

- **Rule:** Any endpoint whose path contains `/academy/` (after the app prefix, e.g. `/v1/admissions/academy/...`) is for **staff** (academy-scoped operations).
- **Required header:** Send the **`Academy`** header with the academy ID (e.g. `Academy: 1`). For endpoints documented with read aggregation, the same header may accept a comma-separated list (e.g. `Academy: 1,2,3`) and the response may include partial-scope metadata. Missing it returns an error (e.g. "Missing academy_id... or 'Academy' header").
- **Examples:** `/v1/admissions/academy/cohort/user`, `/v1/assessment/academy/user/assessment`, `/v1/assignments/academy/coderevision/<id>`, `/v1/marketing/academy/course`.

### Error responses

- **Structure:** Error responses are JSON with at least:
  - **`detail`** (string): Human-readable message.
  - **`status_code`** (integer): HTTP status (e.g. 400, 403, 404; 402 for payment-related errors).
  - Optionally **`slug`** (string): Stable error code for client logic (e.g. `user-not-found`, `session_without_service`).
  - Optionally **`data`** (object): Extra context.
- The HTTP status of the response matches `status_code`.

### Language and translated errors

- **Header:** **`Accept-Language`** — send a language code (e.g. `en`, `es`) to request error messages (and other translated content) in that language when the API uses translation.
- **Behavior:** The API uses the request's `Accept-Language` (or user/settings fallback) for translated messages; if omitted, the default is typically `en`.

---

## Checklist

1. [ ] Identified the domain(s) from the domain map.
2. [ ] Loaded all relevant skill(s) before calling any endpoint.
3. [ ] If cross-domain, checked the cross-domain workflow table and loaded all required skills.
4. [ ] If no skill exists for the task, flagged this to the user rather than guessing.
