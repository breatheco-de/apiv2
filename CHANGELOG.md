# Changelog

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
