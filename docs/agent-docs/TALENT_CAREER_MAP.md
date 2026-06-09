# Talent Career Map API

This document describes every endpoint implemented in
`breathecode/talent_development/views.py`.  All routes live under the
`/v1/talent_development/` namespace and are protected with Capy Core capabilities.

## Shared Behavior

- **Academy scope:** Every endpoint is prefixed with `/academy/`.  When an
  `academy_id` path parameter is present, `academy=None` records are always
  included unless the query string contains `academy=self`, in which case only
  rows belonging to the requesting academy are returned.
- **Capabilities:**
  - `read_career_path` for all `GET` handlers.
  - `crud_career_path` for `POST`, `PUT`, `DELETE`.  Only users with this Django
    permission can change or delete global (`academy=None`) entities.
- **Pagination / sorting:** Each collection view uses `APIViewExtensions` with
  pagination and optional `sort` query parameter (default sort indicated below).
- **Language handling:** Error messages rely on `get_user_language` and are
  translated via `capyc.core.translation`.

## Endpoint Reference

### Job Families

| Method | Path | Capability | Description |
| --- | --- | --- | --- |
| `GET` | `/academy/job_family` | `read_career_path` | Paginated list of job families (`sort=name`). Supports `academy=self`. |
| `POST` | `/academy/job_family` | `crud_career_path` | Creates a job family. If `academy` is omitted the path `academy_id` is used. Body fields: `name`, `description`, `academy` (optional), `is_active`. Slug auto-generates if missing. |
| `GET` | `/academy/job_family/<int:id>` | `read_career_path` | Retrieve a job family by numeric id (honors academy filter). |
| `PUT` | `/academy/job_family/<int:id>` | `crud_career_path` | Partial update by id. Cannot modify global (`academy=None`) rows without `crud_career_path`. |
| `DELETE` | `/academy/job_family/<int:id>` | `crud_career_path` | Deletes by id after ensuring there are no related job roles. |
| `GET` | `/academy/job_family/<slug>` | `read_career_path` | Retrieve by slug (same filtering rules). |
| `PUT` | `/academy/job_family/<slug>` | `crud_career_path` | Partial update by slug. Same permission & academy checks as id route. |
| `DELETE` | `/academy/job_family/<slug>` | `crud_career_path` | Deletes by slug, blocked if job roles exist. |

### Job Roles

| Method | Path | Capability | Description |
| --- | --- | --- | --- |
| `GET` | `/academy/job_role` | `read_career_path` | Paginated job roles (`sort=name`). Optional query `job_family_id` plus the shared academy filter. |
| `POST` | `/academy/job_role` | `crud_career_path` | Creates a job role. Body fields: `name`, `job_family`, `description`, `academy`, `is_active`, `is_model`. Slug auto-generates. |
| `GET` | `/academy/job_role/<int:id>` | `read_career_path` | Retrieve job role by id (academy filter applied). |
| `PUT` | `/academy/job_role/<int:id>` | `crud_career_path` | Partial update by id with same global-entity protections. |
| `DELETE` | `/academy/job_role/<int:id>` | `crud_career_path` | Deletes by id after verifying no linked career paths. |
| `GET` | `/academy/job_role/<slug>` | `read_career_path` | Retrieve job role by slug. |
| `PUT` | `/academy/job_role/<slug>` | `crud_career_path` | Partial update by slug. |
| `DELETE` | `/academy/job_role/<slug>` | `crud_career_path` | Delete by slug, blocked if career paths exist. |
| `GET` | `/academy/job_family/<int:job_family_id>/job_role` | `read_career_path` | Lists roles belonging to a specific job family (`sort=name`). Response embeds `career_paths` (`id`, `name`). Requires `job_family_id` path arg. |

### Skills

| Method | Path | Capability | Description |
| --- | --- | --- | --- |
| `GET` | `/academy/skill` | `read_career_path` | Paginated skills (`sort=name`). Filters: `skill_domains=<slug,...>`, `technologies=<csv>`, `competencies=<slug,...>`, `job_roles=<slug,...>`. |
| `POST` | — | — | Not implemented (all skill mutations are elsewhere). |
| `GET` | `/academy/skill/<int:id>` | `read_career_path` | Detailed skill by id using `SkillDetailSerializer` (includes domain, competencies, indicators, knowledge, attitudes, etc.). |
| `GET` | `/academy/skill/<slug>` | `read_career_path` | Same as above but slug-based. |

### Competencies

| Method | Path | Capability | Description |
| --- | --- | --- | --- |
| `GET` | `/academy/competency` | `read_career_path` | Paginated list (`sort=name`). Filters: `technologies=<csv>`, `job_roles=<slug,...>`. Serializer adds embedded skills (`slug`, `name`). |
| `GET` | `/academy/competency/<int:id>` | `read_career_path` | Detailed competency by id (`CompetencyDetailSerializer`). |
| `GET` | `/academy/competency/<slug>` | `read_career_path` | Detailed competency by slug. |

### Career Paths & Stages

| Method | Path | Capability | Description |
| --- | --- | --- | --- |
| `GET` | `/academy/career_path` | `read_career_path` | Paginated career paths (`sort=name`) with nested stages collection per item. |

### Skill Domains

| Method | Path | Capability | Description |
| --- | --- | --- | --- |
| `GET` | `/academy/skill_domain` | `read_career_path` | Paginated list (`sort=name`) of all skill domains. |

### Skill Knowledge Items

| Method | Path | Capability | Description |
| --- | --- | --- | --- |
| `GET` | `/academy/skill_knowledge_item` | `read_career_path` | Paginated list (`sort=id`). Optional query `skill=<slug,...>` filters by related skill slug(s). |

### Skill Attitude Tags

| Method | Path | Capability | Description |
| --- | --- | --- | --- |
| `GET` | `/academy/skill_attitude_tag` | `read_career_path` | Paginated list (`sort=tag`). Optional query `skill=<slug,...>` filters by skill slug(s). |

## Request & Response Patterns

- **Creation / updates:** Serializers (`JobFamilySerializer`, `JobRoleSerializer`)
  auto-generate slugs when absent and raise `ValidationException` if a slug
  already exists. They also accept numeric ids for related fields and convert
  them to ORM instances.
- **Error handling:** All validation issues raise `ValidationException` with
  translated messages and HTTP-appropriate status codes (400, 403, 404).
- **Deletion guards:** Job families cannot be deleted while job roles exist, and
  job roles cannot be deleted while any career path references them.

Use this reference whenever you need to discover the capabilities, filters, or
side-effects tied to the talent development (“career map”) endpoints.

