---
name: bc-provisioning-manage-vps-server
description: Use when a user, student or academy staff needs to request, list, view, or deprovision a VPS via the API (including staff requesting a VPS on behalf of a student); do NOT use for granting VPS credits via plans or payments.
requires: []
---

# Skill: Manage VPS Provisioning via the API

## When to Use

Use this skill when the user asks to **request a VPS**, **list my VPSs**, **get VPS connection details** (including root password), **list academy VPSs**, **request a VPS for a student (staff)**, or **deprovision a student's VPS** — all via the API. Do **not** use when the user only asks how to configure vendor credentials or create/update provisioning profiles — use bc-provisioning-settings-and-credentials for that. Do **not** use for granting VPS credits through plans or subscriptions.

## Concepts

- **VPS**: One virtual server instance per student per academy. States: `PENDING`, `PROVISIONING`, `ACTIVE`, `ERROR`, `DELETED`. At most one active (or pending/provisioning) VPS per user per academy.
- **VPS credits**: A student can request a VPS only if they have at least one consumable for the service `vps_server` with balance greater than zero. One request consumes one unit. The API does not grant credits; they are managed via plans/subscriptions or other APIs.
- **Provisioning setup**: The academy must have a vendor and a profile linking the academy to that vendor, with credentials stored. Use bc-provisioning-settings-and-credentials to create or update profiles and set credentials via the API.

## Workflow

1. **Student: list my VPSs.** Call `GET /v1/provisioning/me/vps`. Use returned `id` values for details.

2. **Academy staff: fetch allowed vendor options first (when vendor requires selection).** Call `GET /v1/provisioning/academy/provisioningacademy/<provisioning_academy_id>/vendor-options` with `Authorization` and `Academy: <academy_id>`. Use returned `catalog_items`, `templates`, and `data_centers` to build selectable options in UI. Do not offer options outside this response.

3. **Student: request a new VPS.** Call `POST /v1/provisioning/me/vps` with optional `plan_slug` and optional nested `vendor_selection`. For Hostinger, `vendor_selection` supports `item_id`, `template_id`, `data_center_id`. Values must be from the allowlists configured in academy `vendor_settings`.

4. **Student: get one VPS (including root password).** Call `GET /v1/provisioning/me/vps/<vps_id>`. Only the owner gets `root_password`.

5. **Academy: list all VPSs.** Call `GET /v1/provisioning/academy/vps` with headers `Authorization` and `Academy: <academy_id>`. Optional query: `user_id=<user_id>`.

6. **Academy: request a VPS for a student (staff).** Call `POST /v1/provisioning/academy/vps` with headers `Authorization` and `Academy: <academy_id>`. Body requires `user_id`; supports optional `plan_slug` and optional nested `vendor_selection`.

7. **Academy: deprovision a VPS.** Call `DELETE /v1/provisioning/academy/vps/<vps_id>` with headers `Authorization` and `Academy: <academy_id>`.

**Prerequisite:** Vendor, academy profile, and credentials must already be configured. If the user has no academy or the academy has no VPS configuration, the API returns errors; tell the user setup must be completed first. VPS credits are managed via plans/subscriptions or other APIs, not this one.

## Endpoints

| Action | Method | Path | Headers | Body / Query | Response |
|--------|--------|------|---------|--------------|----------|
| List my VPSs | GET | `/v1/provisioning/me/vps` | `Authorization` | — | List of VPSs; see response sample. |
| Request a VPS | POST | `/v1/provisioning/me/vps` | `Authorization` | Optional; supports `plan_slug` and nested `vendor_selection`. | 202 Accepted, VPS object; see response sample. |
| Get one VPS (with password) | GET | `/v1/provisioning/me/vps/<vps_id>` | `Authorization` | — | VPS detail including `root_password` for owner; see response sample. |
| List academy VPSs | GET | `/v1/provisioning/academy/vps` | `Authorization`, `Academy: <academy_id>` | Optional: `?user_id=<user_id>` | List of VPSs for academy (no root_password). |
| Request VPS for student | POST | `/v1/provisioning/academy/vps` | `Authorization`, `Academy: <academy_id>` | `user_id` required; optional `plan_slug` and nested `vendor_selection`. | 202 Accepted, VPS object (no root_password). |
| Deprovision VPS | DELETE | `/v1/provisioning/academy/vps/<vps_id>` | `Authorization`, `Academy: <academy_id>` | — | 204 No Content. |
| Get academy vendor options | GET | `/v1/provisioning/academy/provisioningacademy/<provisioning_academy_id>/vendor-options` | `Authorization`, `Academy: <academy_id>` | — | Allowed `catalog_items`, `templates`, `data_centers` for that academy vendor config. |

**Request a VPS — request (POST `/v1/provisioning/me/vps`):**
```json
{
  "plan_slug": "default",
  "vendor_selection": {
    "item_id": "12345",
    "template_id": 101,
    "data_center_id": 7
  }
}
```
Body is optional; omit `vendor_selection` to let backend auto-pick when an allowlist has exactly one option.

**Request a VPS — response (202 Accepted):**
```json
{
  "id": 100,
  "status": "PENDING",
  "hostname": "",
  "ip_address": null,
  "ssh_user": "",
  "ssh_port": 22,
  "plan_slug": "default",
  "error_message": "",
  "requested_at": "2026-03-26T15:20:00Z",
  "provisioned_at": null,
  "deleted_at": null,
  "created_at": "2026-03-26T15:20:00Z",
  "updated_at": "2026-03-26T15:20:00Z"
}
```
Later the VPS may move to `ACTIVE` or `ERROR`; use GET to fetch updated details and `root_password` when ACTIVE.

**Request VPS for student — request (POST `/v1/provisioning/academy/vps`):**
```json
{
  "user_id": 50,
  "plan_slug": "default",
  "vendor_selection": {
    "item_id": "12345",
    "template_id": 101,
    "data_center_id": 7
  }
}
```

**Get academy vendor options — response (GET `/v1/provisioning/academy/provisioningacademy/<provisioning_academy_id>/vendor-options`):**
```json
{
  "catalog_items": [
    {"id": "12345", "name": "KVM 2"}
  ],
  "templates": [
    {"id": 101, "name": "Ubuntu 24.04", "operating_system": "linux"}
  ],
  "data_centers": [
    {"id": 7, "name": "US East"}
  ]
}
```

**Get one VPS — response (GET `/v1/provisioning/me/vps/<vps_id>`, owner only):**
```json
{
  "id": 100,
  "status": "ACTIVE",
  "hostname": "vps-100.example.com",
  "ip_address": "192.168.1.10",
  "ssh_user": "root",
  "ssh_port": 22,
  "root_password": "generated-secret-password",
  "plan_slug": "default",
  "error_message": "",
  "requested_at": "2026-03-26T15:20:00Z",
  "provisioned_at": "2026-03-26T15:25:00Z",
  "deleted_at": null,
  "created_at": "2026-03-26T15:20:00Z",
  "updated_at": "2026-03-26T15:25:00Z"
}
```

Base path for all: `/v1/provisioning/`. Academy endpoints require capability `crud_provisioning_activity`.

## Edge Cases

- **no-academy-for-vps:** User has no academy (no active cohort or profile). Tell the user they must belong to an academy (e.g. be in a cohort) to request a VPS; do not retry the same request.
- **academy-vps-not-configured:** No provisioning profile with credentials exists for the user's academy. Tell the user the academy must configure a vendor and credentials first.
- **duplicate-vps:** User already has an active or pending VPS for that academy. Tell the user they can have only one active or pending VPS per academy; they must deprovision or wait before requesting another.
- **insufficient-vps-server-credits:** User has no `vps_server` consumable with balance > 0. Tell the user they need VPS credits (via plan/subscription or other API); this API does not grant credits.
- **student-not-in-academy:** Staff POST: the target user is not an active member of the academy in the `Academy` header. Tell the staff user the student must have an active profile or cohort membership in that academy.
- **user-not-found (404):** Staff POST: `user_id` does not match any user.
- **vps-not-found (404):** GET or DELETE by id returns 404. Tell the user the VPS does not exist or does not belong to them (student) or to the academy (staff); verify the id and academy.
- **invalid-vps-item-id / invalid-vps-template-id / invalid-vps-data-center-id:** Request selected an option outside academy allowlists. Tell the user to refresh options from `vendor-options` and retry using only allowed IDs.
- **missing-vendor-token:** Academy config is missing vendor token when fetching vendor options. Tell staff to update provisioning academy credentials first.
- **hostinger-options-fetch-failed:** Hostinger API lookup failed for vendor options. Tell the user to retry later or verify vendor token permissions.

## Checklist

1. For listing or requesting a VPS as a student: call `GET /v1/provisioning/me/vps` or `POST /v1/provisioning/me/vps` with `Authorization`.
2. For VPS connection details (including root password): call `GET /v1/provisioning/me/vps/<vps_id>` as the owning user.
3. For vendor-constrained VPS requests: call `GET /v1/provisioning/academy/provisioningacademy/<provisioning_academy_id>/vendor-options` first, then send selected IDs in nested `vendor_selection`.
4. For academy list: call `GET /v1/provisioning/academy/vps` with `Authorization` and `Academy: <academy_id>` (user must have `crud_provisioning_activity`).
5. For staff requesting a VPS for a student: call `POST /v1/provisioning/academy/vps` with `Authorization`, `Academy: <academy_id>`, and body `user_id` plus optional nested `vendor_selection`; consumes the **student’s** `vps_server` credit.
6. For deprovisioning: call `DELETE /v1/provisioning/academy/vps/<vps_id>` with `Authorization` and `Academy: <academy_id>`.
7. If the API returns allowlist-selection or vendor-options errors, explain the cause and guide the user to refresh allowed options or fix academy credentials before retrying.
