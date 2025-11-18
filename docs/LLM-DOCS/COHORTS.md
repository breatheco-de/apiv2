# Cohort Information API Endpoints

This document provides a comprehensive list of all API endpoints needed to gather complete information about a cohort, including students, teachers, syllabus, schedule, feedback, and activity data.

## Core Cohort Information

### 1. Get Cohort Details
**Endpoint:** `GET /v1/admissions/academy/cohort/{cohort_id}`
- **Purpose:** Get basic cohort information (name, dates, stage, syllabus, etc.)
- **Parameters:** `cohort_id` (can be numeric ID or slug)
- **Response includes:**
  - Basic info: `id`, `slug`, `name`, `kickoff_date`, `ending_date`, `current_day`, `stage`
  - Syllabus: `syllabus_version` with syllabus details and technologies
  - Schedule: `schedule` information
  - Academy: `academy` details
  - Settings: `private`, `never_ends`, `remote_available`, `timezone`
  - Micro-cohorts: `micro_cohorts` if applicable

### 2. Get Current User's Cohorts
**Endpoint:** `GET /v1/admissions/academy/cohort/me`
- **Purpose:** Get cohorts for the authenticated user
- **Query Parameters:**
  - `upcoming=true/false` - Filter by upcoming/past cohorts
  - `stage=INACTIVE,PREWORK,STARTED,FINAL_PROJECT,ENDED` - Filter by stage
- **Response:** List of cohorts the user belongs to

## Students, Teachers, and Staff

### 3. Get Cohort Users (Students, Teachers, TAs, Reviewers)
**Endpoint:** `GET /v1/admissions/academy/cohort/{cohort_id}/user`
- **Purpose:** Get all users in a specific cohort
- **Query Parameters:**
  - `roles=STUDENT,TEACHER,ASSISTANT,REVIEWER` - Filter by role
  - `educational_status=ACTIVE,POSTPONED,SUSPENDED,GRADUATED,DROPPED,NOT_COMPLETING`
  - `finantial_status=FULLY_PAID,UP_TO_DATE,LATE`
  - `tasks=true` - Include task information
  - `plans=true` - Include plan information
- **Response includes:**
  - User details: `id`, `first_name`, `last_name`, `email`, `github`
  - Role: `role` (STUDENT, TEACHER, ASSISTANT, REVIEWER)
  - Status: `educational_status`, `finantial_status`
  - Cohort info: `cohort` details
  - Tasks: If `tasks=true`, includes assignment data
  - Plans: If `plans=true`, includes subscription/plan data

### 4. Get Specific User in Cohort
**Endpoint:** `GET /v1/admissions/academy/cohort/{cohort_id}/user/{user_id}`
- **Purpose:** Get detailed information about a specific user in the cohort
- **Response:** Detailed user information with cohort-specific data

## Syllabus and Technologies

### 5. Get Syllabus Information
**Endpoint:** `GET /v1/admissions/public/syllabus`
- **Purpose:** Get syllabus details including technologies
- **Query Parameters:**
  - `id={syllabus_id}` - Get specific syllabus
- **Response includes:**
  - `name`, `slug`, `main_technologies` (comma-separated)
  - `duration_in_hours`, `duration_in_days`, `week_hours`
  - `github_url`, `logo`
  - `private`, `is_documentation`

### 6. Get Syllabus Versions
**Endpoint:** `GET /v1/admissions/academy/syllabus/version`
- **Purpose:** Get all syllabus versions for an academy
- **Response:** List of syllabus versions with detailed information

## Schedule and Time Slots

### 7. Get Cohort Time Slots
**Endpoint:** `GET /v1/admissions/academy/cohort/{cohort_id}/timeslot`
- **Purpose:** Get schedule/time slots for the cohort
- **Query Parameters:**
  - `recurrency_type=DAILY,WEEKLY,MONTHLY` - Filter by recurrence
- **Response includes:**
  - `starting_at`, `ending_at`
  - `recurrent`, `recurrency_type`
  - `timezone`

### 8. Get Specific Time Slot
**Endpoint:** `GET /v1/admissions/academy/cohort/{cohort_id}/timeslot/{timeslot_id}`
- **Purpose:** Get details of a specific time slot

## Assignments and Tasks

### 9. Get Cohort Tasks/Assignments
**Endpoint:** `GET /v1/assignments/academy/cohort/{cohort_id}/task`
- **Purpose:** Get all tasks/assignments for the cohort
- **Query Parameters:**
  - `task_type=EXERCISE,PROJECT,QUIZ,LESSON` - Filter by task type
  - `task_status=PENDING,STARTED,COMPLETED` - Filter by status
  - `revision_status=PENDING,APPROVED,REJECTED` - Filter by revision status
  - `educational_status=ACTIVE,GRADUATED` - Filter by student status
  - `student={user_ids}` - Filter by specific students
  - `like={search_term}` - Search in title/associated_slug
- **Response includes:**
  - Task details: `id`, `title`, `description`, `task_type`
  - Status: `task_status`, `revision_status`
  - User: `user` information
  - Cohort: `cohort` information
  - Delivery: `github_url`, `live_url`, `delivery_date`

### 10. Get Student Tasks
**Endpoint:** `GET /v1/assignments/user/me/task`
- **Purpose:** Get tasks for the authenticated user
- **Query Parameters:**
  - `cohort={cohort_id_or_slug}` - Filter by cohort
  - `task_type`, `task_status`, `revision_status` - Same as above
  - `associated_slug={slug}` - Filter by syllabus module

## Activity Timeline

### 11. Get Cohort Activity
**Endpoint:** `GET /v1/activity/cohort/{cohort_id}`
- **Purpose:** Get activity timeline for the cohort
- **Query Parameters:**
  - `slug={activity_type}` - Filter by activity type
  - Available activities: `breathecode_login`, `classroom_attendance`, `lesson_opened`, `exercise_success`, `nps_survey_answered`, etc.
- **Response includes:**
  - Activity details: `slug`, `data`, `day`, `created_at`
  - User: `user_id`, `email`
  - Cohort: `cohort` slug

### 12. Get Student Activity
**Endpoint:** `GET /v1/activity/academy/student/{student_id}`
- **Purpose:** Get activity timeline for a specific student
- **Query Parameters:**
  - `slug={activity_type}` - Filter by activity type
  - `cohort={cohort_slug}` - Filter by cohort

### 13. Get My Activity
**Endpoint:** `GET /v1/activity/me`
- **Purpose:** Get activity for the authenticated user
- **Query Parameters:**
  - `slug={activity_type}`, `cohort={cohort_slug}`, `user_id`, `email`

## Cohort History and Logs

### 14. Get Cohort History Log
**Endpoint:** `GET /v1/admissions/academy/cohort/{cohort_id}/log`
- **Purpose:** Get detailed cohort history and daily logs
- **Response includes:**
  - Daily logs with attendance, progress, and notes
  - Current day information
  - Historical data for each day

### 15. Get User Cohort History
**Endpoint:** `GET /v1/admissions/me/cohort/user/log`
- **Purpose:** Get user's cohort history
- **Query Parameters:**
  - `cohort_id={id}` - Get history for specific cohort
- **Response:** User's history log for cohorts

## NPS and Feedback

### 16. Get Cohort Surveys
**Endpoint:** `GET /v1/feedback/academy/survey`
- **Purpose:** Get surveys for the academy
- **Query Parameters:**
  - `cohort={cohort_id}` - Filter by cohort
- **Response includes:**
  - Survey details: `id`, `title`, `status`, `created_at`, `sent_at`
  - Cohort: `cohort` information
  - Scores: `scores` (NPS scores)
  - Response rate: `response_rate`

### 17. Get Survey Answers
**Endpoint:** `GET /v1/feedback/academy/answer`
- **Purpose:** Get NPS/feedback answers
- **Query Parameters:**
  - `cohort={cohort_slugs}` - Filter by cohort
  - `user={user_ids}` - Filter by users
  - `score={score}` - Filter by NPS score
  - `status=PENDING,SENT,ANSWERED` - Filter by status
  - `survey={survey_ids}` - Filter by survey
- **Response includes:**
  - Answer details: `id`, `score`, `comment`, `status`
  - User: `user` information
  - Cohort: `cohort` information
  - Survey: `survey` information
  - Created: `created_at`

### 18. Get My Survey Answers
**Endpoint:** `GET /v1/feedback/user/me/answer`
- **Purpose:** Get current user's survey answers

## Reviews and Testimonials

### 19. Get Reviews
**Endpoint:** `GET /v1/feedback/review`
- **Purpose:** Get reviews/testimonials
- **Query Parameters:**
  - `cohort={cohort_id}` - Filter by cohort
  - `user={user_id}` - Filter by user
- **Response includes:**
  - Review details: `id`, `total_rating`, `comments`, `status`
  - Platform: `platform` information
  - User: `author` information
  - Cohort: `cohort` information

## Additional Cohort Data

### 20. Get Academy Information
**Endpoint:** `GET /v1/admissions/academy/{academy_id}`
- **Purpose:** Get academy details
- **Response includes:**
  - Academy info: `name`, `slug`, `timezone`, `logo_url`
  - Contact: `feedback_email`, `legal_name`

### 21. Get Public Cohorts
**Endpoint:** `GET /v1/admissions/cohort/all`
- **Purpose:** Get public cohorts (for public-facing applications)
- **Query Parameters:**
  - `upcoming=true/false` - Filter by upcoming/past
  - `academy={academy_slugs}` - Filter by academy
  - `stage={stages}` - Filter by stage
  - `location={academy_slugs}` - Filter by location

## Usage Examples

### Get Complete Cohort Overview
```bash
# 1. Get basic cohort info
GET /v1/admissions/academy/cohort/123

# 2. Get all users (students, teachers, TAs)
GET /v1/admissions/academy/cohort/123/user?roles=STUDENT,TEACHER,ASSISTANT,REVIEWER

# 3. Get schedule
GET /v1/admissions/academy/cohort/123/timeslot

# 4. Get assignments
GET /v1/assignments/academy/cohort/123/task

# 5. Get activity timeline
GET /v1/activity/cohort/123

# 6. Get NPS scores
GET /v1/feedback/academy/answer?cohort=cohort-slug

# 7. Get cohort history
GET /v1/admissions/academy/cohort/123/log
```

### Calculate Days Remaining
```javascript
// From cohort data
const kickoffDate = new Date(cohort.kickoff_date);
const endingDate = new Date(cohort.ending_date);
const currentDay = cohort.current_day;
const totalDays = Math.ceil((endingDate - kickoffDate) / (1000 * 60 * 60 * 24));
const daysRemaining = totalDays - currentDay;
```

### Get Technologies Being Taught
```javascript
// From syllabus data
const technologies = cohort.syllabus_version.syllabus.main_technologies.split(',');
```

### Calculate NPS Score
```javascript
// From survey answers
const promoters = answers.filter(a => a.score >= 9).length;
const detractors = answers.filter(a => a.score <= 6).length;
const total = answers.length;
const npsScore = ((promoters - detractors) / total) * 100;
```

## Authentication and Permissions

Most endpoints require authentication and specific permissions:
- `read_all_cohort` - Read cohort information
- `read_single_cohort` - Read single cohort (for students)
- `crud_cohort` - Create/update/delete cohorts
- `read_assignment` - Read assignments
- `read_activity` - Read activity data
- `read_nps_answers` - Read NPS/feedback data

## Rate Limiting and Caching

- Most endpoints support caching with `Cache-Control` headers
- Pagination is available for list endpoints using `limit` and `offset`
- Some endpoints support sorting with `sort` parameter
