---
name: breathecode-api-index
description: Always load this skill first when working with the BreatheCode API. It maps user requests to the correct domain skill(s) to load next. Do NOT use this skill to execute API calls directly — it only routes to other skills.
requires: []
---

# BreatheCode API Index

This skill is the entry point for all BreatheCode API interactions. Its only job is to help you identify which domain skill(s) to load before taking any action. Do not attempt to call the API using only this skill — always load the relevant domain skill(s) first.

## When to Use

- Load this skill at the start of every BreatheCode API task, before loading any other skill.
- Use it whenever the user's request is ambiguous and you are unsure which domain applies.
- Use it when a task spans multiple domains to identify all required skills upfront.
- Do NOT use this as a substitute for the domain skill — always proceed to load the specific skill after consulting this index.

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
| **assignment** | Student task deliveries, project submissions, revision requests | `bc-assignment-*` |
| **authenticate** | Login, token generation, password reset, permissions, API key management | `bc-authenticate-*` |
| **career** | Job listings, job applications post-graduation, employer connections | `bc-career-*` |
| **certificate** | Certificate emission, specialties, certificate-syllabus associations | `bc-certificate-*` |
| **events** | Workshops, live classes, event RSVPs, event checkins | `bc-events-*` |
| **feedback** | NPS surveys, student satisfaction studies, feedback forms | `bc-feedback-*` |
| **marketing** | URL shortener, incoming leads, lead scoring, UTM tracking | `bc-marketing-*` |
| **media** | Images, videos, documents used in LMS content, asset management | `bc-media-*` |
| **mentorship** | Mentors, mentor availability, session scheduling, session notes | `bc-mentorship-*` |
| **notify** | Email, SMS, WhatsApp messaging, notification templates, delivery status | `bc-notify-*` |
| **payments** | Billing plans, invoices, subscriptions, shop items, payment history | `bc-payments-*` |
| **provisioning** | Student VPS servers, Codespaces containers, provisioning requests | `bc-provisioning-*` |
| **registry** | Learning assets — lessons, exercises, projects, asset versioning | `bc-registry-*` |

---

## Common Cross-Domain Workflows

Some user requests touch multiple domains. Load ALL listed skills before proceeding.

| User Request | Skills to Load |
|---|---|
| Create a cohort | `bc-admissions-create-cohort` + `bc-certificate-*` (syllabus must have an associated specialty) |
| Create a macro cohort | `bc-admissions-create-macro-cohort` + `bc-certificate-*` + `bc-admissions-create-cohort` |
| Enroll a student in a cohort | `bc-admissions-enroll-student` + `bc-payments-*` (student must have a valid plan) |
| Issue a certificate to a student | `bc-certificate-*` + `bc-admissions-*` (verify cohort completion status) |
| Schedule a mentorship session | `bc-mentorship-*` + `bc-notify-*` (session confirmation messaging) |
| Send a notification | `bc-notify-*` + the domain that triggered the notification |
| Onboard a new student | `bc-admissions-*` + `bc-payments-*` + `bc-authenticate-*` |
| Provision a resource for a student | `bc-provisioning-*` + `bc-admissions-*` (verify enrollment status first) |
| Configure academy VPS provisioning (profiles, credentials, settings) | `bc-provisioning-settings-and-credentials` |
| Configure academy Slack integration and manage sync health | `bc-notify-manage-academy-slackintegration` + `bc-admissions-*` (students/cohorts drive Slack mappings) + `bc-authenticate-*` (Slack OAuth endpoints live in auth) |

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
- **Required header:** Send the **`Academy`** header with the academy ID (e.g. `Academy: 1`). Missing it returns an error (e.g. "Missing academy_id... or 'Academy' header").
- **Examples:** `/v1/admissions/academy/cohort/user`, `/v1/assessment/academy/user/assessment`, `/v1/assignments/academy/coderevision/<id>`.

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
