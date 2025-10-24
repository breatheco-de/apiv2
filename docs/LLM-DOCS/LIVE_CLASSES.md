# Live Classes API Documentation

This document provides comprehensive information about Live Classes in BreatheCode - how they're automatically generated from cohort timeslots, how to query them, track attendance, and manage class sessions.

## Overview

**Live Classes** are automatically generated instances of scheduled cohort sessions based on **Cohort TimeSlots**. They represent actual class meetings with specific dates and times, attendance tracking, and meeting URLs.

### Key Concepts

- **CohortTimeSlot**: A template/schedule defining when classes occur (e.g., "Every Monday 2-4 PM")
- **LiveClass**: An actual instance of a class (e.g., "Monday October 28, 2025 2-4 PM")
- **Automatic Generation**: Live classes are created automatically via background tasks when timeslots are saved
- **Attendance Tracking**: Classes track when they start (`started_at`) and end (`ended_at`)

### Model Relationships

```
Cohort
  └── CohortTimeSlot (schedule template)
      └── LiveClass (multiple instances)
          ├── starting_at (scheduled start)
          ├── ending_at (scheduled end)
          ├── started_at (actual start - when teacher joins)
          ├── ended_at (actual end - marks completion)
          └── hash (unique join URL identifier)
```

---

## Core Endpoints

### 1. List Live Classes for Current User

**Endpoint:** `GET /v1/events/me/event/liveclass`

**Purpose:** Get live classes for the authenticated user (student, teacher, or TA)

**Authentication:** Required (any authenticated user)

**Query Parameters:**
- `cohort={cohort_slug}` - Filter by cohort slug
- `academy={academy_slug}` - Filter by academy
- `syllabus={syllabus_slug}` - Filter by syllabus
- `starting_at__gte={datetime}` - Classes starting at or after this date
- `starting_at__lte={datetime}` - Classes starting at or before this date
- `ending_at__gte={datetime}` - Classes ending at or after this date
- `ending_at__lte={datetime}` - Classes ending at or before this date
- `upcoming={null}` - Get only upcoming classes (ended_at is null)
- `remote_meeting_url={url}` - Filter by specific meeting URL
- `start={datetime}` - Alias for `starting_at__gte`
- `end={datetime}` - Alias for `ending_at__lte`
- `limit={number}` - Results per page (pagination)
- `offset={number}` - Skip N results (pagination)

**Response:**
```json
[
  {
    "id": 123,
    "hash": "a1b2c3d4e5f6789...",
    "starting_at": "2025-10-28T18:00:00Z",
    "ending_at": "2025-10-28T20:00:00Z",
    "started_at": null,
    "ended_at": null,
    "remote_meeting_url": "https://zoom.us/j/123456789",
    "cohort": {
      "id": 45,
      "slug": "web-dev-ft-2025",
      "name": "Web Development Full Time 2025",
      "kickoff_date": "2025-01-15",
      "ending_date": "2025-06-30",
      "stage": "STARTED",
      "current_day": 85,
      "academy": {
        "id": 1,
        "slug": "downtown-miami",
        "name": "4Geeks Downtown Miami",
        "logo_url": "https://..."
      }
    }
  }
]
```

**Example Requests:**

Get all upcoming classes:
```bash
GET /v1/events/me/event/liveclass?upcoming=null
Authorization: Token {your-token}
```

Get classes for specific cohort:
```bash
GET /v1/events/me/event/liveclass?cohort=web-dev-ft-2025
Authorization: Token {your-token}
```

Get classes in date range:
```bash
GET /v1/events/me/event/liveclass?starting_at__gte=2025-10-28&starting_at__lte=2025-11-04
Authorization: Token {your-token}
```

---

### 2. List Live Classes for Academy (Staff View)

**Endpoint:** `GET /v1/events/academy/event/liveclass`

**Purpose:** Get all live classes for an academy (staff/admin view)

**Authentication:** Required - `start_or_end_class` capability

**Headers:**
- `Academy: {academy_id}` - Required
- `Authorization: Token {your-token}` - Required

**Query Parameters:**
All parameters from user endpoint, plus:
- `user={user_id}` - Filter by specific user ID
- `user_email={email}` - Filter by user email

**Response:** Same format as user endpoint

**Example Requests:**

Get all classes for academy:
```bash
GET /v1/events/academy/event/liveclass
Headers:
  Academy: 1
  Authorization: Token {your-token}
```

Get classes for specific student:
```bash
GET /v1/events/academy/event/liveclass?user=456&cohort=web-dev-ft-2025
Headers:
  Academy: 1
  Authorization: Token {your-token}
```

Get ongoing classes:
```bash
GET /v1/events/academy/event/liveclass?started_at__is_null=false&ended_at__is_null=true
Headers:
  Academy: 1
  Authorization: Token {your-token}
```

---

### 3. Create Live Class (Manual)

**Endpoint:** `POST /v1/events/academy/event/liveclass`

**Purpose:** Manually create a live class instance

**Authentication:** Required - `start_or_end_class` capability

**Headers:**
- `Academy: {academy_id}` - Required
- `Authorization: Token {your-token}` - Required

**Request Body:**
```json
{
  "cohort_time_slot": 123,
  "starting_at": "2025-10-28T18:00:00Z",
  "ending_at": "2025-10-28T20:00:00Z",
  "remote_meeting_url": "https://zoom.us/j/123456789"
}
```

**Required Fields:**
- `cohort_time_slot` (integer) - The timeslot ID this class belongs to
- `starting_at` (ISO datetime) - Scheduled start time
- `ending_at` (ISO datetime) - Scheduled end time
- `remote_meeting_url` (URL) - Meeting link

**Optional Fields:**
- `log` (JSON object) - Additional metadata
- `started_at` (datetime) - Cannot be set on creation
- `ended_at` (datetime) - Cannot be set on creation

**Response:**
```json
{
  "id": 789,
  "hash": "x9y8z7w6v5u4...",
  "cohort_time_slot": 123,
  "starting_at": "2025-10-28T18:00:00Z",
  "ending_at": "2025-10-28T20:00:00Z",
  "started_at": null,
  "ended_at": null,
  "remote_meeting_url": "https://zoom.us/j/123456789",
  "log": {},
  "created_at": "2025-10-21T20:00:00Z",
  "updated_at": "2025-10-21T20:00:00Z"
}
```

**Validation Rules:**
- Cannot set `started_at` on creation
- The cohort must belong to the specified academy
- Times must be valid ISO datetime strings

---

### 4. Update Live Class

**Endpoint:** `PUT /v1/events/academy/event/liveclass/{live_class_id}`

**Purpose:** Update a live class (primarily for marking as started/ended)

**Authentication:** Required - `start_or_end_class` capability

**Headers:**
- `Academy: {academy_id}` - Required
- `Authorization: Token {your-token}` - Required

**Request Body Examples:**

Mark class as started:
```json
{
  "started_at": "2025-10-28T18:05:00Z"
}
```

Mark class as ended:
```json
{
  "ended_at": "2025-10-28T20:00:00Z"
}
```

Update meeting URL:
```json
{
  "remote_meeting_url": "https://meet.google.com/new-link"
}
```

**Validation Rules:**
- Cannot start a class that's already started
- `started_at` must be within 2 minutes of current time (can't backdate)
- Can only update one field at a time when setting `started_at`
- `ended_at` must be after `started_at`
- `ended_at` cannot be more than 24 hours before current time
- Must wait at least 30 minutes between start and end

**Response:** Updated live class object

---

### 5. Join Live Class

**Endpoint:** `GET /v1/events/me/event/liveclass/join/{hash}`

**Purpose:** Join a live class (redirects to meeting URL or shows countdown)

**Authentication:** Required (private view with token)

**URL Parameters:**
- `hash` - The unique hash identifier from the live class

**Query Parameters:**
- `token={auth_token}` - Authentication token

**Behavior:**
1. **If class hasn't started yet:** Shows countdown page with class details
2. **If class is ready:** Redirects to `cohort.online_meeting_url`
3. **If user is teacher/assistant:** Automatically marks class as started

**Example:**
```bash
GET /v1/events/me/event/liveclass/join/a1b2c3d4e5f6789?token={auth_token}
```

**Response:**
- HTML countdown page (if early)
- HTTP 302 Redirect to meeting URL (if ready)

---

### 6. Academy Staff Join Live Class

**Endpoint:** `GET /v1/events/academy/event/liveclass/join/{hash}`

**Purpose:** Same as user endpoint but for academy staff

**Authentication:** Required - `start_or_end_class` capability

**Headers:**
- `Academy: {academy_id}` - Required
- `Authorization: Token {your-token}` - Required

---

## Automatic Generation Workflow

### How Live Classes are Generated

Live classes are **automatically created** when:
1. A `CohortTimeSlot` is created
2. A `CohortTimeSlot` is updated
3. The management command `build_live_classes` is run

### Generation Process

**Trigger:** `post_save` signal on `CohortTimeSlot` model

**Background Task:** `build_live_classes_from_timeslot(timeslot_id)`

**Algorithm:**
1. Load the timeslot and associated cohort
2. Calculate start/end dates:
   - Start: `cohort.kickoff_date`
   - End: `timeslot.removed_at` or `cohort.ending_date`
3. Determine recurrence interval:
   - `DAILY`: +1 day
   - `WEEKLY`: +1 week
   - `MONTHLY`: +1 month
4. Generate classes:
   - Start from first occurrence after kickoff date
   - Create `LiveClass` for each recurrence
   - Stop at end date or if `recurrent=false`
   - Use `get_or_create()` to avoid duplicates
5. Delete obsolete future classes

**Example:**
```
Cohort: kickoff_date=2025-01-15, ending_date=2025-06-30
TimeSlot: starting_at=1400 (2 PM), ending_at=1600 (4 PM),
          recurrent=true, recurrency_type=WEEKLY, timezone=America/New_York

Generated Classes:
- 2025-01-15 14:00 - 16:00 EST
- 2025-01-22 14:00 - 16:00 EST
- 2025-01-29 14:00 - 16:00 EST
- ... (continues weekly until 2025-06-30)
```

---

## Creating Live Classes: Complete Flows

### Flow 1: Automatic Creation (Recommended)

This is the standard workflow - live classes are created automatically when you create timeslots.

**Step 1: Create Cohort TimeSlot**
```bash
POST /v1/admissions/academy/cohort/{cohort_id}/timeslot
Headers:
  Academy: 1
  Authorization: Token {your-token}

Body:
{
  "starting_at": 1400,
  "ending_at": 1600,
  "recurrent": true,
  "recurrency_type": "WEEKLY",
  "timezone": "America/New_York"
}
```

**Step 2: System Automatically:**
- Saves the `CohortTimeSlot`
- Triggers `post_save_cohort_time_slot` signal
- Queues `build_live_classes_from_timeslot.delay(timeslot_id)` task
- Background task generates all future `LiveClass` instances

**Step 3: Verify Classes Were Created**
```bash
GET /v1/events/academy/event/liveclass?cohort={cohort_slug}
Headers:
  Academy: 1
  Authorization: Token {your-token}
```

**Prerequisites:**
- Cohort must have `kickoff_date` set
- Cohort must have `ending_date` set (or `never_ends=false`)
- Cohort should have `online_meeting_url` set
- Celery workers must be running

---

### Flow 2: Manual Creation

For one-off classes or special sessions.

**Step 1: Get TimeSlot ID**
```bash
GET /v1/admissions/academy/cohort/{cohort_id}/timeslot
Headers:
  Academy: 1
  Authorization: Token {your-token}
```

**Step 2: Create Live Class**
```bash
POST /v1/events/academy/event/liveclass
Headers:
  Academy: 1
  Authorization: Token {your-token}

Body:
{
  "cohort_time_slot": 123,
  "starting_at": "2025-10-28T18:00:00Z",
  "ending_at": "2025-10-28T20:00:00Z",
  "remote_meeting_url": "https://zoom.us/j/special-session"
}
```

**Use Cases:**
- Special workshops
- Make-up classes
- Guest speaker sessions
- Classes outside regular schedule

---

### Flow 3: Bulk Regeneration

For maintenance or fixing issues.

**Management Command:**
```bash
poetry run python manage.py build_live_classes
```

**What It Does:**
- Finds all active cohorts (not DELETED or PREWORK stage)
- Finds all timeslots for each cohort
- Triggers `build_live_classes_from_timeslot` for each
- Regenerates all future classes
- Cleans up obsolete classes

**When to Use:**
- After bulk cohort updates
- After changing cohort end dates
- After fixing timeslot issues
- Database migration or recovery

---

## Attendance Tracking Flow

### Teacher Starts Class

**Scenario:** Teacher clicks join link at class time

**Step 1: Teacher Joins**
```bash
GET /v1/events/me/event/liveclass/join/{hash}?token={teacher-token}
```

**Step 2: System Automatically:**
- Checks if user is TEACHER or ASSISTANT role
- Checks if `started_at` is null
- Queues `mark_live_class_as_started.delay(live_class_id)`
- Redirects to meeting URL

**Step 3: Task Marks Class Started**
```python
# Background task updates:
live_class.started_at = timezone.now()
live_class.save()
```

---

### Class Ends

**Option A: Automatic (Scheduled)**

Background tasks can automatically mark classes as ended 30 minutes after scheduled end time.

**Option B: Manual (Staff)**
```bash
PUT /v1/events/academy/event/liveclass/{live_class_id}
Headers:
  Academy: 1
  Authorization: Token {your-token}

Body:
{
  "ended_at": "2025-10-28T20:00:00Z"
}
```

**Step 3: System Triggers Survey**
- `liveclass_ended` signal is sent
- `send_liveclass_survey` task is queued
- Surveys sent to students who attended
- Attendance tracked from cohort `history_log`

---

## Integration with Other Systems

### 1. Cohort History Tracking

When a class ends, the system checks:
- `cohort.history_log` for attendance data
- Students present within 24 hours of class end
- Creates survey answers for attendees

**History Log Format:**
```json
{
  "2025-10-28": {
    "updated_at": "2025-10-28T20:00:00Z",
    "attendance_ids": [101, 102, 103, 104]
  }
}
```

---

### 2. Feedback Surveys

**Automatic Survey Creation:**
- Triggered when `ended_at` is set
- Only if ended within last 24 hours
- Only if no survey exists for this class
- Checks academy feedback settings
- Respects excluded cohorts

**Survey Template:**
- Uses `liveclass_survey_template` from academy settings
- Falls back to default template
- Survey language matches cohort language

---

### 3. iCal Calendar Integration

**Endpoint:** `GET /v1/events/ical/cohorts/{cohort_ids}`

**Purpose:** Generate iCal feed with all live classes

**Format:**
```ics
BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:liveclass-123@breathecode.com
DTSTART:20251028T180000Z
DTEND:20251028T200000Z
SUMMARY:Web Development - Live Class
DESCRIPTION:Join: https://zoom.us/j/123456789
END:VEVENT
END:VCALENDAR
```

---

## Query Examples

### Get Today's Classes
```bash
GET /v1/events/me/event/liveclass?starting_at__gte=2025-10-28T00:00:00Z&starting_at__lte=2025-10-28T23:59:59Z
```

### Get This Week's Classes
```bash
GET /v1/events/me/event/liveclass?starting_at__gte=2025-10-28&starting_at__lte=2025-11-03
```

### Get Currently Active Classes
```bash
GET /v1/events/academy/event/liveclass?started_at__is_null=false&ended_at__is_null=true
Headers:
  Academy: 1
```

### Get Past Classes for Analysis
```bash
GET /v1/events/academy/event/liveclass?ended_at__is_null=false&ending_at__gte=2025-10-01
Headers:
  Academy: 1
```

### Get All Classes for Multiple Cohorts
```bash
GET /v1/events/academy/event/liveclass?cohort__in=cohort-1,cohort-2,cohort-3
Headers:
  Academy: 1
```

---

## Field Reference

### LiveClass Model Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Unique identifier |
| `hash` | String (40) | Unique hash for join URLs |
| `cohort_time_slot` | ForeignKey | Related timeslot template |
| `starting_at` | DateTime | Scheduled start time |
| `ending_at` | DateTime | Scheduled end time |
| `started_at` | DateTime | Actual start (when teacher joined) |
| `ended_at` | DateTime | Actual end (marks completion) |
| `remote_meeting_url` | URL | Meeting link (Zoom, Google Meet, etc.) |
| `log` | JSON | Additional metadata/logs |
| `created_at` | DateTime | Record creation time |
| `updated_at` | DateTime | Last update time |

### CohortTimeSlot Model Fields (Reference)

| Field | Type | Description |
|-------|------|-------------|
| `starting_at` | Integer | Start time in HHMM format (1400 = 2 PM) |
| `ending_at` | Integer | End time in HHMM format (1600 = 4 PM) |
| `recurrent` | Boolean | Whether this repeats |
| `recurrency_type` | String | DAILY, WEEKLY, or MONTHLY |
| `timezone` | String | Timezone (e.g., "America/New_York") |
| `removed_at` | DateTime | When timeslot was removed |

---

## Validation Rules

### Creation Validations
1. ✅ `cohort_time_slot` must exist and belong to academy
2. ✅ `starting_at` and `ending_at` are required
3. ✅ `ending_at` must be after `starting_at`
4. ✅ `remote_meeting_url` must be valid URL
5. ❌ Cannot set `started_at` on creation
6. ❌ Cannot set `ended_at` on creation

### Update Validations
1. ✅ Can update `remote_meeting_url` anytime
2. ✅ Can set `started_at` once (within ±2 minutes of current time)
3. ✅ Can set `ended_at` after class started
4. ❌ Cannot change `started_at` once set
5. ❌ Cannot backdate `started_at` more than 2 minutes
6. ❌ Must wait 30 minutes between start and end
7. ❌ Cannot set `ended_at` more than 24 hours in past

---

## Error Handling

### Common Errors

**404 - Live Class Not Found**
```json
{
  "detail": "Live class not found for this academy",
  "slug": "not-found"
}
```

**400 - Already Started**
```json
{
  "detail": "This class has already been started",
  "slug": "started-at-already-set"
}
```

**400 - Too Early/Late to Start**
```json
{
  "detail": "You can only start a class within 2 minutes of the current time",
  "slug": "started-at-not-now"
}
```

**400 - Class Not Started Yet**
```json
{
  "detail": "The class must be started before you can end it",
  "slug": "started-at-not-set"
}
```

**400 - Ended Too Soon**
```json
{
  "detail": "You cannot end a class less than 30 minutes after it started",
  "slug": "ended-at-too-soon"
}
```

---

## Best Practices

### For Automatic Generation
1. ✅ Always set `cohort.kickoff_date` and `ending_date`
2. ✅ Set `cohort.online_meeting_url` before creating timeslots
3. ✅ Use standard timezones (e.g., "America/New_York", "Europe/Madrid")
4. ✅ Ensure Celery workers are running
5. ✅ Verify classes generated after creating timeslots

### For Manual Creation
1. ✅ Use for special sessions outside regular schedule
2. ✅ Always link to existing `cohort_time_slot`
3. ✅ Use ISO 8601 datetime format with timezone
4. ✅ Include descriptive meeting URLs
5. ❌ Don't manually create what timeslots should generate

### For Querying
1. ✅ Use `upcoming=null` for student dashboards
2. ✅ Use pagination for large result sets
3. ✅ Filter by cohort for focused views
4. ✅ Use date ranges for calendar views
5. ✅ Cache frequent queries

### For Attendance
1. ✅ Let teachers start classes naturally by joining
2. ✅ Wait until class actually ends before marking
3. ✅ Track attendance in cohort history logs
4. ✅ Review surveys for feedback
5. ❌ Don't manually backdate start/end times

---

## Troubleshooting

### Live Classes Not Generated

**Symptoms:** Created timeslot but no live classes appear

**Checklist:**
1. ✅ Check Celery workers running: `celery -A breathecode.celery worker -l info`
2. ✅ Verify cohort has `kickoff_date` and `ending_date`
3. ✅ Check timeslot `recurrency_type` is valid (DAILY/WEEKLY/MONTHLY)
4. ✅ Look for task errors in logs: `build_live_classes_from_timeslot`
5. ✅ Verify cohort not in DELETED or PREWORK stage
6. ✅ Check if `ending_date` is in the past

**Solution:**
```bash
# Manually trigger generation
poetry run python manage.py build_live_classes

# Or via Django shell
from breathecode.events.tasks import build_live_classes_from_timeslot
build_live_classes_from_timeslot(timeslot_id=123)
```

---

### Classes Have Wrong Times

**Symptoms:** Live classes show incorrect times

**Checklist:**
1. ✅ Verify timeslot timezone is correct
2. ✅ Check `starting_at`/`ending_at` in timeslot (HHMM format)
3. ✅ Confirm cohort dates are correct
4. ✅ Check for timezone conversion issues

**Solution:**
```bash
# Update timeslot (will regenerate classes)
PUT /v1/admissions/academy/cohort/{cohort_id}/timeslot/{timeslot_id}
Body: { "timezone": "America/New_York" }

# Or run fix command
poetry run python manage.py fix_live_class_dates
```

---

### Cannot Join Class

**Symptoms:** Join link doesn't work or shows errors

**Checklist:**
1. ✅ Verify `hash` is correct
2. ✅ Check user has access to cohort
3. ✅ Confirm `cohort.online_meeting_url` is set
4. ✅ Check if class time has passed
5. ✅ Verify authentication token is valid

---

### Survey Not Sent After Class

**Symptoms:** Class ended but no surveys sent

**Checklist:**
1. ✅ Check academy feedback settings exist
2. ✅ Verify cohort not in excluded list
3. ✅ Confirm class ended within 24 hours
4. ✅ Check `cohort.history_log` has attendance data
5. ✅ Look for `send_liveclass_survey` task errors
6. ✅ Verify survey template exists

---

## Security & Permissions

### Required Capabilities

**For Academy Endpoints:**
- `start_or_end_class` - Create, update, view academy live classes

**For User Endpoints:**
- Authenticated user - View own live classes
- Must be enrolled in cohort (student) or assigned as teacher/TA

### Data Access Rules

1. **Students** can only see classes for cohorts they're enrolled in
2. **Teachers/TAs** can see classes for cohorts they're assigned to
3. **Academy Staff** with capability can see all academy classes
4. Join links work only for authorized users
5. Starting classes restricted to teachers/assistants

---

## Performance Considerations

### Indexing
- `starting_at` and `ending_at` are indexed for fast date queries
- `hash` is unique and indexed for quick join lookups
- `cohort_time_slot` foreign key is indexed

### Caching
- User live class view has caching enabled (`LiveClassCache`)
- Cache invalidation on class updates
- Consider caching frequently accessed cohort classes

### Pagination
- Always use pagination for academy-wide queries
- Default limit is configurable via `APIViewExtensions`
- Sort by `starting_at` DESC by default

---

## Related Documentation

- [COHORTS.md](./COHORTS.md) - Cohort management and timeslots
- [COHORTS_CREATE.md](./COHORTS_CREATE.md) - Creating cohorts
- See timeslot endpoints in cohort documentation for schedule management

---

## Summary

Live Classes provide automatic scheduling and attendance tracking for cohort sessions:

1. **Create timeslots** → System generates live classes automatically
2. **Students join** via unique hash links
3. **Teachers join** → Marks class as started
4. **Class ends** → Triggers surveys for attendees
5. **Query classes** with flexible filtering for calendars and dashboards

The system handles recurrence, timezone conversion, and cleanup automatically - you just need to define the schedule!
