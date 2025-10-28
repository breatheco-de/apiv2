# Feedback App Documentation

## Overview

The **Feedback** Django app is a comprehensive survey and review management system for the BreatheCode platform. It enables 4Geeks Academy to collect, manage, and analyze student feedback through NPS (Net Promoter Score) surveys and reviews across different educational contexts.

### Primary Purposes

1. **Student Satisfaction Monitoring**: Track student satisfaction throughout their learning journey
2. **Quality Assurance**: Measure teaching quality, cohort experience, and platform usability
3. **Review Generation**: Automatically request public reviews from satisfied students
4. **Data-Driven Insights**: Provide actionable feedback to improve educational services
5. **Automated Feedback Collection**: Trigger surveys based on specific events (mentorship sessions, live classes, events, cohort milestones)

### Key Features

- **Multi-context surveys**: Events, mentorships, live classes, cohorts, and general academy feedback
- **NPS-based scoring**: 1-10 scale with qualitative comments
- **Customizable survey templates**: Multi-language support with template inheritance
- **Automated survey dispatch**: Event-driven surveys via Django signals
- **Review platform integration**: Track reviews on external platforms (CourseReport, SwitchUp, etc.)
- **Real-time tracking**: Monitor survey opens and completion rates
- **Supervisor monitoring**: Ensure mentorship sessions receive feedback

---

## Models

### Answer

The core model representing a single survey question response.

```python
class Answer(models.Model):
    # Question details
    title = models.CharField(max_length=200)
    lowest = models.CharField(max_length=50, default="not likely")
    highest = models.CharField(max_length=50, default="very likely")
    lang = models.CharField(max_length=3, default="en")
    question_by_slug = models.CharField(max_length=100)  # Standardized question type
    
    # Context (what is being rated)
    event = models.ForeignKey(Event, null=True)
    live_class = models.ForeignKey(LiveClass, null=True)
    asset = models.ForeignKey(Asset, null=True)
    mentorship_session = models.ForeignKey(MentorshipSession, null=True)
    mentor = models.ForeignKey(User, related_name="mentor_set", null=True)
    cohort = models.ForeignKey(Cohort, null=True)
    academy = models.ForeignKey(Academy, null=True)
    
    # Response data
    score = models.IntegerField(null=True)  # 1-10 NPS score
    comment = models.TextField(max_length=1000, null=True)
    
    # Metadata
    survey = models.ForeignKey(Survey, null=True)
    status = models.CharField(max_length=15, choices=SURVEY_STATUS)  # PENDING, SENT, ANSWERED, OPENED, EXPIRED
    user = models.ForeignKey(User, null=True)
    token = models.OneToOneField(Token, null=True)  # Temporal token for anonymous access
    
    opened_at = models.DateTimeField(null=True)
    sent_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Key Behaviors:**
- Triggers `survey_answered` signal when status changes to "ANSWERED"
- Can be linked to multiple contexts (mentor, cohort, event, etc.)
- Uses temporal tokens for secure, time-limited access

### Survey

Groups multiple answers into a cohesive survey sent to a cohort.

```python
class Survey(models.Model):
    lang = models.CharField(max_length=3, default="en")
    title = models.CharField(max_length=200, null=True)
    template_slug = models.CharField(max_length=100, null=True)
    
    cohort = models.ForeignKey(Cohort)
    is_customized = models.BooleanField(default=False)
    
    max_assistants_to_ask = models.IntegerField(default=2)
    max_teachers_to_ask = models.IntegerField(default=1)
    
    # Calculated fields
    scores = models.JSONField(null=True)  # Aggregated scores by type
    response_rate = models.FloatField(null=True)  # Percentage of responses
    
    status = models.CharField(max_length=15, choices=SURVEY_STATUS)  # PENDING, SENT, PARTIAL, FATAL
    status_json = models.JSONField(null=True)  # Detailed status log
    
    duration = models.DurationField(default=timedelta(hours=24))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True)
```

**Key Behaviors:**
- Groups multiple `Answer` objects for cohort-wide surveys
- Automatically calculates scores and response rates
- Tracks success/failure of sending surveys to students

### SurveyTemplate

Defines reusable question templates for different feedback contexts.

```python
class SurveyTemplate(models.Model):
    slug = models.SlugField(max_length=100, unique=True)
    lang = models.CharField(max_length=2)
    academy = models.ForeignKey(Academy)
    is_shared = models.BooleanField(default=False)
    original = models.ForeignKey('self', null=True, related_name='translations')
    
    # Question templates for different contexts
    when_asking_event = models.JSONField(null=True)
    when_asking_mentor = models.JSONField(null=True)
    when_asking_cohort = models.JSONField(null=True)
    when_asking_academy = models.JSONField(null=True)
    when_asking_mentorshipsession = models.JSONField(null=True)
    when_asking_platform = models.JSONField(null=True)
    when_asking_liveclass_mentor = models.JSONField(null=True)
    when_asking_mentor_communication = models.JSONField(null=True)
    when_asking_mentor_participation = models.JSONField(null=True)
    additional_questions = models.JSONField(null=True)
```

**JSON Structure for Questions:**
```json
{
    "title": "How was your experience with {}?",
    "highest": "very good",
    "lowest": "not good",
    "survey_subject": "One question about your experience"
}
```

**Key Features:**
- **Multi-language support**: English templates can have translations
- **Template inheritance**: Non-English templates must reference an English original
- **Shared templates**: Academies can share templates across the platform
- **Dynamic placeholders**: Use `{}` in titles for dynamic content (mentor names, cohort names, etc.)

**Static Method:**
```python
SurveyTemplate.get_template(slug, lang, academy=None)
```
Returns the appropriate template based on slug, language, and academy access.

### AcademyFeedbackSettings

Academy-specific configuration for automated surveys.

```python
class AcademyFeedbackSettings(models.Model):
    academy = models.OneToOneField(Academy, related_name='feedback_settings')
    
    # Templates for different survey types
    cohort_survey_template = models.ForeignKey(SurveyTemplate, related_name='cohort_survey_academies', null=True)
    liveclass_survey_template = models.ForeignKey(SurveyTemplate, related_name='liveclass_survey_academies', null=True)
    event_survey_template = models.ForeignKey(SurveyTemplate, related_name='event_survey_academies', null=True)
    mentorship_session_survey_template = models.ForeignKey(SurveyTemplate, related_name='mentorship_survey_academies', null=True)
    
    # Exclusions
    liveclass_survey_cohort_exclusions = models.CharField(max_length=255, null=True)  # Comma-separated cohort IDs
```

**Key Method:**
```python
def get_excluded_cohort_ids(self):
    """Returns list of excluded cohort IDs for live class surveys"""
```

### Review

Tracks external platform reviews (CourseReport, SwitchUp, etc.).

```python
class Review(models.Model):
    nps_previous_rating = models.FloatField(null=True)  # Auto-calculated from NPS answers
    total_rating = models.FloatField(null=True)
    public_url = models.URLField(null=True)
    
    status = models.CharField(max_length=9, choices=REVIEW_STATUS)  # PENDING, REQUESTED, DONE, IGNORE
    status_text = models.CharField(max_length=255, null=True)
    comments = models.TextField(null=True)
    
    cohort = models.ForeignKey(Cohort, null=True)
    author = models.ForeignKey(User)
    platform = models.ForeignKey(ReviewPlatform)
    is_public = models.BooleanField(default=False)
    lang = models.CharField(max_length=3, null=True)
```

**Key Behaviors:**
- Automatically created when students graduate with NPS ≥8
- Tracks review status across multiple platforms
- Public reviews can be displayed on marketing pages

### ReviewPlatform

Defines external review platforms.

```python
class ReviewPlatform(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=100)
    website = models.URLField()
    review_signup = models.URLField(null=True)  # URL to create a new review
    contact_email = models.EmailField()
    contact_name = models.EmailField(null=True)
    contact_phone = models.CharField(max_length=17, null=True)
```

### Proxy Models

```python
class UserProxy(User):
    class Meta:
        proxy = True

class CohortUserProxy(CohortUser):
    class Meta:
        proxy = True

class CohortProxy(Cohort):
    class Meta:
        proxy = True
```

These proxy models enable custom admin actions for sending surveys without modifying core models.

---

## API Endpoints

### Public Endpoints

#### `GET /v1/feedback/answer/<answer_id>/tracker.png`
**Purpose**: Track when a survey email is opened  
**Permissions**: `AllowAny`  
**Behavior**: Returns a 1x1 transparent PNG and marks the answer as "OPENED"

#### `GET /v1/feedback/review`
**Purpose**: List public reviews  
**Permissions**: `AllowAny`  
**Filters**: `academy`, `lang`  
**Returns**: Reviews with status="DONE", is_public=True, with comments and ratings

#### `GET /v1/feedback/review_platform[/<platform_slug>]`
**Purpose**: Get review platform information  
**Permissions**: `AllowAny`

### User Endpoints

#### `GET /v1/feedback/user/me/survey/<survey_id>`
**Purpose**: Get survey details for current user  
**Permissions**: Authenticated user  
**Validates**: Survey hasn't expired, user belongs to cohort

#### `GET /v1/feedback/user/me/survey/<survey_id>/questions`
**Purpose**: Get all questions for a survey  
**Permissions**: Authenticated user  
**Behavior**: 
- Validates user is an active/graduated student in the cohort
- Generates all answer objects for the survey
- Marks answers as "OPENED"
- Returns serialized answers

#### `GET /v1/feedback/user/me/answer/<answer_id>`
**Purpose**: Get a specific answer  
**Permissions**: Authenticated user (must own the answer)  
**Returns**: `BigAnswerSerializer`

#### `PUT /v1/feedback/user/me/answer/<answer_id>`
**Purpose**: Submit an answer to a survey question  
**Permissions**: Authenticated user (must own the answer)  
**Payload**:
```json
{
    "score": 8,
    "comment": "Great experience!"
}
```
**Validations**:
- Score must be between 1-10
- Cannot change score once answered
- Triggers activity logging

### Academy Endpoints (Require Permissions)

#### `GET /v1/feedback/academy/answer`
**Permission**: `read_nps_answers`  
**Filters**: `user`, `cohort`, `mentor`, `event`, `score`, `status`, `survey`, `like`  
**Features**: Pagination, sorting, caching

#### `GET /v1/feedback/academy/answer/<answer_id>`
**Permission**: `read_nps_answers`  
**Returns**: Full answer details for academy

#### `GET /v1/feedback/academy/survey`
**Permission**: `read_survey`  
**Filters**: `status`, `cohort`, `lang`, `template_slug`, `title`, `total_score`  
**Score Filtering**:
- `total_score=8` - Exact match
- `total_score=gte:8` - Greater than or equal
- `total_score=lte:7` - Less than or equal

#### `POST /v1/feedback/academy/survey`
**Permission**: `crud_survey`  
**Payload**:
```json
{
    "cohort": 123,
    "lang": "en",
    "max_assistants_to_ask": 2,
    "max_teachers_to_ask": 1,
    "duration": "24:00:00",
    "send_now": true
}
```
**Validations**:
- Cohort must belong to academy
- Cohort must have at least one teacher
- Minimum duration is 1 hour

#### `PUT /v1/feedback/academy/survey/<survey_id>`
**Permission**: `crud_survey`  
**Restrictions**: Cannot update sent surveys, cannot change cohort

#### `DELETE /v1/feedback/academy/survey[/<survey_id>]`
**Permission**: `crud_survey`  
**Features**: 
- Single or bulk delete via query string
- Cannot delete surveys with answered questions
- Validates academy ownership

#### `GET /v1/feedback/academy/survey/template`
**Permission**: `read_survey_template`  
**Filters**: `is_shared`, `lang`  
**Returns**: Templates accessible to the academy (owned or shared)

#### `GET /v1/feedback/academy/review`
**Permission**: `read_review`  
**Filters**: `start`, `end`, `status`, `platform`, `cohort`, `author`, `like`

#### `PUT /v1/feedback/academy/review/<review_id>`
**Permission**: `crud_review`  
**Restrictions**: Cannot update cohort, author, or platform

#### `DELETE /v1/feedback/academy/review`
**Permission**: `crud_review`  
**Behavior**: Sets status to "IGNORE" (soft delete)

#### `GET /v1/feedback/academy/feedbacksettings`
**Permission**: `get_academy_feedback_settings`  
**Returns**: Academy feedback configuration

#### `PUT /v1/feedback/academy/feedbacksettings`
**Permission**: `crud_academy_feedback_settings`  
**Payload**:
```json
{
    "cohort_survey_template": 1,
    "liveclass_survey_template": 2,
    "event_survey_template": 3,
    "mentorship_session_survey_template": 4,
    "liveclass_survey_cohort_exclusions": "123,456,789"
}
```
**Behavior**: Creates settings with defaults if they don't exist

---

## Actions

Located in `actions.py`, these functions encapsulate core business logic.

### `send_cohort_survey_group(survey=None, cohort=None)`

Sends a survey to all active/graduated students in a cohort.

**Parameters:**
- `survey`: Survey instance (optional)
- `cohort`: Cohort instance (optional)

**Process:**
1. Validates cohort has at least one teacher
2. Gets all active/graduated students
3. Schedules `send_cohort_survey` task for each student
4. Updates survey status (SENT, PARTIAL, or FATAL)
5. Records success/error messages in `status_json`

**Returns:**
```python
{
    "success": ["Survey scheduled for student@example.com", ...],
    "error": ["Error message", ...]
}
```

### `send_question(user, cohort=None)`

Sends a general NPS question to a user.

**Process:**
1. Determines user's cohort (most recent active/graduated)
2. Validates user has email or Slack
3. Validates cohort has syllabus and schedule
4. Creates or updates Answer with temporal token
5. Sends via email and/or Slack
6. Marks answer as "SENT"

**Raises:**
- `ValidationException` if user has no cohort
- `ValidationException` if no email/Slack available
- `ValidationException` if cohort missing syllabus or schedule

### `answer_survey(user, data)`

Creates an answer record (simple wrapper).

### `get_student_answer_avg(user_id, cohort_id=None, academy_id=None)`

Calculates average NPS score for a student.

**Parameters:**
- `user_id`: User ID
- `cohort_id`: Filter by cohort (optional)
- `academy_id`: Filter by academy (optional)

**Returns**: Float (rounded to 2 decimals) or None

### `create_user_graduation_reviews(user, cohort)`

Creates review requests when a student graduates.

**Logic:**
1. Calculate student's average NPS score
2. If average is None or ≥8:
   - Check if reviews already exist for this cohort
   - Create Review objects for all ReviewPlatforms
   - Set `nps_previous_rating` from calculated average

**Returns**: `True` if reviews created, `False` otherwise

### `calculate_survey_response_rate(survey_id)`

Calculates percentage of answered questions in a survey.

**Formula**: `(answered_count / total_count) * 100`

### `calculate_survey_scores(survey_id)`

Calculates aggregated scores for different survey aspects.

**Returns**:
```python
{
    "total": 8.5,           # Overall average
    "academy": 8.2,         # Academy-specific questions
    "cohort": 8.7,          # Cohort-specific questions
    "live_class": 8.4,      # Live class questions
    "mentors": [            # Per-mentor averages
        {"name": "John Doe", "score": 8.9},
        {"name": "Jane Smith", "score": 8.3}
    ]
}
```

**Score Categories:**
- **academy**: Questions about academy (no mentor/cohort/live_class)
- **cohort**: Questions about cohort (no mentor/live_class)
- **live_class**: Questions about live classes
- **mentors**: Aggregated by mentor (including mentorship sessions)

---

## Celery Tasks

Located in `tasks.py`, these async tasks handle email/Slack notifications and data processing.

### `build_question(answer, surveytemplate_slug=None)`

Populates answer fields from a SurveyTemplate.

**Process:**
1. Determines academy from answer context
2. Gets AcademyFeedbackSettings if available
3. Finds appropriate template:
   - From settings (if available)
   - By slug and language
   - Falls back to English
4. Populates `title`, `lowest`, `highest` based on answer type
5. Replaces `{}` placeholders with dynamic content

**Returns**: Updated `answer` object (not saved)

### `send_cohort_survey(user_id, survey_id, template_slug=None)`

Sends a cohort survey to a single user.

**Priority**: `TaskPriority.NOTIFICATION`  
**Process**:
1. Validates survey and user exist
2. Checks survey hasn't expired
3. Validates user is active/graduated student in cohort
4. Generates all survey answers
5. Creates temporal token (48 hours)
6. Sends via email and/or Slack with survey link

**Email Data**:
```python
{
    "SUBJECT": "We need your feedback",
    "MESSAGE": "Please take 5 minutes to give us feedback",
    "TRACKER_URL": "https://api.4geeks.com/v1/feedback/survey/{id}/tracker.png",
    "BUTTON": "Answer",
    "LINK": "https://nps.4geeks.com/survey/{id}?token={key}"
}
```

**Abort Conditions**:
- Survey not found (retry)
- User not found
- Survey expired
- User not in cohort
- No email or Slack

### `send_mentorship_session_survey(session_id)`

Sends survey after a mentorship session completes.

**Priority**: `TaskPriority.NOTIFICATION`  
**Process**:
1. Validates session exists and has mentee
2. Checks session has start and end times
3. Validates session duration > 5 minutes
4. Uses Redis lock to prevent duplicate answers
5. Creates Answer if doesn't exist
6. Sends email with temporal token (48 hours)

**Abort Conditions**:
- Session not found (retry)
- No mentee
- Session hasn't finished
- Duration ≤ 5 minutes
- No service associated
- Already answered
- No mentee email

### `send_event_survey(event_id)`

Sends surveys to all event attendees.

**Priority**: `TaskPriority.NOTIFICATION`  
**Process**:
1. Validates event finished
2. Checks no surveys exist for this event
3. Gets template from AcademyFeedbackSettings
4. Creates Answer for each attendee with `attended_at` set
5. Sends email with temporal token

**Abort Conditions**:
- Event not found (retry)
- Event hasn't finished
- Surveys already exist
- No event survey template

### `send_liveclass_survey(liveclass_id)`

Sends surveys after a live class.

**Priority**: `TaskPriority.NOTIFICATION`  
**Process**:
1. Validates live class finished within 24 hours
2. Checks cohort not in exclusion list
3. Gets attendance from cohort history_log
4. Creates Survey with multiple questions per student:
   - Main live class question
   - Mentor performance
   - Mentor communication
   - Mentor participation
5. Sends email to each attendee

**Abort Conditions**:
- Live class not found (retry)
- Not finished
- Finished > 24 hours ago
- Surveys already exist
- Cohort excluded
- No template configured

### `process_student_graduation(cohort_id, user_id)`

Handles review request generation on graduation.

**Priority**: `TaskPriority.ACADEMY`  
**Calls**: `create_user_graduation_reviews(user, cohort)`

### `recalculate_survey_scores(survey_id)`

Recalculates survey scores and response rate.

**Priority**: `TaskPriority.ACADEMY`  
**Updates**:
- `survey.response_rate`
- `survey.scores`

### `process_answer_received(answer_id)`

Processes a single answer submission.

**Priority**: `TaskPriority.ACADEMY`  
**Process**:
1. Recalculates survey scores and response rate
2. If score < 8, sends notification email to:
   - System email (from env)
   - Academy feedback email

**Email Data** (for negative scores):
```python
{
    "SUBJECT": "A student answered with a bad NPS score at {academy}",
    "FULL_NAME": "John Doe",
    "QUESTION": "How was your experience?",
    "SCORE": 6,
    "COMMENTS": "Could be better...",
    "ACADEMY": "Miami",
    "LINK": "https://admin.4geeks.com/feedback/surveys/miami/123"
}
```

---

## Supervisors

Located in `supervisors.py`, these monitor and auto-fix issues.

### `supervise_mentorship_survey()`

Monitors mentorship sessions missing surveys.

**Schedule**: Every 24 hours  
**Scope**: Completed sessions from last 5 days  
**Detection**:
- Status: "COMPLETED"
- Has start and end times
- Has mentor and mentee
- Duration > 5 minutes
- No associated Answer

**Issue Yielded**:
```python
{
    "message": "Session {id} hasn't a survey",
    "code": "no-survey-for-session",
    "params": {"session_id": session.id}
}
```

### `no_survey_for_session(session_id)`

Issue handler for missing mentorship surveys.

**Retry**: Every 10 minutes  
**Fix**:
1. Verify session still exists
2. Check if Answer now exists
3. Schedule `send_mentorship_session_survey` task

**Returns**:
- `True` - Survey exists (fixed)
- `None` - Task scheduled (will retry)

---

## Signals & Receivers

Located in `receivers.py` and `signals.py`.

### Custom Signal

```python
# signals.py
survey_answered = Signal()
```

### Receivers

#### `answer_received(sender=Answer)`

**Trigger**: `survey_answered` signal  
**Action**: Schedules `process_answer_received` task

#### `post_save_cohort_user(sender=CohortUser)`

**Trigger**: `student_edu_status_updated` signal  
**Condition**: `educational_status == "GRADUATED"`  
**Action**: Schedules `process_student_graduation` task

#### `post_mentorin_session_ended(sender=MentorshipSession)`

**Trigger**: `mentorship_session_saved` signal  
**Conditions**:
- Status: "COMPLETED"
- Duration > 5 minutes
- Has mentor and mentee
- No existing Answer

**Action**: Schedules `send_mentorship_session_survey` task

#### `post_liveclass_ended(sender=LiveClass)`

**Trigger**: `liveclass_ended` signal  
**Conditions**:
- Ended within 24 hours
- Academy has liveclass survey template configured

**Action**: Schedules `send_liveclass_survey` task

#### `post_event_ended(sender=Event)`

**Trigger**: `event_status_updated` signal  
**Conditions**:
- Status: "FINISHED"
- Has end time
- No existing Answer
- Academy has event survey template

**Action**: Schedules `send_event_survey` task

---

## Utilities

### `utils.py` - String Templates

Contains multilingual string templates for surveys.

```python
strings = {
    "es": {
        "event": {
            "title": "¿Qué tan probable es que recomiendes eventos como este?",
            "highest": "muy probable",
            "lowest": "poco probable",
            "survey_subject": "Una pregunta sobre el evento"
        },
        "mentor": {...},
        "cohort": {...},
        # ... more contexts
        "button_label": "Responder",
        "survey_subject": "Necesitamos tu feedback",
        "survey_message": "Por favor toma 5 minutos"
    },
    "en": {
        # English translations
    }
}
```

**Supported Contexts:**
- `event` - Event feedback
- `mentor` - Mentor evaluation
- `cohort` - Cohort experience
- `academy` - Academy recommendation
- `mentorship_session` - Mentorship quality
- `platform` - Platform usability
- `live_class` - Live class quality
- `liveclass_mentor` - Live class instructor
- `mentor_communication` - Communication clarity
- `mentor_participation` - Engagement effectiveness

### `caches.py` - Cache Configuration

```python
class AnswerCache(AppCache):
    model = Answer
```

Uses Capy Core caching for Answer endpoints.

---

## Serializers

Located in `serializers.py`.

### Read Serializers (Serpy)

**Serpy-based** for fast read performance:

- `AnswerSerializer` - Basic answer data
- `BigAnswerSerializer` - Extended answer with timestamps
- `SurveySmallSerializer` - Survey list view
- `GetSurveySerializer` - Survey detail view
- `SurveyTemplateSerializer` - Template data
- `ReviewSmallSerializer` - Review list view
- `AcademyFeedbackSettingsSerializer` - Settings view

### Write Serializers (DRF)

**Django REST Framework** for validation:

#### `AnswerPUTSerializer`

**Validations:**
- Score must be 1-10
- Cannot change score after answering
- User must own the answer

#### `SurveySerializer`

**Validations:**
- Cohort belongs to academy
- Duration ≥ 1 hour
- Cohort has at least one teacher

**Write-only Fields:**
- `send_now` (boolean) - Immediately send survey

#### `SurveyPUTSerializer`

**Validations:**
- Survey status must be "PENDING"
- Cannot update cohort
- Academy must own cohort

#### `ReviewPUTSerializer`

**Validations:**
- Cannot update cohort, author, or platform
- Academy must own cohort

#### `AcademyFeedbackSettingsPUTSerializer`

**Auto-population**: Sets default shared template if fields empty

---

## Admin Interface

Located in `admin.py`.

### Models Registered

1. **UserProxy** - Bulk NPS surveys
2. **CohortUserProxy** - Cohort-specific surveys and review requests
3. **CohortProxy** - View cohorts for feedback
4. **Answer** - Manage individual responses
5. **Survey** - Manage cohort surveys
6. **Review** - Track external reviews
7. **ReviewPlatform** - Configure review platforms
8. **SurveyTemplate** - Create/edit templates
9. **AcademyFeedbackSettings** - Configure academy settings

### Admin Actions

#### User Actions
- **Send General NPS Survey**: Bulk send to selected users

#### CohortUser Actions
- **Send General NPS Survey**: Cohort-specific bulk send
- **Generate Review Requests**: Create review requests for graduated students

#### Survey Actions
- **Send survey to all cohort students**: Bulk send surveys
- **Fill sent_at with created_at**: Backfill timestamps
- **Recalculate all Survey scores**: Recompute aggregations
- **Change status**: Bulk status updates

#### Answer Actions
- **Export as CSV**: Export answer data
- **Add academy to answer**: Backfill academy field

### Custom List Filters

- **AnswerTypeFilter**: Filter by answer context (academy, cohort, mentor, session, event)
- **SentFilter**: Filter surveys by sent status
- **OriginalTemplateFilter**: Filter templates by original/translation

### Custom Displays

- **Survey total score**: Color-coded badge (green ≥8, yellow 7-8, red <7)
- **Review status**: Bootstrap badges
- **Survey/Answer URLs**: Direct links to frontend

### Template Form Features

- **PrettyJSONWidget**: Formatted JSON editor for template questions
- **Collapsible fieldsets**: Organized by question type
- **Validation**: Ensures JSON structure consistency

---

## Usage Examples

### Example 1: Create and Send Cohort Survey

```python
from breathecode.feedback.models import Survey, SurveyTemplate, AcademyFeedbackSettings
from breathecode.feedback.actions import send_cohort_survey_group
from breathecode.admissions.models import Cohort

# Get or create academy settings
cohort = Cohort.objects.get(slug='miami-web-dev-pt-1')
settings, _ = AcademyFeedbackSettings.objects.get_or_create(
    academy=cohort.academy
)

# Assign template
template = SurveyTemplate.objects.filter(
    lang='en',
    is_shared=True
).first()
settings.cohort_survey_template = template
settings.save()

# Create survey
survey = Survey.objects.create(
    cohort=cohort,
    lang='en',
    max_teachers_to_ask=1,
    max_assistants_to_ask=2
)

# Send immediately
result = send_cohort_survey_group(survey=survey)
print(result['success'])  # List of successful sends
print(result['error'])    # List of errors
```

### Example 2: Manually Trigger Event Survey

```python
from breathecode.feedback.tasks import send_event_survey
from breathecode.events.models import Event

event = Event.objects.get(id=123)
event.status = 'FINISHED'
event.save()

# Manually trigger survey
send_event_survey.delay(event.id)
```

### Example 3: Create Custom Survey Template

```python
from breathecode.feedback.models import SurveyTemplate

template = SurveyTemplate.objects.create(
    slug='custom-satisfaction-survey',
    lang='en',
    academy=my_academy,
    is_shared=False,
    when_asking_cohort={
        "title": "How satisfied are you with {}?",
        "highest": "very satisfied",
        "lowest": "not satisfied",
        "survey_subject": "Your satisfaction matters"
    },
    when_asking_mentor={
        "title": "Rate your mentor {}'s teaching",
        "highest": "excellent",
        "lowest": "poor",
        "survey_subject": "Mentor feedback"
    },
    additional_questions={
        "platform_usability": {
            "title": "How easy is the platform to use?",
            "highest": "very easy",
            "lowest": "very difficult",
            "survey_subject": "Platform usability"
        }
    }
)

# Create Spanish translation
spanish_template = SurveyTemplate.objects.create(
    slug='custom-satisfaction-survey-es',
    lang='es',
    academy=my_academy,
    original=template,
    when_asking_cohort={
        "title": "¿Qué tan satisfecho estás con {}?",
        "highest": "muy satisfecho",
        "lowest": "insatisfecho",
        "survey_subject": "Tu satisfacción importa"
    },
    # ... more Spanish translations
)
```

### Example 4: Query Student Feedback Average

```python
from breathecode.feedback.actions import get_student_answer_avg

# Overall average
avg = get_student_answer_avg(user_id=456)
print(f"Student average: {avg}")  # 8.5

# Cohort-specific
cohort_avg = get_student_answer_avg(
    user_id=456,
    cohort_id=123
)

# Academy-specific
academy_avg = get_student_answer_avg(
    user_id=456,
    academy_id=1
)
```

### Example 5: Get Survey Scores Breakdown

```python
from breathecode.feedback.actions import calculate_survey_scores

scores = calculate_survey_scores(survey_id=789)
print(scores)
# {
#     "total": 8.5,
#     "academy": 8.2,
#     "cohort": 8.7,
#     "live_class": 8.4,
#     "mentors": [
#         {"name": "John Doe", "score": 8.9},
#         {"name": "Jane Smith", "score": 8.3}
#     ]
# }
```

### Example 6: Submit Answer via API

```bash
# Student submits answer
curl -X PUT https://api.4geeks.com/v1/feedback/user/me/answer/123 \
  -H "Authorization: Token abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "score": 9,
    "comment": "Great mentorship session!"
  }'
```

### Example 7: Filter Academy Answers

```bash
# Get all low-scoring answers
curl "https://api.4geeks.com/v1/feedback/academy/answer?score=lte:6&status=ANSWERED" \
  -H "Authorization: Token abc123" \
  -H "Academy: 1"

# Search by student name
curl "https://api.4geeks.com/v1/feedback/academy/answer?like=John+Doe" \
  -H "Authorization: Token abc123" \
  -H "Academy: 1"
```

### Example 8: Configure Academy Feedback Settings

```python
from breathecode.feedback.models import AcademyFeedbackSettings, SurveyTemplate

settings = AcademyFeedbackSettings.objects.create(
    academy=my_academy,
    cohort_survey_template=SurveyTemplate.objects.get(slug='nps-standard'),
    liveclass_survey_template=SurveyTemplate.objects.get(slug='liveclass-quality'),
    event_survey_template=SurveyTemplate.objects.get(slug='event-feedback'),
    mentorship_session_survey_template=SurveyTemplate.objects.get(slug='mentorship-quality'),
    liveclass_survey_cohort_exclusions='123,456,789'  # Exclude these cohorts
)
```

---

## Configuration

### Environment Variables

```bash
ADMIN_URL=https://admin.4geeks.com
API_URL=https://api.4geeks.com
SYSTEM_EMAIL=feedback@4geeks.com
ENV=production  # or 'test', 'development'
```

### Required Permissions

#### Read Permissions
- `read_nps_answers` - View answers
- `read_survey` - View surveys
- `read_review` - View reviews
- `read_survey_template` - View templates
- `get_academy_feedback_settings` - View settings

#### Write Permissions
- `crud_survey` - Create/update/delete surveys
- `crud_review` - Update/delete reviews
- `crud_academy_feedback_settings` - Configure settings

### Signal Configuration

Ensure receivers are loaded in `apps.py`:

```python
# breathecode/feedback/apps.py
from django.apps import AppConfig

class FeedbackConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'breathecode.feedback'
    
    def ready(self):
        import breathecode.feedback.receivers  # Load signal receivers
```

### Celery Configuration

Tasks use priorities from `breathecode.utils.TaskPriority`:
- `NOTIFICATION` - Survey emails (high priority)
- `ACADEMY` - Score calculations, graduation processing

### Redis Configuration

Used for:
- Answer caching (`AnswerCache`)
- Distributed locks (prevent duplicate surveys)

---

## Workflow Diagrams

### Cohort Survey Workflow

```
1. Admin/API creates Survey with send_now=True
2. send_cohort_survey_group() validates cohort
3. For each active/graduated student:
   └─> send_cohort_survey.delay(user_id, survey_id)
       ├─> generate_user_cohort_survey_answers()
       │   ├─> Create Answer for cohort
       │   ├─> Create Answers for teachers (max 2)
       │   ├─> Create Answers for assistants (max 2)
       │   ├─> Create Answer for academy
       │   └─> Create Answer for platform
       └─> Send email/Slack with survey link
4. Student clicks link → Frontend loads questions
5. Student submits answers → AnswerPUTSerializer
6. survey_answered signal → process_answer_received
   ├─> Recalculate survey scores
   └─> If score < 8, notify academy
```

### Mentorship Survey Workflow

```
1. MentorshipSession status → "COMPLETED"
2. mentorship_session_saved signal
3. Receiver validates duration > 5 minutes
4. send_mentorship_session_survey.delay(session_id)
   ├─> Redis lock to prevent duplicates
   ├─> build_question() from template
   ├─> Create Answer
   └─> Send email with NPS link
5. Student answers → Answer saved
6. survey_answered signal → process_answer_received
```

### Live Class Survey Workflow

```
1. LiveClass ends
2. liveclass_ended signal
3. Receiver checks:
   ├─> Ended within 24 hours?
   ├─> Template configured?
   └─> Cohort not excluded?
4. send_liveclass_survey.delay(liveclass_id)
   ├─> Get attendance from cohort.history_log
   ├─> Create Survey
   ├─> For each attendee:
   │   ├─> Main live class question
   │   ├─> Mentor performance
   │   ├─> Mentor communication
   │   └─> Mentor participation
   └─> Send email per student
```

### Graduation Review Workflow

```
1. CohortUser.educational_status → "GRADUATED"
2. student_edu_status_updated signal
3. process_student_graduation.delay(cohort_id, user_id)
4. create_user_graduation_reviews()
   ├─> Calculate average NPS score
   ├─> If avg ≥ 8 or None:
   │   ├─> Check for existing reviews
   │   └─> Create Review for each ReviewPlatform
   └─> Set nps_previous_rating
```

---

## Best Practices

### Survey Design
1. **Keep questions focused**: Each answer should target one aspect
2. **Use consistent scales**: 1-10 NPS is standard
3. **Provide context**: Use `{}` placeholders for names
4. **Limit questions**: 5-7 questions max per survey

### Template Management
1. **Always create English first**: Required for translations
2. **Share common templates**: Reduces duplication
3. **Test placeholders**: Ensure `{}` formatting works
4. **Version control slugs**: Use descriptive, stable slugs

### Performance
1. **Use caching**: Leverage `AnswerCache` for reads
2. **Async everything**: All emails/notifications via Celery
3. **Batch operations**: Use Django signals for triggering
4. **Index appropriately**: Status, academy, cohort fields

### Security
1. **Temporal tokens**: 48-hour expiration for survey links
2. **Validate ownership**: Users can only update their answers
3. **Academy isolation**: Always filter by academy_id
4. **Score validation**: Enforce 1-10 range

### Monitoring
1. **Check supervisors**: Ensure mentorship surveys are sent
2. **Monitor response rates**: Track completion metrics
3. **Alert on low scores**: < 8 triggers notifications
4. **Review error logs**: Check status_json for failures

---

## Troubleshooting

### Issue: Surveys not sending

**Checklist:**
1. Cohort has at least one teacher?
2. Students are ACTIVE or GRADUATED?
3. AcademyFeedbackSettings configured?
4. Template exists for language?
5. Check survey.status_json for errors

### Issue: Duplicate surveys

**Solution:** Redis locks prevent duplicates. Check:
1. Redis connection active?
2. Lock timeout appropriate (30s)?
3. Answer doesn't already exist?

### Issue: Wrong language

**Debug:**
1. Check cohort.language
2. Verify template exists for language
3. Fallback to English if not found
4. Check answer.lang field

### Issue: Missing answers in survey

**Check:**
1. max_teachers_to_ask and max_assistants_to_ask settings
2. Cohort has teachers/assistants assigned?
3. User role in CohortUser?
4. Survey generated correctly?

### Issue: Reviews not created

**Requirements:**
1. Student has GRADUATED status
2. Average NPS ≥ 8 (or no answers yet)
3. No existing reviews for cohort
4. ReviewPlatform objects exist

---

## Testing

### Key Test Scenarios

1. **Survey Creation**
   - Valid cohort survey
   - Invalid cohort (no teacher)
   - Duration validation
   - Academy ownership

2. **Answer Submission**
   - Valid score (1-10)
   - Invalid score (0, 11)
   - Duplicate answers
   - Score change prevention

3. **Template System**
   - English-only templates
   - Translations with original
   - Shared vs academy-specific
   - Placeholder replacement

4. **Signal Triggers**
   - Graduation → review creation
   - Session completion → survey
   - Live class end → survey
   - Event finish → survey

5. **Score Calculation**
   - Response rate accuracy
   - Score aggregation by type
   - Mentor score separation
   - Empty survey handling

### Example Test

```python
def test_send_cohort_survey():
    cohort = self.bc.database.create(cohort=1, cohort_user=2)
    survey = Survey.objects.create(cohort=cohort)
    
    result = send_cohort_survey_group(survey=survey)
    
    assert len(result['success']) == 2
    assert survey.status == 'SENT'
    assert Answer.objects.count() > 0
```

---

## Integration Points

### External Systems

1. **Notification System** (`breathecode.notify`)
   - Email templates: `nps`, `nps_survey`, `negative_answer`
   - Slack integration for surveys

2. **Activity Tracking** (`breathecode.activity`)
   - Logs `nps_answered` activity on submission

3. **Mentorship** (`breathecode.mentorship`)
   - Triggered by session completion
   - Uses service.language for survey language

4. **Events** (`breathecode.events`)
   - Triggered by event finish
   - Uses checkin data for attendees

5. **Admissions** (`breathecode.admissions`)
   - Cohort and CohortUser relationships
   - Educational status tracking

6. **Authentication** (`breathecode.authenticate`)
   - Temporal tokens for survey access
   - User permissions

### Frontend Integration

**Survey Frontend**: `https://nps.4geeks.com`

**URL Patterns:**
- Single answer: `/[answer_id]?token=[key]`
- Survey: `/survey/[survey_id]?token=[key]`

**API Calls:**
- `GET /v1/feedback/user/me/survey/{id}/questions` - Load questions
- `PUT /v1/feedback/user/me/answer/{id}` - Submit answer

---

## Future Enhancements

### Potential Features

1. **Advanced Analytics**
   - Time-series score trends
   - Comparative analysis across cohorts
   - Predictive dropout detection

2. **Rich Questions**
   - Multiple choice
   - Ranking questions
   - Matrix questions

3. **Survey Logic**
   - Conditional branching
   - Skip logic based on previous answers

4. **Integration Expansion**
   - Slack surveys directly in DMs
   - WhatsApp integration
   - SMS surveys

5. **AI Analysis**
   - Sentiment analysis on comments
   - Topic extraction
   - Auto-categorization

6. **Gamification**
   - Rewards for survey completion
   - Leaderboards for mentors
   - Badge system

---

## Summary

The **Feedback** app is a mature, production-ready system for collecting and managing educational feedback across the 4Geeks platform. It leverages:

- **Event-driven architecture** via Django signals
- **Async task processing** via Celery
- **Flexible templating** with multi-language support
- **Automated workflows** for various educational contexts
- **Comprehensive monitoring** via supervisors
- **Secure access** via temporal tokens
- **Rich analytics** for decision-making

The system handles thousands of surveys monthly, providing critical insights for educational quality improvement while maintaining high performance and reliability.

