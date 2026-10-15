---
name: bc-authenticate-signup-user
description: Use when a frontend signup form must create a BreatheCode account (or a waiting-list entry) for a plan, course, or cohort via POST /v1/auth/subscribe/ and log the new user in; do NOT use for logging in existing users, staff invitations, or lead capture that does not create an account.
requires:
  - bc-authenticate-share-subdomain-session
---

# Skill: Sign Up a User From a Frontend Form

## When to Use

Use this skill when a public signup form (landing page, lead form with signup, free-plan CTA) must register a visitor for a plan, course, or cohort and, when allowed, log them in immediately.
Do NOT use it to log in an existing account — load [`bc-authenticate-student-authentication`](../bc-authenticate-student-authentication/SKILL.md).
Do NOT use it for staff inviting members — load [`bc-authenticate-staff-invites`](../bc-authenticate-staff-invites/SKILL.md).
Do NOT use it for marketing lead capture without an account — load [`bc-marketing-create-form-entry`](../bc-marketing-create-form-entry/SKILL.md).

## Concepts

- **Signup creates an invite, not a password.** `POST /v1/auth/subscribe/` records the request and, when the plan/course accepts users directly, creates the account and returns a login token in `access_token`. The account has no password; the API emails the user a verification link.
- **Resulting `status`**:

  | `status` | Meaning | `access_token` |
  |---|---|---|
  | `ACCEPTED` (new account) | Account created and logged in | login token |
  | `ACCEPTED` (authenticated existing user) | Plan/course attached to the caller's existing account | `null` — keep the caller's current token |
  | `WAITING_LIST` | Plan or course requires approval; no account access yet | `null` |

- **Existing accounts are protected.** If the email already belongs to a user, the API rejects the signup with `user-exists` unless the request carries that same user's token in `Authorization`. The API never returns a token for an account that existed before the request.
- **Target**: send exactly one of `plan`, `course`, `cohort`, or `syllabus` (slug or numeric id). Free self-serve signups use a plan slug such as `4geeks-basic-subscription`.

## Workflow

1. **Check whether the visitor is already logged in.** Read the shared `4g_tok` cookie as described in [`bc-authenticate-share-subdomain-session`](../bc-authenticate-share-subdomain-session/SKILL.md). If a valid token exists, send it as `Authorization: Token <token>` in Step 3 so the API attaches the plan to that account instead of rejecting it.

2. **Build the payload.** `email` is required. Add the target (`plan`, `course`, `cohort`, or `syllabus`), optional profile fields (`first_name`, `last_name`, `phone`, `country`, `city`), `has_marketing_consent`, and `conversion_info`. `conversion_info` accepts only these keys: `utm_placement`, `utm_referrer`, `utm_medium`, `utm_source`, `utm_term`, `utm_content`, `utm_campaign`, `conversion_url`, `landing_url`, `user_agent`, `plan`, `coupon`, `ref`, `location`, `translations`, `internal_cta_placement`, `internal_cta_content`, `internal_cta_campaign`, `sale`. Any other key fails with `conversion-info-invalid-key`.

3. **Submit the signup.** Call `POST /v1/auth/subscribe/` with `Accept-Language: en` or `es`. For new accounts the API also stores this language as the user's preferred language, so send the visitor's real locale.

4. **Handle the response using `status` and `access_token` from Step 3.**
   - `access_token` is a string → new account. Persist it with Steps 4–5 of [`bc-authenticate-share-subdomain-session`](../bc-authenticate-share-subdomain-session/SKILL.md) (validate with `GET /v1/auth/token/<token>` to get `expires_at`, then write the cookie).
   - `status` is `ACCEPTED` and `access_token` is `null` → the authenticated user from Step 1 now has the plan. Keep using their current token.
   - `status` is `WAITING_LIST` → show a "you are on the waiting list" message. Do not write a cookie.

5. **Handle `user-exists`.** The email belongs to an existing account and the request was not authenticated as that account. Send the user to log in (hosted login or the login form), then repeat Step 3 with their token in `Authorization`. Never retry without a token.

## Endpoints

All endpoints are under `/v1/auth`. Responses are not paginated. Send `Accept-Language` (`en`, `es`) to receive translated error messages.

| Action | Method | Path | Required headers | Body | Important response |
|---|---|---|---|---|---|
| Sign up | POST | `/v1/auth/subscribe/` | `Content-Type: application/json`; optional `Authorization: Token <token>` of the same user | `email` + one target (`plan`/`course`/`cohort`/`syllabus`) | `status`, `access_token`, `user`, `plans` |

### Sign up request sample

```json
{
  "email": "jane.doe@example.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "phone": "+13055551234",
  "plan": "4geeks-basic-subscription",
  "country": "United States",
  "city": "Miami",
  "has_marketing_consent": true,
  "conversion_info": {
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36",
    "landing_url": "/en/coding-bootcamp",
    "conversion_url": "/en/interactive-exercise/python-beginner-exercises",
    "internal_cta_placement": "navbar-start-practicing",
    "utm_source": "google",
    "utm_medium": "cpc",
    "utm_campaign": "python-exercises"
  }
}
```

### Sign up response sample — new account (`201`, relevant subset)

```json
{
  "id": 4512,
  "email": "jane.doe@example.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "status": "ACCEPTED",
  "access_token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "user": 8831,
  "plans": [
    {
      "slug": "4geeks-basic-subscription",
      "title": "4Geeks Basic",
      "status": "ACTIVE",
      "time_of_life": null,
      "time_of_life_unit": null,
      "trial_duration": 0,
      "trial_duration_unit": "MONTH",
      "has_available_cohorts": false,
      "service_items": [],
      "financing_options": []
    }
  ],
  "academy": null,
  "conversion_info": {
    "landing_url": "/en/coding-bootcamp",
    "conversion_url": "/en/interactive-exercise/python-beginner-exercises"
  }
}
```

### Sign up error sample — existing account without its token (`400`)

```json
{
  "detail": "User already exists, go ahead and log in instead.",
  "status_code": 400,
  "silent": true,
  "silent_code": "user-exists"
}
```

## Edge Cases

Error responses include a stable slug in `slug` or `silent_code`. Branch on the slug, not on `detail`.

- **`user-exists`**: existing account, unauthenticated or authenticated as someone else. Send the user to login, then retry with their token (Step 5).
- **`user-invite-exists-status-accepted`**: the user already has this plan/course. Send them to login.
- **`user-invite-exists-status-pending`** or **`invite-exists`**: the user has an unaccepted invitation. Tell them to check their email for the invitation link; do not retry.
- **`user-invite-exists`**: the email is already on this waiting list. Show the waiting-list message.
- **`without-email`**: `email` missing. Ask for it before submitting.
- **`plan-not-found`**, **`course-not-found`**, **`cohort-not-found`**, **`syllabus-not-found`**, **`academy-not-found`**: the target slug or id is wrong. Fix the form configuration; do not show this to the visitor as their fault.
- **`syllabus-not-belong-to-course`**: the `syllabus` does not belong to the `course`. Send only `course`, or a matching pair.
- **`conversion-info-invalid-key`** or **`conversion-info-json-type`**: remove keys not listed in Step 2, and send `conversion_info` as a JSON object.
- **`401` with a token in `Authorization`**: the token is invalid or expired. Clear the shared cookie (see the shared-session skill) and submit again without `Authorization`; expect `user-exists` if the account already exists.
- **`429` with `rate-limit-exceeded`**: more than 3 submissions per hour for the same email, or 10 per hour from the same IP (failed submissions count too). Disable the submit button and tell the user to retry after `Retry-After` seconds; do not retry automatically.

## Checklist

1. Checked the shared `4g_tok` cookie and sent `Authorization` when the visitor was already logged in.
2. Sent `email` plus exactly one target (`plan`, `course`, `cohort`, or `syllabus`).
3. Sent only allowed `conversion_info` keys.
4. Sent `Accept-Language` with the visitor's locale.
5. Persisted `access_token` with the shared-session skill only when it was a non-null string.
6. Kept the existing token when the response was `ACCEPTED` with `access_token: null`.
7. Showed a waiting-list message (no cookie) on `WAITING_LIST`.
8. On `user-exists`, sent the user to login and retried only with their token.
