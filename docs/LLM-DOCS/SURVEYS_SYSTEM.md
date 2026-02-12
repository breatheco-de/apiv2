# Survey System - Complete Documentation

## Overview

The Survey System is a real-time, event-driven feedback collection system that allows administrators to configure surveys that are automatically triggered when students complete specific actions (like finishing a learnpack or course). Surveys are delivered in real-time via Pusher, and responses are stored in the database and forwarded to external systems via webhooks.

### Key Features

- **Admin-Configurable Triggers**: Admins can define when surveys are sent (learnpack completion, course completion, module completion, syllabus completion)
- **Real-Time Delivery**: Surveys are pushed to users via Pusher channels
- **Flexible Question Types**: Supports Likert scale, open-ended questions, and extensible JSON structure for future types
- **Advanced Filtering**: Surveys can be filtered by specific cohorts, learnpacks, syllabi, modules, or academies
- **Module & Syllabus Completion Detection**: Automatically detects when users complete modules or entire syllabi across all activity types (QUIZ, LESSON, EXERCISE, PROJECT)
- **One Survey Per User Per Study**: Guarantees that each user receives only one survey per study, preventing duplicate surveys
- **Equitable Distribution (Round-Robin)**: When a study has multiple configurations, users are distributed equitably across them using a round-robin algorithm based on the last N responses
- **Webhook Integration**: Responses are automatically sent to n8n or other webhook subscribers
- **Scalable Architecture**: Easy to add new trigger types without modifying existing code

---

## Architecture

### Components

1. **Models** (`breathecode/feedback/models.py`)
   - `SurveyConfiguration`: Defines when and how surveys are triggered
   - `SurveyResponse`: Stores user responses to surveys

2. **Actions** (`breathecode/feedback/actions.py`)
   - `trigger_survey_for_user()`: Main function to trigger surveys (wrapper around SurveyManager)
   - `create_survey_response()`: Creates survey response and sends Pusher event
   - `save_survey_answers()`: Validates and saves user answers
   - `has_active_survey_studies()`: Helper to check if active studies exist (optimization)
   - `_find_module_for_asset_in_syllabus()`: Finds module index for an asset
   - `_get_module_assets_from_syllabus()`: Gets all assets in a module
   - `_is_module_complete()`: Checks if a module is complete
   - `_is_syllabus_complete()`: Checks if entire syllabus is complete

3. **SurveyManager** (`breathecode/feedback/utils/survey_manager.py`)
   - `SurveyManager`: Centralized class for handling survey triggers and filtering logic
   - Handles validation, academy resolution, filtering, deduplication, and response creation

3. **Services** (`breathecode/feedback/services/pusher_service.py`)
   - `send_survey_event()`: Sends real-time events via Pusher

4. **Views** (`breathecode/feedback/views.py`)
   - `SurveyConfigurationView`: Admin CRUD for survey configurations
   - `SurveyResponseView`: User endpoints to view and answer surveys

5. **Signals & Receivers** (`breathecode/feedback/signals.py`, `breathecode/admissions/receivers.py`)
   - `survey_response_answered`: Signal fired when user answers
   - `trigger_module_survey_on_completion`: Receiver for `assignment_status_updated` signal that detects module/syllabus completion
   - Webhook integration via `HookManager`

---

## Data Models

### SurveyConfiguration

Defines when and how surveys are triggered.

**Fields:**
- `trigger_type`: Type of event that triggers the survey (`learnpack_completed`, `course_completed`, `module_completed`, `syllabus_completed`)
- `template`: Optional FK to `SurveyQuestionTemplate`. If set, questions are sourced from the template.
- `questions`: JSON structure containing survey questions
- `is_active`: Whether this configuration is active
- `academy`: Academy this survey applies to
- `cohorts`: ManyToMany - If empty, applies to all cohorts. If set, only to specified cohorts
- `asset_slugs`: JSON array - If empty, applies to all learnpacks. If set, only to specified learnpacks
- `syllabus`: JSON field for filtering by syllabus/module. Shape: `{'syllabus': '<slug>', 'version': <int>, 'module': <int>, 'asset_slug': '<slug>'}`. All keys optional.
- `priority`: **CUMULATIVE TARGET (0-100)** - The percentage of ALL users who should have received a survey by the time they complete this module. This is NOT a direct probability, but a cumulative distribution target. **ONLY used for MODULE_COMPLETION triggers** - ignored for other trigger types. See "Module Completion Survey Distribution: Conditional Hazard-Based Sampling" section below for detailed explanation.
- `created_by`: User who created the configuration
- `created_at`, `updated_at`: Timestamps

**Important behavior (template vs inline questions):**
- If `template != null`, then `questions` are sourced from the template and **must not be edited** via API (or Admin) to avoid divergence.
- If `template == null`, then `questions` must be provided.

**Stats:**
- Aggregated stats are stored on `SurveyStudy.stats` (not on `SurveyConfiguration`).

**Example (Learnpack Completion):**
```json
{
  "trigger_type": "learnpack_completed",
  "questions": {
    "questions": [
      {
        "id": "q1",
        "type": "likert_scale",
        "title": "How satisfied are you?",
        "required": true,
        "config": {
          "scale": 5,
          "labels": {
            "1": "Very unsatisfied",
            "5": "Very satisfied"
          }
        }
      }
    ]
  },
  "is_active": true,
  "asset_slugs": ["learnpack-test"]
}
```

**Example (Module Completion with Syllabus Filter):**
```json
{
  "trigger_type": "module_completed",
  "questions": {
    "questions": [...]
  },
  "is_active": true,
  "syllabus": {
    "syllabus": "full-stack",
    "version": 2,
    "module": 3
  },
  "cohorts": []
}
```

**Example (Syllabus Completion):**
```json
{
  "trigger_type": "syllabus_completed",
  "questions": {
    "questions": [...]
  },
  "is_active": true,
  "syllabus": {
    "syllabus": "full-stack",
    "version": 2
  }
}
```

### SurveyResponse

Stores individual user responses to surveys.

**Fields:**
- `survey_config`: ForeignKey to SurveyConfiguration (which configuration was used)
- `survey_study`: ForeignKey to SurveyStudy (which study this response belongs to)
  - **Important**: This field is always populated when a survey is triggered via `SurveyManager`
  - Used for: round-robin distribution, ensuring 1 survey per user per study, and study-level analytics
- `user`: ForeignKey to User
- `token`: UUID token used for email links / direct navigation
- `trigger_context`: JSON with context about what triggered the survey
- `questions_snapshot`: Optional snapshot of the questions used (immutability)
- `answers`: JSON with user's answers (null until answered)
- `status`: PENDING, OPENED, PARTIAL, ANSWERED, or EXPIRED
- `created_at`: When survey was created
- `opened_at`: First time the user opened the survey (set once)
- `email_opened_at`: First time the user opened the survey email (set once)
- `answered_at`: When user answered (null until answered)

**Key Relationships:**
- Each `SurveyResponse` belongs to exactly one `SurveyConfiguration` and one `SurveyStudy`
- The `survey_study` field is critical for:
  - Ensuring only 1 survey per user per study
  - Round-robin distribution across multiple configurations
  - Study-level statistics and analytics

### SurveyQuestionTemplate

Reusable questions template for the new SurveyConfiguration/SurveyResponse system.

**Fields:**
- `slug`, `title`, `description`
- `questions`: JSON structure (same shape as SurveyConfiguration.questions)
- `created_at`, `updated_at`

### SurveyStudy

Groups one or more SurveyConfigurations for a given academy.

**Fields:**
- `academy`
- `slug`, `title`, `description`
- `starts_at`, `ends_at`
- `max_responses` (optional)
- `survey_configurations` (ManyToMany)
- `stats`: JSON aggregated stats (sent/opened/partial/responses/email_opened)

---

## Trigger Types

### Learnpack Completion

**Trigger:** When a user completes a learnpack (completion_rate >= 99.999)

**Location:** `breathecode/assignments/actions.py` → `calculate_telemetry_indicator()`

**Context:**
```python
{
    "asset_slug": "learnpack-test",
    "completion_rate": 99.999,
    "completed_at": "2024-01-01T00:00:00Z"
}
```

**Filtering:**
- If `asset_slugs` is empty: applies to all learnpacks
- If `asset_slugs` has values: only applies to those specific learnpacks

### Course Completion

**Trigger:** When a user completes all mandatory tasks in a SaaS cohort

**Location:** `breathecode/admissions/receivers.py` → `mark_saas_student_as_graduated()`

**Context:**
```python
{
    "cohort": cohort_object,
    "cohort_id": 123,
    "cohort_slug": "cohort-slug",
    "completed_at": "2024-01-01T00:00:00Z"
}
```

**Filtering:**
- If `cohorts` is empty: applies to all cohorts
- If `cohorts` has values: only applies to those specific cohorts

### Module Completion

**Trigger:** When a user completes all activities (QUIZ, LESSON, EXERCISE, PROJECT) in a specific module of a syllabus

**Location:** `breathecode/admissions/receivers.py` → `trigger_module_survey_on_completion()`

**How it works:**
1. Triggered when ANY task (QUIZ, LESSON, EXERCISE, PROJECT) is marked as `DONE`
2. System finds which module the task belongs to using `_find_module_for_asset_in_syllabus()`
3. System checks if ALL activities in that module are complete using `_is_module_complete()`
4. If complete, triggers the survey

**Context:**
```python
{
    "academy": academy_object,
    "cohort": cohort_object,
    "cohort_id": 123,
    "cohort_slug": "web-dev-2024-01",
    "syllabus_slug": "full-stack",
    "syllabus_version": 2,
    "module": 2,  # 0-based index (module 3)
    "asset_slug": "javascript-basics",
    "task_type": "EXERCISE",
    "completed_at": "2024-01-15T10:30:00Z"
}
```

**Filtering:**
- `syllabus.syllabus`: Filter by syllabus slug
- `syllabus.version`: Filter by syllabus version
- `syllabus.module`: Filter by specific module (0-based index)
- `cohorts`: Filter by specific cohorts (if set)

**Note:** Module completion considers ALL activity types (QUIZ, LESSON, EXERCISE, PROJECT), not just learnpacks.

### Syllabus Completion

**Trigger:** When a user completes ALL modules in a syllabus

**Location:** `breathecode/admissions/receivers.py` → `trigger_module_survey_on_completion()`

**How it works:**
1. Triggered when ANY task is marked as `DONE`
2. System checks if ALL modules in the syllabus are complete using `_is_syllabus_complete()`
3. If complete, triggers the survey

**Context:**
```python
{
    "academy": academy_object,
    "cohort": cohort_object,
    "cohort_id": 123,
    "cohort_slug": "web-dev-2024-01",
    "syllabus_slug": "full-stack",
    "syllabus_version": 2,
    "completed_at": "2024-01-15T10:30:00Z"
}
```

**Filtering:**
- `syllabus.syllabus`: Filter by syllabus slug
- `syllabus.version`: Filter by syllabus version
- `cohorts`: Filter by specific cohorts (if set)

**Note:** Syllabus completion is checked on EVERY task completion, but only triggers once when all modules are complete.

---

## Module Completion Survey Distribution: Conditional Hazard-Based Sampling

### Overview

For `MODULE_COMPLETION` triggers, the system uses **Conditional Hazard-Based Sampling** with cumulative priorities to distribute surveys across different modules. This ensures that surveys are distributed according to target percentages while maintaining fairness and consistency.

### Key Concepts

1. **Priority Field (Cumulative Target)**: The `priority` field (0-100) represents the **cumulative target percentage** of users who should have received a survey by the time they complete a specific module. This is NOT a direct probability, but a cumulative distribution target.

2. **Conditional Probability**: The system calculates conditional probabilities based on previous priorities to ensure the cumulative distribution is achieved.

3. **Deterministic Hash**: Each user gets a deterministic "random" value based on their user ID, study ID, and module number. This ensures consistency - the same user will always get the same result for the same module.

4. **One Survey Per User Per Study**: Each user can only receive ONE survey per study, regardless of how many modules they complete.

### How It Works

#### Step-by-Step Process

When a user completes a module:

1. **System identifies eligible configurations**: Only configurations for the current module or previous modules are considered.

2. **For each configuration (sorted by module)**:
   - Calculate conditional probability: `(current_priority - previous_priority) / (100.0 - previous_priority)`
   - Generate deterministic hash: `hash(f"{user.id}_{study.id}_{module}")`
   - Convert to 0-99 range: `abs(hash_value) % 100`
   - Compare: If `random_value < conditional_probability_percent`, user receives survey
   - If user receives survey, stop processing (1 survey per user per study)

3. **Update previous_priority**: Even if user doesn't receive survey, update `previous_priority` for next iteration.

#### Example Calculation

**Configuration:**
- Module 0: priority = 30%
- Module 1: priority = 60%
- Module 2: priority = 100%

**User completes Module 0:**
```
previous_priority = 0%
current_priority = 30%
conditional_probability = (30 - 0) / (100 - 0) = 30%

hash_input = f"{user.id}_{study.id}_0"
random_value = abs(hash(hash_input)) % 100  # Example: 15

Decision: 15 < 30? YES → User receives survey in Module 0
```

**User completes Module 1 (didn't receive survey in Module 0):**
```
previous_priority = 30%
current_priority = 60%
conditional_probability = (60 - 30) / (100 - 30) = 30/70 = 42.9%

hash_input = f"{user.id}_{study.id}_1"
random_value = abs(hash(hash_input)) % 100  # Example: 35

Decision: 35 < 42.9? YES → User receives survey in Module 1
```

**User completes Module 2 (didn't receive survey in Module 0 or 1):**
```
previous_priority = 60%
current_priority = 100%
conditional_probability = (100 - 60) / (100 - 60) = 40/40 = 100%

hash_input = f"{user.id}_{study.id}_2"
random_value = abs(hash(hash_input)) % 100  # Example: 75

Decision: 75 < 100? YES → User receives survey in Module 2
```

### Deterministic Hash Explained

The `random_value` is **NOT truly random** - it's deterministic based on:
- User ID
- Study ID
- Module number

**Why deterministic?**
- **Consistency**: Same user always gets same result for same module
- **Reproducibility**: Can predict who will receive surveys
- **No state needed**: Doesn't need to store which users were selected
- **Uniform distribution**: Hash distributes values uniformly across 0-99

**Hash Calculation:**
```python
hash_input = f"{user.id}_{study.id}_{module}"
hash_value = hash(hash_input)  # Python's built-in hash function
random_value = abs(hash_value) % 100  # Convert to 0-99 range
```

**Important**: Each module has a different hash input, so the same user can get different `random_value` for different modules.

### Real-World Scenarios

#### Scenario 1: Variable User Completion

**Situation**: 50 users in cohort, but only 10 complete all modules.

**How it works**:
- System only evaluates users who complete modules
- If only 10 users complete Module 2, all 10 will receive surveys (priority 100%)
- The algorithm adapts automatically to the actual number of users completing modules

**Key Point**: Priorities are **targets**, not guarantees. The system distributes surveys among users who actually complete modules, not a fixed total.

#### Scenario 2: Users Joining at Different Times

**Situation**: 30 users start at study beginning, 20 users join during study.

**How it works**:
- Users who join early complete modules earlier
- Users who join late may not complete all modules by study end
- System evaluates each user when they complete a module
- Users who complete modules receive surveys according to priorities
- Users who don't complete modules never receive surveys (no event to trigger)

**Key Point**: The system is **reactive** - it only acts when users complete modules. It cannot send surveys to users who haven't completed modules.

#### Scenario 3: Multiple Cohorts, Same Syllabus

**Situation**: Same syllabus used in 5 different cohorts, 1000 total users.

**How it works**:
- Each user is evaluated independently when they complete a module
- Hash is based on `user.id + study.id + module`, so same user in different cohorts gets different results
- System doesn't need to know total users - it works user-by-user
- Priorities are targets for distribution, not absolute numbers

**Key Point**: The system doesn't require a "total expected users" - it works with whatever users actually complete modules.

### Priority Field: Detailed Explanation

The `priority` field is **ONLY used for MODULE_COMPLETION triggers**. For other trigger types (`COURSE_COMPLETION`, `LEARNPACK_COMPLETION`, `SYLLABUS_COMPLETION`), the priority field is ignored.

**Important Rules:**
1. All configurations in a study must have the same `trigger_type`
2. Priorities should generally be non-decreasing (Module 0: 30%, Module 1: 60%, Module 2: 100%)
3. Priority values are cumulative targets, not direct probabilities
4. The system uses conditional probabilities to achieve cumulative distribution

**Example Priority Configurations:**

**Equitable Distribution (~33% per module):**
- Module 0: priority = 33%
- Module 1: priority = 66%
- Module 2: priority = 100%
- Result: ~33% in Module 0, ~33% in Module 1, ~34% in Module 2

**Early Distribution (more surveys at start):**
- Module 0: priority = 50%
- Module 1: priority = 80%
- Module 2: priority = 100%
- Result: ~50% in Module 0, ~30% in Module 1, ~20% in Module 2

**Late Distribution (more surveys at end):**
- Module 0: priority = 20%
- Module 1: priority = 50%
- Module 2: priority = 100%
- Result: ~20% in Module 0, ~30% in Module 1, ~50% in Module 2

### Limitations and Considerations

1. **No Fixed Total**: The system doesn't require knowing total expected users. It works with whatever users actually complete modules.

2. **Reactive System**: Surveys are only sent when users complete modules. Users who don't complete modules never receive surveys.

3. **Hash Variation**: The deterministic hash may cause slight variations from exact percentages (±5-10% is normal).

4. **One Survey Per Study**: Once a user receives a survey in a study, they won't receive another survey in that study, even if they complete more modules.

5. **Adaptive Distribution**: If few users complete modules, all will receive surveys. If many users complete modules, distribution follows priorities.

### Testing

Use the management command to test survey distribution:

```bash
python manage.py test_survey_distribution \
  --study-id 14 \
  --users 50 \
  --new-users-during-study 20 \
  --new-users-join-period-days 30 \
  --module-completion-days 7
```

This simulates:
- Initial users joining at study start
- New users joining during study
- Users completing modules at different times
- Survey distribution according to priorities

See `breathecode/feedback/management/commands/test_survey_distribution.py` for details.

---

## Question Types

### Supported Types (Current)

At the moment, the system only supports these question types:

- `likert_scale`
- `open_question`

Anything else will not be validated/supported by the backend answer validation logic.

### Likert Scale

**Structure:**
```json
{
  "id": "q1",
  "type": "likert_scale",
  "title": "How satisfied are you?",
  "required": true,
  "config": {
    "scale": 5,
    "labels": {
      "1": "Very unsatisfied",
      "2": "Unsatisfied",
      "3": "Neutral",
      "4": "Satisfied",
      "5": "Very satisfied"
    }
  }
}
```

**Bilingual (recommended, for frontend i18n):**
```json
{
  "id": "q1",
  "type": "likert_scale",
  "title": {
    "en": "How satisfied are you?",
    "es": "¿Qué tan satisfecho/a estás?"
  },
  "required": true,
  "config": {
    "scale": 5,
    "labels": {
      "en": {
        "1": "Very unsatisfied",
        "2": "Unsatisfied",
        "3": "Neutral",
        "4": "Satisfied",
        "5": "Very satisfied"
      },
      "es": {
        "1": "Muy insatisfecho/a",
        "2": "Insatisfecho/a",
        "3": "Neutral",
        "4": "Satisfecho/a",
        "5": "Muy satisfecho/a"
      }
    }
  }
}
```

**Validation:**
- Answer must be an integer between 1 and `scale`
- Required if `required: true`

### Open Question

**Structure:**
```json
{
  "id": "q2",
  "type": "open_question",
  "title": "What would you improve?",
  "required": false,
  "config": {
    "max_length": 500
  }
}
```

**Bilingual (recommended, for frontend i18n):**
```json
{
  "id": "q2",
  "type": "open_question",
  "title": {
    "en": "What would you improve?",
    "es": "¿Qué mejorarías?"
  },
  "required": false,
  "config": {
    "max_length": 500
  }
}
```

**Validation:**
- Answer must be a string
- Length must not exceed `max_length`
- Required if `required: true`

---

## API Endpoints

### Base URL and Required Headers (Postman-friendly)

All endpoints below are under:

- `{{base_url}}/v1/...`

When an endpoint is academy-scoped and uses `@capable_of(...)`, you must provide the academy via one of:

- `Academy: {{academy_id}}` header (recommended)
- `?academy={{academy_id}}` querystring

And authentication is typically:

- `Authorization: Token {{token}}`

### Admin/Staff Endpoints

#### Create Survey Configuration

**Method:** `POST`

**URL:** `{{base_url}}/v1/feedback/academy/survey/configuration`

**Permissions:** `crud_survey`

**Headers:**
- `Authorization: Token {{token}}`
- `Academy: {{academy_id}}`
- `Content-Type: application/json`

**Request:**
```json
{
  "trigger_type": "learnpack_completed",
  "questions": {
    "questions": [...]
  },
  "is_active": true,
  "asset_slugs": [],
  "cohorts": [],
  "syllabus": {}
}
```

**Request (Module Completion with Syllabus Filter):**
```json
{
  "trigger_type": "module_completed",
  "questions": {
    "questions": [...]
  },
  "is_active": true,
  "syllabus": {
    "syllabus": "full-stack",
    "version": 2,
    "module": 3
  },
  "cohorts": []
}
```

**Request (Syllabus Completion):**
```json
{
  "trigger_type": "syllabus_completed",
  "questions": {
    "questions": [...]
  },
  "is_active": true,
  "syllabus": {
    "syllabus": "full-stack",
    "version": 2
  },
  "cohorts": []
}
```

**Alternative: create using a template (no inline questions):**
```json
{
  "trigger_type": "course_completed",
  "template": {{template_id}},
  "is_active": true,
  "asset_slugs": [],
  "cohorts": [{{cohort_id}}]
}
```

#### List Survey Configurations

**Method:** `GET`

**URL:** `{{base_url}}/v1/feedback/academy/survey/configuration`

**Permissions:** `read_survey`

**Headers:**
- `Authorization: Token {{token}}`
- `Academy: {{academy_id}}`

**Query Parameters:**
- `trigger_type`: Filter by trigger type
- `id`: Filter by ID

#### Get Survey Configuration

**Method:** `GET`

**URL:** `{{base_url}}/v1/feedback/academy/survey/configuration/{{configuration_id}}`

**Permissions:** `read_survey`

**Headers:**
- `Authorization: Token {{token}}`
- `Academy: {{academy_id}}`

#### Update Survey Configuration

**Method:** `PUT`

**URL:** `{{base_url}}/v1/feedback/academy/survey/configuration/{{configuration_id}}`

**Permissions:** `crud_survey`

**Headers:**
- `Authorization: Token {{token}}`
- `Academy: {{academy_id}}`
- `Content-Type: application/json`

**Common use case: update questions JSON**

First do a GET to copy the existing structure, then PUT the updated `questions`.

**Important:**
- If the configuration has `template != null`, you **cannot** send `"questions"` in the PUT (the API should reject it).

```json
{
  "questions": {
    "questions": [
      {
        "id": "q1",
        "type": "likert_scale",
        "required": true,
        "title": { "en": "Question in English", "es": "Pregunta en Español" },
        "config": {
          "scale": 5,
          "labels": {
            "en": { "1": "Strongly disagree", "2": "Disagree", "3": "Neutral", "4": "Agree", "5": "Strongly agree" },
            "es": { "1": "Totalmente en desacuerdo", "2": "En desacuerdo", "3": "Neutral", "4": "De acuerdo", "5": "Totalmente de acuerdo" }
          }
        }
      }
    ]
  }
}
```

#### List Survey Responses (Staff) with Filters

This endpoint is meant for staff/admin analytics and auditing.

**Method:** `GET`

**URL:** `{{base_url}}/v1/feedback/academy/survey/response`

**Permissions:** `read_survey`

**Headers:**
- `Authorization: Token {{token}}`
- `Academy: {{academy_id}}`

**Query Parameters (optional):**
- `user`: user id (supports comma-separated values, e.g. `?user=8301,9000`)
- `survey_config`: SurveyConfiguration id (supports comma-separated values)
- `cohort_id`: Cohort id (from `trigger_context.cohort_id`)
- `cohort_ids`: comma-separated cohort ids
- `status`: `PENDING|ANSWERED|EXPIRED` (supports comma-separated values)

**Examples:**
- By student: `?user=8301`
- By cohort: `?cohort_id=1183`
- By config: `?survey_config=3`
- Answered only: `?status=ANSWERED`
- Combined: `?survey_config=3&cohort_id=1183&status=ANSWERED`

#### Get Survey Response by ID (Staff)

**Method:** `GET`

**URL:** `{{base_url}}/v1/feedback/academy/survey/response/{{response_id}}`

**Permissions:** `read_survey`

**Headers:**
- `Authorization: Token {{token}}`
- `Academy: {{academy_id}}`

#### SurveyQuestionTemplate CRUD (Staff)

Templates are global, but still require academy-scoped capability checks via the `Academy` header.

- **List**: `GET {{base_url}}/v1/feedback/academy/survey/question_template`
- **Retrieve**: `GET {{base_url}}/v1/feedback/academy/survey/question_template/{{template_id}}`
- **Create**: `POST {{base_url}}/v1/feedback/academy/survey/question_template`
- **Update (partial)**: `PUT {{base_url}}/v1/feedback/academy/survey/question_template/{{template_id}}`
- **Delete**: `DELETE {{base_url}}/v1/feedback/academy/survey/question_template/{{template_id}}`

Headers (all above):
- `Authorization: Token {{token}}`
- `Academy: {{academy_id}}`
- `Content-Type: application/json` (for POST/PUT)

#### SurveyStudy CRUD + bulk email sending (Staff)

- **List**: `GET {{base_url}}/v1/feedback/academy/survey/study`
- **Retrieve**: `GET {{base_url}}/v1/feedback/academy/survey/study/{{study_id}}`
- **Create**: `POST {{base_url}}/v1/feedback/academy/survey/study`
- **Update (partial)**: `PUT {{base_url}}/v1/feedback/academy/survey/study/{{study_id}}`
- **Delete**: `DELETE {{base_url}}/v1/feedback/academy/survey/study/{{study_id}}`

Headers (all above):
- `Authorization: Token {{token}}`
- `Academy: {{academy_id}}`
- `Content-Type: application/json` (for POST/PUT)

**Bulk send (study → list of users)**:

- **Method**: `POST`
- **URL**: `{{base_url}}/v1/feedback/academy/survey/study/{{study_id}}/send_emails`
- **Permissions**: `crud_survey`
- **Body**:

```json
{
  "user_ids": [8301, 8302, 8303],
  "callback": "https://your-frontend.com/after-survey",
  "dry_run": false
}
```

**Bulk send (study → all students in a cohort)**:

```json
{
  "cohort_id": {{cohort_id}},
  "callback": "https://your-frontend.com/after-survey",
  "dry_run": false
}
```

Behavior:
- Creates **one `SurveyResponse` per (study, user)** if missing.
- If the study has multiple configs, assigns users **round-robin** across them (based on user_id modulo number of configs).
- Enqueues `send_survey_response_email` which sends an email containing the `SurveyResponse.token` link.
- If `callback` is provided, it is stored in `SurveyResponse.trigger_context.callback` and appended to the email link as `?callback=...`.

**Note:** For real-time triggers (via `SurveyManager`), the round-robin algorithm is different and based on the last N responses (where N = number of configs), ensuring true rotation. See "Distribution and Round-Robin" section below.

### User Endpoints

#### Get Survey Response

**Method:** `GET`

**URL:** `{{base_url}}/v1/feedback/user/me/survey/response/{{response_id}}`

**Authentication:** Required (user can only see their own)

**Response:**
```json
{
  "id": 1,
  "survey_config": {...},
  "user": {...},
  "trigger_context": {...},
  "answers": null,
  "status": "PENDING",
  "created_at": "2024-01-01T00:00:00Z",
  "answered_at": null
}
```

#### Answer Survey
#### Get Survey Response by Token (for email links)

**Method:** `GET`

**URL:** `{{base_url}}/v1/feedback/survey/response/by_token/{{token}}`

**Authentication:** Required (user can only see their own response)

#### Mark Survey Response Opened

**Method:** `POST`

**URL:** `{{base_url}}/v1/feedback/survey/response/{{response_id}}/opened`

**Authentication:** Required (user can only update their own response)

#### Save Partial Answers (Draft)

**Method:** `POST`

**URL:** `{{base_url}}/v1/feedback/survey/response/{{response_id}}/partial`

**Authentication:** Required (user can only update their own response)

**Request:**
```json
{
  "answers": {
    "q1": 4,
    "q2": "draft text"
  }
}
```

#### Track Survey Email Open (pixel)

**Method:** `GET`

**URL:** `{{base_url}}/v1/feedback/survey/response/{{token}}/tracker.png`

This returns a 1x1 transparent pixel and sets `email_opened_at` only once.


**Method:** `POST`

**URL:** `{{base_url}}/v1/feedback/user/me/survey/response/{{response_id}}/answer`

**Authentication:** Required (user can only answer their own)

**Request:**
```json
{
  "answers": {
    "q1": 5,
    "q2": "Great experience!"
  }
}
```

**Response:** Updated SurveyResponse with `status: "ANSWERED"` and `answers` populated

---

## Real-Time Events (Pusher)

### Channel Format

**Public Channel:** `public-user-{user_id}`

**Example:** `public-user-123`

### Event Name

**Event:** `survey`

### Payload Structure

```json
{
  "survey_response_id": 1,
  "questions": [
    {
      "id": "q1",
      "type": "likert_scale",
      "title": "How satisfied are you?",
      ...
    }
  ],
  "trigger_context": {
    "trigger_type": "learnpack_completed",
    "asset_slug": "learnpack-test",
    ...
  }
}
```

### Frontend Integration

```javascript
const pusher = new Pusher('YOUR_PUSHER_KEY', {
  cluster: 'us2'
});

const channel = pusher.subscribe(`public-user-${userId}`);
channel.bind('survey', (data) => {
  // data.survey_response_id
  // data.questions
  // data.trigger_context
  // Show survey modal/form
});
```

---

## Webhook Integration

### Event Name

**Event:** `survey.survey_answered`

### Hook Registration

Hooks are registered via the `Hook` model in `breathecode.notify.models`.

**Example:**
```python
Hook.objects.create(
    event="survey.survey_answered",
    url="https://n8n.example.com/webhook/survey",
    academy=academy
)
```

### Payload Structure

The webhook payload is serialized using `SurveyResponseHookSerializer`:

```json
{
  "id": 1,
  "survey_response_id": 1,
  "user_id": 123,
  "user_email": "user@example.com",
  "trigger_type": "learnpack_completed",
  "trigger_action": "learnpack_completed",
  "trigger_context": {
    "asset_slug": "learnpack-test",
    "completion_rate": 99.999
  },
  "answers": {
    "q1": 5,
    "q2": "Great experience!"
  },
  "status": "ANSWERED",
  "answered_at": "2024-01-01T00:00:00Z",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Automatic Triggering

When a user answers a survey:
1. `save_survey_answers()` saves the response
2. Signal `survey_response_answered` is fired
3. Receiver `post_survey_response_answered()` calls `HookManager.find_and_fire_hook()`
4. All registered hooks for `survey.survey_answered` are triggered

---

## Flow Diagrams

### Survey Trigger Flow

```
User completes action (learnpack/course/module/syllabus)
    ↓
calculate_telemetry_indicator() or mark_saas_student_as_graduated() or trigger_module_survey_on_completion()
    ↓
trigger_survey_for_user(user, trigger_type, context)
    ↓
Create SurveyManager instance
    ↓
Validate user and trigger_type
    ↓
Resolve academy from context or user profile
    ↓
Find active SurveyConfiguration for trigger_type + academy
    ↓
Group configurations by active SurveyStudy
    ↓
For each study:
    ↓
    Check if user already has response for this study (1 per user per study)
    ↓
    If no existing response:
        ↓
        Get last N responses for this study (N = number of configs)
        ↓
        Apply round-robin: select config not used in last N responses
        ↓
        If all configs were used: continue rotation from most recent
        ↓
        Apply filters (syllabus/module, cohorts, asset_slugs)
        ↓
        Check for existing response (trigger-specific deduplication)
        ↓
        Create SurveyResponse (status: PENDING)
        ↓
        send_survey_event() via Pusher
        ↓
Frontend receives event and shows survey
```

### Module/Syllabus Completion Detection Flow

```
User completes ANY task (QUIZ, LESSON, EXERCISE, PROJECT)
    ↓
Task.task_status = DONE
    ↓
assignment_status_updated signal fired
    ↓
trigger_module_survey_on_completion() receiver
    ↓
Early check: has_active_survey_studies() for MODULE/SYLLABUS triggers
    ↓
Find module index: _find_module_for_asset_in_syllabus()
    ↓
Check module completion: _is_module_complete()
    ├─→ Get all assets in module (QUIZ, LESSON, EXERCISE, PROJECT)
    ├─→ Check if ALL have Task with status=DONE
    └─→ If complete → trigger MODULE_COMPLETION survey
    ↓
Check syllabus completion: _is_syllabus_complete()
    ├─→ For each module in syllabus
    ├─→ Check if module is complete
    └─→ If ALL complete → trigger SYLLABUS_COMPLETION survey
```

### Survey Response Flow

```
User sees survey in frontend
    ↓
User fills out answers
    ↓
POST /user/me/survey/response/{id}/answer
    ↓
save_survey_answers()
    ↓
Validate answers against questions
    ↓
Save answers to SurveyResponse
    ↓
Update status to ANSWERED
    ↓
Fire survey_response_answered signal
    ↓
HookManager triggers webhooks
    ↓
n8n/external system receives payload
```

---

## Filtering Logic

The filtering logic is centralized in the `SurveyManager` class (`breathecode/feedback/utils/survey_manager.py`).

### Cohort Filtering (Course, Module, Syllabus Completion)

```python
# In SurveyManager._filter_by_cohort()
cohort = context.get("cohort")
if cohort:
    if survey_config.cohorts.exists():
        # Only apply if cohort is in the list
        if cohort not in survey_config.cohorts.all():
            return False  # Filtered out
    # If cohorts is empty, apply to all cohorts
return True
```

### Asset Slug Filtering (Learnpack Completion)

```python
# In SurveyManager._filter_by_asset_slug()
asset_slug = context.get("asset_slug")
if asset_slug:
    if survey_config.asset_slugs:
        # Only apply if asset_slug is in the list
        if asset_slug not in survey_config.asset_slugs:
            return False  # Filtered out
    # If asset_slugs is empty, apply to all learnpacks
return True
```

### Syllabus/Module Filtering (Module, Syllabus Completion)

```python
# In SurveyManager._filter_by_syllabus_module()
syllabus_filter = survey_config.syllabus or {}

# Filter by syllabus slug
if syllabus_filter.get("syllabus") and context.get("syllabus_slug"):
    if syllabus_filter["syllabus"] != context["syllabus_slug"]:
        return False  # Filtered out

# Filter by syllabus version
if syllabus_filter.get("version") is not None and context.get("syllabus_version") is not None:
    if syllabus_filter["version"] != context["syllabus_version"]:
        return False  # Filtered out

# Filter by module (only for MODULE_COMPLETION)
if trigger_type == "module_completed":
    if syllabus_filter.get("module") is not None and context.get("module") is not None:
        if syllabus_filter["module"] != context["module"]:
            return False  # Filtered out

return True
```

**Filtering Rules:**
- If `syllabus` field is empty: applies to all syllabi/modules
- If `syllabus.syllabus` is set: only matches that syllabus slug
- If `syllabus.version` is set: only matches that version
- If `syllabus.module` is set (for MODULE_COMPLETION): only matches that specific module (0-based index)
- All filters are AND conditions (all must match)

---

## Validation Rules

### Survey Configuration

1. `questions` must be a dictionary
2. `questions.questions` must be a list
3. `questions.questions` must have at least one question
4. Each question must have: `id`, `type`, `title`
5. Likert scale: `config.scale` must be >= 1
6. Open question: `config.max_length` must be >= 1
7. `asset_slugs` must be a list (if provided)
8. `syllabus` must be a dictionary (if provided) with optional keys:
   - `syllabus`: string (syllabus slug)
   - `version`: integer >= 1
   - `module`: integer >= 0 (0-based module index)
   - `asset_slug`: string (not currently used for filtering)

### Survey Answers

1. Required questions must be answered
2. Likert scale answers must be integer between 1 and scale
3. Open question answers must be string and <= max_length
4. User can only answer their own surveys
5. Survey cannot be answered twice

---

## Extending the System

### Adding a New Trigger Type

1. **Add to Model:**
   ```python
   # In breathecode/feedback/models.py
   class TriggerType(models.TextChoices):
       MODULE_COMPLETION = "module_completed", "Module Completion"
       SYLLABUS_COMPLETION = "syllabus_completed", "Syllabus Completion"
       LEARNPACK_COMPLETION = "learnpack_completed", "Learnpack Completion"
       COURSE_COMPLETION = "course_completed", "Course Completion"
       NEW_TRIGGER = "new_trigger", "New Trigger"  # Add here
   ```

2. **Add Filtering Logic in SurveyManager:**
   ```python
   # In breathecode/feedback/utils/survey_manager.py
   # In SurveyManager._apply_filters()
   elif self.trigger_type == SurveyConfiguration.TriggerType.NEW_TRIGGER:
       # Add filtering logic here
       if not self._filter_by_custom_criteria(survey_config):
           return False
   ```

3. **Add Deduplication Logic (if needed):**
   ```python
   # In SurveyManager._check_deduplication()
   elif self.trigger_type == SurveyConfiguration.TriggerType.NEW_TRIGGER:
       # Add custom deduplication filters
       custom_field = self.context.get("custom_field")
       if custom_field is not None:
           dedupe_query = dedupe_query.filter(trigger_context__custom_field=custom_field)
   ```

4. **Call from Your Code:**
   ```python
   from breathecode.feedback import actions
   from breathecode.feedback.models import SurveyConfiguration
   
   actions.trigger_survey_for_user(
       user,
       SurveyConfiguration.TriggerType.NEW_TRIGGER,
       {"custom_context": "value"}
   )
   ```

### Adding a New Question Type

1. **Update Serializer Validation:**
   ```python
   # In SurveyConfigurationSerializer.validate_questions()
   elif question_type == "new_question_type":
       # Add validation logic
       pass
   ```

2. **Update Answer Validation:**
   ```python
   # In save_survey_answers()
   elif question_type == "new_question_type":
       # Add validation logic
       pass
   ```

3. **Frontend handles rendering** based on `type` field

---

## Security Considerations

### Permissions

- **Admin endpoints:** Require `crud_survey` or `read_survey` capabilities
- **User endpoints:** Users can only access their own survey responses
- **Academy isolation:** Admins can only manage surveys for their academy

### Data Validation

- All inputs are validated at serializer level
- Answers are validated against question configuration
- Race conditions prevented with `select_for_update()`

### Pusher Channels

- Currently using **public channels** (`public-user-{user_id}`)
- For production, consider migrating to **private channels** with authentication endpoint

---

## Performance Optimizations

### Query Optimization

- `prefetch_related("cohorts")` used to avoid N+1 queries
- `has_active_survey_studies()` early check before expensive module/syllabus completion logic
- Indexes recommended on:
  - `SurveyResponse(user, status)`
  - `SurveyConfiguration(trigger_type, is_active, academy)`
  - `Task(user, cohort, associated_slug, task_status)`

### Duplicate Prevention

- **One Survey Per User Per Study**: First check verifies if user already has any response (non-expired) for the study. If yes, no new survey is created.
- **Trigger-Specific Deduplication**: Additional check for existing responses with same trigger context:
  - `COURSE_COMPLETION`: filters by `cohort_id`
  - `SYLLABUS_COMPLETION`: filters by `syllabus_slug`, `syllabus_version`, `cohort_id`
  - `MODULE_COMPLETION`: filters by `syllabus_slug`, `syllabus_version`, `module`, `cohort_id`
- Prevents spam and duplicate surveys

### Early Exit Optimizations

- `has_active_survey_studies()` checks if any active studies exist before running expensive completion checks
- Used in:
  - `calculate_telemetry_indicator()` for learnpack completion
  - `trigger_module_survey_on_completion()` for module/syllabus completion

---

## Error Handling

### Common Errors

1. **Survey already answered:** `400 Bad Request` - `survey-already-answered`
2. **Missing required question:** `400 Bad Request` - `missing-required-question`
3. **Invalid answer format:** `400 Bad Request` - `invalid-likert-answer` / `invalid-open-answer-type`
4. **Survey not found:** `404 Not Found` - `survey-response-not-found`
5. **Permission denied:** `404 Not Found` - User doesn't own the survey

### Logging

- All errors are logged with context
- Pusher failures are logged but don't prevent survey creation
- Webhook failures are logged but don't prevent answer saving

---

## Testing

See `docs/LLM-DOCS/SURVEYS_TESTING.md` for complete testing guide.

---

## Distribution and Round-Robin

### One Survey Per User Per Study

The system guarantees that **each user receives only one survey per study**, regardless of how many configurations the study has. This is enforced by checking for existing responses before creating a new one:

```python
# In SurveyManager.trigger_survey_for_user()
existing_study_response = SurveyResponse.objects.filter(
    survey_study=active_study,
    user=self.user,
).exclude(status=SurveyResponse.Status.EXPIRED).first()

if existing_study_response:
    # User already has a survey for this study - skip
    return None
```

### Round-Robin Distribution Algorithm

When a study has multiple `SurveyConfiguration` instances, the system uses a **round-robin algorithm** to distribute users equitably across configurations.

#### How It Works

1. **Get Last N Responses**: Retrieves the last N responses for the study (where N = number of configurations)
2. **Identify Used Configs**: Determines which configurations were used in those last N responses
3. **Select Missing Config**: If a configuration wasn't used in the last N responses, it's selected
4. **Continue Rotation**: If all configurations were used, continues rotation from the most recent response

#### Example with 3 Configurations (A, B, C)

```
Configs: A (id=1), B (id=2), C (id=3)

1. 0 responses:
   last_responses = []
   used = {}
   → Assigns Config A ✅

2. 1 response (A):
   last_responses = [A]
   used = {A}
   → Assigns Config B ✅

3. 2 responses (A, B):
   last_responses = [B, A]
   used = {A, B}
   → Assigns Config C ✅

4. 3 responses (A, B, C):
   last_responses = [C, B, A]
   used = {A, B, C}
   → All used → Last was C → Next is A ✅

5. 4 responses (A, B, C, A):
   last_responses = [A, C, B]
   used = {A, B, C}
   → All used → Last was A → Next is B ✅
```

#### Implementation

```python
# In SurveyManager.trigger_survey_for_user()
num_configs = len(configs_for_study)
last_responses = SurveyResponse.objects.filter(
    survey_study=active_study,
).exclude(status=SurveyResponse.Status.EXPIRED)
.order_by("-created_at")
.values_list("survey_config_id", flat=True)[:num_configs]

used_config_ids = set(last_responses)

# Find first config not used in last N responses
for config, study in config_study_pairs:
    if config.id not in used_config_ids:
        selected_config = config
        break

# If all were used, continue rotation from most recent
if selected_config is None:
    most_recent_config_id = last_responses[0]
    # Get next config in rotation order
    selected_config = next_config_after(most_recent_config_id)
```

#### Benefits

- **True Rotation**: Ensures A → B → C → A → B → C... pattern
- **Equitable Distribution**: Maintains balance even with non-consecutive user IDs
- **Efficient**: Only queries last N responses, not all responses
- **Works with Multiple Cohorts**: Each study maintains its own distribution independently

## Helper Functions

### Module/Syllabus Completion Helpers

Located in `breathecode/feedback/actions.py`:

- **`_find_module_for_asset_in_syllabus(syllabus_version, asset_slug)`**: Finds the 0-based module index where an asset appears in a syllabus. Returns `int | None`.

- **`_get_module_assets_from_syllabus(syllabus_version, module_index)`**: Gets all asset slugs (QUIZ, LESSON, EXERCISE, PROJECT) from a specific module. Returns `list[str]`.

- **`_is_module_complete(user, cohort, module_index)`**: Checks if ALL activities in a module are complete (all have Task with status=DONE). Returns `bool`.

- **`_is_syllabus_complete(user, cohort)`**: Checks if ALL modules in a syllabus are complete. Returns `bool`.

- **`has_active_survey_studies(academy, trigger_types)`**: Checks if there are any active SurveyStudy instances for the given academy and trigger types. Used for early optimization. Returns `bool`.

### SurveyManager Class

Located in `breathecode/feedback/utils/survey_manager.py`:

The `SurveyManager` class centralizes all survey triggering logic:

- **`__init__(user, trigger_type, context)`**: Initialize with user, trigger type, and context
- **`trigger_survey_for_user()`**: Main method that orchestrates the entire trigger process
  - Groups configurations by active study
  - Checks for existing study response (1 per user per study)
  - Applies round-robin distribution
  - Applies filters and deduplication
  - Creates survey response
- **`_validate_user()`**: Validates user is not None
- **`_validate_trigger_type()`**: Validates trigger type is valid
- **`_resolve_academy()`**: Resolves academy from context or user profile
- **`_get_active_study(survey_config)`**: Gets active SurveyStudy for a configuration
- **`_apply_filters(survey_config, active_study)`**: Applies all filters (syllabus/module, cohort, asset_slug)
- **`_filter_by_syllabus_module(survey_config)`**: Filters by syllabus slug, version, and module
- **`_filter_by_cohort(survey_config)`**: Filters by cohort
- **`_filter_by_asset_slug(survey_config)`**: Filters by asset_slug
- **`_check_deduplication(survey_config, active_study)`**: Checks for existing responses (trigger-specific)
- **`_create_response(survey_config, active_study)`**: Creates SurveyResponse

## Related Documentation

- **Frontend Implementation:** See frontend team documentation
- **Webhook System:** `docs/LLM-DOCS/HOOKS_MANAGEMENT.md`
- **Feedback System:** `breathecode/feedback/llm.md`

