---
name: bc-authenticate-student-authentication
description: Use when implementing or troubleshooting student authentication flows (token login, hosted login redirect, capabilities/permissions lookup, GitHub connect/reconnect); do NOT use for academy staff role management or non-auth student lifecycle flows.
requires: []
---

# Skill: Student Authentication Workflows

## When to Use

Use this skill when the user needs to authenticate a student, connect a third-party app to BreatheCode auth, inspect the student's permissions/capabilities, or connect/reconnect GitHub. Do not use it for academy role CRUD, member invitation administration, or payments/admissions onboarding logic.

## Concepts

- **Login token**: Main API token returned by login flows; send it as `Authorization: Token <token>`.
- **Universal hosted login**: `GET /v1/auth/view/login?url=<callback>` for anonymous users in browser flows; successful auth redirects automatically to `url` with `token` in query string.
- **Permissions vs capabilities**:
  - `permissions`: Django permissions from user groups, returned in `GET /v1/auth/user/me`.
  - `capabilities`: Academy role capability slugs; academy-scoped and checked with academy context.
- **Academy context**: Capability checks require academy context, usually with `Academy` header or `?academy=<id>`.

## Workflow

1. **Choose auth flow.**  
   - Use `POST /v1/auth/login/` for direct API login (backend/SPA that handles credentials).  
   - Use `GET /v1/auth/view/login?url=<callback>` for third-party browser redirect login (anonymous user lands on hosted login page).

2. **Capture token and persist it securely.**  
   - API login returns token in JSON body.  
   - Hosted login returns token via redirect querystring (`?token=<key>`).  
   - Store token in secure session/storage and use `Authorization: Token <token>` in subsequent requests.

3. **Validate/inspect token when needed.**  
   Call `GET /v1/auth/token/<token>` to confirm token validity, token type, expiration, and user id.

4. **Fetch current user auth context.**  
   Call `GET /v1/auth/user/me` to get profile summary, academy roles, and Django permissions.

5. **Resolve academy capabilities.**  
   If user belongs to multiple academies, choose an academy and call:  
   - `GET /v1/auth/me/academy/<slug_or_id>/capabilities` to list capability slugs.  
   - `GET /v1/auth/user/me/capability/<capability_slug>` with `Academy` header (or `?academy=`) to check one capability.

6. **Connect GitHub (self-service).**  
   Start OAuth with `GET /v1/auth/github/?url=<callback>` or `GET /v1/auth/github/<token>?url=<callback>`.  
   API callback links credentials and redirects to callback URL with `token`.

7. **Verify or disconnect GitHub link.**  
   - `GET /v1/auth/github/me` confirms linked account and whether token is currently valid.  
   - `DELETE /v1/auth/github/me` removes linked credentials so user can reconnect cleanly.

8. **Support staff-assisted reconnect (known user).**  
   Staff can generate temporal link with `POST /v1/auth/member/<profile_academy_id>/token` and send returned `reset_github_url` to student.

9. **Logout and cleanup.**  
   Call `POST /v1/auth/logout/` and delete locally stored auth state.

## Endpoints

All endpoints below are under `/v1/auth`.  
Unless noted, responses are not paginated.

| Action | Method | Path | Required headers | Body | Important response |
|---|---|---|---|---|---|
| API login | POST | `/v1/auth/login/` | `Content-Type: application/json` | `email`, `password` | `token`, `user_id`, `email`, `expires_at` |
| Hosted universal login page | GET | `/v1/auth/view/login?url=<callback>` | None | None | HTML form, then redirect to callback with query `token` |
| Token info | GET | `/v1/auth/token/<token>` | None | None | `token`, `token_type`, `expires_at`, `user_id` |
| Create temporal token from current token | POST | `/v1/auth/token/me` | `Authorization` | optional `token_type` | new token metadata |
| Get current user | GET | `/v1/auth/user/me` | `Authorization` | None | user profile + `roles` + `permissions` + `settings` |
| List capabilities for one academy | GET | `/v1/auth/me/academy/<slug_or_id>/capabilities` | `Authorization` | None | sorted array of capability slugs |
| Check one capability in academy context | GET | `/v1/auth/user/me/capability/<capability_slug>` | `Authorization`, and academy context (`Academy` header or `?academy=`) | None | `{"status":"ok"}` when capability exists |
| Start GitHub OAuth | GET | `/v1/auth/github/?url=<callback>` or `/v1/auth/github/<token>?url=<callback>` | None | None | redirect to GitHub authorize URL |
| Callback from GitHub OAuth | GET | `/v1/auth/github/callback/` | None | None | updates/creates GitHub credentials and redirects with `token` |
| View current GitHub link | GET | `/v1/auth/github/me` | `Authorization` | None | `username`, `avatar_url`, `name`, `scopes`, `valid` |
| Disconnect current GitHub link | DELETE | `/v1/auth/github/me` | `Authorization` | None | `204 No Content` |
| Generate known-user temporal link | POST | `/v1/auth/member/<profile_academy_id>/token` | `Authorization` (staff capability: `generate_temporal_token`) | None | includes `key`, `reset_password_url`, `reset_github_url` |
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
      "name": "Can view assignment",
      "codename": "read_assignment"
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
  "read_assignment",
  "read_asset",
  "read_my_academy",
  "read_single_cohort"
]
```

### Capability check success sample

```json
{
  "status": "ok"
}
```

### Known-user GitHub link generation response sample

```json
{
  "user": {
    "id": 1,
    "email": "student@example.com",
    "first_name": "Jane",
    "last_name": "Doe",
    "username": "janedoe"
  },
  "key": "a1b2c3d4e5f6g7h8",
  "reset_password_url": "https://api.example.com/v1/auth/password/a1b2c3d4e5f6g7h8",
  "reset_github_url": "https://api.example.com/v1/auth/github/a1b2c3d4e5f6g7h8"
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
- **GitHub account not linked**: `GET /v1/auth/github/me` can return `404` with `slug: not-found`.
- **GitHub scope mismatch**: callback retries with `scope_retry`; after retry limit, flow returns a user-facing error asking for required org scopes.
- **Missing `url` in hosted login / GitHub OAuth start**: returns `no-callback-url`; always provide callback URL.
- **No student record for staff GitHub check**: staff endpoint `GET /v1/auth/github/<user_id>` can return `profile-academy-not-found`.

For translated messages, clients may send `Accept-Language` (for example `en` or `es`) on API calls that return translated errors.

## Checklist

1. Pick authentication entrypoint: API login (`POST /login/`) or hosted login (`GET /view/login?url=`).
2. Capture `token` from JSON response or callback querystring and persist it securely.
3. Use `Authorization: Token <token>` for all authenticated calls.
4. Call `GET /v1/auth/user/me` to retrieve roles, permissions, and identity context.
5. If academy-scoped logic is needed, select academy and call capabilities endpoints.
6. For GitHub, start OAuth, finish callback redirect, then verify with `GET /v1/auth/github/me`.
7. Use `DELETE /v1/auth/github/me` before reconnect when credentials are stale.
8. For known-user support flows, generate `reset_github_url` via `POST /v1/auth/member/<profile_academy_id>/token`.
9. On sign-out, call `POST /v1/auth/logout/` and clear local session/token state.
