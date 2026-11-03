# Changelog

## 2026-10-15 — Redirect allowlist for auth callbacks (security, breaking for unlisted hosts)

### Why

Hosted login (`/v1/auth/view/login?url=`) appended a fresh login token to any `url`, so a link with an attacker's host leaked the victim's token. GitHub and Google OAuth did the same with their `url`, and the other callbacks were open redirects.

### Behavior change

Client-supplied redirect targets are only accepted when they are:

- `https` on `4geeks.com`, `4geeksacademy.com`, `learnpack.co` or any of their subdomains
- the exact host of `API_URL`, `APP_URL` or `SITE_URL`
- the exact host of an academy `website_url` or `white_label_url` (cached in Redis, refreshed when an academy is saved or deleted)
- a same-origin path (`/...`)
- `http://localhost` / `http://127.0.0.1` only when `DEBUG` is on

Anything else gets `400` (`invalid-redirect-url`): JSON for the DRF endpoints, an HTML message for the HTML pages. The check runs before any token is issued, email is sent or invite is accepted.

| Endpoint | Parameter |
|---|---|
| `GET/POST /v1/auth/view/login` | `url` (also after Base64 decoding) |
| `GET/POST /v1/auth/password/reset` | `url`, `callback` |
| `GET/POST /v1/auth/password/<token>` | `callback` |
| `POST /v1/auth/member/invite/<token>` (HTML form) | `callback` |
| `GET /v1/auth/github/`, `GET /v1/auth/github/<token>`, `GET /v1/auth/github/callback/` | `url` |
| `GET /v1/auth/google`, `GET /v1/auth/google/<token>`, `GET /v1/auth/google/callback` | `url` / `state.url` |
| `GET /v1/auth/slack`, slack callback, `GET /v1/auth/facebook`, facebook callback | `url` / `payload.url` |
| `GET /v1/auth/discord`, discord callback | `url` / `state.url` |

The "invitation not found" page no longer renders an unlisted callback and escapes the allowed one (it was injected as raw HTML).

### Possible side effects (watch after deploy)

- Logins or OAuth connects from preview deployments (`*.vercel.app`, `*.herokuapp.com` other than the API host, custom domains of academies without `website_url`) now fail with "The redirect url is not allowed". Add the academy `website_url`/`white_label_url`, or add the domain to `FIRST_PARTY_DOMAINS`.
- Developers pointing a `localhost` frontend at a non-development API (staging, production) can no longer use hosted login or OAuth.
- Look for `Rejected redirect url with host` warnings in the logs to find legitimate hosts that are missing.

### Files

- `breathecode/authenticate/utils/redirects.py` (new), `breathecode/authenticate/receivers.py` (cache invalidation)
- `breathecode/authenticate/views.py`
- Tests: `breathecode/authenticate/tests/utils/tests_redirects.py` and the view tests listed above

### Rollback

Revert the commit. If only one host is the problem, add it to `FIRST_PARTY_DOMAINS` instead of reverting.

## 2026-10-15 — Password changes revoke every session (security)

### Why

Changing a password left existing login tokens valid for up to 7 days, so a stolen session survived the reset that was supposed to stop it.

### Behavior change

- Setting a password through the reset link (`/v1/auth/password/<token>`, including staff-generated `reset_password_url`) or the invite form deletes every `login`, `temporal` and `short` token of the user. `permanent` and `one_time` tokens (integrations) are kept.
- The reset link becomes single-use for every token type.
- Logout keeps its previous behavior (now through the same helper, `revoke_user_sessions`).

### Possible side effects (watch after deploy)

- Users are signed out on every device after a reset, and frontends get `401` on the old token. Frontends must send them to login.
- A user who accepts an invite with a password while logged in elsewhere is signed out there.

### Files

- `breathecode/authenticate/actions.py` (`revoke_user_sessions`, `accept_invite_action`)
- `breathecode/authenticate/views.py` (`pick_password`, `LogoutView`)
- Tests: `tests_password_token.py`, `tests_member_invite_token.py`

## 2026-10-15 — Standard rate limiting (`@rate_limit`) and new limits on auth endpoints

### Why

Password reset, pick password and subscribe had no abuse protection, and the login limiter used non-atomic counters keyed by a spoofable IP.

### Behavior change

- New `breathecode.utils.decorators.rate_limit` (decorator) and `RateLimiter` (low-level): fixed window in Redis with atomic `add` + `incr`, hashed keys, `429` + `Retry-After` (`rate-limit-exceeded`), fail-open when Redis errors.
- Limits:

| Endpoint | Limit | When exceeded |
|---|---|---|
| `POST /v1/auth/password/reset` | 10/hour per IP | `429` page |
| `POST /v1/auth/password/reset` | 3/hour per email | same success response, no email sent |
| `POST /v1/auth/password/<token>` | 10/15 min per IP, 5/15 min per link | `429` page |
| `POST /v1/auth/subscribe/` | 10/hour per IP, 3/hour per email | `429` JSON |

- Login failure limiting (`LOGIN_RATE_LIMIT_*` envs) keeps its thresholds but now uses `RateLimiter`. In-flight counters under the old `login_fail:*` keys are dropped on deploy.
- `get_client_ip` moved to `breathecode/utils/request.py` and now takes the `X-Forwarded-For` entry at position `-TRUSTED_PROXY_COUNT` (default `1`, the entry Heroku's router appends) instead of the first, client-controlled entry. This also changes the IP sent to Turnstile.
- Kill switches: `RATE_LIMIT_ENABLED=false` disables every decorator limit; `RATE_LIMIT_DISABLED_SCOPES=password-reset,pick-password,subscribe` disables single scopes (flag `authenticate.rate_limit`).

### Possible side effects (watch after deploy)

- Shared IPs (bootcamp classrooms, offices behind NAT) can hit the 10/hour subscribe or reset limits during onboarding sessions. Disable the scope with `RATE_LIMIT_DISABLED_SCOPES` if that happens.
- If the API ever runs behind an extra proxy (e.g. Cloudflare in front of Heroku), set `TRUSTED_PROXY_COUNT` accordingly or every user behind the same proxy edge shares one counter.

### Files

- `breathecode/utils/decorators/rate_limit.py` (new), `breathecode/utils/request.py`, `breathecode/authenticate/flags.py`
- `breathecode/authenticate/utils/login_protection.py`, `breathecode/authenticate/views.py`
- `breathecode/settings.py` (test cache gains `add`/`incr`)
- Tests: `breathecode/utils/tests/decorators/tests_rate_limit.py`, `breathecode/utils/tests/tests_request_client_ip.py`, `tests_password_reset.py`, `tests_password_token.py`, `tests_subscribe.py`

## 2026-10-14 — `POST /v1/auth/subscribe/` no longer issues tokens for existing accounts (security)

### Why

Since 2025-07-07 (commit `2282597c8`) the endpoint returned the login token (`access_token`) of an existing user to anyone who posted that user's email with a plan/course they had no invite for (account takeover).

### Behavior change

| Request | Before | Now |
|---|---|---|
| New email | account created, `access_token` returned | unchanged |
| Existing email, no `Authorization` (or another user's token) | invite created, **existing user's token returned** | `400`, `silent_code: user-exists`, nothing created |
| Existing email + that user's own `Authorization: Token` | — | invite attached to the user, `201`, `access_token: null` |
| `PUT /v1/auth/subscribe/` (waiting-list confirmation with emailed invite token) | token returned | unchanged |

### Possible side effects (watch after deploy)

- Signup forms used by returning users (e.g. accounts created via Google/GitHub login) now get `user-exists` instead of being logged in. Frontends must send the user to login, then retry the signup with their token.
- Any client that treated a `201` from subscribe as "logged in" must check that `access_token` is not null.
- A spike of `user-exists` errors on `/v1/auth/subscribe/` after deploy means a frontend is not handling the "go to login" case.

### Files

- `breathecode/authenticate/serializers.py` (`UserInviteWaitingListSerializer.validate`, `get_access_token`)
- `breathecode/authenticate/views.py` (`WaitingListView.post` passes `request_user`)
- Tests: `breathecode/authenticate/tests/urls/v1/tests_subscribe.py`
- Skill: `docs/agent-docs/skills/bc-authenticate-signup-user/SKILL.md`

### Rollback

Revert the commit. Do not restore the `invites.exists()` condition without another ownership check.

## 2026-10-14 — `/v1/auth/logout/` only revokes the caller's tokens (security)

### Why

The logout view deleted every `login` token in the database, so any authenticated user calling it logged out every user on the platform.

### Behavior change

- Logout now deletes only the requesting user's `login` tokens (all of that user's devices) plus the token used for the call.
- `POST /v1/auth/logout/` is now supported (as documented in the auth skills); `GET` still works for existing clients.

### Files

- `breathecode/authenticate/views.py` (`LogoutView`)
- Tests: `breathecode/authenticate/tests/urls/v1/tests_logout.py`

## April 13

To solve the login case sensitive issue:

```
UPDATE auth_user SET email=LOWER(email);
UPDATE authenticate_profileacademy SET email=LOWER(email);
UPDATE authenticate_userinvite SET email=LOWER(email);
```
