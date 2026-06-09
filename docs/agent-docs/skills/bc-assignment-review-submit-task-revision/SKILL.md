---
name: bc-assignment-review-submit-task-revision
description: Use when staff or teachers review **PROJECT** syllabus tasks via the API (discover queue, load asset `config` from the registry, submit `PUT` with `revision_status` and feedback). Do NOT use for `EXERCISE`, `LESSON`, or `QUIZ` tasks, for capstone `FinalProject` flows, for implementing assignment code, or for Rigobot CodeRevision-only workflows.
requires: []
---

# Skill: Review PROJECT syllabus task and submit revision

## When to Use

- Load when the task is to **find PROJECT assignments awaiting review**, interpret **`learn.json`**-derived expectations from **`GET /v1/registry/asset/`**, and **persist** teacher outcome with **`PUT /v1/assignment/task/{id}`**.
- Use **only** when **`task_type`** is **`PROJECT`** after loading the task row.
- Do NOT use for **`EXERCISE`**, **`LESSON`**, or **`QUIZ`** tasks, **`FinalProject`** endpoints, building assignment features in code, or **telemetry/CodeRevision** as the primary outcome.

## Concepts

- **`associated_slug`**: Syllabus asset slug on the **`Task`**; use it with **`GET /v1/registry/asset/{slug}`** to read **`config`** (synced **`learn.json`**). Full field semantics: [reference/learnpack-configuration.md](reference/learnpack-configuration.md).
- **`revision_status`**: **`PENDING`** (awaiting teacher), **`APPROVED`**, **`REJECTED`**, **`IGNORED`**. There is **no separate HTTP route** to “ignore” — use **`PUT`** with **`revision_status`: `"IGNORED"`**.
- **Teacher queue**: Filter list **`GET`**s with **`revision_status=PENDING`**, **`task_status=DONE`**, **`task_type=PROJECT`**. Order **oldest delivery first** with **`sort=delivered_at`** on academy/cohort lists.
- **Solution references (optional):** In **`GET /v1/registry/asset/{slug}`**, check **`solution_url`**, **`solution_video_url`**, and **`with_solutions`**. Treat them as optional guidance links only; primary review contract remains **`readme_url`** + **`config`**.
- **`AssetContext` (optional LLM context):** Use **`GET /v1/registry/asset/{asset_id}/context`** to retrieve **`ai_context`** plus **`status`**. This is generated asynchronously and may return **`PROCESSING`** first.

## Workflow

1. **Discover** (skip if the user already has **`task_id`** and **`user_id`**): Call **`GET /v1/assignment/academy/task`** or **`GET /v1/assignment/academy/cohort/{cohort_id}/task`** with **`Authorization`**, **`Academy`** header, **`task_type=PROJECT`**, **`task_status=DONE`**, **`revision_status=PENDING`**, **`sort=delivered_at`**, **`limit`**, **`offset`**. Process **earliest `delivered_at` first**. Prefer academy/cohort routes for pagination and FIFO; **`GET /v1/assignment/task/`** uses fixed **`created_at`** sort and is **not** FIFO by **`delivered_at`**.
2. **Load task detail:** **`GET /v1/assignment/user/{user_id}/task/{task_id}`** with **`Authorization`**. If **`task_type`** is not **`PROJECT`**, **stop** this skill.
3. **Load asset contract:** **`GET /v1/registry/asset/{associated_slug}`**. Read **`id`**, **`config`**, **`graded`**, **`asset_type`**, repo/readme URLs, and optional solution references (**`solution_url`**, **`solution_video_url`**, **`with_solutions`**). Use [reference/learnpack-configuration.md](reference/learnpack-configuration.md) when interpreting **`config`** keys.
4. **Load optional AI context:** **`GET /v1/registry/asset/{asset_id}/context`**. If **`status=DONE`**, use **`ai_context`** as additional context for the reviewer. If **`status=PROCESSING`**/**`PENDING`**, continue review using **`readme_url`** + **`config`** (retry later if needed).
5. **Review** the student delivery (**`github_url`**, **`live_url`**, and/or other submitted URLs/files) against project expectations from **`config`** and asset delivery constraints (**`delivery_instructions`**, **`delivery_formats`**, **`delivery_regex_url`** when present). Use **`ai_context`** only as support, not as source of truth.
6. **Draft** teacher feedback for **`description`** — **max 450 characters** (API limit on **`Task.description`**).
7. **Submit:** **`PUT /v1/assignment/task/{task_id}`** with **`revision_status`** (**`APPROVED`**, **`REJECTED`**, **`PENDING`**, or **`IGNORED`**) and **`description`** as needed. Same endpoint for **ignoring** — see **Ignoring projects** under Edge Cases and Endpoints.

## Endpoints

Send **`Accept-Language`** (e.g. **`en`**, **`es`**) if the client should receive translated validation or error messages where the API supports it.

### 1. List tasks (academy) — paginated

- **Method / path:** **`GET /v1/assignment/academy/task`**
- **Headers:** **`Authorization: Token <token>`**, **`Academy: <academy_id>`** (required for this academy-scoped route; staff capability **`read_assignment`**).
- **Query (discovery queue):** **`task_type=PROJECT`**, **`task_status=DONE`**, **`revision_status=PENDING`**, **`sort=delivered_at`** (mandatory for oldest-first), **`limit`**, **`offset`**. Optional: **`user_id`**, **`cohort`**, **`associated_slug`**, **`cohort_live_meeting`** (**`true|false`**, checks **`cohort.online_meeting_url`**).
- **Response:** Paginated envelope per API conventions: **`count`**, **`first`**, **`next`**, **`previous`**, **`last`**, **`results`** (array of tasks). Each task matches the shape in example (2).

**Example request:**

```http
GET /v1/assignment/academy/task?task_type=PROJECT&task_status=DONE&revision_status=PENDING&sort=delivered_at&limit=20&offset=0
Authorization: Token 75126f11546bd9caabb1165ad5ce2c00683d8932
Academy: 1
```

**Example response (abbreviated `results[0]`):**

```json
{
  "count": 3,
  "first": "https://breathecode.test/v1/assignment/academy/task?limit=20&offset=0",
  "next": null,
  "previous": null,
  "last": "https://breathecode.test/v1/assignment/academy/task?limit=20&offset=0",
  "results": [
    {
      "id": 8842,
      "title": "Build a landing page",
      "task_status": "DONE",
      "associated_slug": "react-landing-page",
      "description": "",
      "revision_status": "PENDING",
      "github_url": "https://github.com/student-42/react-landing-page",
      "live_url": "https://student-42.github.io/react-landing-page",
      "task_type": "PROJECT",
      "user": { "id": 42, "first_name": "Ada", "last_name": "Lovelace" },
      "opened_at": null,
      "read_at": null,
      "reviewed_at": null,
      "delivered_at": "2026-04-28T14:22:11Z",
      "cohort": { "id": 9, "name": "Web PT 99", "slug": "web-pt-99" },
      "assignment_telemetry": null,
      "created_at": "2026-02-01T10:00:00Z",
      "updated_at": "2026-04-28T14:22:12Z"
    }
  ]
}
```

### 2. List tasks (cohort) — paginated

- **Method / path:** **`GET /v1/assignment/academy/cohort/{cohort_id}/task`**
- **Headers:** **`Authorization`**, **`Academy`** (same as academy task list).
- **Query:** Same discovery pattern: **`task_type=PROJECT`**, **`task_status=DONE`**, **`revision_status=PENDING`**, **`sort=delivered_at`**, **`limit`**, **`offset`**. Optional: **`student`**, **`educational_status`**, **`like`**, **`cohort_live_meeting`** (**`true|false`**, checks **`cohort.online_meeting_url`**), etc.
- **Response:** Same paginated shape as (1).

### 3. Teacher task list — not paginated

- **Method / path:** **`GET /v1/assignment/task/`**
- **Headers:** **`Authorization`** (user must have **ProfileAcademy**).
- **Query:** **`task_type=PROJECT`**, **`revision_status=PENDING`**, **`task_status=DONE`**, optional **`cohort_live_meeting=true|false`** and other filters as needed. **No `sort` parameter** — server orders by **`created_at`** ascending (not **`delivered_at`** FIFO).
- **Response:** **Plain JSON array** of tasks (not the paginated envelope). Prefer (1) or (2) for large cohorts and **oldest-first by delivery**.

### 4. Single task

- **Method / path:** **`GET /v1/assignment/user/{user_id}/task/{task_id}`**
- **Headers:** **`Authorization`**
- **Response:** One task object (same fields as list items). Confirm **`task_type":"PROJECT`** before review.

**Example response:**

```json
{
  "id": 8842,
  "title": "Build a landing page",
  "task_status": "DONE",
  "associated_slug": "react-landing-page",
  "description": "",
  "revision_status": "PENDING",
  "github_url": "https://github.com/student-42/react-landing-page",
  "live_url": "https://student-42.github.io/react-landing-page",
  "task_type": "PROJECT",
  "user": { "id": 42, "first_name": "Ada", "last_name": "Lovelace" },
  "opened_at": null,
  "read_at": null,
  "reviewed_at": null,
  "delivered_at": "2026-04-28T14:22:11Z",
  "cohort": { "id": 9, "name": "Web PT 99", "slug": "web-pt-99" },
  "assignment_telemetry": null,
  "created_at": "2026-02-01T10:00:00Z",
  "updated_at": "2026-04-28T14:22:12Z"
}
```

### 5. Registry asset (project brief / `config`)

- **Method / path:** **`GET /v1/registry/asset/{asset_slug}`**
- **Headers:** Optional **`Authorization`**; **`Accept-Language`** for translated not-found messages when applicable.
- **Response:** Asset payload including **`config`** (synced **`learn.json`**), **`asset_type`**, **`graded`**, URLs, and optional solution references (**`solution_url`**, **`solution_video_url`**, **`with_solutions`**).

**Example response (subset):**

```json
{
  "slug": "react-landing-page",
  "title": "React landing page",
  "asset_type": "PROJECT",
  "graded": true,
  "status": "PUBLISHED",
  "readme_url": "https://github.com/breatheco-de/react-landing-page/blob/main/README.md",
  "url": "https://github.com/breatheco-de/react-landing-page",
  "solution_url": "https://github.com/breatheco-de/react-landing-page-solution",
  "solution_video_url": "https://www.youtube.com/watch?v=example",
  "with_solutions": true,
  "config": {
    "slug": "react-landing-page",
    "title": "React landing page",
    "projectType": "project",
    "grading": "incremental",
    "localhostOnly": false,
    "gitpod": true,
    "template_url": "self",
    "technologies": ["react", "javascript"]
  }
}
```

### 6. Asset context (optional, LLM-oriented)

- **Method / path:** **`GET /v1/registry/asset/{asset_id}/context`**
- **Headers:** Optional **`Authorization`**.
- **Response:** **`id`**, nested **`asset`**, **`ai_context`**, **`status`** (**`PENDING`**, **`PROCESSING`**, **`DONE`**, **`ERROR`**), and **`status_text`**.
- **Behavior:** If context does not exist yet, API may return **`PROCESSING`** while generating in background. Do not block the review flow; proceed with **`readme_url`** + **`config`**.

**Example response (ready):**

```json
{
  "id": 1203,
  "asset": { "id": 778, "slug": "react-landing-page", "title": "React landing page" },
  "ai_context": "This PROJECT called 'React landing page' is written in English. ...",
  "status": "DONE",
  "status_text": null
}
```

### 7. Submit review (approve)

- **Method / path:** **`PUT /v1/assignment/task/{task_id}`**
- **Headers:** **`Authorization`** (teacher/assistant in student cohort or **`ProfileAcademy`** staff for that academy).
- **Body:** **`revision_status`**, **`description`** (teacher feedback, ≤ 450 chars). **`task_status`** must remain **`DONE`** to approve — do not approve while delivery is still **`PENDING`**.

**Example request:**

```json
{
  "revision_status": "APPROVED",
  "description": "Clean structure and README. Approved."
}
```

**Example response (subset):**

```json
{
  "id": 8842,
  "title": "Build a landing page",
  "task_status": "DONE",
  "associated_slug": "react-landing-page",
  "description": "Clean structure and README. Approved.",
  "revision_status": "APPROVED",
  "github_url": "https://github.com/student-42/react-landing-page",
  "live_url": "https://student-42.github.io/react-landing-page",
  "task_type": "PROJECT",
  "reviewed_at": "2026-05-04T09:15:00Z",
  "delivered_at": "2026-04-28T14:22:11Z"
}
```

### 8. Submit review (reject)

**Example request:**

```json
{
  "revision_status": "REJECTED",
  "description": "Missing responsive navbar per README. Fix and resubmit."
}
```

### 9. Ignore project (no separate ignore endpoint)

There is **no** **`…/ignore`** route. Use the **same** **`PUT /v1/assignment/task/{task_id}`** with **`revision_status`: `"IGNORED"`**.

**Example request:**

```json
{
  "revision_status": "IGNORED",
  "description": "Optional note: cohort policy auto-skips manual review for this delivery."
}
```

**Example response (subset):**

```json
{
  "id": 8842,
  "revision_status": "IGNORED",
  "description": "Optional note: cohort policy auto-skips manual review for this delivery.",
  "reviewed_at": "2026-05-04T09:20:00Z",
  "task_status": "DONE",
  "task_type": "PROJECT"
}
```

## Edge Cases

- **Non-PROJECT task:** If **`task_type`** is **`EXERCISE`**, **`LESSON`**, or **`QUIZ`**, stop — this skill does not apply.
- **Empty queue:** **`results`** empty or **`count`: 0** — widen filters or confirm academy/cohort scope and headers.
- **Auto-ignore on delivery:** If academy feature **`certificate.auto_ignore_projects_on_delivery`** is enabled, a **student** completing **`DONE`** on a **PROJECT** may receive **`revision_status=IGNORED`** without a teacher **`PUT`**. Do **not** change **`IGNORED`** to **`APPROVED`**/**`REJECTED`** unless the user explicitly asks.
- **Listing ignored tasks:** Default pending queue uses **`revision_status=PENDING`**. Tasks already **`IGNORED`** require **`revision_status=IGNORED`** in the list query.
- **Null `delivered_at`:** With **`sort=delivered_at`**, nulls may sort first or last depending on the database; normalize client-side if ordering looks wrong.
- **`GET /v1/assignment/task/`:** Cannot pass **`sort=delivered_at`**; for strict FIFO by submission time use academy or cohort list endpoints.
- **Asset context not ready:** **`GET /v1/registry/asset/{asset_id}/context`** may return **`PENDING`**/**`PROCESSING`**. Continue review with **`readme_url`** + **`config`** and treat **`ai_context`** as optional enrichment only.
- **Non-GitHub delivery:** Some projects are delivered with non-GitHub URLs (for example Drive or custom URL patterns) or file uploads. Do not auto-reject only because **`github_url`** is empty; validate against asset delivery contract (**`delivery_instructions`**, **`delivery_formats`**, **`delivery_regex_url`**) and provided evidence.
- **Permissions:** If **`PUT`** returns permission errors, confirm the caller is teacher/assistant for the student’s cohort or staff on **`ProfileAcademy`** for the student’s academy.

## Checklist

1. [ ] Confirmed **`task_type`** is **`PROJECT`** for the task being reviewed.
2. [ ] Discovered queue with **`task_type=PROJECT`**, **`task_status=DONE`**, **`revision_status=PENDING`**, **`sort=delivered_at`** (when listing), or skipped discovery when **`task_id`** is known.
3. [ ] Loaded **`GET /v1/registry/asset/{associated_slug}`** and used **`config`** / [reference/learnpack-configuration.md](reference/learnpack-configuration.md) for expectations.
4. [ ] Optionally loaded **`GET /v1/registry/asset/{asset_id}/context`** and used **`ai_context`** only as supporting context.
5. [ ] Feedback in **`description`** is **≤ 450 characters** before **`PUT`**.
6. [ ] Called **`PUT /v1/assignment/task/{task_id}`** with correct **`revision_status`** (including **`IGNORED`** only via this **`PUT`**, not a separate URL).
7. [ ] Did not override **`IGNORED`** from auto-ignore without explicit user instruction.
