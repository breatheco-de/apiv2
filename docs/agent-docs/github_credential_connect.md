# Connect a Known User to GitHub Credentials

This document describes how to connect an existing BreatheCode user (a "known user") to GitHub credentials via the API.

## Overview

The flow uses a **temporal token** tied to the user's academy profile. You obtain a token (and the connect URL) from one endpoint, then the user visits the returned URL to complete GitHub OAuth. The callback associates the GitHub account with that user.

---

## Endpoints

### 1. Get the "Connect GitHub" URL for a known user

**Request**

- **Method:** `POST`
- **URL:** `/v1/auth/member/<profile_academy_id>/token`
- **Path parameter:** `profile_academy_id` — ID of the `ProfileAcademy` for the user you want to connect to GitHub.
- **Request body:** None.
- **Authentication:** Required. Academy staff with the **generate_temporal_token** capability.

**Response**

`200 OK` — JSON with temporal token and URLs:

| Field | Type | Description |
|-------|------|-------------|
| `user` | object | The user tied to the token: `id`, `email`, `first_name`, `last_name`, `username`. |
| `key` | string | Temporal token key (use in the GitHub connect URL). |
| `reset_password_url` | string | Full URL to trigger password reset for this user. |
| `reset_github_url` | string | Full URL the user must open to connect their GitHub account. |

**Response example**

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

**Request example**

```http
POST /v1/auth/member/123/token
Authorization: Token <academy_staff_token>
Content-Type: application/json
```

Use the returned `reset_github_url` (or build it as `{API_URL}/v1/auth/github/{key}`) and send it to the user (e.g. by email or in the UI).

---

### 2. Start GitHub OAuth (user-facing URL)

**Request**

- **Method:** `GET`
- **URL:** `/v1/auth/github/<token>`
- **Path parameter:** `token` — temporal token key from step 1.
- **Query parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `url` | Yes | Callback URL where the user should be sent after GitHub OAuth (e.g. your frontend or app URL). |
| `scope` | No | GitHub OAuth scopes (default: `user:email`). Usually not needed. |
| `scope_retry` | No | Internal retry counter; omit when building the link. |

- **Request body:** None.
- **Authentication:** None (user opens this in the browser).

**Behavior**

- Validates the temporal token and redirects the user to GitHub's OAuth authorize page.
- After the user authorizes, GitHub redirects to the API callback; the callback receives the token and links the GitHub credentials to the user who owns that token.

**Example**

```http
GET /v1/auth/github/a1b2c3d4e5f6g7h8?url=https://myapp.com/settings/github-connected
```

The user is redirected to GitHub; after authorizing, they are eventually sent to `url` (or an error page).

---

### 3. Callback (handled by the API)

- **Method:** `GET`
- **URL:** `/v1/auth/github/callback/`
- **Query parameters:** Set by the API and GitHub during the redirect. Implementers do not call this URL directly.

| Parameter | Set by | Description |
|-----------|--------|-------------|
| `code` | GitHub | OAuth authorization code. |
| `url` | API (preserved from step 2) | Callback URL to redirect the user after linking. |
| `user` | API (temporal token key) | Identifies the BreatheCode user to attach credentials to. |
| `scope_retry` | API | Internal; omit when building links. |

- **Authentication:** None (called by GitHub redirect).

This endpoint is used automatically by the OAuth flow. It:

1. Exchanges the `code` for a GitHub access token.
2. Fetches the GitHub user (and email).
3. Resolves the BreatheCode user from the temporal token (passed as `user` in the callback URL).
4. Creates or updates `CredentialsGithub` for that user and redirects the user to the `url` specified in step 2.

Implementers do not call this URL directly; it is invoked by the redirect from GitHub.

---

## Flow summary

| Step | Who        | Action                                                                 |
|------|------------|------------------------------------------------------------------------|
| 1    | Backend / staff | Call `POST /v1/auth/member/<profile_academy_id>/token` (no body). Use response `reset_github_url` or build `{API_URL}/v1/auth/github/{key}`. |
| 2    | Your app   | Send `reset_github_url` to the user (e.g. link or email). Optionally append `?url=<your_callback_url>`. |
| 3    | User       | Opens the URL; is redirected to GitHub to authorize.                   |
| 4    | GitHub     | Redirects to `/v1/auth/github/callback/` with `code` and preserved `url` and `user` (token). |
| 5    | API        | Callback exchanges code, links GitHub to the user, redirects user to `url`. |

---

## Notes

- The **temporal token** is short-lived; use the `reset_github_url` (or the token) soon after obtaining it.
- The admin link that uses `?user={user_id}` (user ID) is a different pattern; the supported flow for "known user" is via **temporal token** from `POST /v1/auth/member/<profile_academy_id>/token`.
- `reset_github_url` is built as: `{API_URL}/v1/auth/github/{key}` (see `get_reset_github_url` in the authenticate serializers).
