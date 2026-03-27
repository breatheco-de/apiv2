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
- **Provisioning setup**: The academy must have a vendor and a profile linking the academy to that vendor, with credentials stored. Use bc-provisioning-settings-and-credentials to create or update profiles and set credentials via the API. For Hostinger/DigitalOcean, staff must persist allowlists in the academy config’s **`vendor_settings`** (e.g. Hostinger: `item_ids`, `template_ids`, `data_center_ids`) using `POST`/`PUT .../provisioningacademy` — not top-level fields like `allowed_template_ids`.

## Workflow

1. **Student: list my VPSs.** Call `GET /v1/provisioning/me/vps`. Use returned `id` values for details.

2. **Academy staff: fetch vendor options (unfiltered universe) first (when the VPS vendor requires selection).** Call `GET /v1/provisioning/academy/provisioningacademy/<provisioning_academy_id>/vendor-options` with `Authorization` and `Academy: <academy_id>`. **Hostinger:** use `catalog_items`, `templates`, `data_centers`. **DigitalOcean:** use `regions`, `sizes`, `images`. Save only the allowed slugs/IDs into the academy config (`vendor_settings`) per vendor via `PUT /v1/provisioning/academy/provisioningacademy/<provisioning_academy_id>` (see bc-provisioning-settings-and-credentials). VPS requests must use `vendor_selection` values that match those allowlists.

3. **Student: request a new VPS.** Call `POST /v1/provisioning/me/vps` with optional `plan_slug` and optional nested `vendor_selection`. **Hostinger:** `item_id`, `template_id`, `data_center_id`. **DigitalOcean:** `region_slug`, `size_slug`, `image_slug`. Values must come from the allowlists in academy `vendor_settings`.

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
| Get academy vendor options | GET | `/v1/provisioning/academy/provisioningacademy/<provisioning_academy_id>/vendor-options` | `Authorization`, `Academy: <academy_id>` | — | **Hostinger:** `catalog_items`, `templates`, `data_centers` (raw payloads). **DigitalOcean:** `regions`, `sizes`, `images` (raw payloads). Other vendors may return empty objects. |

**Request a VPS — request Hostinger (POST `/v1/provisioning/me/vps`):**
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

**Request a VPS — request DigitalOcean (POST `/v1/provisioning/me/vps`):**
```json
{
  "plan_slug": "default",
  "vendor_selection": {
    "region_slug": "nyc1",
    "size_slug": "s-1vcpu-1gb",
    "image_slug": "ubuntu-22-04-x64"
  }
}
```
Body is optional; omit `vendor_selection` to let backend auto-pick when an allowlist has exactly one option (per dimension).

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

**Request VPS for student — request Hostinger (POST `/v1/provisioning/academy/vps`):**
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

**Request VPS for student — request DigitalOcean (POST `/v1/provisioning/academy/vps`):**
```json
{
  "user_id": 50,
  "plan_slug": "default",
  "vendor_selection": {
    "region_slug": "nyc1",
    "size_slug": "s-1vcpu-1gb",
    "image_slug": "ubuntu-22-04-x64"
  }
}
```

**Get academy vendor options — Hostinger example (GET `/v1/provisioning/academy/provisioningacademy/<provisioning_academy_id>/vendor-options`):**
```json
{
  "catalog_items": [
    {
      "id": "hostingercom-vps-kvm1",
      "name": "KVM 1",
      "category": "VPS",
      "metadata": {"cpus": "1", "memory": "4096", "bandwidth": "4096000", "disk_space": "51200", "network": "300"},
      "prices": [
        {"id": "hostingercom-vps-kvm1-usd-1m", "name": "KVM 1 (billed every month)", "currency": "USD", "price": 1949, "first_period_price": 999, "period": 1, "period_unit": "month"}
      ]
    }
  ],
  "templates": [
    {
      "id": 1007,
      "name": "Ubuntu 22.04 LTS",
      "description": "Ubuntu is a complete Linux operating system...",
      "documentation": null
    }
  ],
  "data_centers": [
    {
      "id": 11,
      "name": "bnk",
      "location": "lt",
      "city": "Vilnius",
      "continent": "Europe"
    }
  ]
}
```

**Get academy vendor options — DigitalOcean example (same path; vendor is DigitalOcean):**
```json
{
  "regions": [
    {"slug": "nyc1", "name": "New York 1", "available": true}
  ],
  "sizes": [
    {"slug": "s-1vcpu-1gb", "memory": 1024, "vcpus": 1}
  ],
  "images": [
    {"slug": "ubuntu-22-04-x64", "distribution": "Ubuntu", "name": "22.04 x64"}
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
- **invalid-vps-item-id / invalid-vps-template-id / invalid-vps-data-center-id:** Request selected an option outside academy allowlists (Hostinger). Tell the user to refresh options from `vendor-options` and retry using only allowed IDs.
- **invalid-vps-region-slug / invalid-vps-size-slug / invalid-vps-image-slug (and *-required):** Request selected a DigitalOcean slug outside academy allowlists or omitted a required slug. Tell the user to refresh `vendor-options` and retry.
- **digitalocean-vendor-allowlists-missing:** Academy `vendor_settings` for DigitalOcean is missing `region_slugs`, `size_slugs`, or `image_slugs`. Tell staff to configure allowlists first.
- **missing-vendor-token:** Academy config is missing vendor token when fetching vendor options. Tell staff to update provisioning academy credentials first.
- **hostinger-options-fetch-failed:** Hostinger API lookup failed for vendor options. Tell the user to retry later or verify vendor token permissions.
- **digitalocean-options-fetch-failed:** DigitalOcean API lookup failed for vendor options. Tell the user to retry later or verify the personal access token.

## Checklist

1. For listing or requesting a VPS as a student: call `GET /v1/provisioning/me/vps` or `POST /v1/provisioning/me/vps` with `Authorization`.
2. For VPS connection details (including root password): call `GET /v1/provisioning/me/vps/<vps_id>` as the owning user.
3. For vendor-constrained VPS requests: call `GET /v1/provisioning/academy/provisioningacademy/<provisioning_academy_id>/vendor-options` first, then send selected IDs in nested `vendor_selection`.
4. For academy list: call `GET /v1/provisioning/academy/vps` with `Authorization` and `Academy: <academy_id>` (user must have `crud_provisioning_activity`).
5. For staff requesting a VPS for a student: call `POST /v1/provisioning/academy/vps` with `Authorization`, `Academy: <academy_id>`, and body `user_id` plus optional nested `vendor_selection`; consumes the **student’s** `vps_server` credit.
6. For deprovisioning: call `DELETE /v1/provisioning/academy/vps/<vps_id>` with `Authorization` and `Academy: <academy_id>`.
7. If the API returns allowlist-selection or vendor-options errors, explain the cause and guide the user to refresh allowed options or fix academy credentials before retrying.
