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
  - `last_sync_at`, `deprovisioned_at`

This model is the source of truth for “does this user exist in LiteLLM for this academy/vendor context?”

---

## Base URL and Endpoints

LLM key endpoints are defined in provisioning routes:

```113:115:/workspaces/apiv2/breathecode/provisioning/urls.py
    path("me/llm/keys", MeLLMKeysView.as_view(), name="me_llm_keys"),
    path("me/llm/keys/<str:key_id>", MeLLMKeyByIdView.as_view(), name="me_llm_key_by_id"),
```

All examples below assume `/v1/provisioning` prefix.

---

## Key Concepts Before Calling Endpoints

### 1. Academy context resolution

Backend resolves academy in this order:

- `Academy` request header (explicit academy selection), or
- auto-discovery from user memberships (`CohortUser` / `ProfileAcademy`).

### 2. Entitlement check

Before key operations, backend checks the user still has LLM consumable access.

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

**Response (200)**

```json
[
  {
    "token_id": "tok_abc123",
    "key_alias": "My Laptop",
    "spend": 1.92,
    "created_at": "2026-03-21T14:11:00Z",
    "academy_id": 1
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

## End-to-End Creation Flow (What Happens Internally)

When `POST /me/llm/keys` is called:

1. API validates user context and entitlement.
2. API resolves academy/vendor and builds LiteLLM client.
3. API ensures `ProvisioningLLM` record exists.
4. API checks if external user exists in LiteLLM.
5. If external user is missing, API creates it.
6. API creates key and returns plaintext key once.

Reference snippet:

```1328:1335:/workspaces/apiv2/breathecode/provisioning/views.py
        try:
            client, external_user_id, academy_id = resolve_llm_client_and_external_id(
                request, ensure_llm_user_record=True
            )
            created = client.create_api_key(external_user_id=external_user_id, name=alias)
```

---

## Deprovisioning Paths

The system has two independent ways to deprovision LiteLLM users.

### A) Signal-driven deprovision (reactive)

When payment/services logic emits `deprovision_service` for LLM service:

- Receiver checks if user still has matching consumable.
- If entitlement still exists, it skips deprovision.
- If entitlement is gone, it calls registered deprovisioner.

### B) Supervisor-driven deprovision (safety net)

`supervise_llm_users_without_budget` periodically scans for drift:

- `ProvisioningLLM.status = ACTIVE`
- but user has no LLM entitlement consumable.

It opens issue `llm-user-missing-budget`, and issue handler schedules deprovision task.

This protects against missed signals, transient failures, and out-of-band state drift.

---

## Deprovision Task Details

Task: `deprovision_litellm_user_task(user_id)`

High-level behavior:

1. Abort if local user does not exist.
2. Skip if user still has LLM consumable entitlement.
3. Group rows by `(academy_id, vendor_id)` to use correct tenant credentials.
4. Delete external user ids in LiteLLM (`delete_user`).
5. Update local `ProvisioningLLM` rows:
   - success -> `DEPROVISIONED`
   - failure -> `ERROR` + retry.

Reference:

```600:679:/workspaces/apiv2/breathecode/provisioning/tasks.py
@task(priority=TaskPriority.STUDENT.value)
def deprovision_litellm_user_task(user_id: int, **_: Any):
    ...
    if Consumable.list(user=user, service="free_monthly_llm_budget").exists():
        logger.info(f"User {user_id} still has free_monthly_llm_budget, skipping deprovision")
        return
    ...
    client.delete_user(user_ids=user_id_list)
    ...
    ProvisioningLLM.objects.filter(...).update(
        status=ProvisioningLLM.STATUS_DEPROVISIONED,
        deprovisioned_at=now,
        error_message="",
        updated_at=timezone.now(),
    )
```

---

## LiteLLM Client Methods Used by Backend

Main methods in `breathecode/services/litellm/client.py`:

- `create_api_key(external_user_id, name)`
- `delete_api_keys(user_id, token_ids)`
- `get_user_info(user_id)`
- `create_user(user_id, user_email, user_alias)`
- `delete_user(user_ids)`

These are thin wrappers around LiteLLM proxy endpoints (`/key/generate`, `/key/delete`, `/user/info`, `/user/new`, `/user/delete`).

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

- Deprovision task rechecks entitlement before deleting.
- Supervisor issue handler rechecks conditions before scheduling.
- Grouping by `(academy, vendor)` prevents wrong-tenant deletion calls.

### Frequency Tuning

Supervisor frequency can be tuned by business tolerance:

- lower interval: faster cleanup, more background load.
- higher interval: less load, slower drift correction.

Choose based on cost/risk profile for lingering external LiteLLM users.
