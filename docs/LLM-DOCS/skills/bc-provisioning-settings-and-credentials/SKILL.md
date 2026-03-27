---
name: bc-provisioning-settings-and-credentials
description: Use when academy staff need to create or update provisioning profiles (academy–vendor link) or set credentials and settings for an academy; do NOT use for requesting or listing VPS (use bc-provisioning-manage-vps-server).
requires: []
---

# Skill: Set Provisioning Settings and Credentials

## When to Use

Use this skill when the user asks to **create or update a provisioning profile** (link an academy to a vendor, optionally restrict by cohorts or members), or to **set or change provisioning credentials and settings** (vendor token, idle timeout, max containers) for an academy. Do **not** use when the user only wants to request a VPS, list VPSs, or deprovision a VPS — use bc-provisioning-manage-vps-server for that.

## Concepts

- **Provisioning profile**: Links an academy to a vendor. Optional: restrict which cohorts or members use that vendor. At least one profile and a matching academy config with credentials are required for students to request a VPS.
- **Vendor type**: Vendors are grouped by `vendor_type` (`CODING_EDITOR`, `VPS_SERVER`, `LLM`). Vendors of the same type share connection-check protocol behavior.
- **Provisioning academy config**: Per (academy, vendor): stores credentials (token, optional key) and settings (container_idle_timeout, max_active_containers, allowed_machine_types). Credentials are never returned by the API; the response only indicates whether they are set. List and detail responses also include **vendor API connection health**: `connection_status` (e.g. `UNTESTED`, `OK`, `DEGRADED`, `ERROR`), optional `connection_status_text`, and `connection_test_at` (timestamp of the last connection test, or null). These are read-only in the API; they are updated when the backend runs a vendor connection check.
- **Vendor settings allowlists**: Some vendors (e.g. Hostinger) require extra allowlist values stored in `vendor_settings`. The vendor list endpoint (`GET /v1/provisioning/academy/vendor`) returns a `settings_schema` per vendor that tells you which keys/types must be provided inside `vendor_settings`.
- **Academy scope:** All endpoints use the **Academy** header to identify the academy; there is no academy_id in the URL path.

## Workflow

1. **List provisioning vendors (optional).** When you need valid `vendor_id` values for creating profiles or academy configs, call `GET /v1/provisioning/academy/vendor` with `Authorization` and `Academy: <academy_id>`. Response is a list of vendors; each vendor includes `settings_schema` that describes which keys/types to send inside `vendor_settings` for that vendor.

2. **List current profiles.** Call `GET /v1/provisioning/academy/provisioningprofile` with `Authorization` and `Academy: <academy_id>`. Response includes each profile's id, vendor, academy, cohort_ids, member_ids. Use the profile id for update or delete.

3. **Create a profile.** Call `POST /v1/provisioning/academy/provisioningprofile` with `Authorization` and `Academy: <academy_id>`. Body: `vendor_id` (required), optional `cohort_ids` (list), `member_ids` (list). Cohort and member IDs must belong to that academy. Response is 201 with the new profile.

4. **Update or delete a profile.** Call `PUT /v1/provisioning/academy/provisioningprofile/<profile_id>` to update (body: optional vendor_id, cohort_ids, member_ids) or `DELETE /v1/provisioning/academy/provisioningprofile/<profile_id>` to remove. Academy is from the header.

5. **List academy configs (credentials/settings).** Call `GET /v1/provisioning/academy/provisioningacademy` with `Authorization` and `Academy: <academy_id>`. Response includes id, vendor, academy_id, credentials_set (boolean), `connection_status`, `connection_status_text`, `connection_test_at`, container_idle_timeout, max_active_containers; credentials are never returned.

6. **Create academy config.** Call `POST /v1/provisioning/academy/provisioningacademy` with `Authorization` and `Academy: <academy_id>`. Body: `vendor_id` (required), `credentials_token` (required), optional `credentials_key`, `container_idle_timeout` (default 15), `max_active_containers` (default 2), `allowed_machine_type_ids` (list). Only one config per (academy, vendor). Response is 201; credentials are not echoed.

7. **Update academy config.** Call `PUT /v1/provisioning/academy/provisioningacademy/<provisioning_academy_id>` with optional body fields: credentials_token, credentials_key, container_idle_timeout, max_active_containers, allowed_machine_type_ids. Omit credentials to leave them unchanged.

8. **Delete academy config.** Call `DELETE /v1/provisioning/academy/provisioningacademy/<provisioning_academy_id>` with `Authorization` and `Academy: <academy_id>`. Returns 204 No Content. Deleting the config removes credentials and settings for that (academy, vendor); it does not delete the provisioning profile. To fully stop using a vendor, delete the profile (and optionally delete the config).

9. **Test vendor API connection status.** Call `POST /v1/provisioning/academy/provisioningacademy/<provisioning_academy_id>/test-connection` with `Authorization` and `Academy: <academy_id>`. This endpoint runs a vendor-specific connectivity check, updates `connection_status`, `connection_status_text`, and `connection_test_at`, and returns the updated provisioning academy object.

**For VPS to work:** The academy must have at least one provisioning profile linking it to a vendor, and a provisioning academy config for that same vendor with `credentials_token` set. Additionally, for Hostinger, you must configure non-empty `vendor_settings` allowlists (`item_ids`, `template_ids`, `data_center_ids`). Create the profile first, then create the academy config for that vendor, then fill `vendor_settings`.

After credentials/settings are in place, when the user actually requests a VPS you should switch to `bc-provisioning-manage-vps-server`.

To configure Hostinger allowlists, staff should first fetch the full set of vendor options by calling:
`GET /v1/provisioning/academy/provisioningacademy/<provisioning_academy_id>/vendor-options`.

For Hostinger, this `vendor-options` response returns the full (unfiltered) universe of options from the vendor account (catalog items, templates, and data centers) as raw vendor payload objects (not reduced to only `id`/`name`).

Then select which IDs are allowed and store them in the provisioning academy config (`vendor_settings`: `item_ids`, `template_ids`, `data_center_ids`). VPS provisioning will fail until these allowlists are non-empty.

## Endpoints

| Action | Method | Path | Headers | Body | Response |
|--------|--------|------|---------|------|----------|
| List vendors | GET | `/v1/provisioning/academy/vendor` | `Authorization`, `Academy: <academy_id>` | — | List of vendors (id, name, vendor_type, workspaces_url, settings_schema). Use vendor id when creating profiles or academy configs; use settings_schema to build `vendor_settings` for that vendor. |
| List profiles | GET | `/v1/provisioning/academy/provisioningprofile` | `Authorization`, `Academy: <academy_id>` | — | List of profiles (id, vendor, academy, cohort_ids, member_ids). |
| Create profile | POST | `/v1/provisioning/academy/provisioningprofile` | `Authorization`, `Academy: <academy_id>` | See request sample below. | 201, profile object (see response sample). |
| Get profile | GET | `/v1/provisioning/academy/provisioningprofile/<profile_id>` | `Authorization`, `Academy: <academy_id>` | — | Profile object. |
| Update profile | PUT | `/v1/provisioning/academy/provisioningprofile/<profile_id>` | `Authorization`, `Academy: <academy_id>` | Optional: vendor_id, cohort_ids, member_ids. | Profile object. |
| Delete profile | DELETE | `/v1/provisioning/academy/provisioningprofile/<profile_id>` | `Authorization`, `Academy: <academy_id>` | — | 204 No Content. |
| List academy configs | GET | `/v1/provisioning/academy/provisioningacademy` | `Authorization`, `Academy: <academy_id>` | — | List of configs (id, vendor, academy_id, credentials_set, connection_status, connection_status_text, connection_test_at, container_idle_timeout, max_active_containers; no credentials). |
| Create academy config | POST | `/v1/provisioning/academy/provisioningacademy` | `Authorization`, `Academy: <academy_id>` | See request sample below. | 201, config object (credentials not echoed; see response sample). |
| Get academy config | GET | `/v1/provisioning/academy/provisioningacademy/<provisioning_academy_id>` | `Authorization`, `Academy: <academy_id>` | — | Config object (credentials_set, connection_status, connection_status_text, connection_test_at; no raw credentials). |
| Update academy config | PUT | `/v1/provisioning/academy/provisioningacademy/<provisioning_academy_id>` | `Authorization`, `Academy: <academy_id>` | All optional; omit credentials to leave unchanged. | Config object. |
| Delete academy config | DELETE | `/v1/provisioning/academy/provisioningacademy/<provisioning_academy_id>` | `Authorization`, `Academy: <academy_id>` | — | 204 No Content. |
| Test academy vendor connection | POST | `/v1/provisioning/academy/provisioningacademy/<provisioning_academy_id>/test-connection` | `Authorization`, `Academy: <academy_id>` | — | Runs vendor check and returns updated config with `connection_status`, `connection_status_text`, `connection_test_at`. |

**Create profile — request (POST `/v1/provisioning/academy/provisioningprofile`):**
```json
{
  "vendor_id": 1,
  "cohort_ids": [5, 6],
  "member_ids": [101, 102]
}
```

**Create profile — response (201):**
```json
{
  "id": 42,
  "vendor": {"id": 1, "name": "Codespaces"},
  "academy": {"id": 1, "name": "Academy 1"},
  "cohort_ids": [5, 6],
  "member_ids": [101, 102]
}
```

**Create academy config — request (POST `/v1/provisioning/academy/provisioningacademy`):**
```json
{
  "vendor_id": 1,
  "credentials_token": "secret-token-value",
  "credentials_key": null,
  "container_idle_timeout": 15,
  "max_active_containers": 2,
  "allowed_machine_type_ids": [1, 2]
}
```

**Create academy config — response (201):**
```json
{
  "id": 10,
  "vendor": {"id": 1, "name": "Codespaces"},
  "academy_id": 1,
  "credentials_set": true,
  "vendor_settings": {},
  "connection_status": "UNTESTED",
  "connection_status_text": "",
  "connection_test_at": null,
  "container_idle_timeout": 15,
  "max_active_containers": 2,
  "created_at": "2025-01-01T12:00:00Z",
  "updated_at": "2025-01-01T12:00:00Z"
}
```

**List vendors — response (GET `/v1/provisioning/academy/vendor`):**
```json
[
  {"id": 1, "name": "Codespaces", "workspaces_url": "https://github.com/codespaces", "settings_schema": {"fields": []}},
  {"id": 2, "name": "Gitpod", "workspaces_url": "https://gitpod.io/workspaces", "settings_schema": {"fields": []}}
]
```

Capabilities: `read_provisioning_activity` for GET; `crud_provisioning_activity` for POST, PUT, DELETE.

## Edge Cases

- **vendor-not-found (404):** vendor_id does not exist. Tell the user to use a valid vendor id; do not retry the same id.
- **provisioning-profile-not-found (404):** profile_id or academy does not match. Verify profile_id and that the Academy header matches the profile's academy.
- **provisioning-academy-already-exists (400):** POST academy config for (academy, vendor) when one already exists. Tell the user to use PUT to update the existing config instead.
- **provisioning-academy-not-found (404):** provisioning_academy_id does not exist or does not belong to the academy. Verify id and Academy header. Applies to GET, PUT, and DELETE.
- **Connection test behavior:** `POST .../test-connection` always returns the config payload on success (200), but it may set `connection_status=ERROR` with details in `connection_status_text` if the vendor API call fails or token is missing.
- **Connection test dispatch:** The endpoint routes checks by `vendor_type`: `VPS_SERVER` (VPS client protocol), `CODING_EDITOR` (coding editor client protocol), `LLM` (LLM client protocol).
- **Deleting academy config** does not delete the provisioning profile; to stop using a vendor entirely, delete the profile (and optionally the config).
- **Invalid cohort_ids or member_ids:** IDs must belong to the academy. If the API returns validation errors, tell the user to use cohort/member ids for that academy only.

## Checklist

1. To get valid vendor ids for profiles/configs: call `GET /v1/provisioning/academy/vendor` with `Authorization` and `Academy` header.
2. To list or create profiles: call `GET` or `POST /v1/provisioning/academy/provisioningprofile` with `Authorization` and `Academy` header.
3. To update or delete a profile: call `PUT` or `DELETE /v1/provisioning/academy/provisioningprofile/<profile_id>` with `Academy` header.
4. To list or create academy configs: call `GET` or `POST /v1/provisioning/academy/provisioningacademy` with `Academy` header; for POST send vendor_id and credentials_token.
5. To update academy config: call `PUT /v1/provisioning/academy/provisioningacademy/<id>` with optional body; omit credentials to leave unchanged.
6. To delete academy config: call `DELETE /v1/provisioning/academy/provisioningacademy/<id>` with `Academy` header; returns 204.
7. To refresh connection health fields, call `POST /v1/provisioning/academy/provisioningacademy/<id>/test-connection`.
8. For VPS to work, ensure the academy has at least one profile and one academy config (same vendor) with credentials_token set.
