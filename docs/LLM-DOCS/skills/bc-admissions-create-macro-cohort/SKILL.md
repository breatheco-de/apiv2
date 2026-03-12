---
name: bc-admissions-create-macro-cohort
description: Use when creating a macro cohort (main cohort) that contains multiple micro cohorts via the API; do NOT use for a single cohort, for only listing/reading cohorts, or for retrieving a cohort's certificate specialty.
---

# Skill: Create a Macro Cohort with Multiple Micro Cohorts

## When to Use

Use this skill when the user asks to create a **macro cohort**, a **cohort with sub-cohorts**, or a **main cohort that groups several courses** (micro cohorts). All steps are done via the API (POST/PUT). Do **not** use when the user only wants a single cohort with no sub-cohorts, when they ask only to list or read cohorts, or when they ask only how to get a cohort's certificate specialty (that is a separate task).

## Concepts

- **Macro cohort**: A cohort that acts as a container with a list of linked **micro cohorts**. A cohort is a macro if it has at least one micro cohort linked.
- **Micro cohort**: A normal cohort linked to a macro. Each micro cohort has its own name, slug, syllabus, and kickoff/ending dates.
- **Display order**: The macro can store the order of micro cohorts as a comma-separated list of cohort IDs (e.g. `"10,11"`).

## Workflow

1. **Create each micro cohort first.** Call `POST /v1/admissions/academy/cohort` once per micro cohort. Send name, slug, syllabus, kickoff_date, ending_date, stage, and any other required fields. Save the returned `id` of each cohort. Order matters: micro cohorts must exist before you can link them to the macro.

2. **Create the macro cohort and link micro cohorts.** Call `POST /v1/admissions/academy/cohort` with the macro's name, slug, syllabus, kickoff_date, ending_date, stage, and set `micro_cohorts` to the list of micro cohort IDs from Step 1. Optionally set `cohorts_order` to a comma-separated string of those IDs (e.g. `"10,11"`) to control display order. All micro cohort IDs must belong to the same academy.

3. **Optional: link or change micro cohorts later.** If the macro was created without `micro_cohorts`, call `PUT /v1/admissions/academy/cohort/{cohort_id}` with `micro_cohorts` (list of IDs) and optionally `cohorts_order`. You can send only these two fields.

4. **After linking micro cohorts to an existing macro:** If users were already in the macro before you linked micro cohorts, they are not automatically added to the new micro cohorts. Either ask the user to call the sync endpoint (see Endpoints) for each affected user, or inform the user that a bulk sync may be required on the server side.

**Prerequisite:** Academy, syllabus, and syllabus version must exist. If cohort creation fails with a missing academy or syllabus, tell the user to create or fix those first.

## Endpoints

| Action | Method | Path | Headers | Body (required) | Response |
|--------|--------|------|---------|-----------------|----------|
| Create cohort (micro or macro) | POST | `/v1/admissions/academy/cohort` | `Authorization`, `Academy: <academy_id>` | `name`, `slug`, `syllabus`, `kickoff_date`, `ending_date`, `stage`. For macro only: `micro_cohorts` (list of cohort IDs), optionally `cohorts_order` (string, e.g. `"10,11"`) | Cohort object; include and store `id` for linking. |
| Update cohort (link/change micro cohorts) | PUT | `/v1/admissions/academy/cohort/{cohort_id}` | `Authorization`, `Academy: <academy_id>` | At least one of: `micro_cohorts` (list of cohort IDs), `cohorts_order` (string) | Updated cohort object. |
| Sync current user into macro's micro cohorts | POST | `/v1/admissions/me/micro-cohorts/sync/<macro_cohort_slug>` | `Authorization` | None | Sync result. |

To verify a cohort is a macro or to read its micro cohorts and order, use `GET /v1/admissions/academy/cohort/{id_or_slug}`; the response includes `micro_cohorts` and `cohorts_order` when present.

## Edge Cases

- **Creation fails with missing syllabus or academy:** Tell the user that academy and syllabus (and syllabus version) must exist first; do not retry the same payload.
- **Creation fails with `micro-cohort-syllabus-must-have-specialty`:** The micro cohort's syllabus is not linked to a certificate specialty. Tell the user to link that syllabus to a specialty via the certificate API, then retry.
- **One or more micro cohort IDs do not exist or belong to another academy:** The API will reject the request. Tell the user that all IDs in `micro_cohorts` must be existing cohorts in the same academy; verify IDs from Step 1.
- **Users were already in the macro before micro cohorts were linked:** New micro cohorts will not automatically get those users. Tell the user to use the sync endpoint per user or to run a bulk sync if available; do not leave this unmentioned.

## Checklist

1. Create each micro cohort with `POST /v1/admissions/academy/cohort` and record each returned `id`.
2. Create the macro cohort with `POST /v1/admissions/academy/cohort` including `micro_cohorts` (list of those IDs) and optionally `cohorts_order`, or create the macro then call `PUT /v1/admissions/academy/cohort/{id}` with `micro_cohorts` and/or `cohorts_order`.
3. If the macro already had users before linking micro cohorts, inform the user to sync those users (sync endpoint or bulk sync).
4. Confirm the macro cohort and its micro cohorts appear as intended (e.g. via `GET /v1/admissions/academy/cohort/{id_or_slug}`).
