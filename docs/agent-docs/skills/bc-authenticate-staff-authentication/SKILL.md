---
name: bc-authenticate-staff-authentication
description: Use when implementing or troubleshooting staff authentication (login/token flows, academy context, capability lookup to decide access, integration token, staff-assisted password/GitHub reset, first-party app token exchange); do NOT use for student self-service auth, staff member/invite administration, or custom role management.
requires:
  - bc-authenticate-student-authentication
---

# Skill: Staff Authentication Workflows

## When to Use

Use this skill when the user needs to authenticate a **staff member** (teacher, admin, coordinator, custom academy role), check **what that staff user can do** in an academy, obtain an academy integration token, or run staff-assisted password/GitHub reset for a known member. Staff admin UIs and external 4Geeks apps can authenticate staff via **universal hosted login** (browser redirect to the API login form) — not only via `POST /login/`. Do not use it for student self-service auth (use [`bc-authenticate-student-authentication`](../bc-authenticate-student-authentication/SKILL.md)), staff member/invite administration (use [`bc-authenticate-staff-invites`](../bc-authenticate-staff-invites/SKILL.md)), or custom role CRUD (future `bc-authenticate-manage-academy-roles` skill).

## Concepts

- **Login token**: Same as students — `Authorization: Token <token>` on all authenticated calls.
- **Universal hosted login**: API-hosted HTML login for **cross-app browser authentication**. Staff admin UIs and external 4Geeks apps redirect users to `GET /v1/auth/view/login?url=<callback>` instead of building their own login UI. The `url` query param is the callback where the user returns after success (plain HTTPS or Base64-encoded — API auto-detects). Returns the same `login` token as `POST /v1/auth/login/`; successful auth redirects to `<callback>?token=<login_token>&attempt=1`.
- **ProfileAcademy**: Links user ↔ academy ↔ role. Every staff capability check resolves through this relationship for a **specific academy**.
- **Capabilities (staff-only authorization layer)**: Fine-grained slugs on the role (e.g. `crud_cohort`, `read_member`). Staff access to `/academy/*` routes is gated by capabilities plus the `Academy` header. Staff do **not** use the academy-less permissions layer for staff work.
- **`permissions[]` on `user/me`**: Django group permissions may appear in the response; **ignore them for staff workflows** — they apply to learner routes, not academy admin.
- **Academy header**: Required on `/academy/*` calls and on single-capability probes. Use numeric academy id: `Academy: 1`.
- **Token types**: `login` (normal session), `permanent` (academy integration token), `temporal` (password/GitHub reset links).

## Workflow — Track A: Authenticate a staff member

Staff use the **same login entrypoints as students**. OAuth/GitHub callback details live in the student skill; this track covers the staff login path end-to-end.

1. **Choose auth flow.**
   - `POST /v1/auth/login/` — API/SPA with email + password.
   - `GET /v1/auth/view/login?url=<callback>` — browser hosted login; successful auth redirects to callback with `?token=` (see subsection below).
   - OAuth (`/github`, `/google`, etc.) — see [`bc-authenticate-student-authentication`](../bc-authenticate-student-authentication/SKILL.md) for callback URL handling.

### Universal hosted login (cross-app browser auth)

Other BreatheCode apps authenticate staff by redirecting the browser to the API login page instead of building their own login UI. OAuth uses a different entrypoint but the same `url` callback pattern — see the student skill for OAuth details.

1. App redirects user to `GET /v1/auth/view/login?url=<callback>` (`url` required; plain HTTPS or Base64-encoded).
2. User submits email/password on the API HTML form.
3. API redirects to `<callback>?token=<login_token>&attempt=1`.
4. App reads `token` from the query string, stores it, and sends `Authorization: Token <token>` on API calls.
5. Continue Track A from step 4 — call `GET /v1/auth/user/me` and filter non-`student` entries in `roles[]`.

2. **Capture token and persist it securely.**
   - API login returns `token` in JSON.
   - Hosted login returns `token` in redirect querystring.
   - Send `Authorization: Token <token>` on all subsequent requests.

3. **Validate token (optional).**
   Call `GET /v1/auth/token/<token>` when debugging stale sessions.

4. **Load staff identity.**
   Call `GET /v1/auth/user/me`. Read `roles[]` — each entry is a ProfileAcademy row with `academy` and `role`. **Staff academies** = entries where `role.slug` is not `student` (e.g. `staff`, `teacher`, `admin`, `country_manager`, or custom `{slug}_{academy_id}` roles).

5. **First-time staff only (before step 1 if no account yet).**
   Pending invite with no password: follow [`bc-authenticate-staff-invites`](../bc-authenticate-staff-invites/SKILL.md) workflow step 14 (`GET/POST /v1/auth/member/invite/<token>`), then continue from step 1 here with the returned token.

6. **Logout.**
   Call `POST /v1/auth/logout/` and clear local token state.

## Workflow — Track B: Retrieve capabilities (can this staff user do X?)

Use this track when building staff UIs or before calling `/academy/*` endpoints. Staff have **no academy-less permission layer** — always use capabilities + academy context.

1. **Prerequisite** — completed Track A; hold a valid `Authorization: Token <token>`.

2. **Pick the academy** — from `user/me` → `roles[]`, select the academy for the action. If the user has multiple staff academies, choose one before any capability check. Record `academy.id` (numeric).

3. **List all capabilities for that academy** — call `GET /v1/auth/me/academy/<slug_or_id>/capabilities` with `Authorization`. Response is a sorted array of capability slug strings. Use this when rendering menus, enabling buttons, or prefetching dashboard access.

4. **Check one specific capability** (before a gated endpoint) — either:
   - **Client-side:** confirm the required slug is in the list from step 3, or
   - **Server probe:** `GET /v1/auth/user/me/capability/<capability_slug>` with `Authorization` and **`Academy: <academy_id>`**.
   - **200** `{"status":"ok"}` → user has the capability; safe to call the domain endpoint (still send `Academy` on the actual call).
   - **403** → user lacks the capability; do not call the domain endpoint.

5. **Call the domain endpoint** — every `/academy/*` request must include `Academy: <academy_id>` matching the academy from steps 2–4.

### Decision guide

| Question | Action |
|----------|--------|
| Is this user staff? | `user/me` → any `roles[]` with non-`student` slug |
| Which academies can they work in? | `user/me` → `roles[].academy` for non-student roles |
| What can they do in academy X? | `GET /me/academy/X/capabilities` |
| Can they call an endpoint requiring `crud_cohort`? | List contains `crud_cohort` OR probe `/user/me/capability/crud_cohort` + `Academy: X` |
| 403 on a domain call? | Re-run step 4; verify `Academy` header matches the chosen academy |

## Workflow — Optional staff-only flows

Run only when the task requires them (not part of default login + capability check):

1. **Academy integration token** — `GET/POST /v1/auth/academy/token/` with `Authorization` and `Academy: <academy_id>` (`get_academy_token` / `generate_academy_token`). Returns a `permanent` token for automation; synthetic academy user with role `academy_token`.

2. **Staff-assisted known-user reset** — `POST /v1/auth/member/<profile_academy_id>/token` (`generate_temporal_token`) returns `reset_password_url` and `reset_github_url`. `POST /v1/auth/member/<profileacademy_id>/password/reset` (`send_reset_password`) emails a reset link.

3. **First-party app token exchange** — `POST /v1/auth/app/token` with body `{ "token": "<one_time_token>" }` (linked-services scope `read:token`). Returns login token metadata (`token`, `token_type`, `expires_at`, `user_id`, `email`). Invalid or missing token returns `401` `invalid-token`.

4. **Staff invites (admin or accept)** — load [`bc-authenticate-staff-invites`](../bc-authenticate-staff-invites/SKILL.md).

## Endpoints

All paths below are under `/v1/auth`. Unless noted, responses are not paginated. Send `Accept-Language` (`en`, `es`) for translated errors where applicable.

### Track A — authenticate

| Action | Method | Path | Required headers | Body | Important response |
|--------|--------|------|------------------|------|-------------------|
| API login | POST | `/v1/auth/login/` | `Content-Type: application/json` | `email`, `password` | `token`, `user_id`, `email`, `expires_at` |
| Hosted login page | GET | `/v1/auth/view/login?url=<callback>` | None | None | HTML form, then redirect to callback with `?token=<login_token>&attempt=1` |
| Token info | GET | `/v1/auth/token/<token>` | None | None | `token`, `token_type`, `expires_at`, `user_id` |
| Current user | GET | `/v1/auth/user/me` | `Authorization` | None | `roles[]` (staff academies); ignore `permissions[]` for staff |
| Logout | POST | `/v1/auth/logout/` | `Authorization` | None | success; clear client token |

### Track B — capability lookup

| Action | Method | Path | Required headers | Body | Important response |
|--------|--------|------|------------------|------|-------------------|
| List capabilities for academy | GET | `/v1/auth/me/academy/<slug_or_id>/capabilities` | `Authorization` | None | sorted array of capability slugs |
| Check one capability | GET | `/v1/auth/user/me/capability/<capability_slug>` | `Authorization`, **`Academy: <id>`** (or `?academy=`) | None | `{"status":"ok"}` or **403** |

### Optional — staff-only

| Action | Method | Path | Required headers | Capability | Important response |
|--------|--------|------|------------------|------------|-------------------|
| Read integration token | GET | `/v1/auth/academy/token/` | `Authorization`, **`Academy: <id>`** | `get_academy_token` | `token`, `token_type`, `expires_at` |
| Generate integration token | POST | `/v1/auth/academy/token/` | `Authorization`, **`Academy: <id>`** | `generate_academy_token` | same shape as GET |
| Temporal token + reset URLs | POST | `/v1/auth/member/<profile_academy_id>/token` | `Authorization`, **`Academy: <id>`** | `generate_temporal_token` | `key`, `reset_password_url`, `reset_github_url` |
| Staff password reset email | POST | `/v1/auth/member/<profileacademy_id>/password/reset` | `Authorization`, **`Academy: <id>`** | `send_reset_password` | temporal token metadata |
| Exchange one-time app token | POST | `/v1/auth/app/token` | linked-services scope | `read:token` | login token |

**Out of scope (load other skills):**

- Staff member/invite administration → [`bc-authenticate-staff-invites`](../bc-authenticate-staff-invites/SKILL.md)
- Custom role CRUD → future `bc-authenticate-manage-academy-roles` skill
- Student auth, permissions, GitHub self-service → [`bc-authenticate-student-authentication`](../bc-authenticate-student-authentication/SKILL.md)

### API login request sample

```json
{
  "email": "teacher@example.com",
  "password": "StrongPassword123!"
}
```

### API login response sample

```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "user_id": 456,
  "email": "teacher@example.com",
  "expires_at": "2026-12-31T23:59:59Z"
}
```

### Universal hosted login URL sample

`url` may be a plain HTTPS callback or Base64-encoded; the API auto-detects.

```text
https://breathecode.herokuapp.com/v1/auth/view/login?url=https%3A%2F%2Fadmin.example.com%2Fauth%2Fcallback
```

### Universal hosted login redirect sample

```text
https://admin.example.com/auth/callback?token=9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b&attempt=1
```

### Current user response sample — staff (`GET /v1/auth/user/me`)

```json
{
  "id": 456,
  "email": "teacher@example.com",
  "username": "teacher456",
  "first_name": "Alex",
  "last_name": "Rivera",
  "date_joined": "2024-03-15T10:00:00Z",
  "github": null,
  "profile": {
    "id": 120,
    "avatar_url": "https://cdn.example.com/avatar.png",
    "bio": "Lead instructor"
  },
  "roles": [
    {
      "id": 88,
      "academy": {
        "id": 1,
        "slug": "miami",
        "name": "4Geeks Miami"
      },
      "role": {
        "slug": "teacher",
        "name": "Teacher"
      }
    },
    {
      "id": 91,
      "academy": {
        "id": 4,
        "slug": "downtown-miami",
        "name": "4Geeks Downtown Miami"
      },
      "role": {
        "slug": "staff",
        "name": "Staff (Base)"
      }
    }
  ],
  "permissions": [],
  "settings": {
    "lang": "en",
    "main_currency": "USD"
  }
}
```

### Academy capabilities response sample

```json
[
  "crud_activity",
  "crud_cohort",
  "read_all_cohort",
  "read_assignment",
  "read_member",
  "read_my_academy",
  "read_student",
  "read_syllabus"
]
```

### Capability check success sample

```json
{
  "status": "ok"
}
```

### Capability check failure sample (403)

```json
{
  "detail": "You (user: 456) don't have this capability: crud_member for academy 1",
  "status_code": 403
}
```

### Academy integration token response sample

```json
{
  "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "token_type": "permanent",
  "expires_at": null
}
```

### Staff temporal token response sample

```json
{
  "user": {
    "id": 789,
    "email": "member@example.com",
    "first_name": "Sam",
    "last_name": "Lee",
    "username": "samlee"
  },
  "key": "f6e5d4c3b2a1",
  "reset_password_url": "https://api.example.com/v1/auth/password/f6e5d4c3b2a1",
  "reset_github_url": "https://api.example.com/v1/auth/github/f6e5d4c3b2a1"
}
```

### First-party app token exchange — request sample

```json
{
  "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
}
```

### First-party app token exchange — response sample

```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "token_type": "login",
  "expires_at": "2026-12-31T23:59:59Z",
  "user_id": 456,
  "email": "teacher@example.com"
}
```

## Edge Cases

- **Email not validated (`403`, `slug: email-not-validated`)**: login denied until invitation/email confirmation is completed.
- **Missing or empty `url` in hosted login**: login page shows an error; always pass a callback URL in the `url` query param.
- **Invalid or expired token**: `GET /v1/auth/token/<token>` fails; force re-authentication.
- **Missing `Academy` header on capability probe**: `GET /v1/auth/user/me/capability/<slug>` returns **400** unless `Academy` header or `?academy=` is present.
- **Missing capability**: probe or domain call returns **403**; verify slug and academy id; user may need a different role or academy.
- **Academy not found**: `GET /v1/auth/me/academy/<slug_or_id>/capabilities` returns **404** `academy-not-found`.
- **User has no ProfileAcademy for academy**: capabilities list is empty `[]`; user cannot work in that academy.
- **Multi-academy staff**: capability sets differ per academy; always re-fetch or re-probe when switching `Academy` header.
- **Academy token not generated**: `GET /v1/auth/academy/token/` returns **400** `academy-token-not-found`; call `POST` first with `generate_academy_token`.
- **Self-service password reset is HTML only**: `POST /v1/auth/password/reset` is an HTML form, not JSON. Staff JSON reset is `POST /v1/auth/member/<profileacademy_id>/password/reset`.
- **Public role list hides some slugs**: `GET /v1/auth/role` does not list `student`, `academy_token`, or `admin` — see [`bc-authenticate-staff-invites`](../bc-authenticate-staff-invites/SKILL.md) when building invite UIs.

## Checklist

1. Authenticate: `POST /login/` or redirect the browser to hosted login (`GET /view/login?url=<encoded_callback>`); capture `token` from JSON or callback querystring.
2. Call `GET /v1/auth/user/me`; confirm non-`student` entries in `roles[]`.
3. Pick target `academy.id` from `roles[]`.
4. Call `GET /v1/auth/me/academy/<id>/capabilities` to prefetch access, or probe one slug before a gated call.
5. Send `Academy: <id>` on every `/academy/*` domain request and on capability probes.
6. On **403**, re-check capability slug and `Academy` header before retrying.
7. For integration automation, use `GET/POST /academy/token/` with `Academy` header.
8. For staff-assisted member reset, use `POST /member/<profile_academy_id>/token` with `generate_temporal_token`.
9. On sign-out, call `POST /v1/auth/logout/` and clear local token state.
