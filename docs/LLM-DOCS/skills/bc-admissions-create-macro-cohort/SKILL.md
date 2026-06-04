---
name: bc-admissions-create-macro-cohort
description: Use when creating a macro cohort (main cohort) that contains multiple micro cohorts via the API, or when configuring or reading per-macro syllabus overrides for micro syllabi; do NOT use for a single cohort, for only listing/reading cohorts, or for retrieving a cohort's certificate specialty.
requires: []
---

# Skill: Create a Macro Cohort with Multiple Micro Cohorts

## When to Use

Use this skill when the user asks to create a **macro cohort**, a **cohort with sub-cohorts**, or a **main cohort that groups several courses** (micro cohorts). All steps are done via the API (POST/PUT). Do **not** use when the user only wants a single cohort with no sub-cohorts, when they ask only to list or read cohorts, or when they ask only how to get a cohort's certificate specialty (that is a separate task).

## Concepts

- **Macro cohort**: A cohort that acts as a container with a list of linked **micro cohorts**. A cohort is a macro if it has at least one micro cohort linked.
- **Micro cohort**: A normal cohort linked to a macro. Each micro cohort has its own name, slug, syllabus, and kickoff/ending dates.
- **Display order**: The macro can store the order of micro cohorts as a comma-separated list of cohort IDs (e.g. `"10,11"`).
- **Macro syllabus overrides**: The macro cohort’s **`syllabus_version.json`** may include optional keys **`{micro-syllabus-slug}.v{version}`** (e.g. `front-end.v1`). Each value is merged **by position** into that micro syllabus when the client requests the micro version with **`?macro-cohort=<macro_slug>`**. Root **`days`** on the macro JSON is still supported. See **[SYLLABUS.md — Macro cohort syllabus overrides](../../SYLLABUS.md#macro-cohort-syllabus-overrides)** for structure, merge rules, and `DELETED` markers.

## Workflow

1. **Create each micro cohort first.** Call `POST /v1/admissions/academy/cohort` once per micro cohort. Send name, slug, syllabus, kickoff_date, ending_date, stage, and any other required fields. Save the returned `id` of each cohort. Order matters: micro cohorts must exist before you can link them to the macro.

2. **Create the macro cohort and link micro cohorts.** Call `POST /v1/admissions/academy/cohort` with the macro's name, slug, syllabus, kickoff_date, ending_date, stage, and set `micro_cohorts` to the list of micro cohort IDs from Step 1. Optionally set `cohorts_order` to a comma-separated string of those IDs (e.g. `"10,11"`) to control display order. All micro cohort IDs must belong to the same academy.

3. **Optional: link or change micro cohorts later.** If the macro was created without `micro_cohorts`, call `PUT /v1/admissions/academy/cohort/{cohort_id}` with `micro_cohorts` (list of IDs) and optionally `cohorts_order`. You can send only these two fields.

4. **After linking micro cohorts to an existing macro:** If users were already in the macro before you linked micro cohorts, they are not automatically added to the new micro cohorts. Either ask the user to call the sync endpoint (see Endpoints) for each affected user, or inform the user that a bulk sync may be required on the server side.

**Prerequisite:** Academy, syllabus, and syllabus version must exist. If cohort creation fails with a missing academy or syllabus, tell the user to create or fix those first.

5. **Optional: per-macro overrides for micro syllabi.** Edit the macro cohort’s **`SyllabusVersion`** JSON (via the same syllabus-version APIs you use for any cohort) and add blocks keyed by **`{micro_slug}.v{version}`** as documented in [SYLLABUS.md](../../SYLLABUS.md#macro-cohort-syllabus-overrides). Clients that need the **effective** micro syllabus for students in that macro should call **`GET /v1/admissions/academy/{academy_id}/syllabus/{syllabus_slug}/version/{version}?macro-cohort={macro_cohort_slug}`** (requires `read_syllabus` and `Academy` header). The macro cohort must have a **`syllabus_version`** assigned.

## Endpoints

| Action | Method | Path | Headers | Body | Response |
|--------|--------|------|---------|------|----------|
| Create cohort (micro or macro) | POST | `/v1/admissions/academy/cohort` | `Authorization`, `Academy: <academy_id>` | See request samples below. | Cohort object; store `id` for linking. |
| Update cohort (link/change micro cohorts) | PUT | `/v1/admissions/academy/cohort/{cohort_id}` | `Authorization`, `Academy: <academy_id>` | At least one of: `micro_cohorts`, `cohorts_order`. See request sample. | Updated cohort object. |
| Sync current user into macro's micro cohorts | POST | `/v1/admissions/me/micro-cohorts/sync/<macro_cohort_slug>` | `Authorization` | None | Sync result. |
| Get micro syllabus version with macro merge | GET | `/v1/admissions/academy/{academy_id}/syllabus/{syllabus_slug}/version/{version}` | `Authorization`, `Academy: <academy_id>` | Query: `macro-cohort=<macro_slug>` (optional) | Syllabus version; `json` is merged when `macro-cohort` is set. |

**Create micro cohort — request (POST `/v1/admissions/academy/cohort`):**
```json
{
  "name": "Frontend Jan 2026",
  "slug": "frontend-jan-2026",
  "syllabus": "front-end-development.v2",
  "kickoff_date": "2026-01-15T09:00:00Z",
  "ending_date": "2026-04-15T17:00:00Z",
  "never_ends": false,
  "stage": "STARTED",
  "online_meeting_url": "https://meet.example.com/room",
  "available_as_saas": true
}
```
Save the returned `id` (e.g. 1277) to use in the macro's `micro_cohorts`.

**Create macro cohort — request (POST `/v1/admissions/academy/cohort`):**
```json
{
  "name": "My first macro cohort",
  "slug": "my-first-macro-cohort",
  "syllabus": "front-end-development.v2",
  "kickoff_date": "2026-03-11T15:59:00Z",
  "ending_date": "2026-06-25T15:59:00Z",
  "never_ends": false,
  "available_as_saas": false,
  "micro_cohorts": [1277, 1278],
  "cohorts_order": "1277,1278"
}
```
Use the IDs from the micro cohorts created in Step 1. All must belong to the same academy.

**Create cohort — response (201, micro or macro):**
```json
{
  "id": 1280,
  "name": "My first macro cohort",
  "slug": "my-first-macro-cohort",
  "syllabus_version": {"id": 5, "version": "2", "syllabus": {"slug": "front-end-development"}},
  "kickoff_date": "2026-03-11T15:59:00Z",
  "ending_date": "2026-06-25T15:59:00Z",
  "stage": "STARTED",
  "micro_cohorts": [1277, 1278],
  "cohorts_order": "1277,1278"
}
```
Always store `id` from the response for later use (e.g. linking or PUT).

**Update cohort (link micro cohorts) — request (PUT `/v1/admissions/academy/cohort/{cohort_id}`):**
```json
{
  "micro_cohorts": [1277, 1278],
  "cohorts_order": "1277,1278"
}
```

To verify a cohort is a macro or to read its micro cohorts and order, use `GET /v1/admissions/academy/cohort/{id_or_slug}`; the response includes `micro_cohorts` and `cohorts_order` when present.

## Edge Cases

- **Creation fails with missing syllabus or academy:** Tell the user that academy and syllabus (and syllabus version) must exist first; do not retry the same payload.
- **Creation fails with `micro-cohort-syllabus-must-have-specialty`:** The micro cohort's syllabus is not linked to a certificate specialty. Tell the user to link that syllabus to a specialty via the certificate API, then retry.
- **One or more micro cohort IDs do not exist or belong to another academy:** The API will reject the request. Tell the user that all IDs in `micro_cohorts` must be existing cohorts in the same academy; verify IDs from Step 1.
- **Users were already in the macro before micro cohorts were linked:** New micro cohorts will not automatically get those users. Tell the user to use the sync endpoint per user or to run a bulk sync if available; do not leave this unmentioned.

## Macro syllabus JSON overrides (optional)

If the macro’s **`SyllabusVersion.json`** includes per-micro keys like **`jumpstart.v2`** to merge teacher copy or assets into a micro syllabus, see **[SYLLABUS.md — Macro cohort syllabus overrides](../../SYLLABUS.md#macro-cohort-syllabus-overrides-per-micro-slug)** for merge-by-index rules, **`status: "DELETED"`**, and replacing the first lesson of a day.

## Checklist

1. Create each micro cohort with `POST /v1/admissions/academy/cohort` and record each returned `id`.
2. Create the macro cohort with `POST /v1/admissions/academy/cohort` including `micro_cohorts` (list of those IDs) and optionally `cohorts_order`, or create the macro then call `PUT /v1/admissions/academy/cohort/{id}` with `micro_cohorts` and/or `cohorts_order`.
3. If the macro already had users before linking micro cohorts, inform the user to sync those users (sync endpoint or bulk sync).
4. Confirm the macro cohort and its micro cohorts appear as intended (e.g. via `GET /v1/admissions/academy/cohort/{id_or_slug}`).
5. If using **macro syllabus overrides**, ensure the macro’s `SyllabusVersion` JSON includes the needed `{micro_slug}.v{version}` blocks and verify `GET .../syllabus/.../version/...?macro-cohort=...` returns the merged `json` (see [SYLLABUS.md](../../SYLLABUS.md#macro-cohort-syllabus-overrides)).
