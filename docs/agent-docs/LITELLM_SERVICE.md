# LiteLLM Provisioning & Keys API Documentation

This guide explains the complete LiteLLM integration in BreatheCode: what endpoints exist, how the backend resolves tenant/user context, and how provisioning/deprovisioning is kept consistent over time.

## Overview

LiteLLM support in the provisioning app is designed around three layers:

1. **Access entitlement**
   - A user must have the LLM consumable entitlement to manage keys.
2. **Internal provisioning state**
   - `ProvisioningLLM` tracks the external LiteLLM user by academy and vendor.
3. **External LiteLLM operations**
   - The backend calls LiteLLM to create/delete keys and create/delete users.

### Main model: `ProvisioningLLM`

`ProvisioningLLM` stores the external user lifecycle:

- Unique key: `user + academy + vendor`
- Fields:
  - `external_user_id`
  - `status` (`PENDING`, `ACTIVE`, `DEPROVISIONED`, `ERROR`)
  - `error_message`
  - `last_known_spend` (USD cursor for LiteLLM spend sync)
  - `litellm_team_id` (team used on last sync)
  - `last_budget_sync_at`, `last_budget_sync_error`, `deprovisioned_at`

Service slug for entitlement: **`llm-budget`** (`Service.Consumer.LLM_BUDGET`).

### Team Member Budget sync (v1)

BreatheCode keeps each student's **LiteLLM Team Member Budget** aligned with internal `llm-budget` consumables (USD **cents**, FEFO). LiteLLM enforces `team_memberships[].spend` vs `litellm_budget_table.max_budget`; keys do **not** carry spend caps.

| Phase | LiteLLM | BreatheCode |
| ----- | ------- | ----------- |
| Plan active, never requested a key | No external user | Consumables renew; no FEFO |
| First `POST /me/llm/keys` | `ensure_llm_user` + key + **bootstrap sync** if `last_budget_sync_at is None` | `max = spend + sum(active consumables)/100` |
| Further keys | `create_api_key` only | No extra budget sync |
| Renew with `ProvisioningLLM` ACTIVE | FEFO + `POST /team/member_update` | `align_llm_member_budget_with_consumables` after new consumable |

**Lazy provisioning:** renew does **not** create LiteLLM users. Sync runs only after the student has requested at least one key (`ProvisioningLLM` ACTIVE).

**Core functions** (`breathecode/payments/actions.py`):

- `sync_llm_member_budget_to_llm_provider` — `GET /team/info` + `POST /team/member_update`; updates `last_known_spend`, `litellm_team_id`, `last_budget_sync_at`.
- `align_llm_member_budget_with_consumables` — renew hook: reconcile LiteLLM spend delta via FEFO on older consumables, then call sync.

**`max_budget_in_team` formula:** `spend_actual + (active_llm_budget_cents / 100)`. On renew, consumables expiring within 1 hour are excluded from the sum (cycle rollover forfeit).

**Rate limits:** `tpm_limit` / `rpm_limit` are read from `team_info.team_member_budget_table` when present, else from the member's `litellm_budget_table`, and re-sent on every `member_update` with `budget_duration: null`.

---

## Base URL and Endpoints

LLM key endpoints are defined in provisioning routes:

```113:115:/workspaces/apiv2/breathecode/provisioning/urls.py
    path("me/llm/keys", MeLLMKeysView.as_view(), name="me_llm_keys"),
    path("me/llm/keys/<str:key_id>", MeLLMKeyByIdView.as_view(), name="me_llm_key_by_id"),
    path("academy/admin/llm/teams", AdminLLMTeamsView.as_view(), name="academy_admin_llm_teams"),
```

All examples below assume `/v1/provisioning` prefix.

---

## Key Concepts Before Calling Endpoints

### 1. Academy context resolution

Backend resolves academy in this order:

- `Academy` request header (explicit academy selection), or
- auto-discovery from user memberships (`CohortUser` / `ProfileAcademy`).

### 2. Entitlement check

Before key operations, backend checks the user still has **positive** LLM consumable balance (`Consumable.list` without `include_zero_balance`). Exhausted balance within a valid cycle (`how_many=0`, future `valid_until`) does **not** grant new key management, but it **does** block LiteLLM deprovision (Option B — see below).

### 3. External user identity

Each operation resolves an `external_user_id` (usually from `ProvisioningLLM.external_user_id`, fallback to username-derived value).

---

## API Endpoints

### 1) List LiteLLM API Keys

**Endpoint:** `GET /v1/provisioning/me/llm/keys`

**Purpose**

Returns keys visible for the authenticated user across academies that have LiteLLM provisioning enabled.

**Authentication**

- Required (authenticated user token).

**Headers**

- `Academy` (optional, integer): force academy context.

**Behavior**

- Queries candidate academies for the user.
- Fetches user info from LiteLLM (`get_user_info`) per academy/vendor context.
- Collects `keys` and deduplicates by `token_id`.
- Attaches the same `member_budget` (`spend`, `max`, `remaining`, `currency`) to every key in the academy, read from LiteLLM `GET /team/info` (`team_memberships[]`).
- Resolves `models` per key using priority: `key.models` -> `user_info.models` -> `team.models`.

**Response (200)**

```json
[
  {
    "token_id": "tok_abc123",
    "key_alias": "My Laptop",
    "spend": 1.92,
    "member_budget": {
      "spend": 3.42,
      "max": 10.0,
      "remaining": 6.58,
      "currency": "USD"
    },
    "created_at": "2026-03-21T14:11:00Z",
    "academy_id": 1,
    "models": ["groq/llama-3.1-8b-instant"]
  }
]
```

**Common empty result**

- Returns `[]` when no keys exist or no LiteLLM academy context can be resolved for the user.

---

### 2) Create LiteLLM API Key

**Endpoint:** `POST /v1/provisioning/me/llm/keys`

**Purpose**

Creates a new API key in LiteLLM for the authenticated user.

**Authentication**

- Required.

**Headers**

- `Academy` (optional, integer) to pin academy context.

**Request body**

```json
{
  "key_alias": "My local key"
}
```

**Behavior**

- Normalizes `key_alias`.
- Resolves client/external user id with `ensure_llm_user_record=True`.
- Ensures `ProvisioningLLM` row exists.
- If external user does not exist in LiteLLM, backend attempts `create_user` first.
- Calls LiteLLM `key/generate`.
- **One-time budget bootstrap:** if `ProvisioningLLM.last_budget_sync_at is None`, calls `sync_llm_member_budget_to_llm_provider` (fail-open on LiteLLM errors; retries on a later key). Skipped on subsequent keys.

**Response (201)**

```json
{
  "id": "tok_abc123",
  "key": "sk-plaintext-key",
  "name": "My local key",
  "created_at": "2026-03-21T14:13:00Z"
}
```

**Error responses**

- `403`: user lacks LLM entitlement.
- `404`: academy not found.
- `400`: academy not configured for LLM / invalid context.
- `502`: LiteLLM upstream error.

---

### 3) Delete LiteLLM API Key

**Endpoint:** `DELETE /v1/provisioning/me/llm/keys/{key_id}`

**Purpose**

Deletes one key by token id.

**Authentication**

- Required.

**Path params**

- `key_id` (string): LiteLLM token id.

**Headers**

- `Academy` (optional but recommended).

**Response (204)**

- Empty body.

**Error responses**

- `403`: user has no entitlement or no academy permission.
- `502`: LiteLLM delete call failed.

---

### 4) List LiteLLM Teams (Admin)

**Endpoint:** `GET /v1/provisioning/academy/admin/llm/teams`

**Purpose**

Returns all LiteLLM teams visible to the tenant credentials configured for the selected academy.

**Authentication**

- Required.
- Requires academy capability: `crud_provisioning_activity`.

**Headers**

- `Academy` (required): academy used for authorization and tenant credential resolution.

**Response (200)**

```json
[
  {
    "team_id": "27c669b7-3be8-43a9-94f6-2c1a6c625b3c",
    "team_alias": "AI Engineering",
    "models": ["groq/llama-3.1-8b-instant"],
    "max_budget": 5.0,
    "budget_duration": "30d",
    "budget_reset_at": "2026-06-01T00:00:00Z",
    "spend": 0.0013,
    "blocked": false
  }
]
```

## End-to-End Creation Flow (What Happens Internally)

When `POST /me/llm/keys` is called:

1. API validates user context and entitlement (positive balance).
2. API resolves academy/vendor and builds LiteLLM client.
3. API ensures `ProvisioningLLM` record exists (`ensure_llm_user`).
4. API creates the API key in LiteLLM.
5. If `last_budget_sync_at is None`, API bootstraps Team Member Budget (`sync_llm_member_budget_to_llm_provider`).
6. API returns plaintext key once.

Renew flow (`renew_consumables`, consumer `LLM_BUDGET`):

1. Emit new consumable (existing scheduler logic).
2. If `ProvisioningLLM` ACTIVE for user+academy → `align_llm_member_budget_with_consumables` (FEFO + sync).
3. If no ACTIVE provisioning row → consumable only; no LiteLLM calls.

Reference snippet:

```2102:2118:breathecode/provisioning/views.py
            client, external_user_id, academy_id = resolve_llm_client_and_external_id(
                request, ensure_llm_user_record=True
            )
            created = client.create_api_key(external_user_id=external_user_id, name=alias, metadata=metadata)

            # One-time member budget bootstrap while last_budget_sync_at is null (retries on later keys).
            llm_ctx = resolve_llm_provisioning_context(request.user, academy_id)
            if llm_ctx and llm_ctx[0].last_budget_sync_at is None:
                provisioning_llm, pa_llm, _ = llm_ctx
                try:
                    payment_actions.sync_llm_member_budget_to_llm_provider(
                        provisioning_llm,
                        pa_llm,
                        client,
                    )
```

---

## Deprovisioning Paths (Option B)

The system has two independent ways to deprovision LiteLLM users.

### A) Signal-driven deprovision (reactive)

When payment/services logic emits `deprovision_service` for LLM service:

- Receiver checks if user still has matching consumable with **positive balance** (`user_has_service_entitlement_in_academy`).
- If entitlement still exists, it skips deprovision.
- If entitlement is gone, it calls registered deprovisioner (which enqueues `deprovision_litellm_user_task`).

### B) Supervisor-driven deprovision (safety net)

`supervise_llm_users_without_budget` periodically scans for drift:

- `ProvisioningLLM.status = ACTIVE`
- but user has **no non-expired** `llm-budget` consumable in the academy — **including `how_many=0`** (`include_zero_balance=True`).

It opens issue `llm-user-missing-budget`, and issue handler schedules deprovision task.

### Option B: exhausted balance vs lost cycle

| State | Keys API | LiteLLM user/keys |
| ----- | -------- | ----------------- |
| `how_many > 0`, valid cycle | Allowed | Kept; budget synced on renew |
| `how_many = 0`, valid `valid_until` | 403 (no balance) | **Not** deprovisioned; LiteLLM blocks when `spend >= max` |
| No valid consumable in academy | 403 | Deprovisioned (signal, task, or supervisor) |

This protects against missed signals, transient failures, and out-of-band state drift.

---

## Deprovision Task Details

Task: `deprovision_litellm_user_task(user_id, academy_id=None)`

High-level behavior:

1. Abort if local user does not exist.
2. Skip if user still has a **non-expired** `llm-budget` consumable (`include_zero_balance=True`, scoped by academy when `academy_id` is set).
3. Group rows by `(academy_id, vendor_id)` to use correct tenant credentials.
4. Delete external user ids in LiteLLM (`delete_user`).
5. Update local `ProvisioningLLM` rows:
   - success → `DEPROVISIONED`
   - failure → `ERROR` + retry.

Reference:

```768:792:breathecode/provisioning/tasks.py
    if academy_id:
        if (
            Consumable.list(user=user, service="llm-budget", include_zero_balance=True)
            .filter(
                Q(subscription__academy_id=academy_id)
                | Q(plan_financing__academy_id=academy_id)
                | Q(standalone_invoice__bag__academy_id=academy_id)
                | Q(subscription_seat__billing_team__subscription__academy_id=academy_id)
                | Q(plan_financing_seat__team__financing__academy_id=academy_id)
            )
            .exists()
        ):
            logger.info(
                "User %s still has valid (non-expired) llm-budget consumable for academy %s, skipping deprovision",
                user_id,
                academy_id,
            )
            return
    ...
    provisioning_llms_qs = ProvisioningLLM.objects.filter(user=user).select_related("academy", "vendor").all()
```

---

## LiteLLM Client Methods Used by Backend

Main methods in `breathecode/services/litellm/client.py`:

- `get_team_info(team_id)` — `GET /team/info?team_id=` (`team_memberships[].spend`, tpm/rpm templates)
- `update_team_member(team_id, user_id, max_budget_in_team, *, budget_duration=None, tpm_limit, rpm_limit)` — `POST /team/member_update` (Team Member Budget)
- `create_api_key(external_user_id, name)` — `duration: "30d"` on keys (unchanged)
- `delete_api_keys(user_id, token_ids)`
- `get_user_info(user_id)`
- `create_user(user_id, user_email, user_alias)`
- `add_user_to_team(team_id, user_ids)`
- `delete_user(user_ids)`

These are thin wrappers around LiteLLM proxy endpoints (`/key/generate`, `/key/delete`, `/user/info`, `/user/new`, `/user/delete`).

LiteLLM vendor settings now require `team_id` (`vendor_settings.team_id`) so users can be assigned to the selected team when ensured/created.

---

## Troubleshooting Guide

### Problem: User cannot create key

Check in order:

1. User has LLM entitlement consumable.
2. Academy has provisioning config and LiteLLM vendor credentials.
3. User belongs to selected academy context.
4. LiteLLM upstream is reachable.

### Problem: Key list is empty unexpectedly

Check:

1. Correct academy header/context.
2. `ProvisioningLLM` row exists and has valid `external_user_id`.
3. LiteLLM `user/info` returns keys for that user.

### Problem: User not deprovisioned after losing access

Check:

1. `deprovision_service` signal receiver logs.
2. `deprovision_litellm_user_task` execution status/retries.
3. `ProvisioningLLM.status` and `error_message`.
4. Supervisor issue records (`llm-user-missing-budget`).

---

## Operational Notes

### Idempotency and Safety

- Deprovision task rechecks **valid-cycle** consumables (`include_zero_balance=True`) before deleting.
- Supervisor issue handler rechecks the same before scheduling.
- `last_known_spend` prevents double FEFO on `renew_consumables` retries.
- Grouping by `(academy, vendor)` prevents wrong-tenant deletion calls.

### Deploy checklist

- Ensure `ServiceItem.how_many` for `llm-budget` is finite **USD cents** in production (not `-1`).
- `ProvisioningAcademy.vendor_settings.team_id` must be set per academy.
- No new cron: budget sync runs on **renew** (ACTIVE provisioning) and **first key** bootstrap only.

### Frequency Tuning

Supervisor frequency can be tuned by business tolerance:

- lower interval: faster cleanup, more background load.
- higher interval: less load, slower drift correction.

Choose based on cost/risk profile for lingering external LiteLLM users.
