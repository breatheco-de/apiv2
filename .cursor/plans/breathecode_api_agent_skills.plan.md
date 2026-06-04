# BreatheCode API Agent Skills Plan (Revised)

Agent skills for an **OpenClaw agent** using **BREATHECODE_TOKEN** from the environment. Only **academy-relevant, capability-restricted** endpoints are documented. Designed to **work in practice** and **avoid context bloat** (short playbook + references + wrapper script + canonical outputs).

---

## Scope: Academy + Capabilities Only

**Document in skills:**
- Endpoints whose path contains **`/academy/`** (or are explicitly academy-scoped) and are protected by **`@capable_of("capability_slug")`** in the codebase.
- Required headers: `Authorization: Token {BREATHECODE_TOKEN}`, and for academy endpoints **`Academy: <academy_id_or_slug>`**.
- How to discover what the token can do: **`GET /v1/auth/me/academy/<slug_or_id>/capabilities`** (returns list of capability slugs for that academy; auth via token only, no Academy header).

**Do not document in skills:**
- Public/unauthenticated endpoints (login, OAuth, password reset, invite acceptance, etc.).
- Endpoints that are not academy-scoped or not restricted by capabilities (e.g. other permission models).
- Every v1 endpoint; only those that are both academy-relevant and capability-gated.

**Capability model (from codebase):**
- [breathecode/utils/decorators/capable_of.py](breathecode/utils/decorators/capable_of.py): enforces Academy header/param and checks `ProfileAcademy` + role capabilities.
- [breathecode/authenticate/role_definitions.py](breathecode/authenticate/role_definitions.py): single source of truth for capability slugs and descriptions.
- 403 response when capability is missing: `"You (user: X) don't have this capability: <slug> for academy Y"`.

---

## Practice-First Recommendations

### 1) SKILL.md = Short Playbook; Details in references/

**SKILL.md is a playbook, not the full API docs.**

- **In SKILL.md:** Auth method summary (where token goes, env var names); base URL + gotchas (pagination, rate limits, timezones); 5–10 high-value workflows; explicit: *"When you need endpoint details, read references/endpoints.md"*.
- **In references/:** `references/endpoints.md` (capability → academy endpoints, path, method); `references/auth.md` (token, capability discovery, 401/403, no secrets); `references/examples.md` (example requests/responses, script usage).

### 2) Wrapper Script (Multiplier)

**Include `scripts/breathecode.py`** (or `.ts`) so the agent doesn’t re-implement requests every time.

- **Auth from env:** `BREATHECODE_TOKEN`, `BREATHECODE_BASE_URL`.
- **Academy header:** e.g. `--academy <id_or_slug>` for academy-scoped calls.
- **Pagination:** auto-follow `next` (or limit/offset) so "get all" is one command.
- **Retries/backoff:** on 429 and 5xx (e.g. exponential backoff, max 3 retries).
- **Output:** `--json` (default) and `--csv`; optionally write to file in workspace.

Example CLI: `breathecode.py get cohorts --academy 1 [--json|--csv] [--out file.json]`. Makes usage **deterministic and cheap**.

### 3) Canonical Tool Outputs

**Pick one pattern and stick to it** (document in SKILL.md):

- **JSON** for programmatic follow-ups; **CSV** for spreadsheets.
- **Recommended:** **Bullets (human summary) + save raw JSON/CSV to a file** in workspace.

### 4) No Secrets in the Skill

- Document **how** auth works; never store or reference actual tokens.
- **Guidance:** "Set BREATHECODE_TOKEN in your environment"; "Never paste tokens into chat."

### 5) Trigger Examples (For You + Future You)

**Include "user prompts that should trigger this skill"** (in SKILL.md or author notes):

- "Pull all active cohorts"
- "Export all students for cohort X"
- "Find users who haven't completed assignment Y"
- "List my capabilities for academy Z"

Keeps the skill used consistently (especially when authoring in Cursor + Claude).

### 6) Version the Skill Like Code

| Version | Scope |
|--------|--------|
| **v0** | Auth + 2 endpoints (e.g. get capabilities, get cohorts). Prove token + Academy + script. |
| **v1** | Pagination + exports: script auto-follows next, --csv/--json; 5–10 workflows in playbook. |
| **v2** | "Business meaning": what fields matter, mappings, joins (e.g. cohort slug vs id, status values). |

---

## Skill Layout (Single Skill Dir)

One skill directory; SKILL.md stays small in context.

```
.cursor/skills/breathecode-api/
├── SKILL.md                 # Playbook only: auth summary, gotchas, 5–10 workflows, "read references/..."
├── references/
│   ├── auth.md              # Env vars, capability discovery, 401/403; no secrets
│   ├── endpoints.md         # Capability → academy endpoints (path, method)
│   └── examples.md          # Example requests/responses, script usage
└── scripts/
    └── breathecode.py       # Auth, pagination, retries, --json / --csv
```

**SKILL.md (playbook):** Auth summary; gotchas (pagination, 429, timezones); 5–10 workflows (see list below) + "For details see references/endpoints.md"; "When you need endpoint details, read references/endpoints.md and references/examples.md"; trigger examples; canonical output (bullets + save raw to file).

**High-value workflows:** (1) Get my capabilities (2) Get cohorts (3) Get single cohort (4) Get students / by cohort (5) Export students CSV/JSON (6) Get assignments/tasks (7) Find users who haven't completed assignment Y (8) Get current user (9) Validate token. Exact paths in references/endpoints.md.

---

## 1. BreatheCode API – Basics

**Path:** `.cursor/skills/breathecode-api-basics/`

**SKILL.md:**
- **Environment:** `BREATHECODE_TOKEN` (required); `BREATHECODE_API_URL` (optional, default e.g. `https://breathecode.herokuapp.com`).
- **Headers:** `Authorization: Token {BREATHECODE_TOKEN}`; `Content-Type: application/json` for JSON bodies.
- **Academy-scoped requests:** Any request to an endpoint whose path contains **`/academy/`** must include **`Academy: <academy_id_or_slug>`**. Academy ID/slug may come from task context or env (document the pattern).
- **Errors:** Standard shape `detail`, `slug`, `status_code`, optional `data`. 401 = token invalid/expired; 403 = forbidden (e.g. missing capability for that academy); 404, 429, 500 as usual.
- **Versioning:** Document v1 as primary; academy endpoints live under paths like `/v1/auth/academy/`, `/v1/admissions/academy/`, etc.
- **Scope of documentation:** Only academy-relevant, capability-restricted endpoints are documented in the BreatheCode API skills; other endpoints are out of scope.

No list of endpoints in Basics; that lives in the reference.

---

## 2. BreatheCode API – Authentication

**Path:** `.cursor/skills/breathecode-api-authentication/`

**SKILL.md:**
- Use **BREATHECODE_TOKEN** from env for all authenticated requests; agent does not perform login, OAuth, or invite flows.
- **Token validation:** `GET /v1/auth/token/{token}` (inspect/validate token).
- **Current user:** `GET /v1/auth/user/me` (who am I).
- **Capability discovery:** **`GET /v1/auth/me/academy/<slug_or_id>/capabilities`** — no Academy header; returns a JSON array of capability slugs the authenticated user has for that academy. Use this to know which academy endpoints the token is allowed to call.
- **403 capability errors:** If the API returns 403 with a message like "You don't have this capability: X for academy Y", the token’s roles for that academy do not include the required capability; refer to the capability–endpoint reference to see which capability is required.
- No login, OAuth, invites, or password reset in the instructions.

---

## 3. Capability–Endpoint Reference

**Purpose:** Single place that lists only **academy, capability-restricted** endpoints.

**Options:**
- **A) reference.md** inside `breathecode-api-basics` or `breathecode-api-authentication`: tables or lists by capability (e.g. `read_student` → list of paths/methods) or by domain (auth, admissions, assignments, …) with required capability per endpoint.
- **B) Generated doc:** Script or one-off that greps `@capable_of("...")` and URL config to build a capability → (path, method, view) map; output a markdown file committed under `.cursor/skills/` or `docs/`.

**Source of truth:** [breathecode/utils/decorators/capable_of.py](breathecode/utils/decorators/capable_of.py), [breathecode/authenticate/role_definitions.py](breathecode/authenticate/role_definitions.py), and the various `urls.py` + view classes that use `@capable_of` (authenticate, admissions, assignments, events, feedback, registry, payments, certificate, marketing, activity, assessment, freelance, mentorship, etc.).

**Content:** For each capability slug that guards at least one academy endpoint, list the endpoint path(s) and HTTP method(s). Optionally one-line description. Do not include endpoints that are not academy-scoped or not protected by capabilities.

---

## OpenClaw and Env Contract

- **Env:** OpenClaw (or runner) must set **BREATHECODE_TOKEN**. Optionally **BREATHECODE_BASE_URL** (or BREATHECODE_API_URL) and, for academy endpoints, **academy id or slug** (task or env) for the `Academy` header.
- **Secrets:** Document how auth works only; "Set BREATHECODE_TOKEN in your environment"; "Never paste tokens into chat." Skill path: `.cursor/skills/breathecode-api/`.

---

## Implementation Order (v0 to v2)

1. **v0:** references/auth.md; SKILL.md playbook (auth summary + 2 workflows: capabilities, cohorts); script stub (auth + one GET with Academy, no pagination yet).
2. **v1:** references/endpoints.md (capability to academy endpoints); references/examples.md; script: pagination, retries, --json/--csv; playbook: 5–10 workflows, gotchas, "read references/...", trigger examples, canonical output (bullets + file).
3. **v2 (optional):** references/glossary.md or fields.md (business meaning, mappings); extend workflows (e.g. find incomplete assignments).

---

## Sources

- [breathecode/utils/decorators/capable_of.py](breathecode/utils/decorators/capable_of.py) — capability check, Academy header requirement.
- [breathecode/authenticate/role_definitions.py](breathecode/authenticate/role_definitions.py) — capability slugs and descriptions.
- [breathecode/authenticate/views.py](breathecode/authenticate/views.py) — AcademyCapabilitiesView: `GET /v1/auth/me/academy/<slug_or_id>/capabilities`.
- [breathecode/authenticate/urls/v1.py](breathecode/authenticate/urls/v1.py) — auth URL routing (e.g. path for capabilities).
- [docs/LLM-DOCS/AUTHENTICATION.md](docs/LLM-DOCS/AUTHENTICATION.md), [docs/LLM-DOCS/BC_AUTH_FIRST_PARTY_APPS.md](docs/LLM-DOCS/BC_AUTH_FIRST_PARTY_APPS.md) — header format, base URL, Academy header.
- Grep `@capable_of` across `breathecode/*/views.py` and url configs to build the capability–endpoint map.
