---
name: bc-admissions-read-syllabus-skills
description: Use when staff need to know which catalog skills a syllabus version teaches (union of the skills declared by its lessons, exercises, projects and quizzes), which syllabus assets have no skills yet, or whether the syllabus covers the skills required by a talent development career path or stage; do NOT use to edit syllabus JSON, to change asset skills, or to manage the skills catalog or career paths.
requires:
  - bc-authenticate-staff-authentication
---

# Skill: Read the Skills Taught by a Syllabus Version

## When to Use

Use when the user asks "what skills does this syllabus teach?", "does this syllabus prepare students for the Junior Backend stage?", wants a skills coverage or gap report, or needs to find syllabus assets without skills. Do NOT use to change skills (they come from each asset's source file, see [`bc-registry-manage-assets`](../bc-registry-manage-assets/SKILL.md)), to create skills, stages or career paths ([`bc-talentdevelopment-manage-skills`](../bc-talentdevelopment-manage-skills/SKILL.md)), or to edit syllabus content.

## Concepts

- Skills are not stored on the syllabus. The API computes them on read as the **union** of the skills of every asset referenced in the version's days (`lessons`, `quizzes`, `replits`, `assignments`).
- Asset skills are synced from each asset's source file. A syllabus with few skills usually means its assets do not declare them yet.
- The result is cached and refreshes automatically when the syllabus version is saved or when any asset's skills change. There is no manual refresh.
- **Talent development connection.** Syllabus skills and career path skills share the same global catalog, so they compare by skill `slug`. The chain is: syllabus version → assets → skills ← stage skills ← career stage ← career path ← job role.
- **The API does not link a syllabus to a career path, stage, or job role.** The user must say which career path (and optionally which stage) the syllabus targets. The comparison is done client-side by diffing two responses.
- **Required skills of a stage** are its stage-anchored skills (`stage_ids` filter), each with a `required_level` (`foundation`, `core`, `applied`) and `is_core`. Do not use the `job_roles` skill filter for this comparison: it follows the competency graph and can return a different set.

## Workflow

1. Authenticate staff per [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md). Confirm the `read_syllabus` capability. Send header **`Academy: <academy_id>`**.
2. Identify the syllabus by numeric id or slug and the version number. Use `latest` to read the highest `PUBLISHED` version.
3. Call `GET /v1/admissions/syllabus/{syllabus_id_or_slug}/version/{version}/skills`.
4. Read `skills` (sorted by `asset_count`, highest first). Use `mandatory` to tell required skills from optional ones, `days` to locate them in the syllabus, and `max_difficulty` for depth.
5. Report coverage gaps: `unmapped_assets` counts assets found in the syllabus that declare no skills; `unresolved_slugs` lists syllabus slugs that match no asset. To fix missing skills, switch to [`bc-registry-manage-assets`](../bc-registry-manage-assets/SKILL.md) (skills are declared in the asset source file, not through PUT).

Steps 6–10 apply only when the user wants to compare the syllabus with a career path or stage. They need the `read_career_path` capability in the same academy.

6. Resolve the target career path: `GET /v1/talent/academy/career_path?job_roles={job_role_slug}`. Each result includes its `stages` ordered by `sequence`. If several paths match, ask the user which one. Save the path `id` and the stage `id`s.
7. Choose the target stages. For "prepares students for stage N", use every stage with `sequence` ≤ N (skills accumulate along the path). For "the whole path", use all stages.
8. Get the required skills: `GET /v1/talent/academy/skill?stage_ids={id1},{id2}&limit=200`. Follow pagination until all rows are read. Save the set of `slug`s.
9. Diff by `slug` against the syllabus `skills` from Step 3:
   - **Covered:** in both. Flag as weak if the syllabus entry has `mandatory: false`.
   - **Missing:** required by the stages but absent from the syllabus.
   - **Extra:** taught by the syllabus but not required by the stages (not an error).
10. Only if the user cares about depth: for each covered or missing skill, call `GET /v1/talent/academy/skill/{slug}` and read `stage_assignments` for the target stage ids to get `required_level` and `is_core`. Prioritize missing skills with `is_core: true`, and compare `required_level` against the syllabus `max_difficulty` (`foundation` ≈ `BEGINNER`/`EASY`, `core` ≈ `INTERMEDIATE`, `applied` ≈ `HARD`). This is one call per skill; skip it for large lists unless asked.

Report the result as three lists (covered, missing, extra) plus a coverage ratio `covered / required`. For missing skills, suggest declaring them in the source file of an existing syllabus asset ([`bc-registry-manage-assets`](../bc-registry-manage-assets/SKILL.md)) or adding new assets to the syllabus.

## Endpoints

### Get syllabus version skills

- **Method / path:** `GET /v1/admissions/syllabus/{syllabus_id_or_slug}/version/{version}/skills`
- **Headers:** `Authorization: Token 7f3c2a9e8b1d4f60a5c3e2d1b0a9f8e7`, `Academy: 4`. Optional `Accept-Language: en|es` for translated errors.
- **Capability:** `read_syllabus`
- **Path params:** `syllabus_id_or_slug` (numeric id or slug), `version` (number or `latest`).
- **Query:** `status` (comma-separated). Required to read a `DEPRECATED` or `DELETED` version, e.g. `?status=DEPRECATED`.
- **Pagination:** no. Returns one object.
- **Visibility:** syllabi owned by the `Academy` header or with `private=false`.

**Response `200`:**

```json
{
  "syllabus": "full-stack",
  "version": 3,
  "total_assets": 42,
  "unmapped_assets": 7,
  "unresolved_slugs": ["old-intro-quiz"],
  "skills": [
    {
      "slug": "python-loops",
      "name": "Python loops",
      "domain": "programming",
      "by_asset_type": { "LESSON": 2, "EXERCISE": 3 },
      "max_difficulty": "INTERMEDIATE",
      "days": [2, 3, 5],
      "mandatory": true,
      "asset_count": 5
    },
    {
      "slug": "http-basics",
      "name": "HTTP basics",
      "domain": "web-development",
      "by_asset_type": { "PROJECT": 1 },
      "max_difficulty": "HARD",
      "days": [9],
      "mandatory": false,
      "asset_count": 1
    }
  ]
}
```

- `total_assets`: distinct assets resolved from the syllabus (an asset referenced by an old slug alias counts once).
- `days`: day `position` values (1-based index when a day has no `position`).
- `mandatory`: `true` if at least one syllabus entry that teaches the skill is not marked `"mandatory": false`.
- `max_difficulty`: hardest asset difficulty among `BEGINNER`, `EASY`, `INTERMEDIATE`, `HARD`; `null` if none set.

### List career paths with stages (comparison only)

- **Method / path:** `GET /v1/talent/academy/career_path?job_roles=backend-developer`
- **Headers:** `Authorization`, `Academy`. Optional `Accept-Language: en|es`.
- **Capability:** `read_career_path`
- **Query:** `job_roles` (comma-separated job role slugs) or `job_role_ids`. Returns paths shared globally plus the ones owned by the `Academy` header. **Pagination:** yes.

**Response `200` (one element):**

```json
{
  "id": 12,
  "name": "Backend track",
  "job_role": { "id": 5, "slug": "backend-developer", "name": "Backend Developer" },
  "description": "Primary progression",
  "academy": null,
  "is_active": true,
  "stages": [
    { "id": 31, "sequence": 1, "title": "Junior backend", "goal": "Ship features with review", "description": "" },
    { "id": 32, "sequence": 2, "title": "Mid backend", "goal": "Own services end to end", "description": "" }
  ]
}
```

### List required skills of stages (comparison only)

- **Method / path:** `GET /v1/talent/academy/skill?stage_ids=31,32&limit=200`
- **Capability:** `read_career_path`. **Pagination:** yes; read every page.
- Returns skills anchored to any listed stage. The rows do **not** include `required_level`; use the skill detail for that.

**Response `200` (one element):**

```json
{
  "id": 88,
  "slug": "python-loops",
  "name": "Python loops",
  "domain": { "id": 3, "slug": "programming", "name": "Programming" },
  "description": "Iterate over collections with for and while",
  "technologies": "python",
  "created_at": "2026-05-02T14:10:00Z",
  "updated_at": "2026-05-02T14:10:00Z"
}
```

### Get skill stage assignments (comparison depth only)

- **Method / path:** `GET /v1/talent/academy/skill/{skill_slug}`
- **Capability:** `read_career_path`. **Pagination:** no. An old slug alias resolves to the current skill.

**Response `200` (abbreviated to the field this skill reads):**

```json
{
  "slug": "python-loops",
  "name": "Python loops",
  "stage_assignments": [
    {
      "id": 140,
      "stage": {
        "id": 31,
        "title": "Junior backend",
        "sequence": 1,
        "career_path": {
          "id": 12,
          "name": "Backend track",
          "job_role": { "id": 5, "slug": "backend-developer", "name": "Backend Developer" }
        }
      },
      "required_level": "core",
      "is_core": true
    }
  ]
}
```

## Edge Cases

- **`404` `syllabus-version-not-found`:** the syllabus or version does not exist, is private to another academy, or `latest` has no `PUBLISHED` version. List the academy's syllabi and versions again and retry with an existing version number.
- **`404` on a deprecated or deleted version:** retry with `?status=DEPRECATED` or `?status=DELETED` only if the user explicitly wants that version.
- **`skills` is empty:** the assets do not declare skills yet. Report `total_assets` and `unmapped_assets` and suggest declaring skills in the asset source files.
- **`unresolved_slugs` is not empty:** the syllabus references assets that do not exist. Report them; they are not counted in `total_assets`.
- **`403`:** the user lacks `read_syllabus` in that academy. Ask for the right academy or capability; do not retry with another academy id.
- **User asks for a comparison but does not name a career path or job role:** the API has no syllabus-to-career-path link. Ask which job role or career path the syllabus targets; do not guess from the syllabus name.
- **`403` on talent endpoints:** the user lacks `read_career_path`. Report the syllabus skills alone and say the comparison needs that capability.
- **Career path list is empty:** no path is visible for that job role in this academy. Ask the user to confirm the job role slug, or create the path with [`bc-talentdevelopment-manage-skills`](../bc-talentdevelopment-manage-skills/SKILL.md) if they want one.
- **Stage skill list is empty:** the stages have no anchored skills yet. Report that the comparison is not possible until skills are added to the stages; do not fall back to the `job_roles` skill filter without telling the user it uses competencies instead.
- **Low coverage caused by `unmapped_assets`:** if many syllabus assets declare no skills, missing skills may actually be taught but undeclared. Report `unmapped_assets` next to the coverage ratio.

## Checklist

1. [ ] Sent `Authorization` and `Academy` headers with `read_syllabus`.
2. [ ] Used the syllabus id or slug and a version number or `latest`.
3. [ ] Reported skills with `mandatory`, `days`, and `asset_count`.
4. [ ] Reported `unmapped_assets` and `unresolved_slugs` as coverage gaps.
5. [ ] For a comparison: confirmed the target career path and stages with the user, read every page of `skill?stage_ids=`, and reported covered, missing, and extra skills by `slug` with the coverage ratio.
6. [ ] Switched to `bc-registry-manage-assets` or `bc-talentdevelopment-manage-skills` if the user asked to change skills, stages, or career paths.
