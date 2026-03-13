---
name: Provisioning settings and credentials API and skill
overview: Add API endpoints so academy staff can create/update provisioning profiles and academy credentials+settings via the API (academy from Academy header, no academy_id in URLs). Then add the skill bc-provisioning-settings-and-credentials and update the index.
todos:
  - id: profile-crud-backend
    content: Add POST/PUT/DELETE for provisioning profiles; use academy/provisioningprofile and academy/provisioningprofile/<profile_id> (academy from header)
    status: pending
  - id: profile-urls
    content: Add URL routes for academy/provisioningprofile and academy/provisioningprofile/<profile_id>; optionally migrate existing academy/<academy_id>/provisioningprofile to academy/provisioningprofile
    status: pending
    dependencies:
      - profile-crud-backend
  - id: provisioning-academy-backend
    content: Add ProvisioningAcademyView (GET list, POST create) and by-id (GET/PUT); mask credentials in response; use academy/provisioningacademy
    status: pending
  - id: provisioning-academy-urls
    content: Register academy/provisioningacademy and academy/provisioningacademy/<id> in urls.py
    status: pending
    dependencies:
      - provisioning-academy-backend
  - id: tests
    content: Add tests for new profile and provisioning academy endpoints
    status: pending
    dependencies:
      - profile-urls
      - provisioning-academy-urls
  - id: skill-doc
    content: Create bc-provisioning-settings-and-credentials skill (When to Use, Concepts, Workflow, Endpoints, Edge Cases, Checklist); API-only, no Admin
    status: pending
    dependencies:
      - tests
  - id: index-and-cross-skill
    content: Update breathecode-api-index if cross-domain workflow; update bc-provisioning-manage-vps-server to reference new skill for configuring credentials
    status: pending
    dependencies:
      - skill-doc
isProject: false
---

# Provisioning settings and credentials: API + skill

## Current state

- **ProvisioningProfile** ([breathecode/provisioning/models.py](breathecode/provisioning/models.py)): links an academy to a vendor; optional `cohorts` and `members` M2M. Only **GET** is exposed at `academy/<int:academy_id>/provisioningprofile` (inconsistent with other academy endpoints that use **Academy header** and no academy_id in URL).
- **ProvisioningAcademy** (same models): per (academy, vendor) config: `credentials_key`, `credentials_token`, `container_idle_timeout`, `max_active_containers`, `allowed_machine_types`. Not exposed by any view. VPS request fails with `academy-vps-not-configured` if no profile + ProvisioningAcademy with credentials exists.

**Academy scope:** The `@capable_of` decorator injects `academy_id` from the **Academy** header (see [capable_of.py](breathecode/utils/decorators/capable_of.py)). Other provisioning academy endpoints use paths like `academy/bill`, `academy/vps` with no academy_id in the URL. New endpoints must follow the same pattern: **no academy_id in URLs**; academy comes from the header and view params.

---

## 1. API design (no academy_id in URLs)

### 1.1 Provisioning profiles


| Method | Path                                                        | Purpose                                                                    |
| ------ | ----------------------------------------------------------- | -------------------------------------------------------------------------- |
| GET    | `/v1/provisioning/academy/provisioningprofile`              | List profiles for the academy (academy from Academy header).               |
| POST   | `/v1/provisioning/academy/provisioningprofile`              | Create profile: body `vendor_id`, optional `cohort_ids[]`, `member_ids[]`. |
| GET    | `/v1/provisioning/academy/provisioningprofile/<profile_id>` | Get one profile.                                                           |
| PUT    | `/v1/provisioning/academy/provisioningprofile/<profile_id>` | Update profile.                                                            |
| DELETE | `/v1/provisioning/academy/provisioningprofile/<profile_id>` | Delete profile.                                                            |


- **Capability:** `crud_provisioning_activity` for POST/PUT/DELETE; `read_provisioning_activity` for GET. Views receive `academy_id` from `@capable_of`, not from the URL.
- **Validation:** `vendor_id` must exist; cohort/member IDs must belong to the academy (academy_id from decorator).

**Existing route:** Currently `academy/<int:academy_id>/provisioningprofile` exists. Either (a) add new routes `academy/provisioningprofile` and `academy/provisioningprofile/<profile_id>` and keep the old one for backward compatibility, or (b) replace with `academy/provisioningprofile` and document the path change.

### 1.2 Academy credentials and settings (ProvisioningAcademy)


| Method | Path                                                                     | Purpose                                                                                                                                                                |
| ------ | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GET    | `/v1/provisioning/academy/provisioningacademy`                           | List ProvisioningAcademy for this academy (vendor, settings; credentials masked or omitted).                                                                           |
| POST   | `/v1/provisioning/academy/provisioningacademy`                           | Create: body `vendor_id`, `credentials_token` (required), optional `credentials_key`, `container_idle_timeout`, `max_active_containers`, `allowed_machine_type_ids[]`. |
| GET    | `/v1/provisioning/academy/provisioningacademy/<provisioning_academy_id>` | Get one.                                                                                                                                                               |
| PUT    | `/v1/provisioning/academy/provisioningacademy/<provisioning_academy_id>` | Update (partial; omit credentials to leave unchanged).                                                                                                                 |


- **Capability:** `crud_provisioning_activity` for write; `read_provisioning_activity` for GET. Academy from header only.
- **Validation:** Unique (academy, vendor); vendor exists. Response must not return raw `credentials_token`/`credentials_key` (mask or `credentials_set: true`).

---

## 2. Implementation steps

### 2.1 Backend: Profiles

- **Views:** In [breathecode/provisioning/views.py](breathecode/provisioning/views.py): add `post` to ProvisioningProfileView for create (use `academy_id` from decorator). Add a by-id view or same view with `profile_id` for GET one, PUT, DELETE. Use `@capable_of("read_provisioning_activity")` for GET and `@capable_of("crud_provisioning_activity")` for write.
- **URLs:** In [breathecode/provisioning/urls.py](breathecode/provisioning/urls.py): use `path("academy/provisioningprofile", ...)` and `path("academy/provisioningprofile/<int:profile_id>", ...)`. Decide whether to keep or remove `academy/<int:academy_id>/provisioningprofile`.
- **Serializers:** Request body (vendor_id, cohort_ids, member_ids); reuse or extend [GetProvisioningProfile](breathecode/provisioning/serializers.py) for responses. Filter all queries by `academy_id` from view kwargs.

### 2.2 Backend: ProvisioningAcademy

- **Views:** New `ProvisioningAcademyView` (GET list, POST create) and `ProvisioningAcademyByIdView` (GET, PUT). Both use `academy_id=None` and rely on `@capable_of` to inject `academy_id`. Validate that ProvisioningAcademy belongs to that academy.
- **URLs:** `path("academy/provisioningacademy", ...)` and `path("academy/provisioningacademy/<int:provisioning_academy_id>", ...)`.
- **Serializers:** Request: vendor_id, credentials_token, optional credentials_key, container_idle_timeout, max_active_containers, allowed_machine_type_ids. Response: exclude or mask credentials.

### 2.3 Skill: bc-provisioning-settings-and-credentials

- **Path:** [docs/llm-docs/skills/bc-provisioning-settings-and-credentials/SKILL.md](docs/llm-docs/skills/bc-provisioning-settings-and-credentials/SKILL.md).
- **Structure:** Per [skill-authoring.mdc](.cursor/rules/skill-authoring.mdc): frontmatter, When to Use, Concepts, Workflow, Endpoints, Edge Cases, Checklist. API-only; no Django Admin.
- **Content:** Document creating/updating profiles and academy credentials+settings. Paths must use `academy/provisioningprofile` and `academy/provisioningacademy` (no academy_id in path); state that the **Academy** header is required. For VPS to work, academy must have at least one profile and a corresponding ProvisioningAcademy with credentials_token set.

### 2.4 Index and cross-skill

- **Index:** [docs/llm-docs/skills/breathecode-api-index/SKILL.md](docs/llm-docs/skills/breathecode-api-index/SKILL.md): provisioning domain already has `bc-provisioning-`*. Add cross-domain row if needed (e.g. "Configure academy VPS provisioning" → load bc-provisioning-settings-and-credentials).
- **bc-provisioning-manage-vps-server:** Update "When to Use" / Concepts so that configuring credentials or profiles directs to bc-provisioning-settings-and-credentials. Update Endpoints table to use `academy/provisioningprofile` (no academy_id in path) if the API is migrated.

---

## 3. Security and consistency

- **Credentials:** Never return raw credentials in GET; at most indicate that credentials are set.
- **Scoping:** All endpoints filter by `academy_id` from view kwargs (injected by `@capable_of` from Academy header). No academy_id in URL paths.

