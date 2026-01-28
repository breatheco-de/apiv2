# How to Study an Entire Syllabus

This guide explains how to set up a survey study that automatically triggers when students complete an entire syllabus.

## Overview

When you want to survey students after they complete a full syllabus, you need to:

1. Create a **Survey Question Template** (optional but recommended)
2. Create a **Survey Configuration** with `trigger_type: "syllabus_completed"`
3. Create a **Survey Study** to group your configuration
4. The system will automatically trigger surveys when students complete the syllabus

---

## Available Trigger Types

The `trigger_type` field in `SurveyConfiguration` determines when surveys are automatically triggered. Here are all available options:

### 1. `"syllabus_completed"` - Syllabus Completion
- **Triggers when**: A user completes ALL modules in a syllabus
- **Filtering**: Use `syllabus.syllabus` and optionally `syllabus.version` in the syllabus filter
- **Important**: Do NOT include `syllabus.module` (only for module completion)
- **Use case**: Survey students after they finish an entire course/syllabus

**Example Configuration:**
```json
{
  "trigger_type": "syllabus_completed",
  "template": {{template_id}},
  "is_active": true,
  "syllabus": {
    "syllabus": "full-stack",
    "version": 2
  },
  "cohorts": [],
  "asset_slugs": []
}
```

### 2. `"module_completed"` - Module Completion
- **Triggers when**: A user completes all activities (QUIZ, LESSON, EXERCISE, PROJECT) in a specific module
- **Filtering**: Use `syllabus.module` (0-based index) to target a specific module
- **Special feature**: Supports `priority` field for conditional hazard-based sampling across multiple modules
- **Use case**: Survey students at different points during a course (e.g., after module 1, 3, and 5)

**Example Configuration:**
```json
{
  "trigger_type": "module_completed",
  "template": {{template_id}},
  "is_active": true,
  "syllabus": {
    "syllabus": "full-stack",
    "version": 2,
    "module": 3
  },
  "cohorts": [],
  "asset_slugs": [],
  "priority": 75.0
}
```

**Note**: The `priority` field (0-100) represents the cumulative target percentage of users who should have received a survey by this module. Only used for `module_completed` triggers.

### 3. `"learnpack_completed"` - Learnpack Completion
- **Triggers when**: A user completes a learnpack (completion_rate >= 99.999)
- **Filtering**: Use `asset_slugs` array to filter by specific learnpacks
- **If `asset_slugs` is empty**: Applies to all learnpacks
- **Use case**: Survey students after completing specific learning materials

**Example Configuration (Specific Learnpacks):**
```json
{
  "trigger_type": "learnpack_completed",
  "template": {{template_id}},
  "is_active": true,
  "asset_slugs": ["learnpack-javascript-basics", "learnpack-react-intro"],
  "cohorts": [],
  "syllabus": {}
}
```

**Example Configuration (All Learnpacks):**
```json
{
  "trigger_type": "learnpack_completed",
  "template": {{template_id}},
  "is_active": true,
  "asset_slugs": [],
  "cohorts": [],
  "syllabus": {}
}
```

### 4. `"course_completed"` - Course Completion
- **Triggers when**: A user completes all mandatory tasks in a SaaS cohort
- **Filtering**: Use `cohorts` ManyToMany field to filter by specific cohorts
- **If `cohorts` is empty**: Applies to all cohorts
- **Use case**: Survey students after graduating from a cohort

**Example Configuration (Specific Cohorts):**
```json
{
  "trigger_type": "course_completed",
  "template": {{template_id}},
  "is_active": true,
  "cohorts": [123, 456, 789],
  "asset_slugs": [],
  "syllabus": {}
}
```

**Example Configuration (All Cohorts):**
```json
{
  "trigger_type": "course_completed",
  "template": {{template_id}},
  "is_active": true,
  "cohorts": [],
  "asset_slugs": [],
  "syllabus": {}
}
```

### 5. `null` - No Trigger (Email/List-based Studies)
- **Use case**: For email/list-based studies where surveys are sent manually via the `send_emails` endpoint
- **Not for**: Real-time automatic triggering
- **When to use**: When you want to manually send surveys to a list of users or cohorts

**Example Configuration:**
```json
{
  "trigger_type": null,
  "template": {{template_id}},
  "is_active": true,
  "cohorts": [],
  "asset_slugs": [],
  "syllabus": {}
}
```

**Note**: For `null` trigger types, surveys are not automatically triggered. You must manually send them using the `POST /v1/feedback/academy/survey/study/{{study_id}}/send_emails` endpoint.

### Important Rules

- **All configurations in a study must have the same `trigger_type`**: If you need different trigger types, create separate studies
- **The `priority` field is only used for `module_completed` triggers**: For other trigger types, `priority` is ignored
- **Trigger types are case-sensitive**: Use the exact string values shown above
- **Filtering fields**:
  - `syllabus`: Used for `module_completed` and `syllabus_completed` triggers
  - `asset_slugs`: Used for `learnpack_completed` triggers
  - `cohorts`: Used for `course_completed`, `module_completed`, and `syllabus_completed` triggers

---

## Step 1: Create a Survey Question Template (Optional but Recommended)

Create a reusable template for your questions. This makes it easier to reuse the same questions across multiple configurations.

**Endpoint:** `POST /v1/feedback/academy/survey/question_template`

**Headers:**
- `Authorization: Token {{token}}`
- `Academy: {{academy_id}}`
- `Content-Type: application/json`

**Request Body:**
```json
{
  "slug": "syllabus-completion-v1",
  "title": "Syllabus Completion Survey",
  "description": "Survey when students complete the entire syllabus",
  "questions": {
    "questions": [
      {
        "id": "q1",
        "type": "likert_scale",
        "required": true,
        "title": {
          "en": "How satisfied are you with the overall course?",
          "es": "¿Qué tan satisfecho estás con el curso en general?"
        },
        "config": {
          "scale": 5,
          "labels": {
            "1": "Very unsatisfied",
            "5": "Very satisfied"
          }
        }
      },
      {
        "id": "q2",
        "type": "open_question",
        "required": false,
        "title": {
          "en": "What did you like most about the course?",
          "es": "¿Qué te gustó más del curso?"
        },
        "config": {
          "max_length": 500
        }
      }
    ]
  }
}
```

**Response:** Save the `id` from the response as `{{template_id}}` for use in Step 2.

---

## Step 2: Create a Survey Configuration

Create a configuration that triggers when the syllabus is completed.

**Endpoint:** `POST /v1/feedback/academy/survey/configuration`

**Headers:**
- `Authorization: Token {{token}}`
- `Academy: {{academy_id}}`
- `Content-Type: application/json`

### Option A: Using a Template (Recommended)

**Request Body:**
```json
{
  "trigger_type": "syllabus_completed",
  "template": {{template_id}},
  "is_active": true,
  "syllabus": {
    "syllabus": "full-stack",
    "version": 2
  },
  "cohorts": [],
  "asset_slugs": []
}
```

### Option B: Using Inline Questions

**Request Body:**
```json
{
  "trigger_type": "syllabus_completed",
  "is_active": true,
  "syllabus": {
    "syllabus": "full-stack",
    "version": 2
  },
  "cohorts": [],
  "asset_slugs": [],
  "questions": {
    "questions": [
      {
        "id": "q1",
        "type": "likert_scale",
        "required": true,
        "title": "How satisfied are you?",
        "config": {
          "scale": 5,
          "labels": {
            "1": "Very unsatisfied",
            "5": "Very satisfied"
          }
        }
      },
      {
        "id": "q2",
        "type": "open_question",
        "required": false,
        "title": "What would you improve?",
        "config": {
          "max_length": 500
        }
      }
    ]
  }
}
```

### Important Configuration Fields:

- **`trigger_type`**: Must be `"syllabus_completed"` for syllabus completion surveys
- **`syllabus`**: Filter object that specifies which syllabus to target:
  - `"syllabus"`: The syllabus slug (e.g., `"full-stack"`)
  - `"version"`: Optional, specific version number (integer)
  - **Do NOT include `"module"`** - that's only for module completion surveys
- **`cohorts`**: 
  - Empty array `[]` = applies to all cohorts
  - Array of cohort IDs = only applies to those specific cohorts
- **`asset_slugs`**: Not used for syllabus completion (leave as empty array `[]`)
- **`is_active`**: Must be `true` for the survey to trigger

**Response:** Save the `id` from the response as `{{configuration_id}}` for use in Step 3.

---

## Step 3: Create a Survey Study

Create a study to group your configuration. Studies provide study-level constraints and statistics tracking.

**Endpoint:** `POST /v1/feedback/academy/survey/study`

**Headers:**
- `Authorization: Token {{token}}`
- `Academy: {{academy_id}}`
- `Content-Type: application/json`

**Request Body:**
```json
{
  "slug": "syllabus-completion-study-2025",
  "title": "Syllabus Completion Study - 2025",
  "description": "Study for tracking syllabus completion feedback",
  "starts_at": "2025-01-01T00:00:00Z",
  "ends_at": null,
  "max_responses": null,
  "survey_configurations": [{{configuration_id}}]
}
```

### Study Fields Explained:

- **`slug`**: Unique identifier for the study (URL-friendly)
- **`title`**: Human-readable title
- **`description`**: Optional description
- **`starts_at`**: Optional start date/time (ISO 8601 format). If `null`, study starts immediately
- **`ends_at`**: Optional end date/time. If `null`, study has no end date
- **`max_responses`**: Optional maximum number of ANSWERED responses allowed. If `null`, unlimited
- **`survey_configurations`**: Array containing your configuration ID(s)

**Response:** Save the `id` from the response as `{{study_id}}` for monitoring.

---

## Step 4: Verify the Setup

Check that your study is properly configured:

**Endpoint:** `GET /v1/feedback/academy/survey/study/{{study_id}}`

**Headers:**
- `Authorization: Token {{token}}`
- `Academy: {{academy_id}}`

The response should show your study with the configuration included.

---

## How It Works

### Automatic Triggering

When a user completes all modules in a syllabus, the system automatically:

1. **Detects completion**: The system checks if ALL modules in the syllabus are complete using `_is_syllabus_complete()`
2. **Finds active studies**: Looks for active `SurveyStudy` instances with `syllabus_completed` trigger type
3. **Matches filters**: Checks if the user's syllabus slug and version match your configuration
4. **Creates response**: Creates a `SurveyResponse` and sends a Pusher event to show the survey in real-time

### Syllabus Filtering

Your configuration will match when:

- **Syllabus slug matches**: If you specified `"syllabus": "full-stack"`, it only matches that syllabus
- **Syllabus version matches**: If you specified `"version": 2`, it only matches version 2
- **Cohort matches**: If you specified `cohorts: [123, 456]`, it only matches those cohorts. If `cohorts: []`, it matches all cohorts

### One Survey Per User Per Study

**Important**: Each user can receive only **one survey per study**, even if they complete multiple syllabi. This prevents duplicate surveys.

---

## Example: Multiple Syllabi

If you want to study multiple syllabi, create separate configurations and add them to the same study:

**Step 2 (repeated for each syllabus):**
```json
{
  "trigger_type": "syllabus_completed",
  "template": {{template_id}},
  "is_active": true,
  "syllabus": {
    "syllabus": "full-stack",
    "version": 2
  },
  "cohorts": [],
  "asset_slugs": []
}
```

```json
{
  "trigger_type": "syllabus_completed",
  "template": {{template_id}},
  "is_active": true,
  "syllabus": {
    "syllabus": "data-science",
    "version": 1
  },
  "cohorts": [],
  "asset_slugs": []
}
```

**Step 3 (create study with both configurations):**
```json
{
  "slug": "multi-syllabus-study",
  "title": "Multi-Syllabus Completion Study",
  "description": "Study for multiple syllabi",
  "survey_configurations": [
    {{config_id_syllabus_1}},
    {{config_id_syllabus_2}}
  ]
}
```

Users will be distributed across configurations using **round-robin** distribution to ensure equitable split.

---

## Monitoring Your Study

### View Study Statistics

**Endpoint:** `GET /v1/feedback/academy/survey/study/{{study_id}}`

The response includes a `stats` field with aggregated statistics:

```json
{
  "id": 1,
  "slug": "syllabus-completion-study-2025",
  "stats": {
    "sent": 150,
    "opened": 120,
    "partial_responses": 10,
    "responses": 100,
    "email_opened": 80,
    "updated_at": "2025-01-15T10:30:00Z"
  }
}
```

**Statistics Explained:**
- **`sent`**: Total number of `SurveyResponse` objects created
- **`opened`**: Number of responses that were opened by users
- **`partial_responses`**: Number of partially completed responses
- **`responses`**: Number of fully answered responses
- **`email_opened`**: Number of survey emails that were opened (if using email campaigns)

### View Individual Responses

**Endpoint:** `GET /v1/feedback/academy/survey/response?survey_config={{configuration_id}}`

**Query Parameters:**
- `survey_config`: Filter by configuration ID
- `cohort_id`: Filter by cohort ID
- `status`: Filter by status (`PENDING`, `OPENED`, `PARTIAL`, `ANSWERED`, `EXPIRED`)
- `user`: Filter by user ID

---

## Important Reminders

1. **All configurations in a study must have the same `trigger_type`**: Since you're using `syllabus_completed`, all configurations in your study must use `syllabus_completed`. If you need different trigger types, create separate studies.

2. **Do NOT include `"module"` in the syllabus filter**: The `module` field is only for module completion surveys. For syllabus completion, omit it entirely.

3. **Set `is_active: true`**: Your configuration must be active for surveys to trigger.

4. **Automatic triggering**: The system automatically triggers surveys when users complete the syllabus. You don't need to manually send surveys.

5. **Time windows**: Use `starts_at` and `ends_at` to control when the study is active. Surveys will only trigger during the active period.

6. **Response limits**: Use `max_responses` to limit the total number of answered responses. Once the limit is reached, no new surveys will be created.

---

## Troubleshooting

### Surveys Not Triggering

1. **Check configuration is active**: Verify `is_active: true` in your configuration
2. **Check study time window**: Verify `starts_at` and `ends_at` allow the study to be active
3. **Check syllabus filter**: Verify the syllabus slug and version match what students are actually using
4. **Check cohort filter**: If you specified cohorts, verify students are in those cohorts
5. **Check syllabus completion**: Verify students have actually completed ALL modules in the syllabus

### Viewing Survey Responses

Use the staff endpoint to view responses:
```
GET /v1/feedback/academy/survey/response?survey_config={{configuration_id}}
```

### Testing

To test your setup, you can:
1. Complete a syllabus as a test user
2. Check if a `SurveyResponse` was created
3. Verify the response appears in the study statistics

---

## Related Documentation

- **API Endpoints**: See `docs/LLM-DOCS/SURVEYS_POSTMAN_CHECKLIST.md` for complete API reference
- **Question Types**: See question type documentation for available question formats
- **Module Completion**: For module-level surveys, use `trigger_type: "module_completed"` instead
