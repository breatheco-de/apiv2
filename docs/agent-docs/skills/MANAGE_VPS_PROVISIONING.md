# Skill: Manage VPS Provisioning using the API

This document describes how an academy can configure and use **VPS provisioning** in the BreatheCode API. Students receive a dedicated VPS (e.g. via Hostinger) for development; the academy configures credentials, and students request VPSs via the API. Use this skill when the user asks about VPS provisioning, Hostinger setup, provisioning credentials, listing provisioned VPSs, or deprovisioning.

---

## Concepts

- **ProvisioningVendor**: A vendor that provides VPS (e.g. Hostinger). Registered by name/slug; the Hostinger client is registered under the slug `"hostinger"`.
- **ProvisioningProfile**: Links an **academy** to a **vendor**. Optional: restrict by cohorts or members. Used to decide which vendor a student uses. **Read-only via API**; create/update in Django Admin.
- **ProvisioningAcademy**: Per-academy, per-vendor configuration. Stores **credentials** (e.g. Hostinger API token) and optional settings. **Configured only in Django Admin** (no public API to set credentials).
- **ProvisioningVPS**: One VPS instance per student per academy. States: `PENDING`, `PROVISIONING`, `ACTIVE`, `ERROR`, `DELETED`. At most one **active** (or pending/provisioning) VPS per user per academy.
- **VPS credits**: Students must have **consumables** for the service `vps_server` with `how_many > 0`. One VPS request consumes one unit. Credits are granted via plans/subscriptions or manually (payments/consumables).

---

## Base URL

All provisioning endpoints live under:

- **Base path:** `/v1/provisioning/`

Use `Authorization` (e.g. Bearer token) for authenticated endpoints. Academy-scoped endpoints require the **Academy** header with the academy ID.

---

## 1. Configuring Hostinger (and vendor) credentials

Credentials are **not** configurable via the public API. The academy must use **Django Admin** to set them.

### Step 1: Ensure the vendor exists

- In Django Admin, open **Provisioning** → **Provisioning vendors**.
- There must be a vendor used for VPS (e.g. name **Hostinger**; the code matches by **name** in a case-insensitive way for the client registry, and the Hostinger client is registered under the slug `"hostinger"`). Create one if missing.

### Step 2: Link academy to vendor (ProvisioningProfile)

- **Provisioning** → **Provisioning profiles**.
- Create (or edit) a profile: set **Academy** and **Vendor** (e.g. Hostinger).
- Optionally set **Cohorts** or **Members** to restrict which students use this vendor; leave both empty to apply to the whole academy.

Profiles can be **read** via API (see [Provisioning profile API](#4-provisioning-profile-api)).

### Step 3: Set credentials (ProvisioningAcademy)

- **Provisioning** → **Provisioning academies**.
- Create (or edit) a row with the correct **Academy** and **Vendor** (same vendor as in the profile).

**Hostinger:**

- **Credentials token** (required): Hostinger API **access token**. The Hostinger client uses this to call Hostinger’s API (create VPS, cancel subscription).
- **Credentials key** (optional): Not used by the Hostinger client; can be left blank or used for other vendors/future use.

The Hostinger client also accepts optional `item_id`, `template_id`, and `data_center_id` in the credentials dict. The **ProvisioningAcademy** model only has `credentials_key` and `credentials_token`. If you need to force a specific plan/template/datacenter, that would require extending the model or storing a JSON blob; by default the client fetches defaults from the Hostinger API (first VPS catalog item, first template, first data center) when those are not provided.

**Summary for Hostinger:**

1. Create a **ProvisioningVendor** with name **Hostinger** (or ensure it exists).
2. Create a **ProvisioningProfile** linking your academy to that vendor (optionally restrict by cohorts/members).
3. Create a **ProvisioningAcademy** for that academy + vendor and set **Credentials token** to your Hostinger API access token.

---

## 2. Giving students VPS credits (vps_server consumables)

A student can request a VPS only if they have at least one **consumable** for the service **`vps_server`** with `how_many > 0`. Each request consumes **1** unit.

- Credits are usually granted via **plans** and **subscriptions** (payments app): the plan or subscription includes a **Service** whose slug is **`vps_server`**, and students get consumables from that.
- Alternatively, staff can create or adjust consumables in Django Admin (payments/consumables) or via internal APIs that create consumables for the `vps_server` service.

The API does **not** expose an endpoint to “grant VPS credits” directly; that is done through the payments/plan/subscription flow or admin.

---

## 3. Student: request and manage my VPS

### List my VPSs

**Endpoint:** `GET /v1/provisioning/me/vps`  
**Auth:** Required (current user).

Returns all `ProvisioningVPS` for the current user (all academies). Pagination supported. Response fields include: `id`, `status`, `hostname`, `ip_address`, `ssh_user`, `ssh_port`, `plan_slug`, `error_message`, `requested_at`, `provisioned_at`, `deleted_at`, `created_at`, `updated_at`. **Root password is not included** in the list.

### Request a new VPS

**Endpoint:** `POST /v1/provisioning/me/vps`  
**Auth:** Required.  
**Body (optional):** `{ "plan_slug": "optional-plan-slug" }`

- The backend resolves the user’s academy (from active cohort or profile) and a VPS-capable **ProvisioningProfile** + **ProvisioningAcademy** with credentials.
- If the user already has an active/pending/provisioning VPS for that academy, the API returns an error (duplicate).
- If the user has no `vps_server` consumable with `how_many > 0`, the API returns an error (insufficient credits).
- On success: consumes **1** `vps_server` consumable, creates a **ProvisioningVPS** in `PENDING`, enqueues a background task to provision the VPS (e.g. call Hostinger). Response is **202 Accepted** with the VPS object (e.g. `id`, `status: "PENDING"`). The VPS later moves to `PROVISIONING` then `ACTIVE` (or `ERROR` on failure).

### Get one VPS (with root password)

**Endpoint:** `GET /v1/provisioning/me/vps/<vps_id>`  
**Auth:** Required. Only the **owner** (current user) can access.

Returns the VPS detail; for the **owner**, the response includes **`root_password`** (decrypted). For others the endpoint returns 404.

### Common student errors

- **no-academy-for-vps**: User has no academy (no active cohort, no profile academy).
- **academy-vps-not-configured**: No ProvisioningProfile with a VPS-capable vendor and a ProvisioningAcademy with credentials for that academy.
- **duplicate-vps**: User already has an active or pending VPS for that academy.
- **insufficient-vps-server-credits**: No consumable for service `vps_server` with balance > 0.
- **vps-not-found**: VPS does not exist or does not belong to the current user (GET by id).

---

## 4. Academy: list, request for student, and deprovision VPSs

Academy endpoints require the **Academy** header (academy ID) and a user with the capability **`crud_provisioning_activity`**.

### List all VPSs for the academy

**Endpoint:** `GET /v1/provisioning/academy/vps`  
**Headers:** `Authorization`, `Academy: <academy_id>`  
**Query (optional):** `user_id=<user_id>` – filter by student.

Returns all `ProvisioningVPS` for that academy (with optional filter by user). Each item includes user info (`user_id`, `user_email`) and VPS fields; **no root password**.

### Request a VPS for a student (staff)

**Endpoint:** `POST /v1/provisioning/academy/vps`  
**Headers:** `Authorization`, `Academy: <academy_id>`  
**Body:** `{ "user_id": <student_user_id>, "plan_slug": "optional-plan-slug" }` (`plan_slug` optional).

- Provisioning uses the **academy from the header** (vendor/credentials for that academy).
- The target user must be an **active member** of that academy: active `ProfileAcademy` for the academy, or an active `CohortUser` in a cohort belonging to that academy.
- **One unit** of the **student’s** `vps_server` consumable is consumed (not the staff member’s).
- Same rules as student self-service for duplicates (at most one active/pending/provisioning VPS per student per academy), insufficient credits, and academy VPS configuration.
- Response: **202 Accepted** with the VPS object (same shape as `POST /me/vps` list serializer; **no** `root_password`). The student is emailed connection details when provisioning completes.

### Deprovision a student’s VPS

**Endpoint:** `DELETE /v1/provisioning/academy/vps/<vps_id>`  
**Headers:** `Authorization`, `Academy: <academy_id>`

- Ensures the VPS belongs to the given academy; otherwise 404.
- Enqueues a task to destroy the VPS at the vendor (e.g. Hostinger cancel subscription) and sets the VPS status to **DELETED**.
- Response: **204 No Content**.

---

## 5. Provisioning profile (read-only) API

**Endpoint:** `GET /v1/provisioning/academy/<academy_id>/provisioningprofile`  
**Auth:** Required.  
**Headers:** `Academy: <academy_id>` (for academy-scoped auth if applicable).

Returns the list of **ProvisioningProfile** for that academy (vendor, academy, optional cohorts/members). There is **no POST/PUT** for profiles or credentials in the public API; use Django Admin to create/update profiles and set **ProvisioningAcademy** credentials.

---

## 6. VPS lifecycle and renewal

- **Request (student):** Student calls `POST /v1/provisioning/me/vps`. One `vps_server` consumable is consumed; a **ProvisioningVPS** is created and a **provision_vps_task** is enqueued.
- **Request (staff):** Staff with `crud_provisioning_activity` calls `POST /v1/provisioning/academy/vps` with `Academy` header and `user_id` of the student. The **student’s** consumable is consumed; otherwise the same flow as self-service.
- **Provisioning:** The task uses the academy’s **ProvisioningAcademy** credentials and the vendor’s VPS client (e.g. Hostinger). On success, the VPS is set to **ACTIVE** and connection details (hostname, IP, SSH user/port, root password) are stored; the student is emailed (e.g. template **vps_connection_details**). On failure, status is set to **ERROR**, the consumable is reimbursed, and `error_message` is set.
- **Renewal:** A **monthly** task (**monthly_vps_renewal_dispatcher**) runs (e.g. via Celery beat). For each **ACTIVE** VPS it runs **renew_or_deprovision_vps_task**: if the user has at least one `vps_server` consumable with balance > 0, it consumes 1 and keeps the VPS; otherwise it **deprovisions** the VPS (vendor destroy + set status to **DELETED**) and can send a **vps_deprovisioned** email.
- **Manual deprovision:** Academy staff call `DELETE /v1/provisioning/academy/vps/<vps_id>` to deprovision a student’s VPS.

---

## 7. Summary checklist for academies

1. **Vendor:** Create or use a **ProvisioningVendor** (e.g. Hostinger) in Admin.
2. **Profile:** Create a **ProvisioningProfile** linking the academy to that vendor (optionally restrict by cohorts/members).
3. **Credentials:** Create a **ProvisioningAcademy** for that academy + vendor and set **Credentials token** to the Hostinger API access token (for Hostinger).
4. **Credits:** Ensure students receive **vps_server** consumables (via plans/subscriptions or admin).
5. **Students:** Use **GET/POST /v1/provisioning/me/vps** and **GET /v1/provisioning/me/vps/<id>** to list, request, and view (with password) their VPS.
6. **Staff:** Use **GET /v1/provisioning/academy/vps** to list VPSs, **POST /v1/provisioning/academy/vps** to request a VPS for a student (consumes the student’s credit), and **DELETE /v1/provisioning/academy/vps/<id>** to deprovision (all with `Academy` header and `crud_provisioning_activity`).

All credential and profile creation/updates are done in **Django Admin**; the API is used to list profiles, request/list/view VPSs, and (academy) list/request-for-student/deprovision VPSs.
