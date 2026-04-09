---
name: bc-certificate-manage-and-assign-specialties
description: Use when academy staff need to list or view certificate specialties, create or update academy-owned specialties, link a syllabus to a specialty, or assign a specialty to a student by issuing a certificate; do NOT use for listing a student's own certificates (use certificate me endpoint).
requires: []
---

# Skill: Manage and Assign Certificate Specialties

## When to Use

Use this skill when the user asks to **list or view academy specialties**, **see which specialties are offered** or **which syllabi a specialty uses**, to **create a new specialty**, **edit an existing specialty** (academy-owned), to **link a syllabus to a specialty**, or to **give a specialty to a student** (issue a certificate). Do **not** use for a student listing their own certificates (that is a different endpoint).

## Concepts

- **Specialty**: A certificate type (e.g. "Full-Stack Web Development"). In the API it is the certificate the student receives. A specialty can optionally **belong to an academy** (`academy_id`). Academy-owned specialties can be created and updated by staff with `crud_certificate`; global specialties (no academy) are read-only for academy staff. A specialty is linked to one or many syllabi via the **syllabuses** (ManyToMany); the response also includes `syllabus` (first of syllabuses) for compatibility.
- **Assigning a specialty to a student**: Issuing a certificate — creating a user-specialty record that states the student has completed the specialty. The certificate is tied to a cohort and the cohort's syllabus. The system picks a **single** specialty for that syllabus using **cohort academy first**, then **global** specialties (`academy_id` null): it uses a specialty that lists the cohort's syllabus in **syllabuses** and whose `academy_id` equals the cohort's academy; if none, it uses a global specialty that lists that syllabus. If neither exists, issuance fails with `missing-specialty`.
- **Syllabus–specialty link uniqueness**: For each syllabus, at most **one** specialty per **academy bucket** may list it: one specialty with `academy_id = A` (per academy), and at most **one** global specialty (`academy_id` null). Different academies may each have their own specialty linked to the same syllabus. This is enforced when linking via the API and when editing the M2M in Django admin.
- **Managing specialties**: Staff can **list** specialties, **create** academy-owned specialties (POST), **update** academy-owned specialties (PUT/PATCH when `specialty.academy_id` matches the request academy), and **link a syllabus to a specialty** (POST specialty/:id/syllabus, requires `crud_syllabus`). The source of truth for "which syllabi a specialty uses" is **syllabuses**; the response includes `syllabus` (first of syllabuses) and `syllabuses`.

## Workflow

1. **Create a specialty (academy-owned).** Call `POST /v1/certificate/academy/specialty` with `Authorization`, `Academy: <academy_id>`, and capability `crud_certificate`. Body: at least `name` and `slug`; optionally `description`, `logo_url`, `duration_in_hours`, `expiration_day_delta`, `status`. Response 201 with the created specialty (id, slug, name, status, academy, syllabus, syllabuses, created_at, updated_at).

2. **Update a specialty.** Call `PUT` or `PATCH /v1/certificate/academy/specialty/<specialty_id>` with `Authorization`, `Academy: <academy_id>`, and capability `crud_certificate`. Allowed only when the specialty's `academy_id` equals the request academy. Body: fields to update (name, slug, description, status, etc.). Response 200 with the updated specialty.

3. **Link a syllabus to a specialty.** Call `POST /v1/certificate/academy/specialty/<specialty_id>/syllabus` with `Authorization`, `Academy: <academy_id>`, and capability `crud_syllabus`. Body: `{ "syllabus_id": <id> }` or `{ "syllabus_slug": "<slug>" }`. Response 200 or 201 with the updated specialty (syllabuses list includes the newly linked syllabus). If another specialty in the **same bucket** (same `academy_id`, or both global) already links that syllabus, the API returns **400** with `detail` / slug `syllabus-specialty-already-linked`. If the syllabus is already linked **to this** specialty, the call is idempotent (200).

4. **List specialties offered by the academy.** Call `GET /v1/certificate/academy/specialty` with `Authorization` and `Academy: <academy_id>`. The list includes specialties linked via syllabi owned by the academy and specialties owned by the academy (`academy_id`). Response includes each specialty's id, slug, name, status, academy, syllabus (first of syllabuses), syllabuses. Use query `syllabus_slug=<slug>` to filter by syllabus, or `like=<text>` to search by name.

5. **Get one specialty.** Call `GET /v1/certificate/academy/specialty/<specialty_id>` with `Authorization` and `Academy: <academy_id>`. Response 200 with the full specialty object (or 404 if not found or not visible to the academy).

6. **Assign a specialty to one student (issue one certificate).** Call `POST /v1/certificate/cohort/<cohort_id>/student/<student_id>`. The student must be in that cohort with role STUDENT. The cohort must have a syllabus assigned; that syllabus must be in the specialty's **syllabuses**. Optional body: `{ "layout_slug": "default" }`. Response is 201 with the certificate (user_specialty) object. The student must meet graduation and financial rules (e.g. GRADUATED, FULLY_PAID or UP_TO_DATE, cohort ENDED if applicable).

7. **Issue certificates for an entire cohort.** Call `POST /v1/certificate/cohort/<cohort_id>` with `Authorization` and `Academy: <academy_id>`. Optional body: `{ "layout_slug": "default" }`. All students in that cohort (role STUDENT) receive a certificate for the cohort's specialty. The cohort must have a syllabus linked to a specialty (via syllabuses); cohort stage must be ENDED (or never_ends). Response is 201 with a list of certificate objects.

8. **List or filter issued certificates (academy).** Call `GET /v1/certificate/` (root) with `Authorization` and `Academy: <academy_id>`. Optional query: `user_id=<id>` or `like=<name>` to filter. Use this to verify who has been assigned which specialty.

**Prerequisite:** The cohort's syllabus must appear in a specialty's **syllabuses** for **that cohort's academy** (academy-owned specialty) or in a **global** specialty. If issuing fails with "Specialty has no Syllabus assigned" or "missing-specialty", link the syllabus to an appropriate specialty (POST specialty/:id/syllabus) — e.g. an academy-owned specialty for that academy, or a global one — then retry.

## Endpoints

| Action | Method | Path | Headers | Body / Query | Response |
|--------|--------|------|---------|--------------|----------|
| List academy specialties | GET | `/v1/certificate/academy/specialty` | `Authorization`, `Academy: <academy_id>` | Optional: `syllabus_slug=<slug>`, `like=<text>` | List of specialties (id, slug, name, status, academy, syllabus, syllabuses). |
| Create specialty | POST | `/v1/certificate/academy/specialty` | `Authorization`, `Academy: <academy_id>` | name, slug; optional: description, logo_url, duration_in_hours, expiration_day_delta, status | 201, specialty object. |
| Get one specialty | GET | `/v1/certificate/academy/specialty/<specialty_id>` | `Authorization`, `Academy: <academy_id>` | — | Specialty object or 404. |
| Update specialty | PUT / PATCH | `/v1/certificate/academy/specialty/<specialty_id>` | `Authorization`, `Academy: <academy_id>` | Fields to update | 200, specialty object. |
| Link syllabus to specialty | POST | `/v1/certificate/academy/specialty/<specialty_id>/syllabus` | `Authorization`, `Academy: <academy_id>` | syllabus_id or syllabus_slug | 200/201, specialty object; 400 `syllabus-specialty-already-linked` if another specialty in the same academy/global bucket already uses that syllabus. |
| Issue certificate for one student | POST | `/v1/certificate/cohort/<cohort_id>/student/<student_id>` | `Authorization`, `Academy: <academy_id>` | Optional; see request sample. | 201, certificate (user_specialty) object. |
| Issue certificates for cohort | POST | `/v1/certificate/cohort/<cohort_id>` | `Authorization`, `Academy: <academy_id>` | Optional; see request sample. | 201, list of certificate objects. |
| Get one student's certificate | GET | `/v1/certificate/cohort/<cohort_id>/student/<student_id>` | `Authorization`, `Academy: <academy_id>` | — | Certificate object or 404. |
| List academy certificates | GET | `/v1/certificate/` | `Authorization`, `Academy: <academy_id>` | Optional: `user_id=<id>`, `like=<name>`, `sort` | Paginated list of issued certificates. |
| Delete certificates (bulk) | DELETE | `/v1/certificate/` | `Authorization`, `Academy: <academy_id>` | Query: `id=1&id=2` (ids of user_specialty) | 204 No Content. |

**Capabilities:** `read_certificate` for GET (list and get one specialty, certificates). `crud_certificate` for create/update specialty and for certificate issuance/delete. **`crud_syllabus`** for linking a syllabus to a specialty.

**Create specialty — request (POST `/v1/certificate/academy/specialty`):**
```json
{
  "name": "Full-Stack Web Development",
  "slug": "full-stack",
  "description": "Complete full-stack program",
  "status": "ACTIVE"
}
```

**Create specialty — response (201):**
```json
{
  "id": 1,
  "slug": "full-stack",
  "name": "Full-Stack Web Development",
  "academy": {"id": 1, "slug": "academy-slug", "name": "Academy Name"},
  "syllabus": null,
  "syllabuses": [],
  "status": "ACTIVE",
  "created_at": "2026-03-13T12:00:00Z",
  "updated_at": "2026-03-13T12:00:00Z"
}
```

**Link syllabus — request (POST `/v1/certificate/academy/specialty/<specialty_id>/syllabus`):**
```json
{
  "syllabus_id": 5
}
```
Or `{ "syllabus_slug": "full-stack" }`.

**Link syllabus — response (200/201):** Same shape as get specialty; `syllabuses` array includes the newly linked syllabus.

**Issue certificate for one student — request (POST `/v1/certificate/cohort/<cohort_id>/student/<student_id>`):**
```json
{
  "layout_slug": "default"
}
```
Body is optional; omit or use `"layout_slug": "default"` if the academy has a default layout.

**Issue certificate for one student — response (201):**
```json
{
  "id": 200,
  "user": {"id": 50, "first_name": "Jane", "last_name": "Doe"},
  "specialty": {"id": 1, "slug": "full-stack", "name": "Full-Stack Web Development", "academy": null, "syllabus": {"id": 5, "name": "...", "slug": "..."}, "syllabuses": [{"id": 5, "name": "...", "slug": "..."}]},
  "cohort": {"id": 10, "name": "Cohort Jan 2026"},
  "layout": {"slug": "default"},
  "status": "PERSISTED",
  "created_at": "2026-03-11T12:00:00Z"
}
```

**Issue certificates for cohort — request (POST `/v1/certificate/cohort/<cohort_id>`):**
```json
{
  "layout_slug": "default"
}
```

**Issue certificates for cohort — response (201):**
```json
[
  {
    "id": 200,
    "user": {"id": 50, "first_name": "Jane", "last_name": "Doe"},
    "specialty": {"id": 1, "slug": "full-stack", "name": "Full-Stack Web Development"},
    "cohort": {"id": 10, "name": "Cohort Jan 2026"},
    "status": "PERSISTED"
  }
]
```

## Edge Cases

- **specialty not found (404):** Get/update/link when `specialty_id` is invalid or the specialty is not visible to the academy. Tell the user to check the id.
- **academy cannot update this specialty:** The specialty is global (`academy_id` null) or belongs to another academy. Only create/update when `specialty.academy_id == request academy`. Tell the user they can only update specialties that belong to their academy.
- **syllabus already linked (same specialty):** When linking a syllabus that is already in **this** specialty's syllabuses, the endpoint is idempotent (returns 200 with the same specialty).
- **syllabus-specialty-already-linked (400):** Another specialty in the same **bucket** (same `academy_id`, or both global) already lists this syllabus. Tell the user to unlink from the other specialty or use the existing specialty; the same syllabus may still be linked to specialties **under other academies**.
- **missing-specialty / Specialty has no Syllabus assigned:** No specialty applies for this cohort's syllabus under the **academy-first, then global** rule (e.g. only a specialty owned by a different academy lists the syllabus). Link the syllabus to an academy-owned specialty for the cohort's academy or to a global specialty; then retry.
- **missing-syllabus-version / The cohort has no syllabus assigned:** The cohort has no syllabus. Tell the user to set a syllabus (and syllabus version) for the cohort via the API first, then retry.
- **student-not-found / Student not found for this cohort:** The user is not a STUDENT in that cohort or the cohort does not belong to the academy. Verify cohort_id and student_id; do not retry the same pair.
- **already-exists / This user already has a certificate created:** The student already has an issued (PERSISTED) certificate for that cohort. Tell the user; no need to issue again unless they want to reattempt (use reattempt flow if available).
- **bad-educational-status / bad-finantial-status / cohort-without-status-ended / with-pending-tasks:** The student or cohort does not meet issuance rules. Tell the user the exact slug or message; they must fix the student or cohort state before retrying.
- **no-default-layout / No layout was specified:** The academy has no default certificate layout. Tell the user to pass a valid `layout_slug` in the request body or ensure a default layout is set for the academy.
- **without-main-teacher:** The cohort has no TEACHER. Tell the user to assign a main teacher to the cohort via the API before issuing.

## Checklist

1. To create a new specialty: call `POST /v1/certificate/academy/specialty` with name and slug (and optional fields); requires `crud_certificate`.
2. To update an academy-owned specialty: call `PUT` or `PATCH /v1/certificate/academy/specialty/<id>`; only when the specialty belongs to the academy.
3. To link a syllabus to a specialty: call `POST /v1/certificate/academy/specialty/<id>/syllabus` with syllabus_id or syllabus_slug; requires `crud_syllabus`.
4. To see which specialties are offered: call `GET /v1/certificate/academy/specialty` with `Academy` header; use `syllabus_slug` or `like` if needed.
5. To assign a specialty to one student: call `POST /v1/certificate/cohort/<cohort_id>/student/<student_id>`; ensure the cohort's syllabus is linked to a specialty.
6. To issue certificates for a full cohort: call `POST /v1/certificate/cohort/<cohort_id>`; cohort must be ENDED and have syllabus linked to a specialty.
7. If issuance fails with missing-specialty or missing-syllabus-version: tell the user the cohort's syllabus must be linked to a specialty (or cohort must have a syllabus); then retry.
8. To list who has been assigned which specialty: call `GET /v1/certificate/` with optional `user_id` or `like`; to remove a certificate use `DELETE /v1/certificate/?id=...`.
