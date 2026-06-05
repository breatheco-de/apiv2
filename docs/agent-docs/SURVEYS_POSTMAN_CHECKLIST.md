# Surveys — Postman checklist (staff + student)

Use this doc to copy/paste requests into Postman.

---

## Variables used in this doc

- **`{{base_url}}`**: Example: `https://breathecode-test.herokuapp.com`
- **`{{academy_id}}`**: The academy id you want to operate on
- **`{{token_admin_or_staff}}`**: Auth token for a user with the right capabilities on that academy
- **`{{token_student}}`**: Auth token for a student
- **`{{configuration_id}}`**: `SurveyConfiguration.id`
- **`{{template_id}}`**: `SurveyQuestionTemplate.id`
- **`{{study_id}}`**: `SurveyStudy.id`
- **`{{response_id}}`**: `SurveyResponse.id`
- **`{{response_token}}`**: `SurveyResponse.token` (UUID)
- **`{{user_id}}`**: Django user id
- **`{{cohort_id}}`**: cohort id

---

## Common headers

### Staff endpoints (academy-scoped)

- **Authorization**: `Token {{token_admin_or_staff}}`
- **Academy**: `{{academy_id}}`
- **Content-Type**: `application/json`

### Student endpoints (non-academy scoped)

- **Authorization**: `Token {{token_student}}`
- **Content-Type**: `application/json`

---

## 1) SurveyQuestionTemplate (staff)

### 1.1 List templates

- **Method**: GET
- **URL**: `{{base_url}}/v1/feedback/academy/survey/question_template`
- **Headers**: staff headers

### 1.2 Retrieve template

- **Method**: GET
- **URL**: `{{base_url}}/v1/feedback/academy/survey/question_template/{{template_id}}`
- **Headers**: staff headers

### 1.3 Create template

- **Method**: POST
- **URL**: `{{base_url}}/v1/feedback/academy/survey/question_template`
- **Headers**: staff headers
- **Body**:

```json
{
  "slug": "course-completion-v1",
  "title": "Course completion (v1)",
  "description": "Baseline course completion survey",
  "questions": {
    "questions": [
      {
        "id": "q1",
        "type": "likert_scale",
        "required": true,
        "title": { "en": "How was the course?", "es": "¿Qué tal fue el curso?" },
        "config": { "scale": 5 }
      }
    ]
  }
}
```

### 1.4 Update template (partial)

- **Method**: PUT
- **URL**: `{{base_url}}/v1/feedback/academy/survey/question_template/{{template_id}}`
- **Headers**: staff headers
- **Body**: send only fields you want to change

---

## 2) SurveyStudy (staff)

### 2.1 List studies

- **Method**: GET
- **URL**: `{{base_url}}/v1/feedback/academy/survey/study`
- **Headers**: staff headers

### 2.2 Retrieve study

- **Method**: GET
- **URL**: `{{base_url}}/v1/feedback/academy/survey/study/{{study_id}}`
- **Headers**: staff headers

### 2.3 Create study

- **Method**: POST
- **URL**: `{{base_url}}/v1/feedback/academy/survey/study`
- **Headers**: staff headers
- **Body**:

```json
{
  "slug": "course-completion-study-dec-2025",
  "title": "Course completion — Dec 2025",
  "description": "Study window for course completion surveys",
  "starts_at": "2025-12-01T00:00:00Z",
  "ends_at": "2026-01-01T00:00:00Z",
  "max_responses": null,
  "survey_configurations": [{{configuration_id}}]
}
```

### 2.4 Update study (partial)

- **Method**: PUT
- **URL**: `{{base_url}}/v1/feedback/academy/survey/study/{{study_id}}`
- **Headers**: staff headers

### 2.5 Send study survey by email to a list of users (round-robin across configs)

- **Method**: POST
- **URL**: `{{base_url}}/v1/feedback/academy/survey/study/{{study_id}}/send_emails`
- **Headers**: staff headers
- **Body**:

```json
{
  "user_ids": [1, 2, 3],
  "callback": "https://your-frontend.com/after-survey",
  "dry_run": false
}
```

**Notes**:
- The endpoint creates **one SurveyResponse per (study, user)** if missing.
- If the study has multiple configurations, users are assigned **round-robin** across them (equitable split).
- Emails include the `SurveyResponse.token` in the LINK (and append `?callback=...` if provided).
- You can also target a cohort (all ACTIVE/GRADUATED students) instead of passing explicit user ids:

```json
{
  "cohort_id": {{cohort_id}},
  "callback": "https://your-frontend.com/after-survey",
  "dry_run": false
}
```

---

## 3) SurveyConfiguration (staff)

### 3.1 List configurations

- **Method**: GET
- **URL**: `{{base_url}}/v1/feedback/academy/survey/configuration`
- **Headers**: staff headers

### 3.2 Retrieve configuration

- **Method**: GET
- **URL**: `{{base_url}}/v1/feedback/academy/survey/configuration/{{configuration_id}}`
- **Headers**: staff headers

### 3.3 Create configuration using a template

- **Method**: POST
- **URL**: `{{base_url}}/v1/feedback/academy/survey/configuration`
- **Headers**: staff headers
- **Body**:

```json
{
  "trigger_type": "course_completed",
  "template": {{template_id}},
  "is_active": true,
  "cohorts": [{{cohort_id}}],
  "asset_slugs": []
}
```

### 3.4 Create configuration using inline questions (no template)

- **Method**: POST
- **URL**: `{{base_url}}/v1/feedback/academy/survey/configuration`
- **Headers**: staff headers
- **Body**:

```json
{
  "trigger_type": "course_completed",
  "is_active": true,
  "cohorts": [{{cohort_id}}],
  "asset_slugs": [],
  "questions": {
    "questions": [
      {
        "id": "q1",
        "type": "likert_scale",
        "required": true,
        "title": { "en": "Changed", "es": "Cambiado" },
        "config": { "scale": 5 }
      }
    ]
  }
}
```

### 3.5 Update configuration questions (only when `template` is null)

- **Method**: PUT
- **URL**: `{{base_url}}/v1/feedback/academy/survey/configuration/{{configuration_id}}`
- **Headers**: staff headers
- **Body**:

```json
{
  "questions": {
    "questions": [
      {
        "id": "q1",
        "type": "likert_scale",
        "required": true,
        "title": { "en": "Changed", "es": "Cambiado" },
        "config": { "scale": 5 }
      }
    ]
  }
}
```

**Important**:
- If the configuration has `template != null`, the API should reject any attempt to send `"questions"` in the request.

---

## 4) SurveyResponse (staff)

All endpoints below are staff + academy scoped.

### 4.1 List responses (filter by configuration)

- **Method**: GET
- **URL**: `{{base_url}}/v1/feedback/academy/survey/response?survey_config={{configuration_id}}`
- **Headers**: staff headers

### 4.2 List responses (filter by user)

- **Method**: GET
- **URL**: `{{base_url}}/v1/feedback/academy/survey/response?user={{user_id}}`
- **Headers**: staff headers

### 4.3 List responses (filter by cohort_id inside `trigger_context`)

- **Method**: GET
- **URL**: `{{base_url}}/v1/feedback/academy/survey/response?cohort_id={{cohort_id}}`
- **Headers**: staff headers

### 4.4 Retrieve response (by id)

- **Method**: GET
- **URL**: `{{base_url}}/v1/feedback/academy/survey/response/{{response_id}}`
- **Headers**: staff headers

---

## 5) SurveyResponse (student flow)

### 5.1 Retrieve response by token (direct link)

- **Method**: GET
- **URL**: `{{base_url}}/v1/feedback/survey/response/by_token/{{response_token}}`
- **Headers**: student headers

### 5.2 Mark opened (idempotent)

- **Method**: POST
- **URL**: `{{base_url}}/v1/feedback/survey/response/{{response_id}}/opened`
- **Headers**: student headers
- **Body**: empty

### 5.3 Mark partial (idempotent-ish)

- **Method**: POST
- **URL**: `{{base_url}}/v1/feedback/survey/response/{{response_id}}/partial`
- **Headers**: student headers
- **Body**:

```json
{ "answers": { "q1": 4 } }
```

### 5.4 Submit final answers

- **Method**: POST
- **URL**: `{{base_url}}/v1/feedback/user/me/survey/response/{{response_id}}/answer`
- **Headers**: student headers
- **Body**:

```json
{
  "answers": {
    "q1": 5,
    "q2": "Great experience"
  }
}
```

---

## 6) Trackers (no auth)

### 6.1 Classic Answer tracker (legacy)

- **Method**: GET
- **URL**: `{{base_url}}/v1/feedback/answer/{{answer_id}}/tracker.png`

### 6.2 SurveyResponse email open tracker

- **Method**: GET
- **URL**: `{{base_url}}/v1/feedback/survey/response/{{response_token}}/tracker.png`

---

## Troubleshooting

### A) 405 Method Not Allowed

This means you are hitting the right path, but with a method the server does not implement for that URL.

- **SurveyConfiguration update** supports **PUT** on:  
  `.../academy/survey/configuration/{{configuration_id}}`
- **SurveyStudy retrieve** supports **GET** on:  
  `.../academy/survey/study/{{study_id}}`
- **Trackers** are **GET**.

If you are using the correct method and still getting 405, your Heroku app is likely running an older release (not deployed with the latest view methods/routes).

### B) DRF JSON ParseError (Expecting value at line 1 column 1)

You are sending an empty body, or the body is not valid JSON.

In Postman:
- Body → **raw** → **JSON**
- The body must start with `{` and contain only JSON (no URL text before it).


