# Student Activity API Documentation

Complete guide to the Student Activity API endpoints, including activity tracking, querying, and reporting capabilities.

## Overview

The Student Activity API provides comprehensive activity tracking and monitoring capabilities for students, supporting:
- ✅ Activity creation and logging
- ✅ Activity querying with advanced filtering
- ✅ Cohort-based activity tracking
- ✅ Classroom activity management
- ✅ Activity reporting and analytics
- ✅ BigQuery-based activity storage (V2)

**Base Endpoints:**
- V1: `/v1/activity/`
- V2: `/v2/activity/`

---

## Authentication & Headers

All requests require:

```http
Authorization: Token {your-token}
```

For academy-scoped endpoints, also include:

```http
Academy: {academy_id}
```

---

## Activity Types

The system supports the following activity types (slugs):

| Slug | Description |
|------|-------------|
| `breathecode_login` | Every time a user logs in |
| `online_platform_registration` | First day using breathecode |
| `public_event_attendance` | Attendance on an eventbrite event |
| `classroom_attendance` | When the student attends class |
| `classroom_unattendance` | When the student misses class |
| `lesson_opened` | When a lesson is opened on the platform |
| `office_attendance` | When the office raspberry pi detects the student |
| `nps_survey_answered` | When an NPS survey is answered by the student |
| `exercise_success` | When student successfully tests exercise |
| `registration` | When student successfully joins breathecode |
| `educational_status_change` | Student cohort changes like: starts, drop, postpone, etc |
| `educational_note` | Notes that can be added by teachers, TA's or anyone involved in the student education |
| `career_note` | Notes related to the student career |

**Public Activities** (not tied to a specific academy):
- `breathecode_login`
- `online_platform_registration`

---

## V1 Endpoints

### GET - List Activity Types

**Endpoint:** `GET /v1/activity/type/`

**Permissions:** `read_activity`

**Description:** Get all available activity types

**Response:**
```json
[
  {
    "slug": "breathecode_login",
    "description": "Every time it logs in"
  },
  {
    "slug": "online_platform_registration",
    "description": "First day using breathecode"
  }
]
```

### GET - Get Single Activity Type

**Endpoint:** `GET /v1/activity/type/{activity_slug}`

**Parameters:**
- `activity_slug` - The slug of the activity type

**Permissions:** `read_activity`

**Example:**
```bash
GET /v1/activity/type/breathecode_login
```

**Response:**
```json
{
  "slug": "breathecode_login",
  "description": "Every time it logs in"
}
```

---

### GET - Get My Activities

**Endpoint:** `GET /v1/activity/me`

**Permissions:** `read_activity`

**Query Parameters:**
- `slug={activity_slug}` - Filter by activity type slug
- `cohort={cohort_slug}` - Filter by cohort slug
- `user_id={user_id}` - Filter by user ID (integer)
- `email={email}` - Filter by user email

**Description:** Get activities for the authenticated user. Returns activities from both academy-specific and public (academy_id=0) sources.

**Example:**
```bash
GET /v1/activity/me?slug=classroom_attendance&cohort=web-dev-pt-01
```

**Response:**
```json
[
  {
    "slug": "classroom_attendance",
    "user_id": 123,
    "email": "student@example.com",
    "cohort": "web-dev-pt-01",
    "data": {
      "attendance_type": "present"
    },
    "created_at": "2024-01-15T10:30:00Z",
    "academy_id": 1
  }
]
```

### POST - Create Activity

**Endpoint:** `POST /v1/activity/me`

**Permissions:** `crud_activity`

**Description:** Create a new activity for the authenticated user

**Request Body:**
```json
{
  "slug": "classroom_attendance",
  "user_agent": "Mozilla/5.0...",
  "cohort": "web-dev-pt-01",
  "data": "{\"attendance_type\": \"present\"}"
}
```

**Required Fields:**
- `slug` - Activity type slug
- `user_agent` - User agent string

**Optional Fields:**
- `cohort` - Cohort slug (required for most activity types except public ones)
- `data` - JSON string with additional activity data (required for most activity types)
- `day` - Day number

**Response:**
```json
{
  "slug": "classroom_attendance",
  "user_id": 123,
  "email": "student@example.com",
  "cohort": "web-dev-pt-01",
  "data": {
    "attendance_type": "present"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "academy_id": 1
}
```

---

### GET - Get Cohort Activities

**Endpoint:** `GET /v1/activity/cohort/{cohort_id}`

**Parameters:**
- `cohort_id` - Cohort ID or slug

**Permissions:** `read_activity`

**Query Parameters:**
- `slug={activity_slug}` - Filter by activity type slug (comma-separated for multiple)
- `limit={number}` - Limit results
- `offset={number}` - Offset for pagination

**Description:** Get all activities for a specific cohort

**Example:**
```bash
GET /v1/activity/cohort/web-dev-pt-01?slug=classroom_attendance,classroom_unattendance&limit=50
```

**Response:** Array of activity objects (paginated if limit/offset provided)

---

### GET - Get Classroom Activities

**Endpoint:** `GET /v1/activity/academy/cohort/{cohort_id}`

**Parameters:**
- `cohort_id` - Cohort ID or slug

**Permissions:** `classroom_activity`

**Query Parameters:**
- `slug={activity_slug}` - Filter by activity type slug
- `user_id={user_id}` - Filter by user ID
- `email={email}` - Filter by user email
- `limit={number}` - Limit results
- `offset={number}` - Offset for pagination

**Description:** Get activities for a specific cohort (for teachers/assistants)

**Example:**
```bash
GET /v1/activity/academy/cohort/web-dev-pt-01?slug=classroom_attendance
```

**Response:** Array of activity objects (paginated)

### POST - Create Classroom Activities (Bulk)

**Endpoint:** `POST /v1/activity/academy/cohort/{cohort_id}`

**Parameters:**
- `cohort_id` - Cohort ID or slug

**Permissions:** `classroom_activity`

**Description:** Create activities for multiple students in a cohort. Only teachers or assistants from the cohort can use this endpoint.

**Request Body (Single Activity):**
```json
{
  "user_id": 123,
  "slug": "classroom_attendance",
  "user_agent": "Mozilla/5.0...",
  "data": "{\"attendance_type\": \"present\"}"
}
```

**Request Body (Multiple Activities):**
```json
[
  {
    "user_id": 123,
    "slug": "classroom_attendance",
    "user_agent": "Mozilla/5.0...",
    "data": "{\"attendance_type\": \"present\"}"
  },
  {
    "user_id": 456,
    "slug": "classroom_unattendance",
    "user_agent": "Mozilla/5.0...",
    "data": "{\"reason\": \"sick\"}"
  }
]
```

**Response:** Array of created activity objects

---

### GET - Get Student Activities

**Endpoint:** `GET /v1/activity/academy/student/{student_id}`

**Parameters:**
- `student_id` - Student user ID

**Permissions:** `read_activity`

**Query Parameters:**
- `slug={activity_slug}` - Filter by activity type slug
- `email={email}` - Filter by user email (alternative to student_id)
- `limit={number}` - Limit results
- `offset={number}` - Offset for pagination

**Description:** Get all activities for a specific student within the academy

**Example:**
```bash
GET /v1/activity/academy/student/123?slug=lesson_opened&limit=100
```

**Response:** Array of activity objects (paginated)

### POST - Create Student Activities (Bulk)

**Endpoint:** `POST /v1/activity/academy/student/{student_id}`

**Parameters:**
- `student_id` - Student user ID (can be omitted if provided in body)

**Permissions:** `crud_activity`

**Description:** Create activities for one or more students. Each activity must include a cohort slug.

**Request Body (Single Activity):**
```json
{
  "user_id": 123,
  "slug": "lesson_opened",
  "user_agent": "Mozilla/5.0...",
  "cohort": "web-dev-pt-01",
  "data": "{\"lesson_slug\": \"javascript-basics\"}"
}
```

**Request Body (Multiple Activities):**
```json
[
  {
    "user_id": 123,
    "slug": "lesson_opened",
    "user_agent": "Mozilla/5.0...",
    "cohort": "web-dev-pt-01",
    "data": "{\"lesson_slug\": \"javascript-basics\"}"
  },
  {
    "user_id": 456,
    "slug": "exercise_success",
    "user_agent": "Mozilla/5.0...",
    "cohort": "web-dev-pt-01",
    "data": "{\"exercise_slug\": \"hello-world\"}"
  }
]
```

**Important Notes:**
- Each activity must include a `cohort` field (slug, not numeric ID)
- The `user_id` in the body must match a student in the specified cohort
- The cohort slug must exist in the academy

**Response:** Array of created activity objects

---

## V2 Endpoints (BigQuery-based)

V2 endpoints use BigQuery for storage and provide more advanced querying capabilities.

### GET - Get My Activities (V2)

**Endpoint:** `GET /v2/activity/me/activity`

**Permissions:** None (uses authenticated user)

**Query Parameters:**
- `kind={activity_kind}` - Filter by activity kind
- `cohort={cohort_slug_or_id}` - Filter by cohort (slug or ID)
- `limit={number}` - Limit results (default: 100)
- `page={number}` - Page number (default: 1)

**Description:** Get activities for the authenticated user from BigQuery

**Example:**
```bash
GET /v2/activity/me/activity?kind=login&cohort=web-dev-pt-01&limit=50&page=1
```

**Response:**
```json
[
  {
    "id": "activity-123",
    "user_id": 123,
    "kind": "login",
    "related": {
      "type": "auth.User",
      "id": 123,
      "slug": null
    },
    "meta": {
      "email": "student@example.com",
      "username": "student",
      "cohort": "web-dev-pt-01"
    },
    "timestamp": "2024-01-15T10:30:00Z"
  }
]
```

### GET - Get Single Activity (V2)

**Endpoint:** `GET /v2/activity/me/activity/{activity_id}`

**Parameters:**
- `activity_id` - Activity ID

**Permissions:** None (uses authenticated user)

**Description:** Get a specific activity by ID for the authenticated user

**Example:**
```bash
GET /v2/activity/me/activity/activity-123
```

**Response:**
```json
{
  "id": "activity-123",
  "user_id": 123,
  "kind": "login",
  "related": {
    "type": "auth.User",
    "id": 123,
    "slug": null
  },
  "meta": {
    "email": "student@example.com",
    "username": "student"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### GET - Get Academy Activities (V2)

**Endpoint:** `GET /v2/activity/academy/activity`

**Permissions:** `read_activity`

**Query Parameters:**
- `user_id={user_id}` - Filter by user ID (defaults to authenticated user if not provided)
- `kind={activity_kind}` - Filter by activity kind
- `cohort_id={cohort_id_or_slug}` - Filter by cohort (ID or slug)
- `date_start={timestamp}` - Filter by start date (ISO timestamp)
- `date_end={timestamp}` - Filter by end date (ISO timestamp)
- `limit={number}` - Limit results (default: 100)
- `page={number}` - Page number (default: 1)

**Description:** Get activities for a specific user within an academy from BigQuery

**Example:**
```bash
GET /v2/activity/academy/activity?user_id=123&kind=login&date_start=2024-01-01T00:00:00Z&date_end=2024-01-31T23:59:59Z
```

**Response:** Array of activity objects

### GET - Get Single Academy Activity (V2)

**Endpoint:** `GET /v2/activity/academy/activity/{activity_id}`

**Parameters:**
- `activity_id` - Activity ID

**Permissions:** `read_activity`

**Query Parameters:**
- `user_id={user_id}` - Filter by user ID (defaults to authenticated user)

**Description:** Get a specific activity by ID within an academy

**Example:**
```bash
GET /v2/activity/academy/activity/activity-123?user_id=123
```

**Response:** Single activity object

---

### GET - Activity Report (V2)

**Endpoint:** `GET /v2/activity/report`

**Permissions:** `read_activity`

**Description:** Advanced reporting endpoint with aggregation capabilities

**Query Parameters:**
- `query={json_string}` - JSON query object with filters and grouping functions
- `fields={comma_separated}` - Fields to select
- `by={comma_separated}` - Fields to group by
- `order={comma_separated}` - Fields to order by
- `limit={number}` - Limit results

**Query Object Structure:**
```json
{
  "filter": {
    "user_id": 123,
    "kind": "login",
    "meta.academy": 1
  },
  "grouping_function": {
    "count": ["kind"],
    "sum": ["some_numeric_field"],
    "avg": ["some_numeric_field"]
  }
}
```

**Example - Count activities by kind:**
```bash
GET /v2/activity/report?by=kind&fields=kind&query={"filter":{"meta.academy":1}}
```

**Example - Aggregated report:**
```bash
GET /v2/activity/report?query={"filter":{"meta.academy":1},"grouping_function":{"count":["kind"],"sum":["points"]}}
```

**Response:** Array of report results (structure depends on query)

---

## How the `/v2/activity/report` Endpoint Works

The report endpoint is a powerful BigQuery-based analytics tool that allows you to build complex SQL queries through a simple API interface. Here's a detailed breakdown:

### Endpoint Processing Flow

1. **Query Parameter Parsing**: The `query` parameter is URL-encoded JSON that gets parsed
2. **BigQuery Builder**: Creates a BigQuery query builder instance for the `activity` table
3. **Field Selection**: Uses `fields` parameter to select specific columns
4. **Grouping**: Uses `by` parameter to group results
5. **Filtering**: Applies filters from the `query.filter` object
6. **Aggregation**: Applies aggregation functions (count, sum, avg) from `query.grouping_function`
7. **SQL Generation**: Builds and executes a BigQuery SQL query
8. **Result Formatting**: Returns results as an array of dictionaries

### Example Breakdown

Let's analyze your example URL:

```
/v2/activity/report?query={"filter":{"user_id":19487,"meta.cohort":1521},"grouping_function":{"count":["kind"],"avg":["meta.score"]}}&by=kind&fields=kind
```

**URL Decoded Query Parameter:**
```json
{
  "filter": {
    "user_id": 19487,
    "meta.cohort": 1521
  },
  "grouping_function": {
    "count": ["kind"],
    "avg": ["meta.score"]
  }
}
```

**Additional Parameters:**
- `by=kind` - Group results by the `kind` field
- `fields=kind` - Select only the `kind` field (plus aggregated fields)

### Generated SQL Query

The endpoint generates this BigQuery SQL:

```sql
SELECT 
  kind,
  COUNT(kind) AS count__kind,
  AVG(meta.score) AS avg__meta__score
FROM `{project_id}.{dataset}.activity`
WHERE 
  user_id = @x__user_id AND 
  meta.cohort = @x__meta__cohort
GROUP BY kind
ORDER BY kind DESC
```

**Query Parameters:**
- `@x__user_id` = 19487 (INT64)
- `@x__meta__cohort` = 1521 (INT64)

### Response Structure

The response will be an array of objects, one per `kind` value:

```json
[
  {
    "kind": "login",
    "count__kind": 45,
    "avg__meta__score": 85.5
  },
  {
    "kind": "lesson_opened",
    "count__kind": 120,
    "avg__meta__score": 92.3
  },
  {
    "kind": "exercise_success",
    "count__kind": 78,
    "avg__meta__score": 88.7
  }
]
```

### Parameter Reference

#### Query Object (`query` parameter)

**Filter Object:**
```json
{
  "filter": {
    "user_id": 19487,              // Exact match
    "meta.cohort": 1521,           // Nested field access with dot notation
    "kind": "login",               // String match
    "timestamp.gte": "2024-01-01" // Greater than or equal (use .gte, .gt, .lte, .lt)
  }
}
```

**Filter Operators:**
- `.gte` - Greater than or equal (`>=`)
- `.gt` - Greater than (`>`)
- `.lte` - Less than or equal (`<=`)
- `.lt` - Less than (`<`)
- `.like` - LIKE pattern matching
- No suffix - Exact match (`=`)

**Grouping Functions:**
```json
{
  "grouping_function": {
    "count": ["kind", "user_id"],      // Count occurrences
    "sum": ["meta.points", "meta.score"], // Sum numeric values
    "avg": ["meta.score", "meta.time"]    // Average numeric values
  }
}
```

#### URL Query Parameters

- **`fields`**: Comma-separated list of fields to select
  - Example: `fields=kind,user_id`
  - If not provided, all fields are selected (plus aggregated fields)

- **`by`**: Comma-separated list of fields to group by
  - Example: `by=kind,user_id`
  - Required when using aggregation functions

- **`order`**: Comma-separated list of fields to order by
  - Example: `order=kind,timestamp`
  - Default: DESC order

- **`limit`**: Maximum number of results
  - Example: `limit=100`

### Common Use Cases

#### 1. Count Activities by Kind

**Query:**
```bash
GET /v2/activity/report?by=kind&fields=kind&query={"filter":{"meta.academy":1},"grouping_function":{"count":["kind"]}}
```

**SQL Generated:**
```sql
SELECT kind, COUNT(kind) AS count__kind
FROM `activity`
WHERE meta.academy = @x__meta__academy
GROUP BY kind
```

#### 2. Average Score by User

**Query:**
```bash
GET /v2/activity/report?by=user_id&fields=user_id&query={"filter":{"kind":"exercise_success"},"grouping_function":{"avg":["meta.score"]}}
```

**SQL Generated:**
```sql
SELECT user_id, AVG(meta.score) AS avg__meta__score
FROM `activity`
WHERE kind = @x__kind
GROUP BY user_id
```

#### 3. Multiple Aggregations

**Query:**
```bash
GET /v2/activity/report?by=kind&fields=kind&query={"filter":{"meta.academy":1},"grouping_function":{"count":["kind"],"sum":["meta.points"],"avg":["meta.score"]}}
```

**SQL Generated:**
```sql
SELECT 
  kind,
  COUNT(kind) AS count__kind,
  SUM(meta.points) AS sum__meta__points,
  AVG(meta.score) AS avg__meta__score
FROM `activity`
WHERE meta.academy = @x__meta__academy
GROUP BY kind
```

#### 4. Date Range Filtering

**Query:**
```bash
GET /v2/activity/report?query={"filter":{"timestamp.gte":"2024-01-01","timestamp.lte":"2024-01-31","meta.academy":1},"grouping_function":{"count":["kind"]}}&by=kind
```

**SQL Generated:**
```sql
SELECT kind, COUNT(kind) AS count__kind
FROM `activity`
WHERE 
  timestamp >= @x__timestamp AND
  timestamp <= @x__timestamp_2 AND
  meta.academy = @x__meta__academy
GROUP BY kind
```

### Important Notes

1. **Field Naming**: Aggregated fields use the format `{operation}__{field}` where dots are replaced with double underscores
   - `COUNT(kind)` → `count__kind`
   - `AVG(meta.score)` → `avg__meta__score`

2. **Nested Fields**: Use dot notation for nested fields in `meta` object
   - `meta.cohort` - Access cohort field
   - `meta.score` - Access score field

3. **Grouping Requirement**: When using aggregation functions, you must include the grouped fields in the `by` parameter

4. **Field Selection**: If you specify `fields`, only those fields plus aggregated fields are returned. If omitted, all fields plus aggregated fields are returned.

5. **Type Safety**: BigQuery automatically infers parameter types (INT64, STRING, FLOAT64, etc.) from the filter values

6. **Performance**: This endpoint queries BigQuery directly, so it's optimized for large datasets and analytics workloads

---

## Activity Payload Structure

### V1 Activity Payload

**Required Fields:**
```json
{
  "slug": "classroom_attendance",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
```

**Optional Fields:**
```json
{
  "slug": "lesson_opened",
  "user_agent": "Mozilla/5.0...",
  "cohort": "web-dev-pt-01",           // Required for most activity types
  "data": "{\"lesson_slug\": \"js-101\"}",  // JSON string, required for most activity types
  "day": 5                              // Day number
}
```

**Note:** The `data` field must be a valid JSON string, not a JSON object.

### V2 Activity Response Structure

```json
{
  "id": "activity-123",
  "user_id": 123,
  "kind": "login",
  "related": {
    "type": "auth.User",
    "id": 123,
    "slug": null
  },
  "meta": {
    "email": "student@example.com",
    "username": "student",
    "cohort": "web-dev-pt-01",
    "academy": 1
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## Important Flows and Use Cases

### 1. Student Login Tracking

**Use Case:** Track when a student logs into the platform

**Endpoint:** `POST /v1/activity/me`

**Payload:**
```json
{
  "slug": "breathecode_login",
  "user_agent": "Mozilla/5.0..."
}
```

**Note:** This is a public activity (no cohort required, academy_id=0)

---

### 2. Classroom Attendance Tracking

**Use Case:** Teacher marks attendance for multiple students

**Endpoint:** `POST /v1/activity/academy/cohort/{cohort_id}`

**Payload:**
```json
[
  {
    "user_id": 123,
    "slug": "classroom_attendance",
    "user_agent": "Mozilla/5.0...",
    "data": "{\"attendance_type\": \"present\", \"session_id\": \"session-123\"}"
  },
  {
    "user_id": 456,
    "slug": "classroom_unattendance",
    "user_agent": "Mozilla/5.0...",
    "data": "{\"reason\": \"sick\", \"session_id\": \"session-123\"}"
  }
]
```

**Requirements:**
- User must be a TEACHER or ASSISTANT in the cohort
- Each student must exist in the cohort

---

### 3. Lesson Progress Tracking

**Use Case:** Track when a student opens a lesson

**Endpoint:** `POST /v1/activity/me`

**Payload:**
```json
{
  "slug": "lesson_opened",
  "user_agent": "Mozilla/5.0...",
  "cohort": "web-dev-pt-01",
  "data": "{\"lesson_slug\": \"javascript-basics\", \"module_slug\": \"js-101\"}"
}
```

---

### 4. Exercise Completion Tracking

**Use Case:** Track when a student successfully completes an exercise

**Endpoint:** `POST /v1/activity/me`

**Payload:**
```json
{
  "slug": "exercise_success",
  "user_agent": "Mozilla/5.0...",
  "cohort": "web-dev-pt-01",
  "data": "{\"exercise_slug\": \"hello-world\", \"attempts\": 3, \"time_spent\": 1200}"
}
```

---

### 5. Educational Notes

**Use Case:** Add educational notes about a student

**Endpoint:** `POST /v1/activity/academy/student/{student_id}`

**Payload:**
```json
{
  "user_id": 123,
  "slug": "educational_note",
  "user_agent": "Mozilla/5.0...",
  "cohort": "web-dev-pt-01",
  "data": "{\"note\": \"Student showing great progress\", \"author_id\": 456, \"visibility\": \"private\"}"
}
```

---

### 6. Query Student Activities

**Use Case:** Get all activities for a student in a specific cohort

**Endpoint:** `GET /v1/activity/academy/student/{student_id}`

**Query:**
```bash
GET /v1/activity/academy/student/123?slug=lesson_opened,exercise_success&limit=100
```

---

### 7. Cohort Activity Analysis

**Use Case:** Get all attendance activities for a cohort

**Endpoint:** `GET /v1/activity/academy/cohort/{cohort_id}`

**Query:**
```bash
GET /v1/activity/academy/cohort/web-dev-pt-01?slug=classroom_attendance,classroom_unattendance
```

---

### 8. Advanced Reporting (V2)

**Use Case:** Generate activity statistics by kind

**Endpoint:** `GET /v2/activity/report`

**Query:**
```bash
GET /v2/activity/report?by=kind&fields=kind&query={"filter":{"meta.academy":1},"grouping_function":{"count":["kind"]}}
```

**Response:**
```json
[
  {
    "kind": "login",
    "kind__count": 150
  },
  {
    "kind": "lesson_opened",
    "kind__count": 320
  }
]
```

---

### 9. Date Range Activity Query (V2)

**Use Case:** Get activities for a user within a date range

**Endpoint:** `GET /v2/activity/academy/activity`

**Query:**
```bash
GET /v2/activity/academy/activity?user_id=123&date_start=2024-01-01T00:00:00Z&date_end=2024-01-31T23:59:59Z&kind=lesson_opened
```

---

## Field Validation Rules

### Activity Type Requirements

**Activities that DON'T require `cohort`:**
- `breathecode_login`
- `online_platform_registration`

**Activities that DON'T require `data`:**
- `breathecode_login`
- `online_platform_registration`

**All other activities require both `cohort` and `data` fields.**

### Data Field Validation

- The `data` field must be a valid JSON string
- If `data` is provided, it must be parseable JSON
- Empty or null `data` is allowed only for public activities

### Cohort Validation

- Cohort can be provided as a slug or numeric ID
- For POST requests in student endpoints, cohort must be a slug (not numeric ID)
- Cohort must exist in the specified academy

---

## Error Responses

### Common Error Codes

| Error Slug | Description | Status Code |
|------------|-------------|-------------|
| `activity-not-found` | Activity type not found | 400 |
| `cohort-not-found` | Cohort not found | 400 |
| `cohort-not-exists` | Cohort doesn't exist in academy | 400 |
| `user-not-exists` | User not found | 400 |
| `bad-user-id` | user_id is not an integer | 400 |
| `missing-cohort` | Activity requires a cohort | 400 |
| `missing-data` | Activity requires a data field | 400 |
| `data-is-not-a-json` | Data field is not valid JSON | 400 |
| `not-found-in-cohort` | Student not found in cohort | 400 |
| `student-no-cohort` | Student doesn't belong to any cohort in academy | 400 |

### Example Error Response

```json
{
  "detail": "Cohort not found",
  "status_code": 400,
  "slug": "cohort-not-found"
}
```

---

## Best Practices

1. **Always include user_agent**: Required for all activity creation
2. **Validate data JSON**: Ensure `data` field is valid JSON string before sending
3. **Use appropriate activity types**: Choose the correct slug for the activity
4. **Bulk operations**: Use bulk endpoints when creating multiple activities
5. **Pagination**: Always use limit/offset for large result sets
6. **V2 for analytics**: Use V2 endpoints for advanced reporting and analytics
7. **Cohort validation**: Verify cohort exists before creating cohort-specific activities
8. **Error handling**: Check for specific error slugs to handle validation errors appropriately

---

## Migration Notes

- V1 endpoints use Google Cloud Datastore (NDB)
- V2 endpoints use Google Cloud BigQuery
- V2 provides better querying capabilities and analytics
- Some V1 endpoints are deprecated (see deprecation_list in v2 URLs)
- V2 endpoints are recommended for new implementations

