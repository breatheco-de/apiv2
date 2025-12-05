# Webhooks & Hooks Management

## Overview

The BreatheCode API provides a powerful webhook system that allows academies to subscribe to real-time events happening within the platform. When specific events occur (like a student completing an assignment, a new form entry, or a cohort status change), the system will automatically send HTTP POST requests to your configured endpoints with relevant data payloads.

This webhook system is built on top of Django REST Hooks and integrated with Celery for reliable asynchronous delivery.

## Key Concepts

### Hooks vs Webhooks
- **Hook**: A subscription record that defines which event you want to listen to and where to send the data
- **Webhook**: The actual HTTP POST request sent to your target URL when the event occurs

### Event-Driven Architecture
- Events are triggered automatically when models change or specific actions occur
- Each hook subscription is academy-scoped (you only receive events for your academy's data)
- Superadmins can subscribe to events across all academies

## Authentication

### Academy Token Required

To manage webhooks, you must authenticate using an **Academy Token**. This is a special authentication token where:

- The token's `username` matches the academy's `slug`
- The system validates that the user represents a valid academy

```bash
# Example: Using academy token in headers
Authorization: Token YOUR_ACADEMY_TOKEN
```

### Superadmin Access

Superadmin users can:
- Subscribe to any event without academy restrictions
- Receive webhooks from all academies
- Manage hooks across the entire platform

## Base URL

All webhook management endpoints are under:

```
https://api.4geeks.com/v1/notify/
```

## Available Events

The BreatheCode API supports the following webhook events:

### Student & Cohort Management

| Event Name | Description | Trigger | Model |
|------------|-------------|---------|-------|
| `profile_academy.added` | New academy member added | ProfileAcademy created | `authenticate.ProfileAcademy` |
| `profile_academy.changed` | Academy member profile updated | ProfileAcademy updated | `authenticate.ProfileAcademy` |
| `cohort_user.added` | Student added to cohort | CohortUser created | `admissions.CohortUser` |
| `cohort_user.changed` | Cohort user record updated | CohortUser updated | `admissions.CohortUser` |
| `cohort_user.edu_status_updated` | Student educational status changed | Educational status field changes | `admissions.CohortUser` |
| `cohort.cohort_stage_updated` | Cohort stage changed | Stage field updated | `admissions.Cohort` |
| `user_invite.invite_status_updated` | Invitation status changed | Invite accepted/rejected | `authenticate.UserInvite` |

### Assignments & Learning

| Event Name | Description | Trigger | Model |
|------------|-------------|---------|-------|
| `assignment.assignment_status_updated` | Assignment status changed | Task status field changes | `assignments.Task` |
| `assignment.assignment_created` | New assignment created | New Task created | `assignments.Task` |
| `assignment.assignment_revision_status_updated` | Assignment revision status changed | Revision status field changes | `assignments.Task` |
| `asset.asset_status_updated` | Learning asset status updated | Asset status changes | `registry.Asset` |

### Assessments

| Event Name | Description | Trigger | Model |
|------------|-------------|---------|-------|
| `UserAssessment.userassessment_status_updated` | Assessment status changed | UserAssessment status updated | `assessment.UserAssessment` |

### Events & Attendance

| Event Name | Description | Trigger | Model |
|------------|-------------|---------|-------|
| `event.event_status_updated` | Event status changed | Event status field changes | `events.Event` |
| `event.event_rescheduled` | Event date/time changed | Event rescheduled | `events.Event` |
| `event.new_event_order` | New event registration | New EventCheckin created | `events.EventCheckin` |
| `event.new_event_attendee` | New event attendee | Attendee added to event | `events.EventCheckin` |

### Marketing & Leads

| Event Name | Description | Trigger | Model |
|------------|-------------|---------|-------|
| `form_entry.added` | New form submission | FormEntry created | `marketing.FormEntry` |
| `form_entry.changed` | Form entry updated | FormEntry updated | `marketing.FormEntry` |
| `form_entry.won_or_lost` | Lead won or lost | Deal status changed | `marketing.FormEntry` |
| `form_entry.new_deal` | New deal created | New deal in CRM | `marketing.FormEntry` |

### Payments & Subscriptions

| Event Name | Description | Trigger | Model |
|------------|-------------|---------|-------|
| `planfinancing.planfinancing_created` | New financing plan created | PlanFinancing created | `payments.PlanFinancing` |
| `subscription.subscription_created` | New subscription created | Subscription created | `payments.Subscription` |

### Mentorship

| Event Name | Description | Trigger | Model |
|------------|-------------|---------|-------|
| `session.mentorship_session_status` | Mentorship session status changed | Session status updated | `mentorship.MentorshipSession` |

## API Endpoints

### 1. Get Available Events

Get a list of all available webhook events that can be subscribed to, including their descriptions and metadata.

**Endpoint:** `GET /v1/notify/hook/event`

**Authentication:** Required (Academy Token)

**Headers:**
```
Authorization: Token YOUR_ACADEMY_TOKEN
```

**Query Parameters:**
- `category` (optional): Filter by category (admissions, assignments, marketing, payments, events, mentorship, assessment, authentication, registry)
- `like` (optional): Search in event name, description, or category

**Example Request:**
```bash
# Get all available events
curl -X GET \
  'https://api.4geeks.com/v1/notify/hook/event' \
  -H 'Authorization: Token YOUR_ACADEMY_TOKEN'

# Filter by app
curl -X GET \
  'https://api.4geeks.com/v1/notify/hook/event?app=assignments' \
  -H 'Authorization: Token YOUR_ACADEMY_TOKEN'

# Search for events
curl -X GET \
  'https://api.4geeks.com/v1/notify/hook/event?like=assignment' \
  -H 'Authorization: Token YOUR_ACADEMY_TOKEN'
```

**Example Response:**
```json
[
  {
    "event": "assignment.assignment_created",
    "label": "Assignment Created",
    "description": "Triggered when a new assignment is created for a student",
    "app": "assignments",
    "model": "assignments.Task"
  },
  {
    "event": "assignment.assignment_revision_status_updated",
    "label": "Assignment Revision Status Updated",
    "description": "Triggered when an assignment's revision status changes (PENDING, APPROVED, REJECTED)",
    "app": "assignments",
    "model": "assignments.Task"
  },
  {
    "event": "assignment.assignment_status_updated",
    "label": "Assignment Status Updated",
    "description": "Triggered when an assignment's task status changes (PENDING to DONE)",
    "app": "assignments",
    "model": "assignments.Task"
  },
  {
    "event": "cohort.cohort_stage_updated",
    "label": "Cohort Stage Updated",
    "description": "Triggered when a cohort's stage changes (INACTIVE, PREWORK, STARTED, FINAL_PROJECT, ENDED)",
    "app": "admissions",
    "model": "admissions.Cohort"
  }
]
```

**Response Fields:**
- `event`: The event name to use when subscribing
- `label`: Human-readable label (auto-derived by de-slugifying the action's third part, e.g., "assignment_created" → "Assignment Created")
- `description`: Detailed description of when the event is triggered
- `app`: The Django app that owns this event (auto-derived from action)
- `model`: The Django model that triggers this event (auto-derived from action)

**Available Apps:**
- `admissions`: Student and cohort management events
- `assignments`: Assignment and learning activity events
- `assessment`: Assessment and evaluation events
- `authenticate`: User authentication and invitation events
- `events`: Event and attendance tracking
- `marketing`: Lead generation and CRM events
- `payments`: Payment and subscription events
- `mentorship`: Mentorship session events
- `registry`: Learning asset management events

### 2. List All Hooks

Get all webhook subscriptions for the authenticated academy.

**Endpoint:** `GET /v1/notify/hook/subscribe`

**Headers:**
```
Authorization: Token YOUR_ACADEMY_TOKEN
```

**Query Parameters:**
- `app` (optional): Filter by Django app name(s), comma-separated (e.g., `assignments,admissions`). Matches hooks for events belonging to the specified app(s).
- `event` (optional): Filter by event name(s), comma-separated (e.g., `assignment.assignment_created,cohort_user.added`)
- `signal` (optional): Filter by Django signal path(s), comma-separated. Supports partial matching (e.g., `assignment_created` matches `breathecode.assignments.signals.assignment_created`)
- `service_id` (optional): Filter by service ID, comma-separated
- `like` (optional): Search in event name or target URL
- `limit` (optional): Number of results per page (default: pagination settings)
- `offset` (optional): Pagination offset

**Example Requests:**
```bash
# Filter by single event
curl -X GET \
  'https://api.4geeks.com/v1/notify/hook/subscribe?event=assignment.assignment_created' \
  -H 'Authorization: Token YOUR_ACADEMY_TOKEN'

# Filter by multiple events (comma-separated)
curl -X GET \
  'https://api.4geeks.com/v1/notify/hook/subscribe?event=assignment.assignment_created,cohort_user.added' \
  -H 'Authorization: Token YOUR_ACADEMY_TOKEN'

# Filter by app (all events from assignments app)
curl -X GET \
  'https://api.4geeks.com/v1/notify/hook/subscribe?app=assignments' \
  -H 'Authorization: Token YOUR_ACADEMY_TOKEN'

# Filter by multiple apps
curl -X GET \
  'https://api.4geeks.com/v1/notify/hook/subscribe?app=assignments,admissions' \
  -H 'Authorization: Token YOUR_ACADEMY_TOKEN'

# Filter by signal (partial match)
curl -X GET \
  'https://api.4geeks.com/v1/notify/hook/subscribe?signal=assignment_created' \
  -H 'Authorization: Token YOUR_ACADEMY_TOKEN'

# Filter by full signal path
curl -X GET \
  'https://api.4geeks.com/v1/notify/hook/subscribe?signal=breathecode.assignments.signals.assignment_created' \
  -H 'Authorization: Token YOUR_ACADEMY_TOKEN'

# Combine multiple filters
curl -X GET \
  'https://api.4geeks.com/v1/notify/hook/subscribe?app=assignments&event=assignment.assignment_created,assignment.assignment_status_updated' \
  -H 'Authorization: Token YOUR_ACADEMY_TOKEN'
```

**Example Response:**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 123,
      "event": "assignment.assignment_created",
      "target": "https://your-app.com/webhooks/assignment-created",
      "service_id": "my-service-v1",
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z",
      "total_calls": 45,
      "last_call_at": "2025-01-20T14:22:30Z",
      "last_response_code": 200
    },
    {
      "id": 124,
      "event": "cohort_user.added",
      "target": "https://your-app.com/webhooks/student-added",
      "service_id": null,
      "created_at": "2025-01-16T09:15:00Z",
      "updated_at": "2025-01-16T09:15:00Z",
      "total_calls": 12,
      "last_call_at": "2025-01-19T11:10:00Z",
      "last_response_code": 200
    }
  ]
}
```

### 3. Subscribe to a Hook

Create a new webhook subscription.

**Endpoint:** `POST /v1/notify/hook/subscribe`

**Headers:**
```
Authorization: Token YOUR_ACADEMY_TOKEN
Content-Type: application/json
```

**Request Body:**
```json
{
  "event": "assignment.assignment_created",
  "target": "https://your-app.com/webhooks/assignment-created",
  "service_id": "my-service-v1"
}
```

**Fields:**
- `event` (required): Event name from the available events list
- `target` (required): Full URL where webhook POST requests will be sent
- `service_id` (optional): Custom identifier for your service (useful for managing multiple webhook endpoints)

**Example Request:**
```bash
curl -X POST \
  'https://api.4geeks.com/v1/notify/hook/subscribe' \
  -H 'Authorization: Token YOUR_ACADEMY_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "event": "assignment.assignment_created",
    "target": "https://your-app.com/webhooks/assignment-created",
    "service_id": "production-v2"
  }'
```

**Example Response:**
```json
{
  "id": 125,
  "event": "assignment.assignment_created",
  "target": "https://your-app.com/webhooks/assignment-created",
  "service_id": "production-v2",
  "created_at": "2025-01-20T15:30:00Z",
  "updated_at": "2025-01-20T15:30:00Z",
  "total_calls": 0,
  "last_call_at": null,
  "last_response_code": null
}
```

**Error Responses:**

Invalid event:
```json
{
  "detail": "Unexpected event unknown.event",
  "slug": "invalid-event",
  "status_code": 400
}
```

Invalid academy token:
```json
{
  "detail": "No valid academy token found",
  "slug": "invalid-academy-token",
  "status_code": 400
}
```

### 4. Update a Hook

Update an existing webhook subscription.

**Endpoint:** `PUT /v1/notify/hook/subscribe/{hook_id}`

**Headers:**
```
Authorization: Token YOUR_ACADEMY_TOKEN
Content-Type: application/json
```

**Request Body:**
```json
{
  "event": "assignment.assignment_status_updated",
  "target": "https://your-app.com/webhooks/assignment-updated-v2",
  "service_id": "production-v2"
}
```

**Example Request:**
```bash
curl -X PUT \
  'https://api.4geeks.com/v1/notify/hook/subscribe/123' \
  -H 'Authorization: Token YOUR_ACADEMY_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "event": "assignment.assignment_status_updated",
    "target": "https://your-app.com/webhooks/assignment-updated",
    "service_id": "production-v2"
  }'
```

**Example Response:**
```json
{
  "id": 123,
  "event": "assignment.assignment_status_updated",
  "target": "https://your-app.com/webhooks/assignment-updated",
  "service_id": "production-v2",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-20T16:45:00Z",
  "total_calls": 45,
  "last_call_at": "2025-01-20T14:22:30Z",
  "last_response_code": 200
}
```

### 5. Delete Hook(s)

Unsubscribe from webhook(s). You can delete a specific hook by ID or delete multiple hooks using filters.

**Endpoint:** `DELETE /v1/notify/hook/subscribe/{hook_id}` or `DELETE /v1/notify/hook/subscribe`

**Headers:**
```
Authorization: Token YOUR_ACADEMY_TOKEN
```

**Delete by ID:**
```bash
curl -X DELETE \
  'https://api.4geeks.com/v1/notify/hook/subscribe/123' \
  -H 'Authorization: Token YOUR_ACADEMY_TOKEN'
```

**Delete by filters:**

Query Parameters (at least one required):
- `event`: Event name(s), comma-separated
- `service_id`: Service ID(s), comma-separated

```bash
# Delete all hooks for specific event
curl -X DELETE \
  'https://api.4geeks.com/v1/notify/hook/subscribe?event=assignment.assignment_created' \
  -H 'Authorization: Token YOUR_ACADEMY_TOKEN'

# Delete all hooks for specific service
curl -X DELETE \
  'https://api.4geeks.com/v1/notify/hook/subscribe?service_id=old-service-v1' \
  -H 'Authorization: Token YOUR_ACADEMY_TOKEN'

# Delete hooks matching multiple criteria
curl -X DELETE \
  'https://api.4geeks.com/v1/notify/hook/subscribe?event=assignment.assignment_created,assignment.assignment_status_updated&service_id=staging' \
  -H 'Authorization: Token YOUR_ACADEMY_TOKEN'
```

**Example Response:**
```json
{
  "details": "Unsubscribed from 3 hooks"
}
```

**Error Response (no filters provided):**
```json
{
  "detail": "Please include some filter in the URL",
  "slug": "validation-error",
  "status_code": 400
}
```

### 6. Get Sample Data

Retrieve sample payload data for a specific hook or event type. This is useful for understanding what data structure you'll receive.

**Endpoint:** `GET /v1/notify/hook/sample` or `GET /v1/notify/hook/{hook_id}/sample`

**Headers:**
```
Authorization: Token YOUR_ACADEMY_TOKEN
```

**Get sample by hook ID:**
```bash
curl -X GET \
  'https://api.4geeks.com/v1/notify/hook/123/sample' \
  -H 'Authorization: Token YOUR_ACADEMY_TOKEN'
```

**Get sample by filters:**

Query Parameters (at least one required if not using hook_id):
- `event`: Event name(s), comma-separated
- `service_id`: Service ID(s), comma-separated
- `like`: Search term

```bash
curl -X GET \
  'https://api.4geeks.com/v1/notify/hook/sample?event=assignment.assignment_created' \
  -H 'Authorization: Token YOUR_ACADEMY_TOKEN'
```

**Example Response:**
```json
{
  "id": 456,
  "title": "Build a Landing Page",
  "task_status": "DONE",
  "associated_slug": "build-landing-page",
  "description": "Create a responsive landing page using HTML, CSS and JavaScript",
  "revision_status": "APPROVED",
  "github_url": "https://github.com/student/landing-page",
  "live_url": "https://student.github.io/landing-page",
  "task_type": "PROJECT",
  "user": {
    "id": 789,
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "opened_at": "2025-01-15T10:00:00Z",
  "read_at": "2025-01-16T09:30:00Z",
  "reviewed_at": "2025-01-17T14:20:00Z",
  "delivered_at": "2025-01-16T16:45:00Z",
  "cohort": {
    "id": 12,
    "name": "Full Stack Development - Cohort 45",
    "slug": "full-stack-45"
  },
  "assignment_telemetry": {
    "session_duration": 7200,
    "percentage": 100,
    "completed_at": "2025-01-16T16:40:00Z"
  },
  "created_at": "2025-01-15T09:00:00Z",
  "updated_at": "2025-01-17T14:20:00Z"
}
```

## Webhook Payload Structures

### Common Patterns

All webhook POST requests sent to your target URL will include:

**Headers:**
```
Content-Type: application/json
User-Agent: BreatheCode-Webhooks/1.0
```

**Payload Structure:**

The payload structure varies by event type. Below are detailed examples for each major category.

### Assignment Events

#### `assignment.assignment_created`

Triggered when a new assignment is created for a student.

```json
{
  "id": 456,
  "title": "Build a Todo App",
  "task_status": "PENDING",
  "associated_slug": "build-todo-app",
  "description": "Create a todo application with CRUD operations",
  "revision_status": "PENDING",
  "github_url": null,
  "live_url": null,
  "task_type": "PROJECT",
  "user": {
    "id": 789,
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "opened_at": null,
  "read_at": null,
  "reviewed_at": null,
  "delivered_at": null,
  "cohort": {
    "id": 12,
    "name": "Full Stack Development - Cohort 45",
    "slug": "full-stack-45"
  },
  "assignment_telemetry": null,
  "created_at": "2025-01-15T09:00:00Z",
  "updated_at": "2025-01-15T09:00:00Z"
}
```

#### `assignment.assignment_status_updated`

Triggered when an assignment's status changes (e.g., PENDING → DONE).

```json
{
  "id": 456,
  "title": "Build a Todo App",
  "task_status": "DONE",
  "associated_slug": "build-todo-app",
  "description": "Create a todo application with CRUD operations",
  "revision_status": "PENDING",
  "github_url": "https://github.com/student/todo-app",
  "live_url": "https://student.github.io/todo-app",
  "task_type": "PROJECT",
  "user": {
    "id": 789,
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "opened_at": "2025-01-15T10:00:00Z",
  "read_at": null,
  "reviewed_at": null,
  "delivered_at": "2025-01-16T16:45:00Z",
  "cohort": {
    "id": 12,
    "name": "Full Stack Development - Cohort 45",
    "slug": "full-stack-45"
  },
  "assignment_telemetry": {
    "session_duration": 7200,
    "percentage": 100,
    "completed_at": "2025-01-16T16:40:00Z"
  },
  "created_at": "2025-01-15T09:00:00Z",
  "updated_at": "2025-01-16T16:45:00Z"
}
```

**Task Status Values:**
- `PENDING`: Not started
- `DONE`: Completed by student

**Task Types:**
- `PROJECT`: Full project assignment
- `EXERCISE`: Practice exercise
- `LESSON`: Lesson or reading
- `QUIZ`: Quiz or assessment

#### `assignment.assignment_revision_status_updated`

Triggered when an assignment's revision status changes (teacher review).

```json
{
  "id": 456,
  "title": "Build a Todo App",
  "task_status": "DONE",
  "revision_status": "APPROVED",
  "github_url": "https://github.com/student/todo-app",
  "live_url": "https://student.github.io/todo-app",
  "reviewed_at": "2025-01-17T14:20:00Z",
  "user": {
    "id": 789,
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "cohort": {
    "id": 12,
    "name": "Full Stack Development - Cohort 45",
    "slug": "full-stack-45"
  },
  "created_at": "2025-01-15T09:00:00Z",
  "updated_at": "2025-01-17T14:20:00Z"
}
```

**Revision Status Values:**
- `PENDING`: Awaiting review
- `APPROVED`: Accepted by teacher
- `REJECTED`: Needs improvements

### Cohort & Student Events

#### `cohort_user.added`

Triggered when a student is added to a cohort.

```json
{
  "id": 234,
  "user": {
    "id": 789,
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane.doe@example.com"
  },
  "cohort": {
    "id": 12,
    "name": "Full Stack Development - Cohort 45",
    "slug": "full-stack-45",
    "kickoff_date": "2025-01-10T00:00:00Z",
    "ending_date": "2025-06-30T00:00:00Z",
    "stage": "STARTED",
    "academy": {
      "id": 4,
      "name": "Downtown Campus",
      "slug": "downtown-campus"
    }
  },
  "role": "STUDENT",
  "finantial_status": "FULLY_PAID",
  "educational_status": "ACTIVE",
  "watching": false,
  "created_at": "2025-01-10T08:30:00Z",
  "updated_at": "2025-01-10T08:30:00Z",
  "profile_academy": {
    "id": 567,
    "email": "jane.doe@example.com",
    "first_name": "Jane",
    "last_name": "Doe",
    "phone": "+1234567890",
    "address": "123 Main St"
  }
}
```

**Role Values:**
- `STUDENT`: Regular student
- `TEACHER`: Instructor
- `ASSISTANT`: Teaching assistant

**Financial Status Values:**
- `FULLY_PAID`: Payment complete
- `UP_TO_DATE`: Payment current
- `LATE`: Payment overdue

**Educational Status Values:**
- `ACTIVE`: Currently active
- `POSTPONED`: Temporarily paused
- `SUSPENDED`: Suspended
- `GRADUATED`: Completed program
- `DROPPED`: Withdrew from program

#### `cohort_user.edu_status_updated`

Triggered when a student's educational status changes.

```json
{
  "id": 234,
  "user": {
    "id": 789,
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "cohort": {
    "id": 12,
    "name": "Full Stack Development - Cohort 45",
    "slug": "full-stack-45"
  },
  "role": "STUDENT",
  "educational_status": "GRADUATED",
  "created_at": "2025-01-10T08:30:00Z",
  "updated_at": "2025-06-30T16:00:00Z"
}
```

#### `cohort.cohort_stage_updated`

Triggered when a cohort's stage changes.

```json
{
  "id": 12,
  "slug": "full-stack-45",
  "name": "Full Stack Development - Cohort 45",
  "language": "en",
  "kickoff_date": "2025-01-10T00:00:00Z",
  "ending_date": "2025-06-30T00:00:00Z",
  "current_day": 45,
  "current_module": 3,
  "stage": "FINAL_PROJECT",
  "academy": {
    "id": 4,
    "name": "Downtown Campus",
    "slug": "downtown-campus",
    "street_address": "123 Tech Street",
    "city": "San Francisco",
    "country": "USA"
  },
  "syllabus_version": {
    "version": 2,
    "name": "Full Stack Developer v2",
    "syllabus": {
      "slug": "full-stack-ft",
      "name": "Full Stack Development"
    }
  },
  "is_hidden_on_prework": false,
  "available_as_saas": true
}
```

**Cohort Stage Values:**
- `INACTIVE`: Not started
- `PREWORK`: Pre-course work
- `STARTED`: Active learning
- `FINAL_PROJECT`: Working on final project
- `ENDED`: Completed
- `DELETED`: Archived

### Marketing & Lead Events

#### `form_entry.added`

Triggered when a new lead/form submission is created.

```json
{
  "id": 9876,
  "first_name": "John",
  "last_name": "Smith",
  "email": "john.smith@example.com",
  "phone": "+1987654321",
  "course": "full-stack-development",
  "deal_status": "WON",
  "location": "Miami, FL",
  "language": "en",
  "utm_source": "google",
  "utm_medium": "cpc",
  "utm_campaign": "summer-2025",
  "utm_content": "ad-variant-a",
  "gclid": "EAIaIQobChMI...",
  "tags": "high-intent,fintech-background",
  "country": "USA",
  "city": "Miami",
  "storage_status": "SYNCED",
  "created_at": "2025-01-20T10:15:00Z",
  "updated_at": "2025-01-20T10:15:00Z"
}
```

#### `form_entry.won_or_lost`

Triggered when a lead is marked as won or lost.

```json
{
  "id": 9876,
  "first_name": "John",
  "last_name": "Smith",
  "email": "john.smith@example.com",
  "deal_status": "WON",
  "updated_at": "2025-01-22T14:30:00Z"
}
```

**Deal Status Values:**
- `WON`: Converted to paying student
- `LOST`: Did not convert

### Payment Events

#### `subscription.subscription_created`

Triggered when a new subscription is created.

```json
{
  "id": 445,
  "status": "ACTIVE",
  "paid_at": "2025-01-20T15:00:00Z",
  "valid_until": "2026-01-20T15:00:00Z",
  "is_refundable": true,
  "next_payment_at": "2026-01-20T15:00:00Z",
  "user": {
    "id": 789,
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane.doe@example.com"
  },
  "academy": {
    "id": 4,
    "name": "Downtown Campus",
    "slug": "downtown-campus"
  },
  "selected_cohort": {
    "id": 12,
    "name": "Full Stack Development - Cohort 45",
    "slug": "full-stack-45"
  },
  "plans": [
    {
      "id": 67,
      "slug": "full-stack-monthly",
      "name": "Full Stack Development - Monthly"
    }
  ],
  "invoices": [],
  "created_at": "2025-01-20T15:00:00Z",
  "updated_at": "2025-01-20T15:00:00Z"
}
```

**Subscription Status Values:**
- `ACTIVE`: Currently active
- `CANCELLED`: Cancelled
- `PAYMENT_ISSUE`: Payment failed
- `EXPIRED`: Expired

#### `planfinancing.planfinancing_created`

Triggered when a new financing plan is created.

```json
{
  "id": 334,
  "status": "ACTIVE",
  "monthly_price": 299.00,
  "plan_expires_at": "2026-01-20T00:00:00Z",
  "valid_until": "2026-01-20T23:59:59Z",
  "next_payment_at": "2025-02-20T00:00:00Z",
  "user": {
    "id": 789,
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane.doe@example.com"
  },
  "academy": {
    "id": 4,
    "name": "Downtown Campus",
    "slug": "downtown-campus"
  },
  "selected_cohort": {
    "id": 12,
    "name": "Full Stack Development - Cohort 45",
    "slug": "full-stack-45"
  },
  "plans": [
    {
      "id": 67,
      "slug": "full-stack-financing",
      "name": "Full Stack Development - 12 Month Financing"
    }
  ],
  "created_at": "2025-01-20T15:00:00Z",
  "updated_at": "2025-01-20T15:00:00Z"
}
```

### Event & Attendance

#### `event.new_event_attendee`

Triggered when someone registers for an event.

```json
{
  "id": 5678,
  "status": "PENDING",
  "attended_at": null,
  "event": {
    "id": 234,
    "title": "Introduction to Python Workshop",
    "slug": "intro-python-workshop-jan-2025",
    "event_type": "workshop",
    "starting_at": "2025-01-25T18:00:00Z",
    "ending_at": "2025-01-25T20:00:00Z",
    "capacity": 50,
    "online_event": false,
    "venue": "Downtown Campus Room 101"
  },
  "attendee": {
    "id": 789,
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane.doe@example.com"
  },
  "created_at": "2025-01-20T12:30:00Z",
  "updated_at": "2025-01-20T12:30:00Z"
}
```

### Mentorship Events

#### `session.mentorship_session_status`

Triggered when a mentorship session status changes.

```json
{
  "id": 889,
  "status": "STARTED",
  "started_at": "2025-01-20T15:00:00Z",
  "ended_at": null,
  "mentor": {
    "id": 456,
    "user": {
      "id": 123,
      "first_name": "Michael",
      "last_name": "Chen",
      "email": "michael.chen@example.com"
    },
    "services": [
      {
        "id": 12,
        "name": "Code Review",
        "slug": "code-review"
      }
    ]
  },
  "mentee": {
    "id": 789,
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane.doe@example.com"
  },
  "service": {
    "id": 12,
    "name": "Code Review",
    "slug": "code-review",
    "duration": 3600
  },
  "bill": null,
  "created_at": "2025-01-20T14:00:00Z",
  "updated_at": "2025-01-20T15:00:00Z"
}
```

**Session Status Values:**
- `PENDING`: Scheduled, not started
- `STARTED`: Currently in progress
- `COMPLETED`: Successfully completed
- `FAILED`: Failed or cancelled
- `IGNORED`: Ignored/no-show

## Webhook Delivery

### How Webhooks Are Sent

1. **Event Trigger**: When a model changes or action occurs, a signal is emitted
2. **Hook Lookup**: System finds all hooks subscribed to that event for the relevant academy
3. **Payload Serialization**: Data is serialized using event-specific serializers
4. **Async Delivery**: Webhook is queued in Celery for asynchronous delivery
5. **HTTP POST**: System sends POST request to your target URL with JSON payload
6. **Tracking**: Response code and timestamp are recorded

### Webhook Requirements

Your webhook endpoint must:

1. **Accept POST requests** with JSON body
2. **Respond with 2xx status code** (200, 201, 204) to confirm receipt
3. **Respond within 30 seconds** (requests will timeout after 30s)
4. **Use HTTPS** (highly recommended for security)

### Webhook Response Handling

**Success Response (2xx):**
- Hook marked as successfully delivered
- `last_call_at` updated to current timestamp
- `last_response_code` set to your response code (e.g., 200)
- `total_calls` incremented

**Failure Response (4xx, 5xx, timeout):**
- Error logged in `HookError` model
- `last_response_code` set to error code
- Hook remains active (no automatic disabling)

### Best Practices for Webhook Endpoints

1. **Acknowledge Quickly**: Respond with 200 OK immediately, then process async
   ```python
   # Good pattern
   @app.route('/webhook/assignment-created', methods=['POST'])
   def handle_assignment_created():
       data = request.json
       # Queue processing job
       process_assignment.delay(data)
       return '', 200  # Respond immediately
   ```

2. **Validate Payload**: Check that required fields exist
   ```python
   required_fields = ['id', 'user', 'cohort']
   if not all(field in data for field in required_fields):
       return {'error': 'Invalid payload'}, 400
   ```

3. **Idempotency**: Handle duplicate deliveries gracefully
   ```python
   # Store processed webhook IDs
   if redis.exists(f'webhook:{data["id"]}'):
       return '', 200  # Already processed
   
   redis.setex(f'webhook:{data["id"]}', 86400, '1')
   # Process webhook...
   ```

4. **Error Handling**: Don't let exceptions crash your endpoint
   ```python
   try:
       process_webhook(data)
       return '', 200
   except Exception as e:
       logger.error(f'Webhook processing failed: {e}')
       return '', 500  # Still return a response
   ```

5. **Logging**: Log all webhook receipts for debugging
   ```python
   logger.info(f'Received webhook: {data.get("id")} - {request.path}')
   ```

## Security Considerations

### Authentication

While webhooks are sent as HTTP POST requests without authentication headers, you should:

1. **Use HTTPS**: Always use HTTPS URLs to prevent man-in-the-middle attacks
2. **Validate Source IP**: Consider IP whitelisting (contact support for BreatheCode IP ranges)
3. **Verify Payload Structure**: Validate that payloads match expected schema
4. **Use Service IDs**: Include unique service_id to identify your webhook sources

### Data Privacy

- Webhooks contain **real user data** (names, emails, etc.)
- Store webhook data securely
- Comply with GDPR/privacy regulations
- Only subscribe to events you actually need

### Rate Limiting

- No hard rate limits on webhook creation
- Be mindful of creating too many duplicate subscriptions
- Use `service_id` to manage different environments (staging, production)

## Testing Webhooks

### Using Sample Data

Before setting up webhooks, review sample data:

```bash
# Get sample data for an event type
curl -X GET \
  'https://api.4geeks.com/v1/notify/hook/sample?event=assignment.assignment_created' \
  -H 'Authorization: Token YOUR_ACADEMY_TOKEN'
```

### Testing Locally

For local development, use tools like:

1. **ngrok**: Expose local server to internet
   ```bash
   ngrok http 3000
   # Use ngrok URL as webhook target
   ```

2. **webhook.site**: Test without writing code
   - Visit https://webhook.site
   - Copy unique URL
   - Use as webhook target to see payloads

3. **RequestBin**: Similar to webhook.site
   - Create temporary endpoint
   - Inspect webhook payloads

### Development vs Production

Use `service_id` to differentiate environments:

```json
// Development
{
  "event": "assignment.assignment_created",
  "target": "https://dev-app.ngrok.io/webhooks/assignment",
  "service_id": "development"
}

// Staging
{
  "event": "assignment.assignment_created",
  "target": "https://staging.your-app.com/webhooks/assignment",
  "service_id": "staging"
}

// Production
{
  "event": "assignment.assignment_created",
  "target": "https://your-app.com/webhooks/assignment",
  "service_id": "production"
}
```

## Common Use Cases

### 1. Real-time Student Dashboard

Subscribe to assignment and cohort events to build live student progress dashboards:

```json
[
  {
    "event": "assignment.assignment_status_updated",
    "target": "https://dashboard.com/webhooks/assignment-update"
  },
  {
    "event": "cohort_user.edu_status_updated",
    "target": "https://dashboard.com/webhooks/student-status"
  }
]
```

### 2. CRM Integration

Sync leads and students to your CRM:

```json
[
  {
    "event": "form_entry.added",
    "target": "https://crm-sync.com/webhooks/new-lead"
  },
  {
    "event": "cohort_user.added",
    "target": "https://crm-sync.com/webhooks/student-enrolled"
  }
]
```

### 3. Payment Notifications

Track subscription and payment events:

```json
[
  {
    "event": "subscription.subscription_created",
    "target": "https://billing.com/webhooks/subscription-created"
  },
  {
    "event": "planfinancing.planfinancing_created",
    "target": "https://billing.com/webhooks/financing-created"
  }
]
```

### 4. Custom Notifications

Build custom notification systems:

```json
[
  {
    "event": "assignment.assignment_revision_status_updated",
    "target": "https://notify.com/webhooks/assignment-reviewed"
  },
  {
    "event": "event.new_event_attendee",
    "target": "https://notify.com/webhooks/event-registration"
  }
]
```

## Troubleshooting

### Hook Not Receiving Events

**Check:**
1. Verify event name is correct (see Available Events)
2. Confirm academy token is valid
3. Check that you're authenticated as the academy
4. Verify the entity has an `academy` relationship
5. Ensure the event actually triggered (check Django logs)

### Webhooks Timing Out

**Solutions:**
1. Respond with 200 OK immediately
2. Process webhook data asynchronously
3. Optimize your endpoint performance
4. Check your server isn't overloaded

### Receiving Duplicate Events

**Solutions:**
1. Implement idempotency using event IDs
2. Use Redis/database to track processed events
3. Check if you have duplicate hook subscriptions

### Wrong Payload Structure

**Solutions:**
1. Use `/hook/sample` endpoint to see expected structure
2. Check for null/optional fields
3. Validate against serializer definitions in code

### Debug Webhook Issues

**Check these:**
1. **Hook exists**: List your hooks with GET `/hook/subscribe`
2. **Last response code**: Check `last_response_code` in hook details
3. **Error logs**: Check `HookError` records (contact support)
4. **Event trigger**: Verify the event is actually firing (check Celery logs)

## Monitoring & Observability

### Hook Statistics

Each hook tracks:
- `total_calls`: Total number of webhook deliveries attempted
- `last_call_at`: Timestamp of most recent delivery
- `last_response_code`: HTTP status code from last delivery

Use this data to monitor webhook health.

### Error Tracking

Webhook errors are logged in the `HookError` model. Each error records:
- Error message
- Event name
- Related hooks
- Timestamp

Contact support for access to error logs.

## Rate Limits & Quotas

- **No hard limits** on number of hooks per academy
- **No rate limits** on webhook delivery
- Be respectful of the system and your own endpoints
- Remove unused hooks to keep things clean

## Support & Resources

### Additional Documentation

- [Django REST Hooks Documentation](http://resthooks.org/)
- [BreatheCode API Documentation](https://4geeks.com/docs)

### Getting Help

- Review webhook error logs in admin panel
- Check Celery task logs for delivery issues
- Contact BreatheCode support with hook ID for debugging

### API Status

- Monitor API status at: https://status.4geeks.com
- Subscribe to incident notifications

## Changelog

### Version 2.0 (Current)
- Academy-scoped webhooks
- Support for 25+ event types
- Sample data endpoints
- Bulk delete by filters
- Service ID support for environment management

## Appendix: Complete Event Reference

| Category | Event Name | Model | Trigger |
|----------|------------|-------|---------|
| **Admissions** | `profile_academy.added` | ProfileAcademy | Created |
| | `profile_academy.changed` | ProfileAcademy | Updated |
| | `cohort_user.added` | CohortUser | Created |
| | `cohort_user.changed` | CohortUser | Updated |
| | `cohort_user.edu_status_updated` | CohortUser | Educational status changed |
| | `cohort.cohort_stage_updated` | Cohort | Stage changed |
| **Assignments** | `assignment.assignment_created` | Task | Created |
| | `assignment.assignment_status_updated` | Task | Task status changed |
| | `assignment.assignment_revision_status_updated` | Task | Revision status changed |
| **Authentication** | `user_invite.invite_status_updated` | UserInvite | Invite status changed |
| **Registry** | `asset.asset_status_updated` | Asset | Asset status changed |
| **Assessment** | `UserAssessment.userassessment_status_updated` | UserAssessment | Status updated |
| **Events** | `event.event_status_updated` | Event | Status changed |
| | `event.event_rescheduled` | Event | Date/time changed |
| | `event.new_event_order` | EventCheckin | Created |
| | `event.new_event_attendee` | EventCheckin | Attendee added |
| **Marketing** | `form_entry.added` | FormEntry | Created |
| | `form_entry.changed` | FormEntry | Updated |
| | `form_entry.won_or_lost` | FormEntry | Deal status changed |
| | `form_entry.new_deal` | FormEntry | New deal created |
| **Payments** | `planfinancing.planfinancing_created` | PlanFinancing | Created |
| | `subscription.subscription_created` | Subscription | Created |
| **Mentorship** | `session.mentorship_session_status` | MentorshipSession | Status changed |

---

**Last Updated:** December 2025  
**API Version:** v1  
**Document Version:** 2.0

