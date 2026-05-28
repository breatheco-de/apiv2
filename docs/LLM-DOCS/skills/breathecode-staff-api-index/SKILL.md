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
| **authenticate** | Login, token generation, password reset, permissions, API key management | `bc-authenticate-*` |
| **career** | Job listings, job applications post-graduation, employer connections | `bc-career-*` |
| **certificate** | Certificate emission, specialties, certificate-syllabus associations | `bc-certificate-*` |
| **events** | Workshops, live classes, event RSVPs, event checkins | `bc-events-*` |
| **feedback** | NPS surveys, student satisfaction studies, feedback forms | `bc-feedback-*` |
| **marketing** | URL shortener, incoming leads, lead scoring, UTM tracking, **academy-scoped marketing courses** (list/create/clone under `/v1/marketing/academy/course`) | `bc-marketing-*` |
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
| Create a cohort | `bc-admissions-create-cohort` + `bc-certificate-*` (syllabus must have an associated specialty) |
| Create and apply syllabus schedule templates to cohorts | `bc-admissions-create-manage-syllabus-schedules` + `bc-admissions-create-cohort` (cohorts must have `schedule` assigned before sync) |
| Create a macro cohort | `bc-admissions-create-macro-cohort` + `bc-certificate-*` + `bc-admissions-create-cohort` |
| Configure or fetch micro syllabus with macro-specific overrides | `bc-admissions-create-macro-cohort` + [SYLLABUS.md — Macro cohort syllabus overrides](../../SYLLABUS.md#macro-cohort-syllabus-overrides) (supports `slug.vN` and ordered `N:slug.vN` keys) |
| Enroll a student in a cohort | `bc-admissions-enroll-student` + `bc-payments-*` (student must have a valid plan) |
| Issue a certificate to a student | `bc-certificate-*` + `bc-admissions-*` (verify cohort completion status) |
| Schedule a mentorship session | `bc-mentorship-*` + `bc-notify-*` (session confirmation messaging) |
| Send a notification | `bc-notify-*` + the domain that triggered the notification |
| Inbound signups, attribution, and acquisition (forms + invites) | `bc-marketing-inbound-leads-attribution-and-acquisition` (covers `/v1/marketing` lead capture/analytics + `/v1/auth` invite-based signup attribution, plus referral and webhook context) |
| Onboard a new student | `bc-admissions-*` + `bc-payments-*` + `bc-authenticate-*` |
| Connect a third-party app to student authentication (hosted login redirect + callback token) | `bc-authenticate-student-authentication` |
| Provision a resource for a student | `bc-provisioning-*` + `bc-admissions-*` (verify enrollment status first) |
| Create and run an NPS-style cohort satisfaction study | `bc-feedback-create-manage-nps-survey` + `bc-admissions-*` (resolve target cohorts before configuration scope or `send_emails`) |
| Configure academy VPS provisioning (profiles, credentials, settings) | `bc-provisioning-settings-and-credentials` |
| Create or edit an academy event with tags and workshop asset selection | `bc-events-create-and-edit-event` + `bc-marketing-*` (fetch valid `DISCOVERY` tags) + `bc-registry-*` (search and validate workshop assets by type) |
| Connect Luma webhooks for real-time guest registration and check-in | `bc-events-configure-luma-webhooks` + `bc-events-create-and-edit-event` (set `luma_id` on the event) + `bc-marketing-*` (ActiveCampaign automation for registrations) |
| Configure academy Slack integration and manage sync health | `bc-notify-manage-academy-slackintegration` + `bc-admissions-*` (students/cohorts drive Slack mappings) + `bc-authenticate-*` (Slack OAuth endpoints live in auth) |
| Build or debug a frontend dashboard that reads monitoring reports | `bc-monitoring-read-reports-api` + `bc-authenticate-*` (academy-scoped capability and header requirements drive access outcomes) |
| Read acquisition monitoring insights (funnel tiers, top assets, top workshops, attribution mix) | `bc-monitoring-read-report-acquisition` + `bc-authenticate-*` (academy-scoped capability and `Academy` header drive access and scope) |
| Create a marketing course from scratch or by cloning another course | `bc-marketing-create-or-clone-course` + `bc-authenticate-*` (staff list: `GET /v1/marketing/academy/course` with comma-separated numeric `Academy` ids and `crud_course` read-aggregate; create/clone: `POST` with `Academy` header; clone requires `crud_course` on source course academy too) |
| Diagnose why graduation/certificate auto-issuance did not happen for a student or cohort | `bc-certificate-manage-and-assign-specialties` + `bc-admissions-*` (use `GET /v1/certificate/diagnostic` with `kind=graduation|certificate`, plus academy-scoped capability/header) |
| Align or extend syllabus design with the school skills framework (job role stages, skills on the go) | `bc-admissions-*` (syllabus, cohorts) + `bc-talentdevelopment-manage-skills` (career path, stages, `stage_skill`, domains) |
| Cancel a user subscription and optionally issue a refund | `bc-payments-cancel-subscription-and-refund` + [`docs/llm-docs/BC_REFUNDS.md`](../../BC_REFUNDS.md) (use the skill for actor-specific flow and endpoint order, then use BC_REFUNDS for refund payload semantics and validations) |
| Diagnose why an asset telemetry is missing for users/tasks | `bc-assignment-diagnose-asset-telemetry` + `bc-registry-*` (validate asset slug and translation/canonical context when telemetry appears split by locale) |
| Queue or interpret asset-level telemetry_stats (`telemetry_stats` JSON on assets) | `bc-assignment-diagnose-asset-telemetry` + `bc-registry-*` (registry asset action `sync_telemetry_stats` queues Celery recompute; read updated stats from asset) |
| Inspect incoming LearnPack telemetry webhook logs by student/event/asset/package filters | `bc-assignment-diagnose-asset-telemetry` + `bc-authenticate-*` (academy capability/header scope and identity checks) |
| Delete LearnPack webhook logs (single or bulk cleanup) | `bc-assignment-diagnose-asset-telemetry` + `bc-authenticate-*` (cleanup is academy-scoped and restricted to `ERROR` webhooks; bulk delete requires `status=ERROR`) |
| Configure per-academy LearnPack telemetry webhook ignore rules (by user, package, asset slug, or event) | `bc-assignment-diagnose-asset-telemetry` — use `GET`/`PUT /v1/assignment/academy/learnpack/telemetry-webhook-ignore` (rules are stored under `learnpack_features.telemetry_webhook_ignore` on academy auth settings) |
| Review **PROJECT** syllabus tasks (list pending **`DONE`** deliveries oldest-first, load asset **`config`**, submit **`PUT`** approval/rejection — **ignoring** uses the same **`PUT`** with **`revision_status=IGNORED`**, not a separate route) | [`bc-assignment-review-submit-task-revision`](../bc-assignment-review-submit-task-revision/SKILL.md) + registry asset read (`GET /v1/registry/asset/{slug}`) + `bc-authenticate-*` (token / headers as needed) |

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
