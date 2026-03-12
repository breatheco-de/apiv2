---
name: bc-certificate-manage-and-assign-specialties
description: Use when academy staff need to see which certificate specialties are offered, filter by syllabus, or assign a specialty to a student by issuing a certificate; do NOT use for creating/editing specialties or linking syllabi (not exposed by this API), or for listing a student's own certificates (use certificate me endpoint).
requires: []
---

# Skill: Manage and Assign Certificate Specialties

## When to Use

Use this skill when the user asks to **list or view academy specialties**, **see which specialties are offered** or **which syllabi a specialty uses**, or to **give a specialty to a student** (issue a certificate that the student has mastered that specialty). Do **not** use when the user only wants to create or edit specialties or link syllabi to specialties — the API does not expose those operations. Do **not** use for a student listing their own certificates (that is a different endpoint).

## Concepts

- **Specialty**: A certificate type (e.g. "Full-Stack Web Development"). In the API it is the certificate the student receives. A specialty can be linked to one or many syllabi; the academy sees specialties that have at least one syllabus owned by the academy.
- **Assigning a specialty to a student**: Issuing a certificate — creating a user-specialty record that states the student has completed the specialty. The certificate is tied to a cohort and the cohort's syllabus; the system finds the specialty that matches that syllabus.
- **Managing specialties**: Via the API, staff can **list** which specialties are offered (and see their linked syllabi in the response). Creating, updating, or linking syllabi to specialties is not exposed by this API.

## Workflow

1. **List specialties offered by the academy.** Call `GET /v1/certificate/academy/specialty` with `Authorization` and `Academy: <academy_id>`. The response includes each specialty's slug, name, status, and linked syllabi (single `syllabus` or list `syllabuses`). Use query `syllabus_slug=<slug>` to filter by syllabus, or `like=<text>` to search by name. This shows which specialties the academy can issue.

2. **Assign a specialty to one student (issue one certificate).** Call `POST /v1/certificate/cohort/<cohort_id>/student/<student_id>`. The student must be in that cohort with role STUDENT. The cohort must have a syllabus assigned; that syllabus must be linked to a specialty. Optional body: `{ "layout_slug": "default" }`. The backend resolves the specialty from the cohort's syllabus and creates or updates the user's certificate. Response is 201 with the certificate (user_specialty) object. The student must meet graduation and financial rules (e.g. GRADUATED, FULLY_PAID or UP_TO_DATE, cohort ENDED if applicable).

3. **Issue certificates for an entire cohort.** Call `POST /v1/certificate/cohort/<cohort_id>` with `Authorization` and `Academy: <academy_id>`. Optional body: `{ "layout_slug": "default" }`. All students in that cohort (role STUDENT) receive a certificate for the cohort's specialty. The cohort must have a syllabus linked to a specialty; cohort stage must be ENDED (or never_ends). Response is 201 with a list of certificate objects.

4. **List or filter issued certificates (academy).** Call `GET /v1/certificate/` (root) with `Authorization` and `Academy: <academy_id>`. Optional query: `user_id=<id>` or `like=<name>` to filter. Use this to verify who has been assigned which specialty.

**Prerequisite:** The cohort's syllabus must be linked to a specialty. If issuing fails with "Specialty has no Syllabus assigned" or "missing-specialty", tell the user the cohort's syllabus is not linked to any specialty and must be linked before issuing.

## Endpoints

| Action | Method | Path | Headers | Body / Query | Response |
|--------|--------|------|---------|--------------|----------|
| List academy specialties | GET | `/v1/certificate/academy/specialty` | `Authorization`, `Academy: <academy_id>` | Optional: `syllabus_slug=<slug>`, `like=<text>` | List of specialties (id, slug, name, status, syllabus, syllabuses). |
| Issue certificate for one student | POST | `/v1/certificate/cohort/<cohort_id>/student/<student_id>` | `Authorization`, `Academy: <academy_id>` | Optional; see request sample. | 201, certificate (user_specialty) object; see response sample. |
| Issue certificates for cohort | POST | `/v1/certificate/cohort/<cohort_id>` | `Authorization`, `Academy: <academy_id>` | Optional; see request sample. | 201, list of certificate objects. |
| Get one student's certificate | GET | `/v1/certificate/cohort/<cohort_id>/student/<student_id>` | `Authorization`, `Academy: <academy_id>` | — | Certificate object or 404. |
| List academy certificates | GET | `/v1/certificate/` | `Authorization`, `Academy: <academy_id>` | Optional: `user_id=<id>`, `like=<name>`, `sort` | Paginated list of issued certificates. |
| Delete certificates (bulk) | DELETE | `/v1/certificate/` | `Authorization`, `Academy: <academy_id>` | Query: `id=1&id=2` (ids of user_specialty) | 204 No Content. |

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
  "specialty": {"id": 1, "slug": "full-stack", "name": "Full-Stack Web Development"},
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
  },
  {
    "id": 201,
    "user": {"id": 51, "first_name": "John", "last_name": "Smith"},
    "specialty": {"id": 1, "slug": "full-stack", "name": "Full-Stack Web Development"},
    "cohort": {"id": 10, "name": "Cohort Jan 2026"},
    "status": "PERSISTED"
  }
]
```

All academy endpoints require capability `read_certificate` for GET and `crud_certificate` for POST/DELETE.

## Edge Cases

- **missing-specialty / Specialty has no Syllabus assigned:** The cohort's syllabus is not linked to any specialty. Tell the user the syllabus must be linked to a specialty before issuing; then retry.
- **missing-syllabus-version / The cohort has no syllabus assigned:** The cohort has no syllabus. Tell the user to set a syllabus (and syllabus version) for the cohort via the API first, then retry.
- **student-not-found / Student not found for this cohort:** The user is not a STUDENT in that cohort or the cohort does not belong to the academy. Verify cohort_id and student_id; do not retry the same pair.
- **already-exists / This user already has a certificate created:** The student already has an issued (PERSISTED) certificate for that cohort. Tell the user; no need to issue again unless they want to reattempt (use reattempt flow if available).
- **bad-educational-status / bad-finantial-status / cohort-without-status-ended / with-pending-tasks:** The student or cohort does not meet issuance rules (e.g. must be GRADUATED, FULLY_PAID or UP_TO_DATE, cohort ENDED, no mandatory pending projects). Tell the user the exact slug or message; they must fix the student or cohort state before retrying.
- **no-default-layout / No layout was specified:** The academy has no default certificate layout. Tell the user to pass a valid `layout_slug` in the request body or ensure a default layout is set for the academy.
- **without-main-teacher:** The cohort has no TEACHER. Tell the user to assign a main teacher to the cohort via the API before issuing.

## Checklist

1. To see which specialties are offered: call `GET /v1/certificate/academy/specialty` with `Academy` header; use `syllabus_slug` or `like` if needed.
2. To assign a specialty to one student: call `POST /v1/certificate/cohort/<cohort_id>/student/<student_id>`; ensure the cohort's syllabus is linked to a specialty.
3. To issue certificates for a full cohort: call `POST /v1/certificate/cohort/<cohort_id>`; cohort must be ENDED and have syllabus linked to a specialty.
4. If issuance fails with missing-specialty or missing-syllabus-version: tell the user the cohort's syllabus must be linked to a specialty (or cohort must have a syllabus); then retry.
5. To list who has been assigned which specialty: call `GET /v1/certificate/` with optional `user_id` or `like`; to remove a certificate use `DELETE /v1/certificate/?id=...`.
