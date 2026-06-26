---
name: bc-admissions-create-cohort
description: Use when creating a new academy cohort (single certificate or macro with micro cohorts) via the API; do NOT use for listing/updating cohorts, enrolling students, or issuing certificates.
requires:
  - bc-certificate-manage-and-assign-specialties
---

# Skill: Create a Cohort

## When to Use

Use this skill when the user asks to **start a new class**, **create a cohort**, or **create a macro cohort** with multiple certificates. All steps are done via the API (`POST`/`PUT`). Do **not** use when the user only wants to list or read cohorts, update an existing cohort's details (unless linking micro cohorts as part of creation), enroll students, or issue certificates.

## Concepts

- **Single-certificate cohort**: One syllabus, one certificate at program end. Created with a single `POST /v1/admissions/academy/cohort` and no `micro_cohorts`.
- **Macro cohort**: A container cohort that links multiple **micro cohorts** (each micro cohort maps to one certificate milestone). A cohort is a macro when `micro_cohorts` is non-empty on create.
- **Never-ending micro cohort**: A reusable template cohort (`never_ends: true`, no `ending_date`) used as the enrollment target for a certificate track. The UI prefers reusing these instead of creating dated micro cohorts.
- **Syllabus string**: Always `"syllabus_slug.v{version}"` or `"syllabus_slug.vlatest"`. Version 1 is marketing-only and cannot be assigned to cohorts.
- **Ending strategy**: Every cohort must have `ending_date` **or** `never_ends: true`, never both.
- **Display order**: Macro cohorts store micro cohort order in `cohorts_order` as a comma-separated string of cohort IDs (e.g. `"1277,1278"`).
- **Macro syllabus overrides**: The macro cohort's `syllabus_version.json` may include keys like `{micro-slug}.v{version}` or ordered `N:{micro-slug}.v{version}` to customize micro syllabi per program. See [SYLLABUS.md — Macro cohort syllabus overrides](../../SYLLABUS.md#macro-cohort-syllabus-overrides).

## Workflow

### Step 0 — Verify prerequisites (both paths)

1. Confirm the academy exists and you have `crud_cohort` capability.
2. Confirm the target syllabus exists with a **published version ≥ 2**.
3. For macro micro cohorts: confirm each micro syllabus is linked to a **Specialty**. If not, load `bc-certificate-manage-and-assign-specialties` and link the syllabus before continuing.

If any prerequisite fails, stop and fix it before creating the cohort.

### Step 1 — Choose cohort type (client-side decision, no API field)

Ask the user or infer from the request:

- **Single certificate** — students earn one certificate upon completing the full program.
- **Macro cohort (multiple certificates)** — students earn a certificate at each milestone (micro cohort). Set `available_as_saas: true` on the macro cohort (the UI requires this; the API defaults from the academy if omitted).

### Path A — Single certificate (UI: Syllabus → Cohort Details)

1. **List syllabi.** Call `GET /v1/admissions/academy/{academy_id}/syllabus?owner=me` with `Authorization` and `Academy: <academy_id>`. Pick the syllabus slug from `results`.
2. **List versions.** Call `GET /v1/admissions/academy/{academy_id}/syllabus/{slug}/version`. Pick a published version ≥ 2 (or use `.vlatest` on create).
3. **Verify specialty (recommended).** Call `GET /v1/certificate/academy/specialty?syllabus_slug={slug}`. If the list is empty, link the syllabus to a specialty using `bc-certificate-manage-and-assign-specialties`, then continue.
4. **Collect cohort details** from the user: `name`, `slug`, `kickoff_date`, ending strategy (`ending_date` or `never_ends`), optional `online_meeting_url`, optional `available_as_saas`, optional `schedule`.
5. **Create the cohort.** Call `POST /v1/admissions/academy/cohort` with `syllabus: "{slug}.v{version}"` (or `.vlatest`). Save the returned `id` and `slug`.

### Path B — Macro cohort (UI: Type → Macro Syllabus → Certificates → Cohort Details)

1. **Select macro syllabus.** Use the same list/version endpoints from Path A steps 1–2. Pick the macro syllabus slug and version.
2. **Derive suggested certificate order.** Read the macro syllabus version JSON. Keys like `web-ui-fundamentals.v2` or `0:web-ui-fundamentals.v2` indicate which micro syllabi (and order) the program expects. Use this list as the default order for certificate configuration.
3. **Configure certificates — reuse existing never-ending micro cohorts first.** For each micro syllabus in the suggested order:
   - Call `GET /v1/certificate/academy/specialty?syllabus_slug={micro_slug}` to confirm the specialty exists.
   - Call `GET /v1/admissions/academy/cohort?syllabus={micro_slug}&ending_date_isnull=true` (paginated) to find reusable template cohorts.
   - Pick one cohort `id` per certificate milestone. Save each `id` in display order.
4. **Fallback — create missing micro cohorts.** Only when no reusable cohort exists for a micro syllabus, call `POST /v1/admissions/academy/cohort` once per missing certificate with that micro syllabus, `never_ends: true`, and `available_as_saas: true`. Save each returned `id`.
5. **Collect macro cohort details** from the user: `name`, `slug`, macro `syllabus`, `kickoff_date`, ending strategy, optional `online_meeting_url`, and **`available_as_saas: true`**.
6. **Create the macro cohort.** Call `POST /v1/admissions/academy/cohort` with `micro_cohorts` set to the list of micro cohort IDs from steps 3–4 and `cohorts_order` set to a comma-separated string of those IDs in display order (e.g. `"1277,1278"`). Save the returned macro `id` and `slug`.
7. **Optional — link or change micro cohorts later.** If the macro was created without `micro_cohorts`, call `PUT /v1/admissions/academy/cohort/{cohort_id}` with `micro_cohorts` and optionally `cohorts_order`.
8. **Optional — sync users after linking.** If users were already enrolled in the macro before micro cohorts were linked, they are not automatically added to new micro cohorts. Ask affected users to call `POST /v1/admissions/me/micro-cohorts/sync/{macro_slug}`, or inform the user that a bulk sync may be required.
9. **Optional — macro syllabus overrides.** To customize micro syllabi for this program, edit the macro `SyllabusVersion` JSON with `{micro_slug}.v{version}` blocks (see [SYLLABUS.md](../../SYLLABUS.md#macro-cohort-syllabus-overrides)). Verify with `GET /v1/admissions/academy/{academy_id}/syllabus/{syllabus_slug}/version/{version}?macro-cohort={macro_slug}`.

### Step final — Verify creation (both paths)

Call `GET /v1/admissions/academy/cohort/{id_or_slug}` and confirm `name`, `slug`, `syllabus_version`, dates, and (for macros) `micro_cohorts` match the intent.

## Endpoints

All `/academy/` endpoints require the **`Academy`** header with the academy ID. List endpoints are **paginated** (`limit`, `offset`; response has `count` and `results`). Send **`Accept-Language`** (e.g. `en`, `es`) to receive translated error messages.

| Action | Method | Path | Capability | Used in |
|--------|--------|------|------------|---------|
| List syllabi | GET | `/v1/admissions/academy/{academy_id}/syllabus` | `read_syllabus` | Both |
| List syllabus versions | GET | `/v1/admissions/academy/{academy_id}/syllabus/{slug}/version` | `read_syllabus` | Both |
| List specialties | GET | `/v1/certificate/academy/specialty` | `read_certificate` | Both |
| List cohorts (find templates) | GET | `/v1/admissions/academy/cohort` | `read_all_cohort` | Macro |
| Create cohort | POST | `/v1/admissions/academy/cohort` | `crud_cohort` | Both |
| Update cohort (link micros) | PUT | `/v1/admissions/academy/cohort/{cohort_id}` | `crud_cohort` | Macro |
| Get cohort (verify) | GET | `/v1/admissions/academy/cohort/{id_or_slug}` | `read_all_cohort` | Both |
| Sync user into micro cohorts | POST | `/v1/admissions/me/micro-cohorts/sync/{macro_slug}` | (authenticated user) | Macro edge case |
| Get micro syllabus with macro merge | GET | `/v1/admissions/academy/{academy_id}/syllabus/{slug}/version/{version}?macro-cohort={macro_slug}` | `read_syllabus` | Macro optional |

**List syllabi — response (GET, paginated subset):**
```json
{
  "count": 12,
  "first": null,
  "next": null,
  "previous": null,
  "last": null,
  "results": [
    {
      "id": 5,
      "slug": "full-stack-web-development",
      "name": "Full Stack Web Development",
      "duration_in_hours": 400
    }
  ]
}
```

**List syllabus versions — response (GET, paginated subset):**
```json
{
  "count": 2,
  "results": [
    {
      "id": 10,
      "version": 2,
      "status": "PUBLISHED",
      "syllabus": {"id": 5, "slug": "full-stack-web-development"}
    }
  ]
}
```

**List specialties — response (GET):**
```json
[
  {
    "id": 3,
    "slug": "full-stack-web-development",
    "name": "Full Stack Web Development",
    "syllabuses": [{"id": 5, "slug": "full-stack-web-development"}]
  }
]
```

**List cohorts (find never-ending templates) — request query:**
```
GET /v1/admissions/academy/cohort?syllabus=web-ui-fundamentals&ending_date_isnull=true&limit=20&offset=0
```

**List cohorts — response (GET, paginated subset):**
```json
{
  "count": 1,
  "results": [
    {
      "id": 1277,
      "slug": "web-ui-fundamentals-never-ending",
      "name": "Web UI Fundamentals With Tailwind",
      "never_ends": true,
      "ending_date": null,
      "syllabus_version": {
        "version": 2,
        "syllabus": {"slug": "web-ui-fundamentals"}
      }
    }
  ]
}
```

**Create single-certificate cohort — request (POST `/v1/admissions/academy/cohort`):**
```json
{
  "name": "Full Stack - Miami 2026",
  "slug": "full-stack-miami-2026",
  "syllabus": "full-stack-web-development.v2",
  "kickoff_date": "2026-06-05T12:30:00Z",
  "ending_date": "2026-12-15T18:00:00Z",
  "never_ends": false,
  "online_meeting_url": "https://zoom.us/j/123456789",
  "available_as_saas": true,
  "stage": "INACTIVE"
}
```

**Create single-certificate cohort (never-ending) — request:**
```json
{
  "name": "Self-Paced Web Dev",
  "slug": "self-paced-web-dev",
  "syllabus": "web-dev-basics.vlatest",
  "kickoff_date": "2026-06-05T12:30:00Z",
  "never_ends": true,
  "online_meeting_url": "https://meet.google.com/abc-defg-hij",
  "available_as_saas": true
}
```

**Create micro cohort (fallback, macro path) — request (POST `/v1/admissions/academy/cohort`):**
```json
{
  "name": "Web UI Fundamentals With Tailwind",
  "slug": "web-ui-fundamentals-never-ending",
  "syllabus": "web-ui-fundamentals.v2",
  "kickoff_date": "2020-01-01T00:00:00Z",
  "never_ends": true,
  "available_as_saas": true,
  "stage": "STARTED"
}
```
Save the returned `id` (e.g. 1277) for the macro's `micro_cohorts`.

**Create macro cohort — request (POST `/v1/admissions/academy/cohort`):**
```json
{
  "name": "Full Stack - Miami 2026",
  "slug": "full-stack-miami-2026",
  "syllabus": "full-stack-web-development.v2",
  "kickoff_date": "2026-06-05T12:30:00Z",
  "ending_date": "2027-06-05T18:00:00Z",
  "never_ends": false,
  "online_meeting_url": "https://zoom.us/j/123456789",
  "available_as_saas": true,
  "micro_cohorts": [1277, 1278, 1279],
  "cohorts_order": "1277,1278,1279"
}
```

**Create cohort — response (201, single or macro):**
```json
{
  "id": 1280,
  "name": "Full Stack - Miami 2026",
  "slug": "full-stack-miami-2026",
  "syllabus_version": {
    "id": 10,
    "version": 2,
    "syllabus": {"slug": "full-stack-web-development"}
  },
  "kickoff_date": "2026-06-05T12:30:00Z",
  "ending_date": "2027-06-05T18:00:00Z",
  "never_ends": false,
  "stage": "INACTIVE",
  "available_as_saas": true,
  "micro_cohorts": [1277, 1278, 1279],
  "cohorts_order": "1277,1278,1279"
}
```
Always store `id` and `slug` from the response.

**Update cohort (link micro cohorts) — request (PUT `/v1/admissions/academy/cohort/{cohort_id}`):**
```json
{
  "micro_cohorts": [1277, 1278],
  "cohorts_order": "1277,1278"
}
```

## Edge Cases

- **`missing-syllabus-field`:** Include `syllabus` in the POST body using `"slug.v{version}"` format.
- **`cohort-without-ending-date-and-never-ends`:** Set `ending_date` or `never_ends: true` — one is required.
- **`cohort-with-ending-date-and-never-ends`:** Remove one — they are mutually exclusive.
- **`assigning-a-syllabus-version-1`:** Use version ≥ 2 or `.vlatest` (resolves to highest published version).
- **`micro-cohort-syllabus-must-have-specialty`:** The micro cohort's syllabus has no linked specialty. Link it via `bc-certificate-manage-and-assign-specialties`, then retry.
- **`micro-cohort-syllabus-required`:** A micro cohort ID in `micro_cohorts` has no syllabus. Pick a different cohort or create one with a valid syllabus.
- **No reusable never-ending cohort found for a micro syllabus:** Create a micro cohort with `never_ends: true` and `available_as_saas: true` (Path B step 4), then use its `id`.
- **Micro cohort IDs from another academy:** All IDs in `micro_cohorts` must belong to the same academy. Re-list cohorts scoped to the current academy.
- **Users already in macro before micro cohorts linked:** New micro cohorts do not auto-enroll existing macro users. Inform the user about the sync endpoint or bulk sync.
- **`available_as_saas` omitted on macro:** API defaults to the academy's setting. Set `available_as_saas: true` explicitly for macro cohorts.
- **Academy cohort list has no `never_ends` filter:** Use `ending_date_isnull=true` as a workaround to find template cohorts.

## Checklist

1. Verified academy, syllabus, and published version ≥ 2 exist.
2. Chose cohort type: single certificate (Path A) or macro (Path B).
3. **Path A:** Listed syllabus and version, verified specialty, collected details, and called `POST /v1/admissions/academy/cohort`.
4. **Path B:** Selected macro syllabus, derived certificate order from syllabus JSON, found or created never-ending micro cohorts, collected macro details, and called `POST` with `micro_cohorts` and `cohorts_order`.
5. Confirmed creation via `GET /v1/admissions/academy/cohort/{id_or_slug}`.
6. **Path B only:** If users were already in the macro before linking, informed the user about user sync.
7. **Path B optional:** If using macro syllabus overrides, verified merged JSON via `GET .../version/...?macro-cohort=...`.
