---
name: bc-authenticate-student-authentication
description: Use when implementing or troubleshooting student authentication (token login, hosted login redirect, academy-scoped capabilities via ProfileAcademy, academy-less permissions via Django groups, GitHub connect/reconnect); do NOT use for staff-only academy admin, member/invite CRUD, or custom role management.
requires: []
---

# Skill: Student Authentication Workflows

## When to Use

Use this skill when the user needs to authenticate a student, connect a third-party app to BreatheCode auth, inspect what a student **can do** (capabilities and permissions), or connect/reconnect GitHub. Use **universal hosted login** when a browser-based app (another BreatheCode / 4Geeks frontend) should not collect credentials locally and instead forwards the user to the API login form. Do not use it for staff academy administration (non-`student` roles — load [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md)), academy role CRUD, member invitation administration, or payments/admissions onboarding logic.

## Concepts

Students use **two parallel authorization layers**. Both may appear on `GET /v1/auth/user/me`; use the right layer for the route you are calling.

| | Capabilities | Permissions |
|---|---|---|
| **Scope** | Academy-bound (`ProfileAcademy`) | Academy-less (global Django groups) |
| **Who** | Students (`student` role) and staff | Students only |
| **Source** | `roles[].role.slug` → capability slugs for that academy | `permissions[].codename` from Django groups |
| **Check** | `GET /me/academy/<id>/capabilities` or `GET /user/me/capability/<slug>` + `Academy` header | Inspect `permissions[]` on `user/me`; learner routes use permission codenames |
| **Dynamic?** | Changes when role/capability assignment changes per academy | Groups change via enrollment, plan, seat, mentor signals — not directly assignable via auth API |

- **Login token**: Main API token returned by login flows; send it as `Authorization: Token <token>`.
- **Universal hosted login**: API-hosted HTML login for **cross-app browser authentication**. Other BreatheCode apps redirect users to `GET /v1/auth/view/login?url=<callback>` instead of building their own login UI. The `url` query param is the callback where the user returns after success (plain HTTPS or Base64-encoded — API auto-detects). Returns the same `login` token as `POST /v1/auth/login/`; successful auth redirects to `<callback>?token=<login_token>&attempt=1`.
- **ProfileAcademy**: Anchor for capabilities — every capability check resolves user + academy + role.
- **Groups** (`Default`, `Student`, `Paid Student`, `Events`, `Classes`, `Mentorships`, `Legacy`, etc.): grant permission codenames independent of which academy the student belongs to. Membership changes as side effects of admissions, payments, and enrollment flows.
- **Staff**: non-student academy roles use **capabilities only** — see [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md).

## Workflow

1. **Choose auth flow.**
   - Use `POST /v1/auth/login/` for direct API login (backend/SPA that handles credentials).
   - Use `GET /v1/auth/view/login?url=<callback>` for third-party browser redirect login (see subsection below).

### Universal hosted login (cross-app browser auth)

Other BreatheCode apps authenticate users by redirecting the browser to the API login page instead of building their own login UI. OAuth (`/github`, `/google`) uses a different entrypoint but the same `url` callback pattern — see steps 8–9 below.

1. App redirects user to `GET /v1/auth/view/login?url=<callback>` (`url` required; plain HTTPS or Base64-encoded).
2. User submits email/password on the API HTML form.
3. API redirects to `<callback>?token=<login_token>&attempt=1`.
4. App reads `token` from the query string, stores it, and sends `Authorization: Token <token>` on API calls.
5. Optionally validate with `GET /v1/auth/user/me`.

2. **Capture token and persist it securely.**
   - API login returns token in JSON body.
   - Hosted login returns token via redirect querystring (`?token=<key>`).
   - Store token securely and use `Authorization: Token <token>` in subsequent requests.

3. **Validate/inspect token when needed.**
   Call `GET /v1/auth/token/<token>` to confirm token validity, token type, expiration, and user id.

4. **Fetch current user auth context.**
   Call `GET /v1/auth/user/me` to get profile summary, `roles[]` (ProfileAcademy), and `permissions[]` (Django groups).

5. **Resolve academy-scoped capabilities.**
   Pick academy from `roles[]` where `role.slug` is `student`. Call:
   - `GET /v1/auth/me/academy/<slug_or_id>/capabilities` to list capability slugs for that academy.
   - `GET /v1/auth/user/me/capability/<capability_slug>` with `Academy` header (or `?academy=`) before capability-gated routes.
   Use capabilities when the target route is under `/academy/` or requires the `Academy` header.

6. **Resolve academy-less permissions.**
   Read `permissions[].codename` from `user/me` (e.g. `get_my_certificate`, `join_mentorship`, `get_private_link`, `live_class_join`, `upload_assignment_telemetry`). Use this for learner routes under `/me/` or `/user/{id}/` that do not require an `Academy` header.

7. **Debug 403 responses.**
   - Route uses `Academy` header or `/academy/` path → missing **capability** for that academy.
   - Route is a learner `/me/` or `/user/{id}/` path without academy context → missing **permission** codename.
   - Staff-only task → load [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md).

8. **Connect GitHub (self-service).**
   Start OAuth with `GET /v1/auth/github/?url=<callback>` or `GET /v1/auth/github/<token>?url=<callback>`.
   API callback links credentials and redirects to callback URL with `token`.

9. **Verify or disconnect GitHub link.**
   - `GET /v1/auth/github/me` confirms linked account and whether token is currently valid.
   - `DELETE /v1/auth/github/me` removes linked credentials so user can reconnect cleanly.

10. **Staff-assisted reconnect (if a staff member is helping).**
    Staff generates a temporal link via `POST /v1/auth/member/<profile_academy_id>/token` — documented in [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md). Student follows `reset_github_url` or `reset_password_url` from that response.

11. **Logout and cleanup.**
    Call `POST /v1/auth/logout/` and delete locally stored auth state.

## Endpoints

All endpoints below are under `/v1/auth`.
Unless noted, responses are not paginated.
Send `Accept-Language` (`en`, `es`) for translated errors where applicable.

| Action | Method | Path | Required headers | Body | Important response |
|---|---|---|---|---|---|
| API login | POST | `/v1/auth/login/` | `Content-Type: application/json` | `email`, `password` | `token`, `user_id`, `email`, `expires_at` |
| Hosted universal login page | GET | `/v1/auth/view/login?url=<callback>` | None | None | HTML form, then redirect to callback with `?token=<login_token>&attempt=1` |
| Token info | GET | `/v1/auth/token/<token>` | None | None | `token`, `token_type`, `expires_at`, `user_id` |
| Create temporal token from current token | POST | `/v1/auth/token/me` | `Authorization` | optional `token_type` | new token metadata |
| Get current user | GET | `/v1/auth/user/me` | `Authorization` | None | user profile + `roles` + `permissions` + `settings` |
| List capabilities for one academy | GET | `/v1/auth/me/academy/<slug_or_id>/capabilities` | `Authorization` | None | sorted array of capability slugs |
| Check one capability in academy context | GET | `/v1/auth/user/me/capability/<capability_slug>` | `Authorization`, and academy context (`Academy` header or `?academy=`) | None | `{"status":"ok"}` when capability exists |
| Start GitHub OAuth | GET | `/v1/auth/github/?url=<callback>` or `/v1/auth/github/<token>?url=<callback>` | None | None | redirect to GitHub authorize URL |
| Callback from GitHub OAuth | GET | `/v1/auth/github/callback/` | None | None | updates/creates GitHub credentials and redirects with `token` |
| View current GitHub link | GET | `/v1/auth/github/me` | `Authorization` | None | `username`, `avatar_url`, `name`, `scopes`, `valid` |
| Disconnect current GitHub link | DELETE | `/v1/auth/github/me` | `Authorization` | None | `204 No Content` |
| Logout | POST | `/v1/auth/logout/` | `Authorization` | None | success status; client must clear local auth data |

### API login request sample

```json
{
  "email": "student@example.com",
  "password": "StrongPassword123!"
}
```

### API login response sample

```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "user_id": 123,
  "email": "student@example.com",
  "expires_at": "2026-12-31T23:59:59Z"
}
```

### Universal hosted login URL sample

`url` may be a plain HTTPS callback or Base64-encoded; the API auto-detects.

```text
https://breathecode.herokuapp.com/v1/auth/view/login?url=https%3A%2F%2F4geeksacademy.com%2F
```

### Universal hosted login redirect sample

```text
https://4geeksacademy.com/?token=9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b&attempt=1
```

### Token info response sample

```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "token_type": "login",
  "expires_at": "2026-12-31T23:59:59Z",
  "user_id": 123
}
```

### Current user response sample (`GET /v1/auth/user/me`)

```json
{
  "id": 123,
  "email": "student@example.com",
  "username": "student123",
  "first_name": "Jane",
  "last_name": "Doe",
  "date_joined": "2025-11-01T10:00:00Z",
  "github": {
    "id": 987,
    "username": "janedoe",
    "avatar_url": "https://avatars.githubusercontent.com/u/987?v=4"
  },
  "profile": {
    "id": 88,
    "avatar_url": "https://cdn.example.com/avatar.png",
    "bio": "Full stack student"
  },
  "roles": [
    {
      "id": 44,
      "academy": {
        "id": 1,
        "slug": "miami",
        "name": "4Geeks Miami"
      },
      "role": {
        "slug": "student",
        "name": "Student"
      }
    }
  ],
  "permissions": [
    {
      "name": "Get my certificate",
      "codename": "get_my_certificate"
    },
    {
      "name": "Join mentorship",
      "codename": "join_mentorship"
    },
    {
      "name": "Upload assignment telemetry",
      "codename": "upload_assignment_telemetry"
    },
    {
      "name": "Get private link",
      "codename": "get_private_link"
    }
  ],
  "settings": {
    "lang": "en",
    "main_currency": "USD"
  }
}
```

### Academy capabilities response sample

```json
[
  "crud_assignment",
  "read_assignment",
  "read_asset",
  "read_my_academy",
  "read_single_cohort",
  "upload_assignment_telemetry"
]
```

### Capability check success sample

```json
{
  "status": "ok"
}
```

### GitHub connection status response sample (`GET /v1/auth/github/me`)

```json
{
  "username": "janedoe",
  "avatar_url": "https://avatars.githubusercontent.com/u/987?v=4",
  "name": "Jane Doe",
  "scopes": "repo user:email",
  "valid": true
}
```

## Edge Cases

- **Email not validated (`403`, `slug: email-not-validated`)**: login denied until invitation/email confirmation is completed.
- **Invalid or expired token**: `GET /v1/auth/token/<token>` fails; force re-authentication.
- **Missing academy context on capability check**: `GET /v1/auth/user/me/capability/<slug>` fails unless `Academy` header or `?academy=` is present.
- **Academy not found**: `GET /v1/auth/me/academy/<slug_or_id>/capabilities` returns `academy-not-found`.
- **403 on learner route**: check `permissions[].codename` — student may lack a group (e.g. `Paid Student` for `get_private_link`).
- **403 on academy-scoped route**: check capabilities for that academy, not permissions.
- **GitHub account not linked**: `GET /v1/auth/github/me` can return `404` with `slug: not-found`.
- **GitHub scope mismatch**: callback retries with `scope_retry`; after retry limit, flow returns a user-facing error asking for required org scopes.
- **Missing `url` in hosted login / GitHub OAuth start**: returns `no-callback-url`; always provide callback URL.

## Checklist

1. Pick authentication entrypoint: API login (`POST /login/`) or redirect the browser to hosted login (`GET /view/login?url=<encoded_callback>`) for third-party cross-app auth.
2. Capture `token` from JSON response or callback querystring and persist it securely.
3. Use `Authorization: Token <token>` for all authenticated calls.
4. Call `GET /v1/auth/user/me` to retrieve `roles[]` and `permissions[]`.
5. For `/academy/` or `Academy` header routes: pick student academy and call capabilities endpoints.
6. For `/me/` learner routes: verify required permission codename is in `permissions[]`.
7. On 403, determine whether the route needs a capability (academy-scoped) or permission (academy-less).
8. For GitHub, start OAuth, finish callback redirect, then verify with `GET /v1/auth/github/me`.
9. Use `DELETE /v1/auth/github/me` before reconnect when credentials are stale.
10. On sign-out, call `POST /v1/auth/logout/` and clear local session/token state.
