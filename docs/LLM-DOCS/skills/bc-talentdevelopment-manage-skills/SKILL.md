---
name: bc-talentdevelopment-manage-skills
description: Guides coding agents through the BreatheCode talent development API (job families, roles, career paths and stages, skill domains, global skills, competencies, stage-anchored skills), including search and filter query parameters on list endpoints. Use when building or querying the school skills framework, linking skills to career stages while designing syllabi, or automating talent_development endpoints under /v1/talent/.
requires: []
---

# Skill: Manage talent development (skills framework)

## When to use

Use when the user needs to **list or mutate** the skills framework: job families, job roles, career paths, career stages, skill domains, skills, competencies, or **stage-anchored skills** (`StageSkill`). Typical prompts: syllabus design tied to job roles, “add a skill for this stage”, career path setup, or filtering skills by competency/job role.

Do **not** use for student-facing career job boards (a different `career` app may apply). This skill is only for **`breathecode.talent_development`** routes.

## Base URL and auth

- **Prefix:** all paths below are under **`/v1/talent/`** (Django mounts `talent_development` URLs at `v1/talent/`).
- **Staff academy routes:** send **`Authorization`** (Bearer) and header **`Academy: <academy_id>`** (integer as string is fine).
- **Capabilities:** **`read_career_path`** for GET list/detail; **`crud_career_path`** for POST/PUT/DELETE and stage-skill creation.
- **List query parameters:** pagination, sorting, optional academy scope, and resource-specific filters are documented in **Search and filter** below.

## Search and filter

List GETs under `/v1/talent/academy/…` share common mechanics; several also accept **resource-specific** query parameters. Multi-value filters use **comma-separated** lists unless noted.

### Shared (all list endpoints that paginate)

| Parameter | Role |
|-----------|------|
| `limit` | Page size (positive integer). Default page size depends on server env (`ENABLE_DEFAULT_PAGINATION` / `DEFAULT_LIMIT`). |
| `offset` | Starting index (default `0`). |
| `sort` | Override ordering. Default **per view** is usually `name`; exceptions: career stages default to `sequence`, skill knowledge items to `id`, skill attitude tags to `tag`. Pass a field name (e.g. `sort=name` or `sort=-name` for descending if the ORM accepts it). |
| `envelope` | When set (and pagination applies), response can be wrapped with `count`, `results`, and pagination links; response headers include `X-Total-Count`, `X-Per-Page`, `X-Page`, and `Link`. |

### Academy visibility on lists (`apply_academy_filter`)

For **job family**, **job role**, **career path**, and **career stage** lists, rows may be **global** (`academy` null) or **owned** by an academy.

| Parameter | Behavior |
|-----------|----------|
| *(default)* | Include rows where `academy` is **null** (shared) **or** `academy` matches the **`Academy`** request header. |
| `academy=self` | Include **only** rows for the academy in the header (exclude global/shared rows). If no academy header is present, the list is empty. |

### Resource-specific filters

| GET path | Extra query parameters | Notes |
|----------|-------------------------|--------|
| `/v1/talent/academy/job_family` | — | Uses academy visibility above. |
| `/v1/talent/academy/job_role` | — | Uses academy visibility above. |
| `/v1/talent/academy/job_family/<job_family_id>/job_role` | — | Roles are filtered by **`job_family_id` in the path** (not a query param). Uses academy visibility. |
| `/v1/talent/academy/career_path` | `job_role_ids`, `job_roles` | `job_role_ids`: comma-separated numeric IDs. `job_roles`: comma-separated **job role slugs**. Uses academy visibility. |
| `/v1/talent/academy/career_stage` | `career_path_ids`, `job_role_ids`, `job_roles` | `career_path_ids`: comma-separated numeric IDs. `job_role_ids` / `job_roles` filter via the stage’s career path’s job role. Uses academy visibility on the **career path’s** academy. |
| `/v1/talent/academy/skill` | `skill_domains`, `technologies`, `competencies`, `stage_ids`, `career_path_ids`, `career_paths`, `job_roles` | See **Skills list semantics** below. |
| `/v1/talent/academy/competency` | `technologies`, `job_roles` | `job_roles`: comma-separated **job role slugs** (competencies linked to stages on paths for those roles). |
| `/v1/talent/academy/skill_domain` | — | Global domains; only shared list mechanics apply. |
| `/v1/talent/academy/skill_knowledge_item` | `skill` | Comma-separated **skill slugs**. |
| `/v1/talent/academy/skill_attitude_tag` | `skill` | Comma-separated **skill slugs**. |

**Skills list semantics**

- **`skill_domains`:** comma-separated **domain slugs** (`domain__slug`).
- **`technologies`:** comma-separated tokens; a skill matches if **any** token appears as a **substring** in the skill’s `technologies` field (case-insensitive).
- **`competencies`:** comma-separated **competency slugs** (skills linked via `CompetencySkill`).
- **`stage_ids`:** comma-separated **career stage IDs** (digits only); skills that have a **`StageSkill`** on any listed stage.
- **`career_path_ids`:** comma-separated path IDs (digits or mixed with `career_paths`); skills linked via **`StageSkill`** on any stage belonging to those paths. If **`career_path_ids`** and **`career_paths`** are both present, the API applies **both** filters on `CareerPath` (intersection: paths must match ID **and** name constraints when both are set).
- **`career_paths`:** comma-separated **career path names** (exact match on `name`); same StageSkill-based resolution as path IDs.
- **`job_roles`:** comma-separated **job role slugs**. This filter uses the **competency graph only**: job role → career path → stage → **StageCompetency** → competency → skill (`CompetencySkill`). It does **not** include skills that appear **only** through **`StageSkill`** without that competency chain. For stage-anchored-only skills, use **`stage_ids`**, **`career_path_ids`**, or **`career_paths`** instead.

## Model overview

- **JobFamily** → **JobRole** → **CareerPath** → **CareerStage** (hierarchy for a role’s progression).
- **SkillDomain** → **Skill** (global taxonomy; skills are not academy-scoped).
- **StageSkill** links a **CareerStage** to a **Skill** with `required_level` (`foundation` | `core` | `applied`) and `is_core`. Use this to add skills “on the go” for a stage without requiring competency wiring first.
- **Competency**, **CompetencySkill**, **StageCompetency** connect broader competencies to skills and stages (list/filter via existing GET endpoints).

**Global vs academy-owned:** `JobFamily`, `JobRole`, and `CareerPath` may have `academy` null (shared). Mutating those rows requires Django permission `crud_career_path` on the user when `academy` is null; when `academy` is set, it must match the request `Academy` header.

## Workflows

1. **Bootstrap hierarchy (academy-owned):** `POST /v1/talent/academy/job_family` → `POST /v1/talent/academy/job_role` (with `job_family`) → `POST /v1/talent/academy/career_path` (with `job_role`, optional `name` / `description` / `is_active`; `academy` defaults from header) → `POST /v1/talent/academy/career_path/<career_path_id>/career_stage` (`sequence`, `title`, `goal`, `description`).
2. **Ensure a skill domain exists:** `POST /v1/talent/academy/skill_domain` (`name`, optional `slug`, `description`); slug auto-derived from name if omitted.
3. **Add a skill anchored to a stage:** `POST /v1/talent/academy/stage_skill` with `stage_id`, `name`, and **either** `domain_id` **or** `domain_slug` (not both). Optional: `slug`, `description`, `technologies`, `required_level`, `is_core`. Creates **Skill** if slug is new; **updates or creates** `StageSkill`. Returns `201` when the stage–skill link is new, `200` when the link existed and was updated.
4. **Discover data:** `GET .../academy/career_path` (paths with nested stages), `GET .../academy/skill` and other list endpoints using **Search and filter** above, `GET .../academy/skill/<id|slug>` for detail including `stage_assignments` and competencies. Example: `GET /v1/talent/academy/skill?competencies=communication&skill_domains=soft-skills&limit=50`.
5. **Delete safely:** `DELETE .../academy/career_path/<id>` only if no stages exist. `DELETE .../academy/career_path/<id>/career_stage/<stage_id>` only if no `StageSkill` or `StageCompetency` on that stage. `DELETE .../academy/skill_domain/<id|slug>` only if no **Skill** uses the domain.

## Endpoints (summary)

| Action | Method | Path |
|--------|--------|------|
| List/create job families | GET, POST | `/v1/talent/academy/job_family` |
| Job family by id or slug | GET, PUT, DELETE | `/v1/talent/academy/job_family/<id>` or `.../<slug>` |
| List/create job roles | GET, POST | `/v1/talent/academy/job_role` |
| Job roles by family | GET | `/v1/talent/academy/job_family/<job_family_id>/job_role` |
| Job role by id or slug | GET, PUT, DELETE | `/v1/talent/academy/job_role/<id>` or `.../<slug>` |
| List/create career paths | GET, POST | `/v1/talent/academy/career_path` |
| Delete career path | DELETE | `/v1/talent/academy/career_path/<career_path_id>` |
| Create career stage | POST | `/v1/talent/academy/career_path/<career_path_id>/career_stage` |
| Delete career stage | DELETE | `/v1/talent/academy/career_path/<career_path_id>/career_stage/<career_stage_id>` |
| List skills | GET | `/v1/talent/academy/skill` |
| Skill detail | GET | `/v1/talent/academy/skill/<id>` or `.../<slug>` |
| Stage-anchored skill create/update | POST | `/v1/talent/academy/stage_skill` |
| List/create skill domains | GET, POST | `/v1/talent/academy/skill_domain` |
| Delete skill domain | DELETE | `/v1/talent/academy/skill_domain/<id>` or `.../<slug>` |
| List competencies | GET | `/v1/talent/academy/competency` |
| Competency detail | GET | `/v1/talent/academy/competency/<id>` or `.../<slug>` |
| List skill knowledge items | GET | `/v1/talent/academy/skill_knowledge_item` |
| List skill attitude tags | GET | `/v1/talent/academy/skill_attitude_tag` |

## Request examples

**Create stage-anchored skill:**

```http
POST /v1/talent/academy/stage_skill
Authorization: Bearer <token>
Academy: 1
Content-Type: application/json

{
  "stage_id": 3,
  "name": "PostgreSQL",
  "domain_slug": "database",
  "required_level": "core",
  "is_core": true
}
```

**Create career path:**

```json
{
  "name": "Backend track",
  "job_role": 12,
  "description": "Primary progression",
  "is_active": true
}
```

**Create career stage:**

```json
{
  "sequence": 1,
  "title": "Junior backend",
  "goal": "Ship features with review",
  "description": ""
}
```

## Cross-domain note

Syllabus versions and cohort syllabi live under **admissions** (`bc-admissions-*`). Align syllabus content with this framework by resolving the right **job role / career path / stage** here first, then linking syllabus design in admissions as your product flow requires.
