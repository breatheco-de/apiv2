---
name: bc-authenticate-share-subdomain-session
description: Use when a 4Geeks frontend on a *.4geeks.com subdomain must read, write, validate, or clear the shared BreatheCode login cookie so users stay logged in across sibling subdomains; do NOT use for obtaining the token itself (login, hosted login, OAuth), capability checks, or apps hosted outside *.4geeks.com.
requires:
  - bc-authenticate-student-authentication
---

# Skill: Share the BreatheCode Session Across 4Geeks Subdomains

## When to Use

Use this skill when building or fixing a frontend on any `*.4geeks.com` subdomain (e.g. `4geeks.com`, `learn.4geeks.com`, `app.4geeks.com`) that must detect an existing login from a sibling subdomain, or persist a new login so siblings detect it.
Do NOT use it to perform the login itself — load [`bc-authenticate-student-authentication`](../bc-authenticate-student-authentication/SKILL.md) for `POST /v1/auth/login/` and hosted login.
Do NOT use it for apps on other registrable domains (e.g. `4geeksacademy.com`, `*.vercel.app`, `*.herokuapp.com`) — browsers will not share the cookie; use hosted login redirect instead.

## Concepts

- **The API never sets cookies.** It returns a login token; clients send it as `Authorization: Token <token>`. The shared cookie is a client-side contract between 4Geeks frontends, not an API feature. Never rely on the cookie being sent to the API.
- **Shared cookie contract** — every 4Geeks frontend must use exactly these attributes:

  | Attribute | Value | Why |
  |---|---|---|
  | Name | `4g_tok` | Single name all subdomains agree on |
  | Value | `encodeURIComponent(<login_token>)` | Safe cookie encoding |
  | `Domain` | `.4geeks.com` | Makes the cookie visible to every sibling subdomain |
  | `Path` | `/` | Visible on every route |
  | `SameSite` | `Lax` | Survives top-level navigation from hosted login callback; blocks cross-site subrequests |
  | `Secure` | always on HTTPS | Never transmit the token over plain HTTP |
  | `Max-Age` | seconds until token `expires_at` | Login tokens expire after 7 days; a longer cookie leaves a dead token behind |
  | `HttpOnly` | not set | Frontends must read the token to build the `Authorization` header for the API (different domain) |

- **Host-only vs parent-domain cookies**: a cookie written without `Domain` is host-only and invisible to siblings. If both variants exist, the browser returns both under the same name and reads become ambiguous. Always clear both variants before writing and on logout.
- **Local development**: omit `Domain` on `localhost`, `*.localhost`, and IP addresses; sharing across subdomains is not possible there. Omit `Secure` on `http:`.
- **Logout scope**: `POST /v1/auth/logout/` deletes every `login` token of the current user, so the user is signed out on all devices and all subdomains, not only the current browser.

## Workflow

1. **Check eligibility.** Read `window.location.hostname`. If it is not `4geeks.com` or does not end with `.4geeks.com`, stop using this skill and use the hosted login redirect from [`bc-authenticate-student-authentication`](../bc-authenticate-student-authentication/SKILL.md) on every app load instead.

2. **Read the shared cookie on app start.** Read `4g_tok` from `document.cookie` and `decodeURIComponent` it. Read it client-side after hydration only; during SSR, read it from the incoming `Cookie` request header instead of `document.cookie`.

3. **If no cookie, check for a hosted-login callback token.** Read `token` from the query string (hosted login redirects to `<callback>?token=<login_token>&attempt=1`). If present, immediately remove `token` and `attempt` from the URL with `history.replaceState` so the token does not stay in history, bookmarks, or `Referer` headers. Continue to Step 4 with this token.

4. **Validate the token and get its expiry.** Call `GET /v1/auth/token/<token>`. Save `expires_at` from the response — Step 5 needs it to compute `Max-Age`. If the call fails or `expires_at` is in the past, clear the cookie (Step 7) and send the user to login.

5. **Write the shared cookie.** First clear both variants (Step 7), then write the parent-domain cookie with `Max-Age = floor((expires_at - now) / 1000)`. Use the `expires_at` from Step 4, or from the `POST /v1/auth/login/` response when the app logged in directly. A non-null `access_token` from signup ([`bc-authenticate-signup-user`](../bc-authenticate-signup-user/SKILL.md)) is also a login token: run Step 4 on it to get `expires_at`, then write it here.

   ```ts
   const COOKIE = "4g_tok";
   const isLocal = (h: string) =>
     h === "localhost" || h.endsWith(".localhost") || /^\d{1,3}(\.\d{1,3}){3}$/.test(h) || h.includes(":");

   function cookieAttrs(maxAge: number): string {
     const parts = [`path=/`, `max-age=${maxAge}`, `samesite=lax`];
     if (location.protocol === "https:") parts.push("secure");
     if (!isLocal(location.hostname)) parts.push("domain=.4geeks.com");
     return parts.join("; ");
   }

   export function writeSharedToken(token: string, expiresAt: string): void {
     clearSharedToken();
     const maxAge = Math.max(0, Math.floor((Date.parse(expiresAt) - Date.now()) / 1000));
     document.cookie = `${COOKIE}=${encodeURIComponent(token)}; ${cookieAttrs(maxAge)}`;
   }

   export function clearSharedToken(): void {
     document.cookie = `${COOKIE}=; path=/; max-age=0; samesite=lax`;
     if (!isLocal(location.hostname)) {
       document.cookie = `${COOKIE}=; path=/; max-age=0; samesite=lax; domain=.4geeks.com`;
     }
   }
   ```

6. **Use the token.** Send `Authorization: Token <token>` on every API call. Call `GET /v1/auth/user/me` once per app load to get the profile. On any `401` from the API, clear the cookie (Step 7) and send the user to login — a sibling subdomain may have logged out.

7. **Clear on invalid token.** Call `clearSharedToken()` from Step 5 and delete any in-memory copy of the token. Every `*.4geeks.com` subdomain sees the user as logged out on its next read.

8. **Log out.** When the user signs out, call `POST /v1/auth/logout/` with the current token first, then run Step 7. Revoke on the server before clearing the cookie because the token is needed to authenticate the logout call. If the logout call fails with `401`, the token is already invalid — still run Step 7.

9. **Migrate legacy storage once.** If the app previously stored the token in `localStorage` (e.g. key `4g_auth_token`) and no `4g_tok` cookie exists, run Steps 4–5 with the legacy value, then delete the `localStorage` key. If a `4g_tok` cookie already exists, delete the legacy key without using it.

## Endpoints

All endpoints are under `/v1/auth`. Responses are not paginated. Send `Accept-Language` (`en`, `es`) to receive translated error messages.

| Action | Method | Path | Required headers | Body | Important response |
|---|---|---|---|---|---|
| Validate token / get expiry | GET | `/v1/auth/token/<token>` | None | None | `token_type`, `expires_at`, `user_id` |
| Current user profile | GET | `/v1/auth/user/me` | `Authorization: Token <token>` | None | `id`, `email`, `first_name`, `last_name`, `roles`, `permissions` |
| Logout (revoke all login tokens of the current user) | POST | `/v1/auth/logout/` | `Authorization: Token <token>` | None | `message` |

### Token info response sample (`GET /v1/auth/token/9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b`)

```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "token_type": "login",
  "expires_at": "2026-10-21T18:30:00Z",
  "user_id": 123
}
```

### Current user response sample (`GET /v1/auth/user/me`, relevant subset)

```json
{
  "id": 123,
  "email": "student@example.com",
  "username": "student123",
  "first_name": "Jane",
  "last_name": "Doe",
  "roles": [],
  "permissions": [
    { "name": "Get my certificate", "codename": "get_my_certificate" }
  ]
}
```

### Logout response sample (`POST /v1/auth/logout/`)

```json
{
  "message": "User tokens successfully deleted"
}
```

## Edge Cases

- **Cookie written without `Domain`** (sibling subdomains do not see the login): clear both variants and rewrite with `domain=.4geeks.com` (Step 5).
- **Two `4g_tok` values in `document.cookie`**: a stale host-only cookie shadows the shared one. Clear both variants, then re-run Steps 4–5 with the token that validates.
- **`expires_at` already past or `GET /v1/auth/token/<token>` returns an error**: clear the cookie and redirect to login; do not retry with the same token.
- **API returns `401` mid-session**: another subdomain logged out or the token expired. Clear the cookie and redirect to login.
- **Logout returns `401`**: the token was already revoked or expired. Clear the cookie anyway (Step 7).
- **App runs on `localhost`, a preview domain, or a non-4geeks.com domain**: the shared cookie cannot work there. Store the token host-only for development, or use hosted login on each load in production.
- **Login returns `403` with `slug: email-not-validated`**: do not write a cookie; show the email-confirmation message.
- **Token appears in logs or analytics** (query string captured before Step 3 stripped it): strip `token` from the URL before any analytics/tag manager initializes.

## Checklist

1. Confirmed the app hostname is `4geeks.com` or ends with `.4geeks.com`; otherwise used hosted login instead.
2. Read `4g_tok` on load (client after hydration, or from the `Cookie` header during SSR).
3. Stripped `token` and `attempt` from the URL immediately after reading a hosted-login callback.
4. Validated the token with `GET /v1/auth/token/<token>` and saved `expires_at`.
5. Cleared both host-only and `.4geeks.com` variants before writing.
6. Wrote `4g_tok` with `Domain=.4geeks.com`, `Path=/`, `SameSite=Lax`, `Secure` (HTTPS), and `Max-Age` derived from `expires_at`.
7. Sent `Authorization: Token <token>` on API calls and never relied on the cookie reaching the API.
8. Cleared both cookie variants on any `401`.
9. On sign-out, called `POST /v1/auth/logout/` before clearing both cookie variants.
10. Migrated and deleted any legacy `localStorage` token key.
