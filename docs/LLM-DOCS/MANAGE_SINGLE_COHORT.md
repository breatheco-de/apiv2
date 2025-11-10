# Manage Single Cohort (Marketing Course & Translation CRUD)

This guide explains how to work with the marketing-facing `Course` resource and its `CourseTranslation` companion, which model the public representation of a cohort. Follow the patterns in this document to read course information, discover available translations, and understand the boundaries of the current public API.

---

## Table of Contents

- [Manage Single Cohort (Marketing Course \& Translation CRUD)](#manage-single-cohort-marketing-course--translation-crud)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Base URLs](#base-urls)
  - [Authentication \& Permissions](#authentication--permissions)
  - [Course Resource](#course-resource)
    - [Data Shape](#data-shape)
    - [Endpoint Summary](#endpoint-summary)
    - [List Courses](#list-courses)
    - [Retrieve a Single Course](#retrieve-a-single-course)
    - [Create, Update, Delete](#create-update-delete)
    - [Update Course](#update-course)
    - [Update plan_by_country_code](#update-plan_by_country_code)
  - [Course Translation Resource](#course-translation-resource)
    - [Translation Data Shape](#translation-data-shape)
    - [Endpoint Summary](#endpoint-summary-1)
    - [List Course Translations](#list-course-translations)
    - [Create, Update, Delete](#create-update-delete-1)
    - [Update Course Translation](#update-course-translation)
    - [Update course_modules](#update-course_modules)
    - [Update landing_variables](#update-landing_variables)
    - [Update prerequisite](#update-prerequisite)
  - [Common Error Responses](#common-error-responses)
  - [Caching \& Performance Notes](#caching--performance-notes)
  - [FAQ](#faq)

---

## Overview

- A **Course** is a marketing artifact that points to one or more syllabi and (optionally) a cohort. Courses power landing pages, pricing information, and catalog listings.
- A **CourseTranslation** contains localized marketing copy, media, and landing URLs for a specific language variant of the course.
- Public catalog endpoints remain read-only for anonymous clients. Academy-scoped endpoints allow authenticated staff with the `crud_course` capability to update critical marketing metadata directly through the API.

---

## Base URLs

```
Production: https://breathecode.herokuapp.com
Development: http://localhost:8000
```

All endpoints documented here are served from the Marketing API namespace: `/v1/marketing`.

---

## Authentication & Permissions

- `GET /v1/marketing/course` and related endpoints are **public** (`AllowAny`); no token or academy header is required.
- Responses automatically localize text using the `lang` query parameter when available, falling back to the requester’s preferred language (`Accept-Language` header inferred by `get_user_language`).
- Although public, results exclude `PRIVATE` courses and any course with status `DELETED`. Users cannot access archived content through this API.
- Authenticated **academy** endpoints (`/v1/marketing/academy/course/*`) require:
  - `Authorization: Token {auth-token}`
  - `Academy: {academy_id}` header
  - A staff member whose role carries the `crud_course` capability.

---

## Course Resource

### Data Shape

Courses are serialized with `GetCourseSerializer` and include nested academy, syllabus, cohort, and translation details. Example payload:

```json
{
  "slug": "full-stack-developer",
  "icon_url": "https://assets.4geeks.com/courses/full-stack/icon.svg",
  "banner_image": "https://assets.4geeks.com/courses/full-stack/banner.png",
  "academy": {
    "id": 4,
    "slug": "downtown-miami",
    "name": "BreatheCode Miami",
    "logo_url": "https://assets.4geeks.com/academies/downtown-miami/logo.png",
    "icon_url": "https://assets.4geeks.com/academies/downtown-miami/icon.png"
  },
  "syllabus": [
    {
      "id": 7,
      "slug": "full-stack",
      "name": "Full Stack Developer",
      "logo": null
    }
  ],
  "course_translation": {
    "title": "Full Stack Developer",
    "featured_assets": "intro-to-python,react-project",
    "description": "Become a full stack developer in 18 weeks.",
    "short_description": "Python, React, and DevOps in one course.",
    "lang": "en",
    "course_modules": [
      {"title": "Backend Fundamentals", "weeks": 4},
      {"title": "Frontend Frameworks", "weeks": 6}
    ],
    "landing_variables": {"cta_label": "Apply Now"},
    "landing_url": "https://4geeks.com/course/full-stack",
    "preview_url": "https://4geeks.com/course/full-stack/preview",
    "video_url": "https://youtu.be/xyz",
    "heading": "Train with the best instructors in Miami.",
    "prerequisite": ["Basic programming knowledge", "Laptop with 8GB RAM"]
  },
  "cohort": {
    "id": 21,
    "slug": "downtown-miami-full-stack-101",
    "name": "Full Stack 101"
  },
  "status": "ACTIVE",
  "visibility": "PUBLIC",
  "is_listed": true,
  "technologies": "python,react,flask,devops",
  "color": "#0B5FFF",
  "plan_slug": "full-stack-us"
}
```

Key notes:

- `plan_slug` automatically swaps to a country-specific slug when you supply `country_code` in the query string and the course has `plan_by_country_code` metadata.
- `course_translation` is language-aware. The serializer tries to match `lang`, `lang[:2]`, or any translation whose language starts with the two-letter prefix.
- `cohort` appears only when the course is linked to a never-ending SaaS-ready cohort (see `Course.clean()` validation).

### Endpoint Summary

| Method | Endpoint | Description | Availability |
|--------|----------|-------------|--------------|
| `GET` | `/v1/marketing/course` | List courses with optional filters | ✅ Public |
| `GET` | `/v1/marketing/course/{course_slug}` | Retrieve a single course by slug | ✅ Public |
| `PUT` | `/v1/marketing/academy/course/{course_id}` | Update course fields scoped to an academy | 🔒 Requires `crud_course` |
| `PUT` | `/v1/marketing/academy/course/{course_id}/plan-by-country-code` | Replace the `plan_by_country_code` JSON blob | 🔒 Requires `crud_course` |
| `POST` | `/v1/marketing/course` | Create a course | ❌ Not exposed via public API |
| `DELETE` | `/v1/marketing/course/{course_slug}` | Delete a course | ❌ Not exposed via public API |

### List Courses

**Endpoint**  
`GET /v1/marketing/course`

**Query Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lang` | string | No | Overrides language negotiation for course translations (`en`, `es`, `pt-BR`, etc.). Defaults to user language. |
| `country_code` | string | No | ISO country code (`us`, `es`, `co`) used to choose a localized `plan_slug`. |
| `academy` | string | No | Comma-separated academy slugs or numeric IDs. Accepts mixed input (`downtown-miami,3`). |
| `syllabus` | string | No | Comma-separated syllabus slugs or IDs to match courses referencing those syllabi. |
| `status` | string | No | Comma-separated course statuses (`ACTIVE`, `ARCHIVED`, `INACTIVE`). Defaults to active-only (excludes `ARCHIVED`). |
| `icon_url` | string | No | Case-insensitive substring filter on the `icon_url`. |
| `technologies` | string | No | Comma-separated keywords (logical OR) matched against the `technologies` field. |
| `is_listed` | string/bool | No | When `true`/`1` filters to catalog-visible courses; `false`/`0` shows hidden courses. |
| `limit`, `offset` | integer | No | Standard pagination provided by `APIViewExtensions`. |

**Example Request**

```
GET /v1/marketing/course?academy=downtown-miami&lang=es&country_code=co&technologies=python,react HTTP/1.1
Host: breathecode.herokuapp.com
```

**Example Response (200 OK)**

```json
[
  {
    "slug": "full-stack-developer",
    "icon_url": "https://assets.4geeks.com/courses/full-stack/icon.svg",
    "banner_image": "https://assets.4geeks.com/courses/full-stack/banner.png",
    "academy": {
      "id": 4,
      "slug": "downtown-miami",
      "name": "BreatheCode Miami",
      "logo_url": "https://assets.4geeks.com/academies/downtown-miami/logo.png",
      "icon_url": "https://assets.4geeks.com/academies/downtown-miami/icon.png"
    },
    "syllabus": [
      {
        "id": 7,
        "slug": "full-stack",
        "name": "Full Stack Developer",
        "logo": null
      }
    ],
    "course_translation": {
      "title": "Desarrollador Full Stack",
      "featured_assets": "intro-a-python,react-proyecto",
      "description": "Conviértete en desarrollador full stack en 18 semanas.",
      "short_description": "Python, React y DevOps en un solo curso.",
      "lang": "es",
      "course_modules": [
        {"title": "Fundamentos Backend", "weeks": 4},
        {"title": "Frameworks Frontend", "weeks": 6}
      ],
      "landing_variables": {"cta_label": "Aplicar Ahora"},
      "landing_url": "https://4geeks.com/es/course/full-stack",
      "preview_url": "https://4geeks.com/es/course/full-stack/preview",
      "video_url": "https://youtu.be/xyz-es",
      "heading": "Entrena con los mejores instructores de Latinoamérica.",
      "prerequisite": ["Conocimientos básicos de programación", "Laptop con 8GB RAM"]
    },
    "cohort": null,
    "status": "ACTIVE",
    "visibility": "PUBLIC",
    "is_listed": true,
    "technologies": "python,react,flask,devops",
    "color": "#0B5FFF",
    "plan_slug": "full-stack-co"
  }
]
```

### Retrieve a Single Course

**Endpoint**  
`GET /v1/marketing/course/{course_slug}`

**Path Parameters**

| Name | Type | Description |
|------|------|-------------|
| `course_slug` | string | Unique slug for the target course. |

**Query Parameters**

All parameters from the list endpoint remain valid (`lang`, `country_code`). No additional filters are accepted.

**Response Codes**

| Status | Description |
|--------|-------------|
| `200 OK` | Course found and visible. Body matches the schema above. |
| `404 Not Found` | Returned when the slug does not exist, the course is `DELETED`, or visibility is `PRIVATE`. |

**Example Error**

```json
{
  "detail": "course-not-found",
  "status_code": 404
}
```

### Create, Update, Delete

The public marketing API does not expose course creation or deletion. Use the academy-scoped endpoints (`/v1/marketing/academy/course/*`) to update an existing record. Attempting unsupported verbs on `/v1/marketing/course` still returns `405 Method Not Allowed`.

### Update Course

**Endpoint**  
`PUT /v1/marketing/academy/course/{course_id}`

**Headers**

```http
Authorization: Token {auth-token}
Academy: {academy_id}
Content-Type: application/json
```

**Body Fields**

All fields are optional; omitted keys remain unchanged.

| Field | Type | Notes |
|-------|------|-------|
| `slug` | string | Update the public slug (must remain unique). |
| `syllabus` | array[int] | Replace the list of attached syllabus IDs. |
| `cohort` | integer | Associate a never-ending cohort (must belong to the same academy). |
| `is_listed` | boolean | Toggle catalog visibility. |
| `plan_slug` | string \| null | Default plan slug when no country override matches. |
| `status` | enum | `ACTIVE`, `ARCHIVED`, or `DELETED`. |
| `color` | string | Hex color used in marketing surfaces. |
| `status_message` | string | Optional explanation when status is not `ACTIVE`. |
| `visibility` | enum | `PUBLIC`, `UNLISTED`, or `PRIVATE`. |
| `icon_url` | url | Course icon. |
| `banner_image` | url \| null | Optional hero image. |
| `technologies` | string | Comma-separated technology tags. |
| `has_waiting_list` | boolean | Enables the waiting list flow. |

**Example Request**

```http
PUT /v1/marketing/academy/course/42?lang=es&country_code=co HTTP/1.1
Authorization: Token abc123
Academy: 7
Content-Type: application/json

{
  "plan_slug": "full-stack-global",
  "status": "ARCHIVED",
  "is_listed": false,
  "color": "#0A558C"
}
```

**Response (200 OK)**

Returns the same payload structure as `GET /v1/marketing/course/{course_slug}` (honoring `lang`/`country_code` query parameters).

### Update plan_by_country_code

**Endpoint**  
`PUT /v1/marketing/academy/course/{course_id}/plan-by-country-code`

**Headers** — same as `Update Course`.

**Body**

```json
{
  "plan_by_country_code": {
    "us": "full-stack-us",
    "co": "full-stack-co"
  }
}
```

- The value must be a JSON object (or `null` to clear overrides).  
- Keys should be ISO 3166-1 alpha-2 country codes in lowercase.

**Response (200 OK)**

```json
{
  "plan_by_country_code": {
    "us": "full-stack-us",
    "co": "full-stack-co"
  }
}
```

---

## Course Translation Resource

### Translation Data Shape

`CourseTranslation` serializers surface marketing copy and ancillary metadata used by landing pages. Each translation is associated with a course and a language code (e.g., `en`, `es`, `pt-BR`).

### Endpoint Summary

| Method | Endpoint | Description | Availability |
|--------|----------|-------------|--------------|
| `GET` | `/v1/marketing/course/{course_slug}/translations` | List all translations for a visible course | ✅ Public |
| `PUT` | `/v1/marketing/academy/course/{course_id}/translation` | Update non-JSON translation fields (requires `lang` in body) | 🔒 Requires `crud_course` |
| `PUT` | `/v1/marketing/academy/course/{course_id}/course_modules` | Replace `course_modules` JSON array for a specific translation | 🔒 Requires `crud_course` |
| `PUT` | `/v1/marketing/academy/course/{course_id}/landing_variables` | Replace `landing_variables` JSON object for a translation | 🔒 Requires `crud_course` |
| `PUT` | `/v1/marketing/academy/course/{course_id}/prerequisite` | Replace the `prerequisite` list for a translation | 🔒 Requires `crud_course` |
| `POST` | `/v1/marketing/course/{course_slug}/translations` | Create a translation | ❌ Not exposed via public API |
| `DELETE` | `/v1/marketing/course/{course_slug}/translations/{lang}` | Delete a translation | ❌ Not exposed via public API |

### List Course Translations

**Endpoint**  
`GET /v1/marketing/course/{course_slug}/translations`

**Path Parameters**

| Name | Type | Description |
|------|------|-------------|
| `course_slug` | string | Slug of the parent course. |

**Response Codes**

| Status | Description |
|--------|-------------|
| `200 OK` | Returns an array of translations (possibly empty). |
| `400 Bad Request` | Triggered when `course_slug` is missing. |
| `404 Not Found` | Course not found, not active, or not publicly visible. |

**Example Response (200 OK)**

```json
[
  {
    "title": "Full Stack Developer",
    "featured_assets": "intro-to-python,react-project",
    "description": "Become a full stack developer in 18 weeks.",
    "short_description": "Python, React, and DevOps in one course.",
    "lang": "en",
    "course_modules": [
      {"title": "Backend Fundamentals", "weeks": 4},
      {"title": "Frontend Frameworks", "weeks": 6}
    ],
    "landing_variables": {"cta_label": "Apply Now"},
    "landing_url": "https://4geeks.com/course/full-stack",
    "preview_url": "https://4geeks.com/course/full-stack/preview",
    "video_url": "https://youtu.be/xyz",
    "heading": "Train with the best instructors in Miami.",
    "prerequisite": ["Basic programming knowledge", "Laptop with 8GB RAM"]
  },
  {
    "title": "Desarrollador Full Stack",
    "featured_assets": "intro-a-python,react-proyecto",
    "description": "Conviértete en desarrollador full stack en 18 semanas.",
    "short_description": "Python, React y DevOps en un solo curso.",
    "lang": "es",
    "course_modules": [
      {"title": "Fundamentos Backend", "weeks": 4},
      {"title": "Frameworks Frontend", "weeks": 6}
    ],
    "landing_variables": {"cta_label": "Aplicar Ahora"},
    "landing_url": "https://4geeks.com/es/course/full-stack",
    "preview_url": "https://4geeks.com/es/course/full-stack/preview",
    "video_url": "https://youtu.be/xyz-es",
    "heading": "Entrena con los mejores instructores de Latinoamérica.",
    "prerequisite": ["Conocimientos básicos de programación", "Laptop con 8GB RAM"]
  }
]
```

**Visibility Rules**

- The parent course must be `ACTIVE` and `PUBLIC`/`UNLISTED`. Otherwise a `404` is returned even if translations exist.
- No additional query parameters are supported; pagination is provided automatically through `APIViewExtensions`.

### Create, Update, Delete

Translation creation and deletion remain internal-only. Use the academy endpoints described below to update existing translations.

### Update Course Translation

**Endpoint**  
`PUT /v1/marketing/academy/course/{course_id}/translation`

Provide the translation language in the request body to identify the record.

```http
Authorization: Token {auth-token}
Academy: {academy_id}
Content-Type: application/json
```

```json
{
  "lang": "en",
  "title": "Full Stack Developer",
  "heading": "Build production-ready apps",
  "video_url": "https://youtu.be/xyz"
}
```

The response body returns the full translation serialized via `GetCourseTranslationSerializer`.

### Update course_modules

**Endpoint**  
`PUT /v1/marketing/academy/course/{course_id}/course_modules`

- `lang` is required in the body.
- `course_modules` must be an array of objects with `name`, `slug`, and `description`.

```json
{
  "lang": "en",
  "course_modules": [
    {"name": "Backend Fundamentals", "slug": "backend", "description": "Python, Flask, SQL"},
    {"name": "Frontend Frameworks", "slug": "frontend", "description": "React, state management"}
  ]
}
```

### Update landing_variables

**Endpoint**  
`PUT /v1/marketing/academy/course/{course_id}/landing_variables`

```json
{
  "lang": "en",
  "landing_variables": {
    "cta_label": "Apply Now",
    "hero_copy": "Kickstart your tech career in 18 weeks"
  }
}
```

- `landing_variables` must be a JSON object or `null`.

### Update prerequisite

**Endpoint**  
`PUT /v1/marketing/academy/course/{course_id}/prerequisite`

```json
{
  "lang": "en",
  "prerequisite": [
    "Comfort with basic HTML/CSS",
    "Fundamental programming knowledge"
  ]
}
```

- `prerequisite` accepts an array of Markdown strings (or `null` to clear the list).

Each JSON-focused endpoint returns the updated translation serialized with `GetCourseTranslationSerializer`.

---

## Common Error Responses

| Status | Body | Scenario |
|--------|------|----------|
| `400` | `{"detail": "course-slug-required", "status_code": 400}` | Calling `/course/{slug}/translations` without providing the slug parameter. |
| `400` | `{"detail": "missing-lang", "status_code": 400}` | Missing `lang` key when using academy translation endpoints. |
| `400` | `{"detail": "missing-course-modules", "status_code": 400}` | `course_modules` key omitted in `/course_modules` payloads. |
| `400` | `{"detail": "missing-plan-by-country-code", "status_code": 400}` | `plan_by_country_code` key omitted while calling the plan override endpoint. |
| `404` | `{"detail": "course-not-found", "status_code": 404}` | Course slug does not exist, is deleted, or is private. |
| `404` | `{"detail": "course-translation-not-found", "status_code": 404}` | Translation not found for the supplied `lang` and academy course. |
| `405` | `{"detail": "method-not-allowed"}` | Attempting unsupported verbs (POST/PUT/DELETE). |

These payloads are generated by `ValidationException`, which wraps errors using Capy Core translations to respect the requested language.

---

## Caching & Performance Notes

- Both endpoints use `CourseCache` through `APIViewExtensions`. Expect cached responses at the view layer; purge the cache when modifying courses via admin tools to see updates immediately.
- Sorting defaults to `-updated_at`. Use pagination parameters to page through large catalogs rather than fetching everything in one request.

---

## FAQ

- **How do I create or edit a course?**  
  Use the Django admin (`/admin/marketing/course/`) or the internal back-office UI. Public API clients cannot modify courses yet.

- **Why is my course missing from the response?**  
  Verify the course is `ACTIVE`, not `DELETED`, and has `visibility` set to `PUBLIC` or `UNLISTED`.

- **How can I fetch only one specific language?**  
  Use `GET /v1/marketing/course/{course_slug}` with the `lang` query parameter to have the embedded `course_translation` automatically select the closest matching translation.

- **Can I request unpublished translations?**  
  No. The endpoint returns all translations attached to the course, but the course itself must meet the visibility rules to be exposed.


