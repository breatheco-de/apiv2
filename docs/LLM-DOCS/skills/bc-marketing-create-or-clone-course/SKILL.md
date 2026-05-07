---
name: bc-marketing-create-or-clone-course
description: Use when staff need to create a marketing course from scratch or by cloning another course via API; do NOT use for updating an existing course or editing course translations only.
requires: []
---

# Skill: Create or Clone Marketing Course

## When to Use

- Use when the goal is to create a new course through `POST /v1/marketing/academy/course`.
- Use for both creation modes: scratch and clone.
- Use when the request includes source-course permission or slug-conflict concerns.
- Do NOT use for translation-only updates; use translation endpoints after creation.
- Do NOT use for updating an existing course.

## Concepts

- `scratch_create`: A normal course create where core required fields must be sent explicitly.
- `clone_create`: A create request that includes `source_course`; non-identity fields are copied from source and can be overridden by payload.
- `source_course`: Source course identifier (slug or numeric id) used only for cloning.
- `Academy` header: Required academy scope for all `/academy/` marketing endpoints.

## Workflow

1. Confirm destination academy and send `Academy: <academy_id>` header.
2. Determine mode: if `source_course` is provided, use clone flow; otherwise use scratch flow.
3. For scratch flow, collect required fields: `slug`, `icon_url`, `technologies`.
4. For clone flow, collect `slug` and `source_course`; verify caller has `crud_course` capability in destination academy and source academy.
5. Apply defaults and optional overrides (`visibility`, `status`, `is_listed`, `cohort`, `syllabus`, branding fields).
6. Submit `POST /v1/marketing/academy/course` with JSON payload.
7. If create succeeds, capture new course response and then call translation endpoints if translation data must be added or adjusted.

## Endpoints

### Create course (scratch or clone)

- **Method / path:** `POST /v1/marketing/academy/course`
- **Headers:** `Authorization: Token <token>`, `Academy: <academy_id>`, optional `Accept-Language: en|es`.
- **Permissions:** Caller must have `crud_course` in destination academy. Clone mode also requires `crud_course` in source course academy.
- **Body required (scratch):** `slug`, `icon_url`, `technologies`.
- **Body required (clone):** `slug`, `source_course`.
- **Response:** Full course object (academy, syllabus list, status/visibility/listing fields, translation object for requested language if available).

**Scratch request example:**

```json
{
  "slug": "ai-engineering",
  "icon_url": "https://assets.example.com/course-ai-icon.png",
  "technologies": "python,llm,agents",
  "visibility": "PUBLIC",
  "status": "ACTIVE",
  "is_listed": true,
  "has_waiting_list": false,
  "plan_slug": "ai-engineering-pro"
}
```

**Clone request example:**

```json
{
  "slug": "ai-engineering-latam",
  "source_course": "ai-engineering",
  "visibility": "UNLISTED",
  "is_listed": false
}
```

**Response example (subset):**

```json
{
  "slug": "ai-engineering-latam",
  "academy": {
    "id": 12,
    "slug": "my-academy",
    "name": "My Academy",
    "logo_url": "https://assets.example.com/logo.png",
    "icon_url": "https://assets.example.com/icon.png"
  },
  "syllabus": [
    {
      "id": 55,
      "slug": "ai-engineering",
      "name": "AI Engineering",
      "logo": "https://assets.example.com/syllabus-logo.png"
    }
  ],
  "status": "ACTIVE",
  "visibility": "UNLISTED",
  "is_listed": false,
  "icon_url": "https://assets.example.com/course-ai-icon.png",
  "technologies": "python,llm,agents",
  "course_translation": null
}
```

## Edge Cases

- Source course not found (`source-course-not-found`): verify `source_course` slug/id and retry.
- Source permission missing (`source-course-forbidden`): use a source academy where caller has `crud_course`, or change actor token.
- Slug conflict on create: send a different `slug`; no automatic suffixing is applied.
- Invalid cohort on create/clone: if cohort is not never-ending, not SaaS-available, or not in destination academy, provide a valid cohort or omit it.
- Translation data expected on create: create course first, then call translation update endpoints.

## Data Model Clarification

- `Course.syllabus` is many-to-many because a marketing course can bundle or present multiple syllabi.
- Admissions runtime entities (for example schedule/version objects) use syllabus foreign keys because each runtime object must point to one concrete syllabus/version at a time.
- This is intentional separation: marketing catalog composition vs admissions operational delivery.

## Checklist

1. [ ] Confirmed mode (`scratch_create` or `clone_create`) and destination `Academy` header.
2. [ ] Confirmed required fields for chosen mode (`slug` + scratch fields or `slug` + `source_course`).
3. [ ] For clone mode, confirmed `crud_course` permission in both source and destination academies.
4. [ ] Confirmed requested `slug` is final (no auto-rename on conflict).
5. [ ] Submitted `POST /v1/marketing/academy/course` and validated success payload.
6. [ ] If translations are needed, scheduled translation update endpoints after create.
