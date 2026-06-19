---
name: bc-admissions-read-student-my-cohorts-and-progress
description: Use when an authenticated student needs to list cohorts they joined as STUDENT and interpret progress, including self-paced never_ends cohorts and macro cohorts that contain micro cohorts (hide micro as duplicate when also enrolled in the parent macro); do NOT use for staff listing other users, academy /academy/ cohort admin, teacher assignment review queues, or enrollments where the user is only TEACHER/ASSISTANT.
requires:
  - breathecode-student-api-index
  - bc-authenticate-student-authentication
---

# Skill: My cohorts and progress (never_ends aware)

## When to Use

- The learner asks what **courses/cohorts they are in** and how **far along** they are.
- You need a repeatable flow: **`user/me`** → filter student memberships → branch on **`never_ends`** → optional **`history_log`** → paginated **`user/me/task`** per cohort.
- Do **not** use this skill to manage other users’ cohorts, to call staff-only admissions routes, or to answer teacher review queues.

## Concepts

- **`GET /v1/admissions/user/me`** returns `cohorts`: one row per `CohortUser` for the current user (any role). For “courses I take as a student”, keep only rows where **`role` is `STUDENT`**.
- **Macro vs micro cohorts:** a **macro** cohort lists child cohorts under **`cohort.micro_cohorts`** (each child has at least **`id`**, **`slug`**, **`name`**). If the student is enrolled in **both** a macro and one of its micro cohorts, **do not** report the micro as its own line item: **deduplicate** so the report only reflects the **macro** (see Workflow step 3). If the student is **only** enrolled in a micro and has **no** enrolled macro in `cohorts` that lists that micro under **`micro_cohorts`**, keep that single membership as usual.
- **`cohort.never_ends`**: when **`true`**, the cohort is **self-paced**; cohort-level **`current_day`** / **`current_module`** must **not** be treated as the primary progress signal. When **`false`**, cohort day/module are meaningful **alongside** the student’s tasks.
- **Authoritative task state**: **`GET /v1/assignment/user/me/task?cohort=…`** (paginated). Aggregate `task_status` / `revision_status` per cohort for personal progress.
- **Backend completion**: `CohortUser` serializers can include a `completion` object calculated by `evaluate_cohort_user_completion(cohort_user)`. Prefer this object when present because it uses the cohort syllabus grading strategy and official backend rules.
- **`CohortUser.history_log`**: optional snapshot (e.g. `delivered_assignments`, `pending_assignments` as `{id, type}` entries). It can **lag** behind live `Task` rows; prefer tasks when they disagree.

## Progress rules (decision table)

| `cohort.never_ends` | Primary progress signals | Cohort `current_day` / `current_module` |
|---------------------|---------------------------|----------------------------------------|
| **`false`**         | Cohort day/module **and** task counts/status | Use as schedule position with tasks for detail |
| **`true`**        | Task aggregates (and optional `history_log`) | **Do not** present as main self-paced progress |

## Workflow

1. Ensure the client has a valid **`Authorization: Token <token>`** for the student (see [`bc-authenticate-student-authentication`](../bc-authenticate-student-authentication/SKILL.md)). Optionally send **`Accept-Language`** (e.g. `en`, `es`) for translated API errors.
2. Call **`GET /v1/admissions/user/me`** (admissions). From **`cohorts`**, keep only items where **`role === "STUDENT"`**. Each item includes nested **`cohort`** (includes **`never_ends`**, **`current_day`**, **`current_module`**, **`stage`**, syllabus, academy, **`micro_cohorts`** for macro setups, etc.) plus **`educational_status`**, **`finantial_status`**.
3. **Macro / micro deduplication (reporting only):** Build the set **`childCohortIds`** = every **`id`** appearing in **`cohort.micro_cohorts`** across **all** remaining student rows (macros list their micros here). **Remove** any student row whose **`cohort.id`** is in **`childCohortIds`**. After this, the report lists **one line per logical program** for nested setups: the **macro** row stays; **micro** rows that are children of another enrolled cohort **drop out**. Do **not** mention those dropped micro cohorts as separate courses. When fetching tasks / **`history_log`**, use the **macro** cohort id/slug for rows you kept (tasks may still be stored per real cohort in the DB—if tasks for a micro do not appear under the macro filter, fetch tasks once per **reported** cohort id the product uses; prefer one parent cohort when the API returns tasks under the macro only).
4. For **each** remaining student cohort, read **`cohort.never_ends`**:
   - If **`false`**: summarize progress using **`cohort.current_day`**, **`cohort.current_module`**, **`educational_status`**, then enrich with tasks from step 5.
   - If **`true`**: summarize progress from **tasks** (step 5) and optionally **`history_log`** (step 6). **Do not** lead with cohort **`current_day`** / **`current_module`** as “how far you are” in the program.
5. **Tasks per cohort (paginate):** call **`GET /v1/assignment/user/me/task`** with query **`cohort=<cohort_id_or_slug>`** for each **reported** cohort after deduplication. Repeat with **`offset`** / **`limit`** until **`next`** is null (or use total from headers if documented for this endpoint). Count rows by **`task_status`** (e.g. `PENDING`, `DONE`) and **`revision_status`** where relevant (e.g. projects). If the `CohortUser` response already includes `completion`, use its percentages instead of inventing a syllabus denominator. If tasks are attached to a **micro** cohort id that you hid from the report, you may need a **second** task pass with **`cohort=<micro_id>`** only when the macro-filtered list is empty but the student clearly has work in that micro; merge counts **under the macro** in the narrative without listing the micro as a separate course.
6. **Optional:** call **`GET /v1/admissions/me/cohort/<cohort_id>/user/log`** for that cohort’s **`history_log`** snapshot, or **`GET /v1/admissions/me/cohort/user/log`** for all cohorts. Use **`delivered_assignments`** / **`pending_assignments`** as a secondary view; if they conflict with step 5, **trust step 5**. Prefer logs for **reported** (macro) cohort ids; omit separate callouts for micro ids you deduplicated away unless merging into the parent summary.

## Endpoints

### 1. Current user with cohort memberships

- **Method / path:** `GET /v1/admissions/user/me`
- **Headers:** `Authorization: Token <token>`; optional `Accept-Language: <lang>`
- **Response (subset):** Top-level user fields plus **`cohorts`** array.

**Example response (subset — one student cohort):**

```json
{
  "id": 42,
  "email": "student@example.com",
  "username": "student42",
  "cohorts": [
    {
      "id": 901,
      "role": "STUDENT",
      "finantial_status": "UP_TO_DATE",
      "educational_status": "ACTIVE",
      "created_at": "2025-01-10T12:00:00Z",
      "cohort": {
        "id": 9,
        "slug": "web-self-paced-01",
        "name": "Web Self Paced",
        "kickoff_date": "2025-01-15T00:00:00Z",
        "ending_date": null,
        "never_ends": true,
        "current_day": 3,
        "current_module": 1,
        "stage": "STARTED",
        "academy": { "id": 1, "name": "4Geeks", "slug": "4geeks" },
        "syllabus_version": { "id": 5, "version": "1.0", "syllabus": { "id": 2, "slug": "full-stack" } },
        "micro_cohorts": [],
        "cohorts_order": null,
        "intro_video": null,
        "color": null,
        "is_hidden_on_prework": false,
        "available_as_saas": false,
        "enable_assessments_telemetry": false,
        "shortcuts": []
      }
    }
  ]
}
```

### 2. My tasks for a cohort (paginated)

- **Method / path:** `GET /v1/assignment/user/me/task`
- **Headers:** `Authorization: Token <token>`
- **Query:** **`cohort`** (required for per-cohort progress): cohort **id** or **slug** (comma-separated not needed for one cohort). Optional: **`task_status`**, **`revision_status`**, **`task_type`**. Pagination: **`limit`** (default 20), **`offset`** (default 0).
- **Response:** Paginated envelope when applicable: **`count`**, **`first`**, **`next`**, **`previous`**, **`last`**, **`results`**; list items include at least **`id`**, **`title`**, **`task_status`**, **`revision_status`**, **`task_type`**, **`associated_slug`**, **`cohort`**.

**Example request:**

```http
GET /v1/assignment/user/me/task?cohort=web-self-paced-01&limit=50&offset=0
Authorization: Token <token>
```

**Example `results` item (shape):**

```json
{
  "id": 5001,
  "title": "Landing page",
  "task_status": "DONE",
  "associated_slug": "landing-page",
  "description": "",
  "revision_status": "APPROVED",
  "github_url": "https://github.com/student42/landing",
  "live_url": null,
  "task_type": "PROJECT",
  "opened_at": null,
  "read_at": null,
  "reviewed_at": null,
  "delivered_at": "2025-02-01T10:00:00Z",
  "cohort": { "id": 9, "slug": "web-self-paced-01", "name": "Web Self Paced" },
  "created_at": "2025-01-20T08:00:00Z",
  "updated_at": "2025-02-01T10:00:00Z"
}
```

### 3. Optional — cohort user history log

- **Method / path:** `GET /v1/admissions/me/cohort/user/log` (all memberships) or **`GET /v1/admissions/me/cohort/<cohort_id>/user/log`** (one cohort)
- **Headers:** `Authorization: Token <token>`
- **Response (single cohort):** `{ "cohort": { "id", "slug" }, "history_log": { ... } }` where **`history_log`** is a JSON object (may include **`delivered_assignments`** and **`pending_assignments`** as arrays of `{ "id", "type" }`, plus other keys such as attendance-related data when present).

**Example `history_log` fragment:**

```json
{
  "delivered_assignments": [{ "id": 5001, "type": "PROJECT" }],
  "pending_assignments": [{ "id": 5002, "type": "EXERCISE" }]
}
```

## Edge Cases

- **`user/me` `cohorts`:** memberships with **`educational_status`** `DROPPED` or `SUSPENDED` are **excluded** from the list. Do not claim the student is still active in those.
- **Non-student roles:** same user may appear as **TEACHER** / **ASSISTANT** in other `cohorts` rows; filter **`role === "STUDENT"`** for this skill’s scope.
- **`history_log` vs tasks:** if counts differ, prefer **`user/me/task`** as source of truth for live status.
- **Empty tasks:** student may have no synced tasks yet; say “no tasks returned” instead of guessing progress.
- **Macro / micro enrollment overlap:** after step 3, **do not** surface micro cohorts that were removed as separate courses. If **`micro_cohorts`** on a kept row is empty but the student was only enrolled in a micro (no parent in `cohorts`), keep that cohort. If **`micro_cohorts`** in the API does not list a child you know exists, deduplication cannot hide it—only apply removal when **`cohort.id`** appears in **`micro_cohorts`** of **another** row in the same **`user/me`** response.

## Checklist

1. [ ] Used **`GET /v1/admissions/user/me`**, filtered **`cohorts`** to **`STUDENT`**, and **deduplicated micro cohorts** hidden under an enrolled macro (step 3).
2. [ ] Branched progress explanation on **`cohort.never_ends`** per the decision table.
3. [ ] Fetched **all pages** of **`GET /v1/assignment/user/me/task?cohort=…`** when summarizing tasks.
4. [ ] Did not use cohort **`current_day`** / **`current_module`** as the primary signal when **`never_ends`** is **true**.
5. [ ] Treated **`history_log`** as optional and possibly stale when compared to tasks.
