# Skill: Create a Macro Cohort with Multiple Micro Cohorts

This document teaches an agent how to create a **macro cohort** (main cohort) that contains multiple **micro cohorts** in the BreatheCode API. **Everything is done via the API** (create and link cohorts with `POST`/`PUT`); Django Admin is not required. Use this skill when the user asks to create a macro cohort, a cohort with sub-cohorts, or a main cohort that groups several small courses.

---

## Concepts

- **Macro cohort**: A cohort that acts as a container. It has a `micro_cohorts` ManyToMany relationship to other cohorts. A cohort is treated as a "macro" when `cohort.micro_cohorts.exists()` is true.
- **Micro cohort**: A normal cohort (same `Cohort` model) that is linked to a macro cohort via `micro_cohorts`. Each micro cohort typically has its own syllabus, schedule, and kickoff/ending dates.
- **Order**: The macro cohort can store display order in `cohorts_order` (comma-separated cohort IDs, e.g. `"5,3,7"`).

**Model reference** (`breathecode.admissions.models.Cohort`):

- `micro_cohorts`: ManyToManyField to `"Cohort"`, blank=True, related_name=`"main_cohorts"`. These are the child cohorts.
- `cohorts_order`: CharField, optional. Comma-separated cohort IDs for display order (e.g. `"1,2,3"`).

---

## High-Level Flow (all via API)

1. Create each **micro cohort** first with `POST /v1/admissions/academy/cohort` (each with its own name, slug, syllabus, kickoff_date, etc.) and note each `id`.
2. Create the **macro cohort** with `POST /v1/admissions/academy/cohort`, including `micro_cohorts` (list of those IDs) and optionally `cohorts_order` (comma-separated ID string). Alternatively, create the macro then link with `PUT /v1/admissions/academy/cohort/{id}`.
3. When users are added to the macro cohort, they are automatically added to all linked micro cohorts (see [User sync](#user-sync)).

---

## Step 1: Create Micro Cohorts

Create each micro cohort using the same flow as a normal cohort. Ensure academy, syllabus, and syllabus version exist (see [COHORTS_CREATE.md](../../LLM-DOCS/COHORTS_CREATE.md)).

**Endpoint:** `POST /v1/admissions/academy/cohort`  
**Headers:** `Authorization`, `Academy: <academy_id>`

Example for two micro cohorts:

```json
// Micro cohort 1
{
  "name": "Frontend - Miami 2024",
  "slug": "frontend-miami-2024",
  "syllabus": "frontend.vlatest",
  "kickoff_date": "2024-03-01T09:00:00Z",
  "ending_date": "2024-04-15T18:00:00Z",
  "stage": "INACTIVE"
}

// Micro cohort 2
{
  "name": "Backend - Miami 2024",
  "slug": "backend-miami-2024",
  "syllabus": "backend.vlatest",
  "kickoff_date": "2024-04-16T09:00:00Z",
  "ending_date": "2024-06-01T18:00:00Z",
  "stage": "INACTIVE"
}
```

Save the returned `id` of each cohort for linking (e.g. `id: 10`, `id: 11`).

---

## Step 2: Create the Macro Cohort and Link Micro Cohorts (API)

Create the macro cohort with the same endpoint, and pass **micro_cohorts** (list of micro cohort IDs) and optionally **cohorts_order** (comma-separated string of IDs for display order). All micro cohort IDs must belong to the same academy.

**Endpoint:** `POST /v1/admissions/academy/cohort`  
**Headers:** `Authorization`, `Academy: <academy_id>`

**Body example** (using micro cohort IDs `10` and `11` from Step 1):

```json
{
  "name": "Full Stack - Miami 2024",
  "slug": "fullstack-miami-2024",
  "syllabus": "fullstack.vlatest",
  "kickoff_date": "2024-03-01T09:00:00Z",
  "ending_date": "2024-06-01T18:00:00Z",
  "stage": "INACTIVE",
  "available_as_saas": true,
  "micro_cohorts": [10, 11],
  "cohorts_order": "10,11"
}
```

- **micro_cohorts**: List of cohort IDs (integers). Each must exist and belong to the same academy. Omit or `null` for a non-macro cohort.
- **cohorts_order**: Optional. Comma-separated cohort IDs (e.g. `"10,11"`) to control display order of micro cohorts.

---

### Option: Link or update micro cohorts later via PUT

To create the macro first without micro cohorts, then link or change them:

**Endpoint:** `PUT /v1/admissions/academy/cohort/{cohort_id}`  
**Headers:** `Authorization`, `Academy: <academy_id>`

**Body example:**

```json
{
  "micro_cohorts": [10, 11],
  "cohorts_order": "10,11"
}
```

You can send only `micro_cohorts` and/or `cohorts_order`; other fields are optional on PUT.

---

## Macro syllabus overrides (micro syllabi in context of a macro)

A **macro cohort** should have a **`syllabus_version`**. Besides the usual root **`days`** array, that JSON may contain **reference keys** for each micro syllabus you want to customize for this program:

- **Key format:** `<micro-syllabus-slug>.v<version>` (e.g. `front-end.v1`, `python.v2`).
- **Value:** An object, typically with a **`days`** array whose items merge **by index** with the corresponding micro syllabus’s `days`. Asset lists `lessons`, `quizzes`, `replits`, and `assignments` also merge by index; use **`"status": "DELETED"`** to remove an asset or a day from the effective syllabus.

**Reading the effective micro syllabus for UI / students in that macro:**

- `GET /v1/admissions/academy/{academy_id}/syllabus/{syllabus_slug}/version/{version}?macro-cohort=<macro_cohort_slug>`
- The macro cohort `slug` must exist in the same academy and must have **`syllabus_version`** set.

Full specification: [SYLLABUS.md — Macro cohort syllabus overrides](../SYLLABUS.md#macro-cohort-syllabus-overrides).

---

## User Sync

- **On join**: When a user is added to the **macro** cohort, the signal `cohort_user_created` runs and `join_to_micro_cohorts` adds that user to **every** linked micro cohort with the same role and `finantial_status="FULLY_PAID"` (see `breathecode.admissions.receivers.join_to_micro_cohorts`).
- **Self-sync**: A user already in a macro cohort can sync themselves into missing micro cohorts:  
  `POST /v1/admissions/me/micro-cohorts/sync/<macro_cohort_slug>`  
  (see `UserMicroCohortsSyncView` in `breathecode.admissions.views`).
- **Bulk sync**: To sync all users from macro cohorts to their micro cohorts (e.g. after linking new micro cohorts), run:  
  `python manage.py add_user_to_micro_cohorts`  
  (see `breathecode.admissions.management.commands.add_user_to_micro_cohorts`).

---

## Reading Macro vs Micro

- **Single cohort:** `GET /v1/admissions/academy/cohort/{id_or_slug}` — response includes `micro_cohorts` (and `cohorts_order` where implemented) when the cohort is a macro.
- **Current user cohorts:** `GET /v1/admissions/academy/cohort/me` — uses `GetMeCohortSerializer`, which includes `micro_cohorts` and `cohorts_order`.

Macro detection in code:

```python
is_macro = bool(
    cohort
    and hasattr(cohort, "micro_cohorts")
    and cohort.micro_cohorts.exists()
)
```

---

## Retrieving the Certificate Specialty from a Cohort (API only)

The agent may need to know which **certificate specialty** (e.g. "Full-Stack Web Development") is associated with a cohort. Do it in two steps using the API.

### Step 1: Get the cohort and read the syllabus slug

**Request:** `GET /v1/admissions/academy/cohort/{id_or_slug}`  
**Headers:** `Authorization`, `Academy: <academy_id>`

From the response, read `syllabus_version`. Inside it you get the syllabus (e.g. `syllabus_version.syllabus.slug` or the syllabus id). If the cohort has no `syllabus_version`, there is no syllabus and no certificate specialty for that cohort.

### Step 2: Get the specialty that uses that syllabus

**Request:** `GET /v1/certificate/academy/specialty?syllabus_slug={syllabus_slug}`  
**Headers:** `Authorization`, `Academy: <academy_id>`

Use the syllabus slug from step 1 as `syllabus_slug`. The response is the list of academy specialties; filter or take the one that matches the cohort’s syllabus (typically one result when using `syllabus_slug`). That is the certificate specialty for the cohort.

**Note:** The academy specialty list only includes specialties that have that syllabus in their **syllabuses** (many-to-many). If the cohort’s syllabus is linked to a specialty only via the legacy one-to-one link, it may not appear here; in that case the list can be empty even though the cohort has a syllabus.

### When there is no specialty

- Cohort response has no `syllabus_version` → no syllabus, so no certificate specialty.
- Step 2 returns an empty list → either no specialty is linked to that syllabus, or the specialty is linked in a way the list endpoint does not expose. Micro cohorts are required to have a syllabus linked to a specialty (creation will fail with `micro-cohort-syllabus-must-have-specialty` if not).

---

## Checklist for the Agent

When creating a macro cohort with multiple micro cohorts (all via API):

1. [ ] Create each micro cohort via `POST /v1/admissions/academy/cohort` and note each `id`.
2. [ ] Create the macro cohort via `POST /v1/admissions/academy/cohort` with `micro_cohorts` (list of those IDs) and optionally `cohorts_order` (e.g. `"10,11"`). Or create the macro first, then `PUT /v1/admissions/academy/cohort/{id}` with `micro_cohorts` and/or `cohorts_order`.
3. [ ] If users were already in the macro cohort before linking, run `add_user_to_micro_cohorts` or ask users to call `POST /v1/admissions/me/micro-cohorts/sync/<macro_cohort_slug>` so they are added to the new micro cohorts.
4. [ ] When the agent needs the **certificate specialty** for a cohort: get the cohort with `GET /v1/admissions/academy/cohort/{id_or_slug}`, read the syllabus slug from `syllabus_version`, then call `GET /v1/certificate/academy/specialty?syllabus_slug={syllabus_slug}` (see [Retrieving the Certificate Specialty from a Cohort (API only)](#retrieving-the-certificate-specialty-from-a-cohort-api-only)).

---

## Related Files and Docs

- **Models:** `breathecode.admissions.models.Cohort` (`micro_cohorts`, `cohorts_order`)
- **Serializers:** `breathecode.admissions.serializers.CohortSerializer` (POST), `CohortPUTSerializer` (PUT) — both accept `micro_cohorts` and `cohorts_order`
- **Receivers:** `breathecode.admissions.receivers.join_to_micro_cohorts`, `new_cohort_user`
- **Views:** `breathecode.admissions.views.AcademyCohortView`, `UserMicroCohortsSyncView`
- **Management command:** `breathecode.admissions.management.commands.add_user_to_micro_cohorts`
- **Cohort creation:** [COHORTS_CREATE.md](../../LLM-DOCS/COHORTS_CREATE.md)
- **Macro syllabus overrides (JSON + API):** [SYLLABUS.md — Macro cohort syllabus overrides](../SYLLABUS.md#macro-cohort-syllabus-overrides)
- **Macro cohort reporting:** [COHORT_REPORT_CALCULATION.md](../../LLM-DOCS/COHORT_REPORT_CALCULATION.md) (macro case: progress and dates aggregated across micro cohorts)
- **Certificate specialty (API):** `GET /v1/certificate/academy/specialty?syllabus_slug=...` — use syllabus slug from the cohort’s `syllabus_version`.
