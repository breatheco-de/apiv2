---
name: bc-provisioning-manage-my-llm-keys
description: Use when an authenticated student needs to check LLM budget entitlement, list LiteLLM API keys and per-key spend, create a new LLM API key, or delete an existing key; do NOT use for academy staff configuring LiteLLM vendors or teams, VPS provisioning, or granting LLM budget through plans.
requires:
  - bc-authenticate-student-authentication
---

# Skill: Manage My LiteLLM API Keys

## When to Use

Use this skill when a **student** asks to **check LLM budget access**, **list LLM API keys**, **see key spend or usage**, **create an LLM API key**, or **delete/revoke an LLM API key** via the BreatheCode API.

Do **not** use for academy staff configuring LiteLLM vendors, credentials, or teams (`bc-provisioning-settings-and-credentials`). Do **not** use for VPS provisioning (`bc-provisioning-manage-vps-server`). Do **not** use for granting LLM budget through plans or subscriptions.

## Concepts

- **LLM budget entitlement**: Service slug `free-monthly-llm-budget`. Type VOID — it gates key management; it is **not** decremented on each LLM call.
- **LiteLLM proxy**: External service where keys are used for inference. The `host` field in API responses is the base URL for LiteLLM calls.
- **spend**: Per-key USD spend reported by LiteLLM on the list endpoint. BreatheCode does **not** expose team-level budget remaining — only entitlement presence and per-key `spend`.
- **Academy header**: Required on **POST** (create) and **DELETE** (revoke) even though paths are under `/me/`. Use the academy where the user holds the entitlement (from consumables or cohort membership).

## Workflow

1. **Authenticate.** Load [`bc-authenticate-student-authentication`](../bc-authenticate-student-authentication/SKILL.md) if the user has no token. All endpoints require `Authorization`.

2. **Check entitlement (optional but recommended).** Call `GET /v1/payments/me/service/consumable?service_slug=free-monthly-llm-budget`. Confirm `voids` contains an entry with slug `free-monthly-llm-budget` and `balance.unit > 0` (or `-1` for unlimited). If the user has a standalone grant, note `academy.id` from the consumable item — you need it for the `Academy` header in steps 4 and 5.

3. **List keys and spend.** Call `GET /v1/provisioning/me/llm/keys`. Response is a **JSON array (not paginated)**. Read `token_id`, `spend`, `models`, `host`, `academy_id`, and `key_alias`. An empty array `[]` is normal before the first key is created — proceed to step 4 if the user wants a key.

4. **Create a key.** Call `POST /v1/provisioning/me/llm/keys` with header **`Academy: <academy_id>`**. Optional body: `key_alias`, `plan_slug`. Save the returned **`key`** immediately — it is shown **only once**. Use `host` as the LiteLLM base URL for inference calls outside BreatheCode.

5. **Delete a key.** Call `DELETE /v1/provisioning/me/llm/keys/<token_id>` with header **`Academy: <academy_id>`** matching the key's `academy_id` from step 3. Expect **204 No Content**.

**Prerequisite:** The academy must have LiteLLM provisioning configured by staff. If the API returns `academy-llm-not-configured`, tell the user to contact their program manager. LLM budget is granted via plans or subscriptions — this skill does not grant it.

## Endpoints

| Action | Method | Path | Headers | Body / Query | Response |
|--------|--------|------|---------|--------------|----------|
| Check LLM entitlement | GET | `/v1/payments/me/service/consumable` | `Authorization` | Optional: `?service_slug=free-monthly-llm-budget` | Balance object; see response sample |
| List my LLM keys | GET | `/v1/provisioning/me/llm/keys` | `Authorization` | — | **Unpaginated** JSON array; see response sample |
| Create LLM key | POST | `/v1/provisioning/me/llm/keys` | `Authorization`, **`Academy: <academy_id>`** | Optional JSON body | 201; plaintext `key` shown once |
| Delete LLM key | DELETE | `/v1/provisioning/me/llm/keys/<token_id>` | `Authorization`, **`Academy: <academy_id>`** | — | 204 No Content |

Send **`Accept-Language`** (e.g. `en`, `es`) to receive translated error messages when the API supports translation.

**Check entitlement — response (GET `/v1/payments/me/service/consumable?service_slug=free-monthly-llm-budget`):**

```json
{
  "mentorship_service_sets": [],
  "cohort_sets": [],
  "event_type_sets": [],
  "voids": [
    {
      "id": 42,
      "slug": "free-monthly-llm-budget",
      "balance": {
        "unit": 1
      },
      "items": []
    }
  ]
}
```

**List keys — response (GET `/v1/provisioning/me/llm/keys`, not paginated):**

```json
[
  {
    "token_id": "tok-a",
    "key_alias": "My Laptop",
    "spend": 1.2,
    "created_at": "2026-01-01T00:00:00Z",
    "academy_id": 1,
    "host": "https://litellm.example.com",
    "vendor_name": "litellm",
    "metadata": {},
    "models": ["groq/llama-3.1-8b-instant"]
  }
]
```

**Create key — request (POST `/v1/provisioning/me/llm/keys`):**

```json
{
  "key_alias": "My Laptop",
  "plan_slug": "4geeks-plus-subscription"
}
```

Both fields are optional. If `key_alias` is omitted, the API uses the user's first name or username.

**Create key — response (201 Created):**

```json
{
  "id": "tok-created",
  "key": "sk-xxx",
  "name": "My Laptop",
  "created_at": "2026-01-03T00:00:00Z",
  "models": ["groq/llama-3.1-8b-instant"],
  "host": "https://litellm.example.com",
  "vendor_name": "LiteLLM"
}
```

**Delete key — response (DELETE `/v1/provisioning/me/llm/keys/tok-a`):**

Empty body, HTTP 204.

Base paths: `/v1/payments/` for entitlement, `/v1/provisioning/` for keys.

## Edge Cases

- **llm-budget-required (403):** User lacks the `free-monthly-llm-budget` consumable. Tell the user they need an active plan or subscription that includes LLM budget; do not retry key endpoints.
- **llm-academy-header-required (400):** Missing `Academy` header on POST or DELETE. Ask the user which academy they belong to (from cohort membership or consumable `academy_id`) and retry with `Academy: <id>`.
- **academy-not-permitted (403):** User is not a member of the academy in the header. Verify academy id from enrollment or consumables.
- **academy-not-found (404):** Invalid academy id in header.
- **academy-llm-not-configured / llm-client-not-configured (400):** Academy has no LiteLLM provisioning setup. Tell the user to contact their program manager; do not retry.
- **llm-key-create-error / llm-key-delete-error (502):** LiteLLM upstream failure. Tell the user to retry later.
- **plan-not-found (404):** Invalid `plan_slug` in POST body. Omit `plan_slug` or use a valid plan slug.
- **Empty list with valid entitlement:** Normal before the first key — call POST to create a key (which also provisions the user in LiteLLM).
- **Key expired:** Keys are created with a 30-day duration in LiteLLM. Create a new key when the old one expires.

## Checklist

1. [ ] User is authenticated (`Authorization` header set).
2. [ ] Checked entitlement via `GET /v1/payments/me/service/consumable` when the user asks about budget access.
3. [ ] Listed keys via `GET /v1/provisioning/me/llm/keys` when the user asks about keys or spend.
4. [ ] Sent `Academy: <academy_id>` on POST and DELETE.
5. [ ] Saved the plaintext `key` from the 201 response immediately after create.
6. [ ] Used `token_id` from the list response for DELETE.
7. [ ] Did not call staff-only endpoints (e.g. `/academy/admin/llm/teams`).
