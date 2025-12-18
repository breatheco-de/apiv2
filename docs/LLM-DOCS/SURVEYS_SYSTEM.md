# Survey System - Complete Documentation

## Overview

The Survey System is a real-time, event-driven feedback collection system that allows administrators to configure surveys that are automatically triggered when students complete specific actions (like finishing a learnpack or course). Surveys are delivered in real-time via Pusher, and responses are stored in the database and forwarded to external systems via webhooks.

### Key Features

- **Admin-Configurable Triggers**: Admins can define when surveys are sent (learnpack completion, course completion, etc.)
- **Real-Time Delivery**: Surveys are pushed to users via Pusher channels
- **Flexible Question Types**: Supports Likert scale, open-ended questions, and extensible JSON structure for future types
- **Filtering**: Surveys can be filtered by specific cohorts, learnpacks, or academies
- **Webhook Integration**: Responses are automatically sent to n8n or other webhook subscribers
- **Scalable Architecture**: Easy to add new trigger types without modifying existing code

---

## Architecture

### Components

1. **Models** (`breathecode/feedback/models.py`)
   - `SurveyConfiguration`: Defines when and how surveys are triggered
   - `SurveyResponse`: Stores user responses to surveys

2. **Actions** (`breathecode/feedback/actions.py`)
   - `trigger_survey_for_user()`: Main function to trigger surveys
   - `create_survey_response()`: Creates survey response and sends Pusher event
   - `save_survey_answers()`: Validates and saves user answers

3. **Services** (`breathecode/feedback/services/pusher_service.py`)
   - `send_survey_event()`: Sends real-time events via Pusher

4. **Views** (`breathecode/feedback/views.py`)
   - `SurveyConfigurationView`: Admin CRUD for survey configurations
   - `SurveyResponseView`: User endpoints to view and answer surveys

5. **Signals & Receivers** (`breathecode/feedback/signals.py`, `receivers.py`)
   - `survey_response_answered`: Signal fired when user answers
   - Webhook integration via `HookManager`

---

## Data Models

### SurveyConfiguration

Defines when and how surveys are triggered.

**Fields:**
- `trigger_type`: Type of event that triggers the survey (`learnpack_completed`, `course_completed`)
- `template`: Optional FK to `SurveyQuestionTemplate`. If set, questions are sourced from the template.
- `questions`: JSON structure containing survey questions
- `is_active`: Whether this configuration is active
- `academy`: Academy this survey applies to
- `cohorts`: ManyToMany - If empty, applies to all cohorts. If set, only to specified cohorts
- `asset_slugs`: JSON array - If empty, applies to all learnpacks. If set, only to specified learnpacks
- `stats`: JSON aggregated stats for this configuration (sent/opened/partial/responses/email_opened)
- `created_by`: User who created the configuration
- `created_at`, `updated_at`: Timestamps

**Example:**
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

### SurveyResponse

Stores individual user responses to surveys.

**Fields:**
- `survey_config`: ForeignKey to SurveyConfiguration
- `survey_study`: Optional FK to SurveyStudy
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
  "cohorts": []
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

#### Delete Survey Configuration

**Method:** `DELETE`

**URL:** `{{base_url}}/v1/feedback/academy/survey/configuration/{{configuration_id}}`

**Permissions:** `crud_survey`

**Headers:**
- `Authorization: Token {{token}}`
- `Academy: {{academy_id}}`

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
User completes action (learnpack/course)
    ↓
calculate_telemetry_indicator() or mark_saas_student_as_graduated()
    ↓
trigger_survey_for_user(user, trigger_type, context)
    ↓
Find active SurveyConfiguration for trigger_type + academy
    ↓
Apply filters (cohorts, asset_slugs)
    ↓
Check for existing pending response (prevent duplicates)
    ↓
create_survey_response()
    ↓
Create SurveyResponse (status: PENDING)
    ↓
send_survey_event() via Pusher
    ↓
Frontend receives event and shows survey
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

### Cohort Filtering (Course Completion)

```python
if trigger_type == "course_completed":
    cohort = context.get("cohort")
    if cohort:
        if survey_config.cohorts.exists():
            # Only apply if cohort is in the list
            if cohort not in survey_config.cohorts.all():
                continue  # Skip this config
        # If cohorts is empty, apply to all cohorts
```

### Asset Slug Filtering (Learnpack Completion)

```python
if trigger_type == "learnpack_completed":
    asset_slug = context.get("asset_slug")
    if asset_slug:
        if survey_config.asset_slugs:
            # Only apply if asset_slug is in the list
            if asset_slug not in survey_config.asset_slugs:
                continue  # Skip this config
        # If asset_slugs is empty, apply to all learnpacks
```

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
   class TriggerType(models.TextChoices):
       LEARNPACK_COMPLETION = "learnpack_completed", "Learnpack Completion"
       COURSE_COMPLETION = "course_completed", "Course Completion"
       NEW_TRIGGER = "new_trigger", "New Trigger"  # Add here
   ```

2. **Add Filtering Logic:**
   ```python
   # In trigger_survey_for_user()
   elif trigger_type == SurveyConfiguration.TriggerType.NEW_TRIGGER:
       # Add filtering logic here
       pass
   ```

3. **Call from Your Code:**
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
- Indexes recommended on:
  - `SurveyResponse(user, status)`
  - `SurveyConfiguration(trigger_type, is_active, academy)`

### Duplicate Prevention

- Checks for existing pending responses before creating new ones
- Prevents spam and duplicate surveys

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

## Related Documentation

- **Frontend Implementation:** See frontend team documentation
- **Webhook System:** `docs/LLM-DOCS/HOOKS_MANAGEMENT.md`
- **Feedback System:** `breathecode/feedback/llm.md`

