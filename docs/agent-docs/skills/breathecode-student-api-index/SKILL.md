---
name: breathecode-student-api-index
description: Load first for authenticated learner BreatheCode API work (user-scoped /me and user/me routes, public join/catalog where applicable). Maps requests to domain skills. Do NOT use for academy admin tasks requiring /academy/ or the Academy header — use breathecode-staff-api-index instead.
requires: []
---

# BreatheCode Student API Index

This skill is the entry point for **learner-scoped** BreatheCode API work. Its only job is to help you identify which domain skill(s) to load before taking any action. Do not attempt to call the API using only this skill — always load the relevant domain skill(s) first.

## When to Use

- Load this skill at the start of tasks for an **authenticated student** or end-user (paths such as **`…/me…`**, **`…/user/me…`**, or public discovery/join flows that do not require staff capabilities).
- Use it when the request spans multiple **learner** domains (for example assignments plus events).
- Do NOT use this as a substitute for the domain skill — always proceed to load the specific skill after consulting this index.

## Related index

If the task requires **`/academy/`** routes, the **`Academy`** header, or **staff capabilities**, load [`breathecode-staff-api-index`](../breathecode-staff-api-index/SKILL.md) instead of this file.

---

## Staff-first domains

These areas are primarily documented for **academy staff** in the staff index. If the user’s goal clearly belongs here, switch to [`breathecode-staff-api-index`](../breathecode-staff-api-index/SKILL.md): **monitoring**, **marketing**, **talent development** (`/v1/talent/` academy paths).

---

## Workflow

1. Read the user's request.
2. Identify the domain(s) from the table below.
3. Load the corresponding skill(s) before proceeding.
4. If the task spans multiple domains, load all relevant skills and check each one for cross-domain instructions before calling any endpoint.

---

## Domain Map (learner scope)

| Domain | Covers (learner-facing) | Skill to Load |
|---|---|---|
| **admissions** | My cohorts, enrollment visibility, syllabus consumption as a student | `bc-admissions-*` |
| **activity** | My engagement, daily summaries, login streaks | `bc-activity-*` |
| **assessment** | My quizzes and attempts | `bc-assessment-*` |
| **assignment** | My tasks, submissions, final project, LearnPack telemetry ingestion | `bc-assignment-*`, [`bc-assignment-diagnose-asset-telemetry`](../bc-assignment-diagnose-asset-telemetry/SKILL.md) (for `POST …/me/telemetry` and related learner diagnostics) |
| **authenticate** | Login, token, hosted redirect, academy-scoped capabilities + academy-less permissions for the current user | `bc-authenticate-*`, [`bc-authenticate-student-authentication`](../bc-authenticate-student-authentication/SKILL.md) |
| **career** | Job listings and applications after graduation | `bc-career-*` |
| **certificate** | My issued certificates | `bc-certificate-*` |
| **events** | My workshops, RSVPs, check-ins, live class join | `bc-events-*`, [`bc-events-create-and-edit-event`](../bc-events-create-and-edit-event/SKILL.md) (where it documents student-facing paths) |
| **feedback** | Surveys assigned to me, responses | `bc-feedback-*`, [`bc-feedback-create-manage-feedback-survey`](../bc-feedback-create-manage-feedback-survey/SKILL.md) |
| **media** | Media used in learning content | `bc-media-*` |
| **mentorship** | My mentorship sessions and bills | `bc-mentorship-*` |
| **notify** | My notification hooks / subscriptions where exposed under user-scoped routes | `bc-notify-*` |
| **payments** | My plans, subscriptions, invoices, shop purchases | `bc-payments-*`, [`bc-payments-cancel-subscription-and-refund`](../bc-payments-cancel-subscription-and-refund/SKILL.md) |
| **provisioning** | My VPS, containers, or LiteLLM API keys / budget entitlement | `bc-provisioning-*`, [`bc-provisioning-manage-vps-server`](../bc-provisioning-manage-vps-server/SKILL.md), [`bc-provisioning-manage-my-llm-keys`](../bc-provisioning-manage-my-llm-keys/SKILL.md) |
| **registry** | Reading learning assets (lessons, exercises, projects) | `bc-registry-*` |

---

## Common Cross-Domain Workflows (learner)

Some user requests touch multiple domains. Load ALL listed skills before proceeding.

| User Request | Skills to Load |
|---|---|
| Log in or connect a third-party app using hosted student auth (redirect + callback token) | [`bc-authenticate-student-authentication`](../bc-authenticate-student-authentication/SKILL.md) |
| List, request, or deprovision **my** VPS | [`bc-provisioning-manage-vps-server`](../bc-provisioning-manage-vps-server/SKILL.md) + `bc-authenticate-*` (token) |
| List, create, or delete **my** LiteLLM API keys; check LLM budget entitlement or key spend | [`bc-provisioning-manage-my-llm-keys`](../bc-provisioning-manage-my-llm-keys/SKILL.md) + [`bc-authenticate-student-authentication`](../bc-authenticate-student-authentication/SKILL.md) |
| View or cancel **my** subscription (and optional refund flow when applicable) | [`bc-payments-cancel-subscription-and-refund`](../bc-payments-cancel-subscription-and-refund/SKILL.md) + `bc-authenticate-*` |
| See **my** events, join, check in, or live class | [`bc-events-create-and-edit-event`](../bc-events-create-and-edit-event/SKILL.md) + `bc-authenticate-*` (student-facing event paths) |
| Send LearnPack / package telemetry as the current user | [`bc-assignment-diagnose-asset-telemetry`](../bc-assignment-diagnose-asset-telemetry/SKILL.md) + `bc-authenticate-*` |
| See **my** joined cohorts and progress (including self-paced `never_ends`) | [`bc-admissions-read-student-my-cohorts-and-progress`](../bc-admissions-read-student-my-cohorts-and-progress/SKILL.md) + `bc-authenticate-*` |

## Routing Rules

**When only one domain is involved:** Load the single matching skill and proceed.

**When multiple domains are involved:** Load all relevant skills, read each one fully, then identify any conflict or ordering constraint between them before calling any endpoint.

**When no skill exists yet for the task:** Fall back to the BreatheCode API documentation directly. Do not guess endpoint behavior — ask the user to confirm the correct endpoint or create a new skill for the use case.

**When unsure which domain applies:** Re-read the domain map above. If still ambiguous, ask the user to clarify before proceeding — do not assume.

---

## API Conventions

Assume these conventions for all BreatheCode API endpoints unless a domain skill or endpoint docs say otherwise.

### Pagination

- **Default:** List endpoints are paginated unless the domain skill or endpoint docs say otherwise.
- **Query params:** `limit` (default 20), `offset` (default 0).
- **Paginated response:** When envelope is used, the body has `count`, `first`, `next`, `previous`, `last`, and `results`; headers include `X-Total-Count` and `Link`.

### Learner-scoped routing

- Prefer endpoints documented under **`Authorization`** for the **current user**, including paths containing **`/me/`** or **`/user/me/`**, and public catalog endpoints where no staff scope is required.
- **Do not** call **`/academy/`** routes or send the **`Academy`** header for staff operations unless the authenticated user is staff and the task explicitly requires it; if it does, use [`breathecode-staff-api-index`](../breathecode-staff-api-index/SKILL.md).

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

1. [ ] Confirmed the task is learner-scoped (not staff-only); otherwise switched to the staff index.
2. [ ] Identified the domain(s) from the domain map.
3. [ ] Loaded all relevant skill(s) before calling any endpoint.
4. [ ] If cross-domain, checked the learner workflow table and loaded all required skills.
5. [ ] If no skill exists for the task, flagged this to the user rather than guessing.
