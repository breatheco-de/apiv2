# Event Types and Visibility Settings API Documentation

This document provides comprehensive information about managing Event Types and their Visibility Settings in the BreatheCode platform - how to create, update, and manage event types, and how to configure visibility settings to control which users can see specific event types.

## Overview

**Event Types** are categories or classifications for events (e.g., "Workshop", "Webinar", "Meetup"). Each event type can have multiple **Visibility Settings** that determine which users can see events of that type based on their academy, syllabus, and cohort access.

### Key Concepts

- **Event Type**: A category for events with properties like name, description, icon, and language
- **Visibility Settings**: Rules that determine who can see events of a specific type based on:
  - **Academy** (required) - The academy the setting belongs to
  - **Syllabus** (optional) - Users must have access to this syllabus
  - **Cohort** (optional) - Users must belong to this cohort
- **Shared Creation**: Event types can allow other academies to create events of that type
- **Free for Bootcamps**: Whether users from non-SaaS academies can join without consuming credits

### Model Relationships

```
EventType
  ├── academy (ForeignKey)
  ├── visibility_settings (ManyToMany)
  │   └── EventTypeVisibilitySetting
  │       ├── academy (ForeignKey)
  │       ├── syllabus (ForeignKey, optional)
  │       └── cohort (ForeignKey, optional)
  └── events (reverse relation)
```

---

## Event Types API

### 1. List All Event Types (Public)

**Endpoint:** `GET /v1/events/eventype`

**Purpose:** Get a list of all event types (public endpoint, no authentication required)

**Authentication:** Not required

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `academy` | string | Filter by academy slug |
| `allow_shared_creation` | boolean | Filter by shared creation status (true/false) |
| `lang` | string | Filter by language code (e.g., "en", "es") |

**Response:**

```json
[
  {
    "id": 1,
    "slug": "workshop",
    "name": "Workshop",
    "description": "Hands-on learning sessions",
    "lang": "en",
    "technologies": "Python, JavaScript",
    "academy": {
      "id": 1,
      "slug": "downtown-miami",
      "name": "4Geeks Downtown Miami"
    }
  },
  {
    "id": 2,
    "slug": "webinar",
    "name": "Webinar",
    "description": "Online educational sessions",
    "lang": "en",
    "technologies": null,
    "academy": {
      "id": 1,
      "slug": "downtown-miami",
      "name": "4Geeks Downtown Miami"
    }
  }
]
```

**Example Requests:**

```bash
# Get all event types
GET /v1/events/eventype

# Get event types for a specific academy
GET /v1/events/eventype?academy=downtown-miami

# Get shared event types
GET /v1/events/eventype?allow_shared_creation=true

# Get event types in Spanish
GET /v1/events/eventype?lang=es
```

---

### 2. List Academy Event Types

**Endpoint:** `GET /v1/events/academy/{academy_id}/eventype`

**Purpose:** Get event types for a specific academy, including shared event types

**Authentication:** Required - `read_event_type` capability

**Headers:**

```http
Authorization: Token {your-token}
Academy: {academy_id}
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `academy` | string | Filter by academy slug |
| `allow_shared_creation` | boolean | Filter by shared creation status (true/false) |

**Response:**

Returns a list of event types (same format as public endpoint) that belong to the academy or are shared.

**Example Request:**

```bash
GET /v1/events/academy/1/eventype
Authorization: Token {your-token}
Academy: 1
```

---

### 3. Get Specific Event Type

**Endpoint:** `GET /v1/events/academy/{academy_id}/eventype/{event_type_slug}`

**Purpose:** Get detailed information about a specific event type, including visibility settings

**Authentication:** Required - `read_event_type` capability

**Headers:**

```http
Authorization: Token {your-token}
Academy: {academy_id}
```

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `academy_id` | integer | ✅ Yes | The academy ID |
| `event_type_slug` | string | ✅ Yes | The slug of the event type |

**Response:**

```json
{
  "id": 1,
  "slug": "workshop",
  "name": "Workshop",
  "description": "Hands-on learning sessions",
  "icon_url": "https://example.com/workshop-icon.png",
  "lang": "en",
  "technologies": "Python, JavaScript",
  "allow_shared_creation": true,
  "academy": {
    "id": 1,
    "slug": "downtown-miami",
    "name": "4Geeks Downtown Miami"
  },
  "visibility_settings": [
    {
      "id": 1,
      "academy": {
        "id": 1,
        "slug": "downtown-miami",
        "name": "4Geeks Downtown Miami"
      },
      "syllabus": {
        "id": 5,
        "slug": "full-stack",
        "name": "Full Stack Development"
      },
      "cohort": null
    },
    {
      "id": 2,
      "academy": {
        "id": 1,
        "slug": "downtown-miami",
        "name": "4Geeks Downtown Miami"
      },
      "syllabus": null,
      "cohort": {
        "id": 10,
        "slug": "web-dev-ft-2025",
        "name": "Web Development Full Time 2025"
      }
    }
  ]
}
```

**Error Responses:**

#### 404 Not Found

```json
{
  "detail": "event-type-not-found",
  "status_code": 404
}
```

**Example Request:**

```bash
GET /v1/events/academy/1/eventype/workshop
Authorization: Token {your-token}
Academy: 1
```

---

### 4. Create Event Type

**Endpoint:** `POST /v1/events/academy/{academy_id}/eventype`

**Purpose:** Create a new event type for an academy

**Authentication:** Required - `crud_event_type` capability

**Headers:**

```http
Authorization: Token {your-token}
Academy: {academy_id}
Content-Type: application/json
```

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `academy_id` | integer | ✅ Yes | The academy ID |

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | ✅ Yes | Unique slug identifier (max 150 chars) |
| `name` | string | ✅ Yes | Display name (max 150 chars) |
| `description` | string | ✅ Yes | Public description (max 255 chars) |
| `icon_url` | string | No | URL to icon image |
| `lang` | string | ✅ Yes | Language code (e.g., "en", "es") |
| `free_for_bootcamps` | boolean | No | Default: `true` |
| `allow_shared_creation` | boolean | No | Default: `true` |
| `technologies` | string | No | Comma-separated list (max 200 chars) |

**Note:** The `academy` field is automatically set from the `academy_id` in the URL.

**Request Example:**

```json
{
  "slug": "workshop-python",
  "name": "Python Workshop",
  "description": "Learn Python programming fundamentals",
  "icon_url": "https://example.com/python-icon.png",
  "lang": "en",
  "free_for_bootcamps": true,
  "allow_shared_creation": true,
  "technologies": "Python, Django, Flask"
}
```

**Response (201 Created):**

```json
{
  "id": 5,
  "slug": "workshop-python",
  "name": "Python Workshop",
  "description": "Learn Python programming fundamentals",
  "icon_url": "https://example.com/python-icon.png",
  "lang": "en",
  "free_for_bootcamps": true,
  "allow_shared_creation": true,
  "technologies": "Python, Django, Flask",
  "academy": {
    "id": 1,
    "slug": "downtown-miami",
    "name": "4Geeks Downtown Miami"
  }
}
```

**Error Responses:**

#### 400 Bad Request - Validation Error

```json
{
  "slug": ["event type with this slug already exists."],
  "name": ["This field is required."]
}
```

**Example Request:**

```bash
POST /v1/events/academy/1/eventype
Authorization: Token {your-token}
Academy: 1
Content-Type: application/json

{
  "slug": "workshop-python",
  "name": "Python Workshop",
  "description": "Learn Python programming fundamentals",
  "icon_url": "https://example.com/python-icon.png",
  "lang": "en",
  "technologies": "Python, Django, Flask"
}
```

---

### 5. Update Event Type

**Endpoint:** `PUT /v1/events/academy/{academy_id}/eventype/{event_type_slug}`

**Purpose:** Update an existing event type

**Authentication:** Required - `crud_event_type` capability

**Headers:**

```http
Authorization: Token {your-token}
Academy: {academy_id}
Content-Type: application/json
```

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `academy_id` | integer | ✅ Yes | The academy ID |
| `event_type_slug` | string | ✅ Yes | The slug of the event type to update |

**Request Body:**

All fields are optional except `icon_url`:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | No | Unique slug identifier (max 150 chars) |
| `name` | string | No | Display name (max 150 chars) |
| `description` | string | No | Public description (max 255 chars) |
| `icon_url` | string | ✅ Yes | URL to icon image |
| `lang` | string | No | Language code (e.g., "en", "es") |
| `allow_shared_creation` | boolean | No | Whether other academies can create events of this type |
| `technologies` | string | No | Comma-separated list (max 200 chars) |

**Request Example:**

```json
{
  "name": "Advanced Python Workshop",
  "description": "Advanced Python programming concepts",
  "icon_url": "https://example.com/python-advanced-icon.png",
  "allow_shared_creation": false,
  "technologies": "Python, Django, FastAPI, Celery"
}
```

**Response (200 OK):**

Returns the updated event type object.

**Error Responses:**

#### 404 Not Found

```json
{
  "detail": "event-type-not-found",
  "status_code": 404
}
```

#### 400 Bad Request - Validation Error

```json
{
  "icon_url": ["This field is required."]
}
```

**Example Request:**

```bash
PUT /v1/events/academy/1/eventype/workshop-python
Authorization: Token {your-token}
Academy: 1
Content-Type: application/json

{
  "name": "Advanced Python Workshop",
  "description": "Advanced Python programming concepts",
  "icon_url": "https://example.com/python-advanced-icon.png",
  "allow_shared_creation": false
}
```

**Note:** There is no DELETE endpoint for event types in the current implementation.

---

## Visibility Settings API

Visibility settings control which users can see events of a specific type. They are based on academy, syllabus, and/or cohort access.

### 1. List Visibility Settings

**Endpoint:** `GET /v1/events/academy/{academy_id}/eventype/{event_type_slug}/visibilitysetting`

**Purpose:** Get all visibility settings for a specific event type

**Authentication:** Required - `read_event_type` capability

**Headers:**

```http
Authorization: Token {your-token}
Academy: {academy_id}
```

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `academy_id` | integer | ✅ Yes | The academy ID |
| `event_type_slug` | string | ✅ Yes | The slug of the event type |

**Query Parameters:**

Standard pagination and sorting parameters are supported:
- `limit` - Results per page
- `offset` - Skip N results
- `sort` - Sort field (default: `-id`)

**Response:**

```json
[
  {
    "id": 1,
    "academy": {
      "id": 1,
      "slug": "downtown-miami",
      "name": "4Geeks Downtown Miami"
    },
    "syllabus": {
      "id": 5,
      "slug": "full-stack",
      "name": "Full Stack Development"
    },
    "cohort": null
  },
  {
    "id": 2,
    "academy": {
      "id": 1,
      "slug": "downtown-miami",
      "name": "4Geeks Downtown Miami"
    },
    "syllabus": null,
    "cohort": {
      "id": 10,
      "slug": "web-dev-ft-2025",
      "name": "Web Development Full Time 2025"
    }
  }
]
```

**Important Notes:**

- If `allow_shared_creation` is `false` and the event type belongs to a different academy, an empty list is returned
- Only visibility settings for the specified academy are returned

**Error Responses:**

#### 404 Not Found

```json
{
  "detail": "not-found",
  "status_code": 404
}
```

**Example Request:**

```bash
GET /v1/events/academy/1/eventype/workshop/visibilitysetting
Authorization: Token {your-token}
Academy: 1
```

---

### 2. Add Visibility Setting

**Endpoint:** `POST /v1/events/academy/{academy_id}/eventype/{event_type_slug}/visibilitysetting`

**Purpose:** Add a new visibility setting to an event type

**Authentication:** Required - `crud_event_type` capability

**Headers:**

```http
Authorization: Token {your-token}
Academy: {academy_id}
Content-Type: application/json
```

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `academy_id` | integer | ✅ Yes | The academy ID |
| `event_type_slug` | string | ✅ Yes | The slug of the event type |

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `syllabus` | integer | No | Syllabus ID (must belong to the academy or be public) |
| `cohort` | integer | No | Cohort ID (must belong to the academy) |

**Note:** 
- At least one of `syllabus` or `cohort` should be provided (or neither for academy-wide visibility)
- The `academy` is automatically set from the `academy_id` in the URL
- If a visibility setting with the same academy, syllabus, and cohort already exists, it will be reused

**Request Examples:**

Academy-wide visibility (no syllabus or cohort):
```json
{}
```

Syllabus-specific visibility:
```json
{
  "syllabus": 5
}
```

Cohort-specific visibility:
```json
{
  "cohort": 10
}
```

Combined syllabus and cohort:
```json
{
  "syllabus": 5,
  "cohort": 10
}
```

**Response (201 Created or 200 OK):**

Returns `201 Created` if a new visibility setting was created, or `200 OK` if an existing one was reused:

```json
{
  "id": 1,
  "academy": {
    "id": 1,
    "slug": "downtown-miami",
    "name": "4Geeks Downtown Miami"
  },
  "syllabus": {
    "id": 5,
    "slug": "full-stack",
    "name": "Full Stack Development"
  },
  "cohort": null
}
```

**Error Responses:**

#### 404 Not Found - Event Type

```json
{
  "detail": "event-type-not-found",
  "status_code": 404
}
```

#### 404 Not Found - Syllabus

```json
{
  "detail": "syllabus-not-found",
  "status_code": 404
}
```

#### 404 Not Found - Cohort

```json
{
  "detail": "cohort-not-found",
  "status_code": 404
}
```

**Example Request:**

```bash
POST /v1/events/academy/1/eventype/workshop/visibilitysetting
Authorization: Token {your-token}
Academy: 1
Content-Type: application/json

{
  "syllabus": 5,
  "cohort": 10
}
```

---

### 3. Remove Visibility Setting

**Endpoint:** `DELETE /v1/events/academy/{academy_id}/eventype/{event_type_slug}/visibilitysetting/{visibility_setting_id}`

**Purpose:** Remove a visibility setting from an event type

**Authentication:** Required - `crud_event_type` capability

**Headers:**

```http
Authorization: Token {your-token}
Academy: {academy_id}
```

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `academy_id` | integer | ✅ Yes | The academy ID |
| `event_type_slug` | string | ✅ Yes | The slug of the event type |
| `visibility_setting_id` | integer | ✅ Yes | The ID of the visibility setting to remove |

**Request Body:**

No request body required.

**Response (204 No Content):**

Empty response body.

**Behavior:**

- If the visibility setting is used by other event types, it is only removed from the specified event type
- If the visibility setting is only used by this event type, it is deleted completely

**Error Responses:**

#### 404 Not Found - Event Type

```json
{
  "detail": "event-type-not-found",
  "status_code": 404
}
```

#### 404 Not Found - Visibility Setting

```json
{
  "detail": "event-type-visibility-setting-not-found",
  "status_code": 404
}
```

**Example Request:**

```bash
DELETE /v1/events/academy/1/eventype/workshop/visibilitysetting/1
Authorization: Token {your-token}
Academy: 1
```

---

## How Visibility Works

### Visibility Logic

When a user tries to view events of a specific type, the system checks if they have access based on the visibility settings:

1. **Academy Check**: User must belong to or have access to the academy
2. **Syllabus Check**: If a visibility setting specifies a syllabus, the user must have access to that syllabus
3. **Cohort Check**: If a visibility setting specifies a cohort, the user must belong to that cohort

### Examples

**Example 1: Academy-wide visibility**
```json
{
  "academy": 1,
  "syllabus": null,
  "cohort": null
}
```
All users in academy 1 can see events of this type.

**Example 2: Syllabus-specific visibility**
```json
{
  "academy": 1,
  "syllabus": 5,
  "cohort": null
}
```
Only users who have access to syllabus 5 in academy 1 can see events of this type.

**Example 3: Cohort-specific visibility**
```json
{
  "academy": 1,
  "syllabus": null,
  "cohort": 10
}
```
Only users who belong to cohort 10 in academy 1 can see events of this type.

**Example 4: Combined visibility**
```json
{
  "academy": 1,
  "syllabus": 5,
  "cohort": 10
}
```
Only users who have access to syllabus 5 AND belong to cohort 10 in academy 1 can see events of this type.

### Multiple Visibility Settings

An event type can have multiple visibility settings. If a user matches ANY of the visibility settings, they can see events of that type.

**Example:**
- Visibility Setting 1: Academy 1, Syllabus 5, Cohort null
- Visibility Setting 2: Academy 1, Syllabus null, Cohort 10

Users who have access to syllabus 5 OR belong to cohort 10 can see events of this type.

---

## Complete Workflow Example

### Step 1: Create an Event Type

```bash
POST /v1/events/academy/1/eventype
Authorization: Token {your-token}
Academy: 1
Content-Type: application/json

{
  "slug": "workshop-react",
  "name": "React Workshop",
  "description": "Learn React fundamentals",
  "icon_url": "https://example.com/react-icon.png",
  "lang": "en",
  "technologies": "React, JavaScript, JSX"
}
```

**Response:**
```json
{
  "id": 10,
  "slug": "workshop-react",
  "name": "React Workshop",
  ...
}
```

### Step 2: Add Visibility Settings

Add visibility for Full Stack syllabus:
```bash
POST /v1/events/academy/1/eventype/workshop-react/visibilitysetting
Authorization: Token {your-token}
Academy: 1
Content-Type: application/json

{
  "syllabus": 5
}
```

Add visibility for specific cohort:
```bash
POST /v1/events/academy/1/eventype/workshop-react/visibilitysetting
Authorization: Token {your-token}
Academy: 1
Content-Type: application/json

{
  "cohort": 10
}
```

### Step 3: Verify Visibility Settings

```bash
GET /v1/events/academy/1/eventype/workshop-react/visibilitysetting
Authorization: Token {your-token}
Academy: 1
```

### Step 4: Update Event Type (if needed)

```bash
PUT /v1/events/academy/1/eventype/workshop-react
Authorization: Token {your-token}
Academy: 1
Content-Type: application/json

{
  "name": "Advanced React Workshop",
  "icon_url": "https://example.com/react-advanced-icon.png",
  "allow_shared_creation": false
}
```

### Step 5: Remove a Visibility Setting (if needed)

```bash
DELETE /v1/events/academy/1/eventype/workshop-react/visibilitysetting/1
Authorization: Token {your-token}
Academy: 1
```

---

## Important Notes

### Event Type Constraints

1. **Slug Uniqueness**: The `slug` field must be unique across all event types
2. **No Delete Endpoint**: There is currently no DELETE endpoint for event types
3. **Academy Auto-Assignment**: The `academy` field is automatically set from the URL `academy_id`
4. **Visibility Settings Exclusion**: Visibility settings cannot be set directly in the event type create/update endpoints - they must be managed separately

### Visibility Settings Constraints

1. **Academy Required**: Every visibility setting must have an academy (automatically set)
2. **Syllabus Validation**: Syllabus must belong to the academy or be public
3. **Cohort Validation**: Cohort must belong to the academy
4. **Reuse Logic**: If a visibility setting with the same academy, syllabus, and cohort exists, it will be reused rather than creating a duplicate
5. **Shared Creation**: If `allow_shared_creation` is `false`, only the owning academy can see and manage visibility settings

### Best Practices

1. **Use Descriptive Slugs**: Use clear, descriptive slugs for event types (e.g., `workshop-python-basics` instead of `wp1`)
2. **Set Appropriate Icons**: Always provide an `icon_url` for better UI presentation
3. **Language Consistency**: Use consistent language codes across related event types
4. **Visibility Granularity**: Start with broader visibility (academy-wide) and add more specific settings as needed
5. **Shared vs Private**: Use `allow_shared_creation` to control whether other academies can create events of this type
6. **Technology Tags**: Use comma-separated technology tags to help with filtering and search

---

## Error Reference

### Common Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `event-type-not-found` | 404 | Event type does not exist or doesn't belong to the academy |
| `syllabus-not-found` | 404 | Syllabus does not exist or is not accessible |
| `cohort-not-found` | 404 | Cohort does not exist or doesn't belong to the academy |
| `event-type-visibility-setting-not-found` | 404 | Visibility setting does not exist |
| `not-found` | 404 | Generic not found error |

### Permission Errors

If you receive a `403 Forbidden` response, ensure:
- You have the `read_event_type` capability for GET requests
- You have the `crud_event_type` capability for POST, PUT, and DELETE requests
- The `Academy` header matches the academy you're trying to access

---

## Related Documentation

- [Event Suspension API](./EVENT_SUSPENSION.md) - How to suspend events
- [Live Classes API](./LIVE_CLASSES.md) - Information about live classes
- [Cohorts API](./COHORTS.md) - Managing cohorts
- [Syllabus API](./SYLLABUS.md) - Managing syllabi

