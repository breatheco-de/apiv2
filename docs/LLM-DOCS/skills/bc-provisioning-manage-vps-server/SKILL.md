---
name: bc-provisioning-manage-vps-server
description: Use when a user, student or academy staff needs to request, list, view, or deprovision a VPS via the API; do NOT use for granting VPS credits via plans or payments.
requires: []
---

# Skill: Manage VPS Provisioning via the API

## When to Use

Use this skill when the user asks to **request a VPS**, **list my VPSs**, **get VPS connection details** (including root password), **list academy VPSs**, or **deprovision a student's VPS** — all via the API. Do **not** use when the user only asks how to configure vendor credentials or create/update provisioning profiles — use bc-provisioning-settings-and-credentials for that. Do **not** use for granting VPS credits through plans or subscriptions.

## Concepts

- **VPS**: One virtual server instance per student per academy. States: `PENDING`, `PROVISIONING`, `ACTIVE`, `ERROR`, `DELETED`. At most one active (or pending/provisioning) VPS per user per academy.
- **VPS credits**: A student can request a VPS only if they have at least one consumable for the service `vps_server` with balance greater than zero. One request consumes one unit. The API does not grant credits; they are managed via plans/subscriptions or other APIs.
- **Provisioning setup**: The academy must have a vendor and a profile linking the academy to that vendor, with credentials stored. Use bc-provisioning-settings-and-credentials to create or update profiles and set credentials via the API.

## Workflow

1. **Student: list my VPSs.** Call `GET /v1/provisioning/me/vps`. The response lists all VPSs for the current user (all academies). Use the returned `id` to fetch details or to reference a VPS for deprovisioning.

2. **Student: request a new VPS.** Call `POST /v1/provisioning/me/vps`. Optional body: `{ "plan_slug": "optional-plan-slug" }`. The user must have an academy (e.g. from active cohort) and at least one `vps_server` consumable with balance > 0. If the user already has an active or pending VPS for that academy, the API returns an error. On success the response is 202 Accepted with the VPS object (e.g. `id`, `status: "PENDING"`); the VPS later moves to ACTIVE or ERROR.

3. **Student: get one VPS (including root password).** Call `GET /v1/provisioning/me/vps/<vps_id>`. Only the owner gets `root_password` in the response. Use the `id` from Step 1 or 2.

4. **Academy: list all VPSs.** Call `GET /v1/provisioning/academy/vps` with headers `Authorization` and `Academy: <academy_id>`. The requesting user must have the capability `crud_provisioning_activity`. Optional query: `user_id=<user_id>` to filter by student. Response does not include root password.

5. **Academy: deprovision a VPS.** Call `DELETE /v1/provisioning/academy/vps/<vps_id>` with headers `Authorization` and `Academy: <academy_id>`. The VPS must belong to that academy. Response is 204 No Content; the VPS is destroyed at the vendor and marked DELETED.

**Prerequisite:** Vendor, academy profile, and credentials must already be configured. If the user has no academy or the academy has no VPS configuration, the API returns errors; tell the user setup must be completed first. VPS credits are managed via plans/subscriptions or other APIs, not this one.

## Endpoints

| Action | Method | Path | Headers | Body / Query | Response |
|--------|--------|------|---------|--------------|----------|
| List my VPSs | GET | `/v1/provisioning/me/vps` | `Authorization` | — | List of VPSs; see response sample. |
| Request a VPS | POST | `/v1/provisioning/me/vps` | `Authorization` | Optional; see request sample. | 202 Accepted, VPS object; see response sample. |
| Get one VPS (with password) | GET | `/v1/provisioning/me/vps/<vps_id>` | `Authorization` | — | VPS detail including `root_password` for owner; see response sample. |
| List academy VPSs | GET | `/v1/provisioning/academy/vps` | `Authorization`, `Academy: <academy_id>` | Optional: `?user_id=<user_id>` | List of VPSs for academy (no root_password). |
| Deprovision VPS | DELETE | `/v1/provisioning/academy/vps/<vps_id>` | `Authorization`, `Academy: <academy_id>` | — | 204 No Content. |
| List provisioning profiles | GET | `/v1/provisioning/academy/provisioningprofile` | `Authorization`, `Academy: <academy_id>` | — | List of profiles (vendor, academy, cohort_ids, member_ids). |

**Request a VPS — request (POST `/v1/provisioning/me/vps`):**
```json
{
  "plan_slug": "default"
}
```
Body is optional; omit or send empty object to use default.

**Request a VPS — response (202 Accepted):**
```json
{
  "id": 100,
  "status": "PENDING",
  "hostname": null,
  "ip_address": null,
  "ssh_user": null,
  "ssh_port": null,
  "academy": {"id": 1, "name": "Academy 1"},
  "user": 50
}
```
Later the VPS may move to `ACTIVE` or `ERROR`; use GET to fetch updated details and `root_password` when ACTIVE.

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
  "academy": {"id": 1, "name": "Academy 1"},
  "user": 50
}
```

Base path for all: `/v1/provisioning/`. Academy endpoints require capability `crud_provisioning_activity`.

## Edge Cases

- **no-academy-for-vps:** User has no academy (no active cohort or profile). Tell the user they must belong to an academy (e.g. be in a cohort) to request a VPS; do not retry the same request.
- **academy-vps-not-configured:** No provisioning profile with credentials exists for the user's academy. Tell the user the academy must configure a vendor and credentials first.
- **duplicate-vps:** User already has an active or pending VPS for that academy. Tell the user they can have only one active or pending VPS per academy; they must deprovision or wait before requesting another.
- **insufficient-vps-server-credits:** User has no `vps_server` consumable with balance > 0. Tell the user they need VPS credits (via plan/subscription or other API); this API does not grant credits.
- **vps-not-found (404):** GET or DELETE by id returns 404. Tell the user the VPS does not exist or does not belong to them (student) or to the academy (staff); verify the id and academy.

## Checklist

1. For listing or requesting a VPS as a student: call `GET /v1/provisioning/me/vps` or `POST /v1/provisioning/me/vps` with `Authorization`.
2. For VPS connection details (including root password): call `GET /v1/provisioning/me/vps/<vps_id>` as the owning user.
3. For academy list: call `GET /v1/provisioning/academy/vps` with `Authorization` and `Academy: <academy_id>` (user must have `crud_provisioning_activity`).
4. For deprovisioning: call `DELETE /v1/provisioning/academy/vps/<vps_id>` with `Authorization` and `Academy: <academy_id>`.
5. If the API returns no-academy, not-configured, duplicate-vps, or insufficient-credits: explain the cause and what the user must do (complete setup or obtain credits via the appropriate API), and do not retry the same request.
