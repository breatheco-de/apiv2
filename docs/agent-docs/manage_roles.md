# Manage Academy Roles

This document describes the API endpoints and payloads for academies to manage their own custom roles. Only users with the **manage_academy_roles** capability (system admin or academy admin / country manager) can use these endpoints.

**Native roles** (e.g. `staff`, `teacher`, `country_manager`) are defined by the platform and cannot be created, updated, or deleted by academies. Academies can only **create, update, and delete custom roles** and assign capabilities from the global capability list to them.

---

## Base URL and authentication

- **Base path:** `/v1/auth/academy/<academy_id>/...`
- **Authentication:** All requests require a valid token in the `Authorization` header:
  ```http
  Authorization: Token <your-token>
  ```
- **Academy context:** Pass the academy id in the URL. The authenticated user must have the **manage_academy_roles** capability for that academy (admin or academy admin role).

---

## 1. List capabilities

Returns all capabilities available in the system. Use this to build the role form (e.g. checkboxes for capabilities when creating or editing a custom role).

**Endpoint:** `GET /v1/auth/academy/<academy_id>/capability`

**Response:** `200 OK`

```json
[
  { "slug": "read_member", "description": "Read academy staff member information" },
  { "slug": "crud_member", "description": "Create, update or delete academy members..." },
  { "slug": "read_student", "description": "Read student information" }
]
```

- **slug:** Unique capability identifier (use these when assigning capabilities to a role).
- **description:** Human-readable description of the capability.

---

## 2. List roles for an academy

Returns all roles available for the academy: **native roles** (platform-managed, read-only) and **custom roles** (academy-owned, editable).

**Endpoint:** `GET /v1/auth/academy/<academy_id>/role`

**Response:** `200 OK`

```json
[
  {
    "id": "staff",
    "slug": "staff",
    "display_slug": "staff",
    "name": "Staff (Base)",
    "capabilities": ["read_member", "read_syllabus", "..."],
    "native": true
  },
  {
    "id": "content_editor_42",
    "slug": "content_editor_42",
    "display_slug": "content_editor",
    "name": "Content Editor",
    "capabilities": ["read_asset", "crud_asset", "read_media"],
    "native": false
  }
]
```

- **id:** Same as `slug` (for compatibility).
- **slug:** Stored slug (for custom roles this is `{base_slug}_{academy_id}`; use this in URLs and when assigning the role to a member).
- **display_slug:** Slug without the academy id suffix; use this for UI labels.
- **name:** Display name of the role.
- **capabilities:** List of capability slugs assigned to the role.
- **native:** `true` = platform role (read-only); `false` = academy custom role (can be updated/deleted by the academy).

---

## 3. Get one role

Returns a single role by its **stored slug** (e.g. `staff` for native, `content_editor_42` for a custom role of academy 42).

**Endpoint:** `GET /v1/auth/academy/<academy_id>/role/<role_slug>`

**Path parameters:**
- **role_slug:** The full slug (e.g. `content_editor_42` for a custom role). Must be a role that belongs to this academy or a native role.

**Response:** `200 OK`

```json
{
  "id": "content_editor_42",
  "slug": "content_editor_42",
  "display_slug": "content_editor",
  "name": "Content Editor",
  "capabilities": ["read_asset", "crud_asset", "read_media"],
  "native": false
}
```

**Errors:**
- `404` – Academy not found or role with that slug not found for this academy.

---

## 4. Create custom role

Creates a new **custom role** for the academy. The stored slug is built as `{slug}_{academy_id}` so it is globally unique.

**Endpoint:** `POST /v1/auth/academy/<academy_id>/role`

**Request body:**

```json
{
  "name": "Content Editor",
  "slug": "content_editor",
  "capabilities": ["read_asset", "crud_asset", "read_media", "read_tag"]
}
```

| Field         | Type     | Required | Description |
|---------------|----------|----------|-------------|
| name          | string   | Yes      | Display name of the role (non-empty). |
| slug          | string   | Yes      | Base slug: lowercase letters, numbers, underscores only. Must not match a native role slug (e.g. `staff`, `teacher`). |
| capabilities  | string[] | No       | List of capability slugs to assign. Default: `[]`. |

**Response:** `201 Created`

```json
{
  "id": "content_editor_42",
  "slug": "content_editor_42",
  "display_slug": "content_editor",
  "name": "Content Editor",
  "capabilities": ["read_asset", "crud_asset", "read_media", "read_tag"],
  "native": false
}
```

**Validation / errors:**
- `400` – **invalid-name:** name missing or empty.
- `400` – **invalid-slug:** slug missing or empty.
- `400` – **invalid-slug-format:** slug must contain only `a-z`, `0-9`, `_`.
- `400` – **slug-reserved:** slug matches a native role (e.g. `staff`, `teacher`).
- `400` – **role-already-exists:** a custom role with that base slug already exists for this academy.
- `400` – **invalid-capabilities:** one or more capability slugs are not valid (must exist in the system).
- `404` – Academy not found.

---

## 5. Update custom role

Updates the **name** and/or **capabilities** of a custom role. Only custom roles (`native: false`) can be updated; native roles return `400`.

**Endpoint:** `PUT /v1/auth/academy/<academy_id>/role/<role_slug>`

**Path parameters:**
- **role_slug:** The **stored** slug of the role (e.g. `content_editor_42`).

**Request body:** All fields are optional; send only what you want to change.

```json
{
  "name": "Senior Content Editor",
  "capabilities": ["read_asset", "crud_asset", "read_media", "crud_media", "read_tag", "crud_tag"]
}
```

| Field        | Type     | Required | Description |
|--------------|----------|----------|-------------|
| name         | string   | No       | New display name (non-empty if provided). |
| capabilities | string[] | No       | New list of capability slugs (replaces existing). |

**Response:** `200 OK`

```json
{
  "id": "content_editor_42",
  "slug": "content_editor_42",
  "display_slug": "content_editor",
  "name": "Senior Content Editor",
  "capabilities": ["read_asset", "crud_asset", "read_media", "crud_media", "read_tag", "crud_tag"],
  "native": false
}
```

**Errors:**
- `400` – **native-role-read-only:** the role is a native role and cannot be updated.
- `400` – **invalid-name:** name provided but empty.
- `400` – **invalid-capabilities:** one or more capability slugs are not valid.
- `404` – Academy or role not found.

---

## 6. Delete custom role

Deletes a **custom role**. Only custom roles can be deleted. The role must not be assigned to any member or used in any invite.

**Endpoint:** `DELETE /v1/auth/academy/<academy_id>/role/<role_slug>`

**Path parameters:**
- **role_slug:** The **stored** slug of the role (e.g. `content_editor_42`).

**Response:** `204 No Content` (empty body).

**Errors:**
- `400` – **native-role-read-only:** the role is a native role and cannot be deleted.
- `400` – **role-in-use:** the role is assigned to one or more members or is used in one or more invites. Reassign or remove those usages first.
- `404` – Academy or role not found.

---

## Assigning a role to a member

To assign a role (native or custom) to a member, use the member endpoints (e.g. `POST /v1/auth/academy/<academy_id>/member` or `PUT .../member/<user_id_or_email>`) with a **role** field. The value must be either:

- The **stored slug** of a native role (e.g. `staff`, `teacher`), or  
- The **stored slug** of a custom role for this academy (e.g. `content_editor_42`).

Only roles that are native or belong to the same academy are accepted; otherwise the API returns `400` with slug **role-not-available-for-academy**.

---

## Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET    | `/v1/auth/academy/<academy_id>/capability` | List all capabilities for building role forms |
| GET    | `/v1/auth/academy/<academy_id>/role` | List native + custom roles for the academy |
| GET    | `/v1/auth/academy/<academy_id>/role/<role_slug>` | Get one role by stored slug |
| POST   | `/v1/auth/academy/<academy_id>/role` | Create a custom role |
| PUT    | `/v1/auth/academy/<academy_id>/role/<role_slug>` | Update a custom role (name, capabilities) |
| DELETE | `/v1/auth/academy/<academy_id>/role/<role_slug>` | Delete a custom role (only if not in use) |

All of these endpoints require the **manage_academy_roles** capability (admin or academy admin).
