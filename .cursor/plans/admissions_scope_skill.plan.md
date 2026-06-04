---
name: ""
overview: ""
todos: []
isProject: false
---

# Admissions Scope Skill Plan

Add a BreatheCode API **domain skill** for the **admissions** scope: academy-scoped, capability-restricted endpoints under `/v1/admissions/` (cohorts, cohort users, syllabus, academy, reports). Playbook + reference; depends on existing Basics and Authentication skills.

**Base path:** All paths below are relative to `/v1/admissions/`. Full URL = `{BASE_URL}/v1/admissions/{path}`. All require `Authorization: Token {BREATHECODE_TOKEN}` and `Academy: {academy_id_or_slug}` unless noted.

---

## List of endpoints (academy-scoped, capability-restricted)

Derived from [breathecode/admissions/urls.py](breathecode/admissions/urls.py) and `@capable_of` in [breathecode/admissions/views.py](breathecode/admissions/views.py). Excludes public, admin-only, and deprecated routes.

### Academy


| Method | Path             | Capability      |
| ------ | ---------------- | --------------- |
| GET    | academy/me       | read_my_academy |
| GET    | academy/features | read_my_academy |


Note: `GET academy` (list academies) and `GET academy/<int:academy_id>` (single academy) are AllowAny; not capability-restricted.

### Teachers


| Method | Path            | Capability  |
| ------ | --------------- | ----------- |
| GET    | academy/teacher | read_member |


### Cohorts


| Method | Path                                          | Capability         |
| ------ | --------------------------------------------- | ------------------ |
| GET    | academy/cohort/me                             | read_single_cohort |
| GET    | academy/cohort                                | read_all_cohort    |
| GET    | academy/cohort/[str:cohort_id](str:cohort_id) | read_all_cohort    |


### Cohort users


| Method | Path                                                                          | Capability      |
| ------ | ----------------------------------------------------------------------------- | --------------- |
| GET    | academy/cohort/user                                                           | read_all_cohort |
| GET    | academy/cohort/user/[int:cohort_user_id](int:cohort_user_id)                  | read_all_cohort |
| GET    | academy/cohort/[int:cohort_id](int:cohort_id)/user                            | read_all_cohort |
| GET    | academy/cohort/[int:cohort_id](int:cohort_id)/user/[int:user_id](int:user_id) | read_all_cohort |


### Cohort log and reports


| Method | Path                                                                 | Capability        |
| ------ | -------------------------------------------------------------------- | ----------------- |
| GET    | academy/cohort/[str:cohort_id](str:cohort_id)/log                    | read_cohort_log   |
| GET    | academy/cohort/[int:cohort_id](int:cohort_id)/report/attendance.csv  | read_cohort_log   |
| GET    | academy/cohort/[int:cohort_id](int:cohort_id)/report/attendance.json | read_cohort_log   |
| GET    | academy/cohort/[int:cohort_id](int:cohort_id)/report.csv             | academy_reporting |


### Cohort timeslots


| Method | Path                                                                                      | Capability      |
| ------ | ----------------------------------------------------------------------------------------- | --------------- |
| GET    | academy/cohort/[int:cohort_id](int:cohort_id)/timeslot                                    | read_all_cohort |
| GET    | academy/cohort/[int:cohort_id](int:cohort_id)/timeslot/[int:timeslot_id](int:timeslot_id) | read_all_cohort |


### Schedule (certificate / syllabus schedule)


| Method | Path                                                                                                  | Capability       |
| ------ | ----------------------------------------------------------------------------------------------------- | ---------------- |
| GET    | academy/schedule                                                                                      | read_certificate |
| GET    | academy/schedule/[int:certificate_id](int:certificate_id)                                             | read_certificate |
| GET    | academy/schedule/[int:certificate_id](int:certificate_id)/timeslot                                    | read_certificate |
| GET    | academy/schedule/[int:certificate_id](int:certificate_id)/timeslot/[int:timeslot_id](int:timeslot_id) | read_certificate |


### Syllabus (academy-scoped)


| Method | Path                                                                                                                        | Capability    |
| ------ | --------------------------------------------------------------------------------------------------------------------------- | ------------- |
| GET    | academy/[int:academy_id](int:academy_id)/syllabus                                                                           | read_syllabus |
| GET    | academy/[int:academy_id](int:academy_id)/syllabus/[int:syllabus_id](int:syllabus_id)                                        | read_syllabus |
| GET    | academy/[int:academy_id](int:academy_id)/syllabus/[str:syllabus_slug](str:syllabus_slug)                                    | read_syllabus |
| GET    | academy/[int:academy_id](int:academy_id)/syllabus/[int:syllabus_id](int:syllabus_id)/version                                | read_syllabus |
| GET    | academy/[int:academy_id](int:academy_id)/syllabus/[int:syllabus_id](int:syllabus_id)/version/[int:version](int:version)     | read_syllabus |
| GET    | academy/[int:academy_id](int:academy_id)/syllabus/[str:syllabus_slug](str:syllabus_slug)/version                            | read_syllabus |
| GET    | academy/[int:academy_id](int:academy_id)/syllabus/[str:syllabus_slug](str:syllabus_slug)/version/[str:version](str:version) | read_syllabus |


### Syllabus (global; read-only)


| Method | Path                                                                                   | Capability    |
| ------ | -------------------------------------------------------------------------------------- | ------------- |
| GET    | syllabus                                                                               | read_syllabus |
| GET    | syllabus/[int:syllabus_id](int:syllabus_id)                                            | read_syllabus |
| GET    | syllabus/[str:syllabus_slug](str:syllabus_slug)                                        | read_syllabus |
| GET    | syllabus/[int:syllabus_id](int:syllabus_id)/version                                    | read_syllabus |
| GET    | syllabus/[int:syllabus_id](int:syllabus_id)/version/[int:version](int:version)         | read_syllabus |
| GET    | syllabus/[str:syllabus_slug](str:syllabus_slug)/version                                | read_syllabus |
| GET    | syllabus/[str:syllabus_slug](str:syllabus_slug)/version/[str:version](str:version)     | read_syllabus |
| GET    | syllabus/[str:syllabus_id](str:syllabus_id)/version/[str:version](str:version).csv     | read_syllabus |
| GET    | syllabus/[str:syllabus_id](str:syllabus_id)/version/[str:version](str:version)/preview | (see views)   |


### Syllabus asset (admin)


| Method | Path                                                  | Capability    |
| ------ | ----------------------------------------------------- | ------------- |
| GET    | admin/syllabus/asset/[str:asset_slug](str:asset_slug) | read_syllabus |


### Reports (academy-level)


| Method | Path       | Capability        |
| ------ | ---------- | ----------------- |
| GET    | report     | academy_reporting |
| GET    | report.csv | academy_reporting |


### User (admissions user/me)


| Method | Path    | Capability                  |
| ------ | ------- | --------------------------- |
| GET    | user/me | (authenticated; check view) |
| GET    | user    | (authenticated; check view) |


Note: `user/me` and `user` may use different permission models; confirm in views if including in skill.

---

## Excluded from list

- **Public:** `public/syllabus`, `public/cohort/user`, `cohort/all`, `cohort/user`, `cohort/<id>/join`, `cohort/<id>/user`
- **AllowAny (no capability):** `academy` (list), `academy/<id>` (get_single_academy), `catalog/timezones`, `catalog/countries`, `catalog/cities`, `syllabus/version` (AllSyllabusVersionsView)
- **Admin-only (superuser):** `admin/cohort`, `admin/student`
- **Deprecated:** paths under `academy/certificate/`, `certificate`, `schedule` (legacy), etc.

---

## Skill layout

```
.cursor/skills/breathecode-api-admissions/
├── SKILL.md       # Playbook: auth/headers recap, 5–10 workflows, "read reference.md"
└── reference.md   # Copy of endpoint list above + links to LLM-DOCS
```

**Dependencies:** breathecode-api-basics, breathecode-api-authentication.

---

## SKILL.md contents (playbook)

- Recap: All requests need `Authorization: Token {BREATHECODE_TOKEN}` and `Academy: {academy_id_or_slug}`. Base URL from env (see Basics).
- Gotchas: Pagination on list endpoints; report endpoints return CSV or JSON.
- High-value workflows: List cohorts, get cohort, list cohort users, cohort attendance/report CSV, list syllabi, academy/me, academy report/report.csv, cohort log.
- Trigger examples: "List all cohorts for the academy", "Get students in cohort X", "Export cohort report CSV", "List syllabus versions".
- Instruction: "When you need full path and capability per endpoint, read reference.md."

---

## reference.md contents

- Paste the **List of endpoints** tables above (by section: Academy, Teachers, Cohorts, Cohort users, etc.).
- Add links to LLM-DOCS: [COHORTS.md](docs/LLM-DOCS/COHORTS.md), [MANAGE_SINGLE_COHORT.md](docs/LLM-DOCS/MANAGE_SINGLE_COHORT.md), [COHORTS_CREATE.md](docs/LLM-DOCS/COHORTS_CREATE.md), [ADD_STUDENT.md](docs/LLM-DOCS/ADD_STUDENT.md), [STUDENT_REPORT.md](docs/LLM-DOCS/STUDENT_REPORT.md), [SYLLABUS.md](docs/LLM-DOCS/SYLLABUS.md), [BUILD_SYLLABUS.md](docs/LLM-DOCS/BUILD_SYLLABUS.md).

---

## Implementation steps

1. Create `.cursor/skills/breathecode-api-admissions/`.
2. Write SKILL.md (frontmatter, recap, gotchas, workflows, trigger examples, pointer to reference.md).
3. Write reference.md with the endpoint list above and LLM-DOCS links.
4. Update `.cursor/skills/README.md`: add breathecode-api-admissions to the skills table and layout.

---

## Note on students

Listing **academy students** (all students in an academy) is under **auth**: `GET /v1/auth/academy/student` (capability `read_student`), not admissions. Admissions covers **cohort users** (users in a specific cohort). In the playbook, mention: for academy-wide students use auth/academy/student; for users in a cohort use admissions academy/cohort/user or academy/cohort/{id}/user.