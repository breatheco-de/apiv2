---
name: bc-talentdevelopment-manage-skills
description: Guides coding agents through the BreatheCode talent development API (job families, roles, career paths and stages, skill domains, global skills, competencies, stage-anchored skills). Use when building or querying the school skills framework, linking skills to career stages while designing syllabi, or automating talent_development endpoints under /v1/talent/.
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
- **Pagination:** list endpoints support `limit`, `offset`, sort fields as elsewhere in the API.

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
4. **Discover data:** `GET .../academy/career_path` (paths with stages), `GET .../academy/skill` (filters: `skill_domains`, `technologies`, `competencies`, `job_roles`), `GET .../academy/skill/<id|slug>` for detail including `stage_assignments` and competencies.
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
