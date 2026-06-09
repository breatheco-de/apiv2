# Cohort Creation - Complete Guide

This guide covers the entire flow to create a cohort, including all dependencies and prerequisites.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Step-by-Step Flow](#step-by-step-flow)
3. [API Endpoints Reference](#api-endpoints-reference)
4. [Complete Examples](#complete-examples)
5. [Troubleshooting](#troubleshooting)

---

## 🎯 Prerequisites

Before creating a cohort, you need to have the following dependencies in place:

### 1. **Academy** (Required)
- An academy must exist to create cohorts
- Academy provides the context and ownership for cohorts

### 2. **Syllabus** (Required)
- A syllabus defines the curriculum content
- Must have at least one published version

### 3. **Syllabus Version** (Required)
- Each syllabus needs a published version (version 2 or higher)
- Version 1 is only for marketing purposes

### 4. **Syllabus Schedule** (Optional)
- Defines when classes are held
- Can be created after cohort creation

---

## 🚀 Step-by-Step Flow

### Step 1: Create or Verify Academy

**Endpoint:** `POST /v1/admissions/academy`

**Required Fields:**
- `slug` - Unique academy identifier
- `name` - Academy display name
- `logo_url` - Academy logo URL
- `street_address` - Physical address
- `city` - City ID (from catalog)
- `country` - Country code

**Example:**
```bash
curl -X POST "https://your-api.com/v1/admissions/academy" \
  -H "Authorization: Token your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "miami-academy",
    "name": "Miami Academy",
    "logo_url": "https://example.com/logo.png",
    "street_address": "123 Main St",
    "city": 1,
    "country": "us",
    "timezone": "America/New_York"
  }'
```

**Response:**
```json
{
  "id": 1,
  "slug": "miami-academy",
  "name": "Miami Academy",
  "owner": {
    "id": 123,
    "email": "admin@miami-academy.com"
  },
  "timezone": "America/New_York",
  "status": "ACTIVE"
}
```

### Step 2: Create Syllabus

**Endpoint:** `POST /v1/admissions/syllabus`

**Required Fields:**
- `slug` - Unique syllabus identifier
- `name` - Syllabus display name

**Example:**
```bash
curl -X POST "https://your-api.com/v1/admissions/syllabus" \
  -H "Authorization: Token your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "full-stack-web-development",
    "name": "Full Stack Web Development",
    "main_technologies": "HTML, CSS, JavaScript, React, Node.js",
    "duration_in_hours": 400,
    "duration_in_days": 16,
    "week_hours": 25,
    "logo": "https://example.com/syllabus-logo.png",
    "academy_owner": 1
  }'
```

**Response:**
```json
{
  "id": 1,
  "slug": "full-stack-web-development",
  "name": "Full Stack Web Development",
  "main_technologies": "HTML, CSS, JavaScript, React, Node.js",
  "duration_in_hours": 400,
  "academy_owner": 1
}
```

**Note:** A signal automatically creates version 1 when a syllabus is created.

### Step 3: Create Syllabus Version

**Endpoint:** `POST /v1/admissions/syllabus/{syllabus_id}/version`

**Required Fields:**
- `json` - Syllabus content in JSON format
- `status` - Must be "PUBLISHED" for cohorts

**Example:**
```bash
curl -X POST "https://your-api.com/v1/admissions/syllabus/1/version" \
  -H "Authorization: Token your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "json": {
      "days": [
        {
          "id": 1,
          "name": "Introduction to Web Development",
          "lessons": [
            {
              "id": 1,
              "name": "HTML Basics",
              "duration": 120
            }
          ]
        }
      ]
    },
    "status": "PUBLISHED",
    "change_log_details": "Initial version with basic web development curriculum"
  }'
```

**Response:**
```json
{
  "id": 1,
  "version": 2,
  "syllabus": 1,
  "status": "PUBLISHED",
  "change_log_details": "Initial version with basic web development curriculum"
}
```

### Step 4: Create Syllabus Schedule (Optional)

**Endpoint:** `POST /v1/admissions/academy/schedule`

**Required Fields:**
- `name` - Schedule name
- `schedule_type` - "FULL-TIME" or "PART-TIME"
- `description` - Schedule description
- `syllabus` - Syllabus ID
- `academy` - Academy ID

**Example:**
```bash
curl -X POST "https://your-api.com/v1/admissions/academy/schedule" \
  -H "Authorization: Token your_token_here" \
  -H "Academy: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Full-Time Morning Schedule",
    "schedule_type": "FULL-TIME",
    "description": "Monday to Friday, 9 AM to 5 PM",
    "syllabus": 1,
    "academy": 1
  }'
```

**Response:**
```json
{
  "id": 1,
  "name": "Full-Time Morning Schedule",
  "schedule_type": "FULL-TIME",
  "description": "Monday to Friday, 9 AM to 5 PM",
  "syllabus": 1,
  "academy": 1
}
```

### Step 5: Create Cohort

**Endpoint:** `POST /v1/admissions/academy/cohort`

**Required Fields:**
- `name` - Cohort display name
- `slug` - Unique cohort identifier
- `syllabus` - Format: "syllabus_slug.vversion_number" or "syllabus_slug.vlatest"
- `kickoff_date` - Start date/time

**Example:**
```bash
curl -X POST "https://your-api.com/v1/admissions/academy/cohort" \
  -H "Authorization: Token your_token_here" \
  -H "Academy: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Full Stack Web Development - Miami 2024",
    "slug": "full-stack-miami-2024",
    "syllabus": "full-stack-web-development.vlatest",
    "kickoff_date": "2024-02-15T09:00:00Z",
    "stage": "INACTIVE",
    "schedule": 1
  }'
```

**Response:**
```json
{
  "id": 1,
  "slug": "full-stack-miami-2024",
  "name": "Full Stack Web Development - Miami 2024",
  "kickoff_date": "2024-02-15T09:00:00Z",
  "stage": "INACTIVE",
  "academy": {
    "id": 1,
    "slug": "miami-academy",
    "name": "Miami Academy"
  },
  "syllabus_version": {
    "id": 1,
    "version": 2
  },
  "schedule": {
    "id": 1,
    "name": "Full-Time Morning Schedule"
  }
}
```

---

## 📚 API Endpoints Reference

### Academy Management

| Method | Endpoint | Description | Required Headers |
|--------|----------|-------------|------------------|
| `GET` | `/v1/admissions/academy` | List all academies | None |
| `POST` | `/v1/admissions/academy` | Create academy | `Authorization` |
| `GET` | `/v1/admissions/academy/{id}` | Get academy details | None |
| `PUT` | `/v1/admissions/academy/{id}` | Update academy | `Authorization` |

### Syllabus Management

| Method | Endpoint | Description | Required Headers |
|--------|----------|-------------|------------------|
| `GET` | `/v1/admissions/syllabus` | List all syllabi | None |
| `POST` | `/v1/admissions/syllabus` | Create syllabus | `Authorization` |
| `GET` | `/v1/admissions/syllabus/{id}` | Get syllabus details | None |
| `PUT` | `/v1/admissions/syllabus/{id}` | Update syllabus | `Authorization` |

### Syllabus Version Management

| Method | Endpoint | Description | Required Headers |
|--------|----------|-------------|------------------|
| `GET` | `/v1/admissions/syllabus/{id}/version` | List syllabus versions | None |
| `POST` | `/v1/admissions/syllabus/{id}/version` | Create syllabus version | `Authorization` |
| `GET` | `/v1/admissions/syllabus/{id}/version/{version}` | Get specific version | None |
| `PUT` | `/v1/admissions/syllabus/{id}/version/{version}` | Update version | `Authorization` |

### Schedule Management

| Method | Endpoint | Description | Required Headers |
|--------|----------|-------------|------------------|
| `GET` | `/v1/admissions/academy/schedule` | List academy schedules | `Academy` |
| `POST` | `/v1/admissions/academy/schedule` | Create schedule | `Authorization`, `Academy` |
| `GET` | `/v1/admissions/academy/schedule/{id}` | Get schedule details | `Academy` |
| `PUT` | `/v1/admissions/academy/schedule/{id}` | Update schedule | `Authorization`, `Academy` |

### Cohort Management

| Method | Endpoint | Description | Required Headers |
|--------|----------|-------------|------------------|
| `GET` | `/v1/admissions/academy/cohort` | List academy cohorts | `Academy` |
| `POST` | `/v1/admissions/academy/cohort` | Create cohort | `Authorization`, `Academy` |
| `GET` | `/v1/admissions/academy/cohort/{id}` | Get cohort details | `Academy` |
| `PUT` | `/v1/admissions/academy/cohort/{id}` | Update cohort | `Authorization`, `Academy` |

---

## 🎯 Complete Examples

### Example 1: Minimal Cohort Creation

```bash
# 1. Create Academy
curl -X POST "https://api.breatheco.de/v1/admissions/academy" \
  -H "Authorization: Token your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "miami-academy",
    "name": "Miami Academy",
    "logo_url": "https://example.com/logo.png",
    "street_address": "123 Main St",
    "city": 1,
    "country": "us"
  }'

# 2. Create Syllabus
curl -X POST "https://api.breatheco.de/v1/admissions/syllabus" \
  -H "Authorization: Token your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "web-dev-basics",
    "name": "Web Development Basics",
    "academy_owner": 1
  }'

# 3. Create Syllabus Version
curl -X POST "https://api.breatheco.de/v1/admissions/syllabus/1/version" \
  -H "Authorization: Token your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "json": {"days": []},
    "status": "PUBLISHED"
  }'

# 4. Create Cohort
curl -X POST "https://api.breatheco.de/v1/admissions/academy/cohort" \
  -H "Authorization: Token your_token" \
  -H "Academy: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Web Dev Cohort 2024",
    "slug": "web-dev-2024",
    "syllabus": "web-dev-basics.vlatest",
    "kickoff_date": "2024-03-01T09:00:00Z"
  }'
```

### Example 2: Complete Cohort with Schedule

```bash
# 1. Create Academy (same as above)

# 2. Create Syllabus (same as above)

# 3. Create Syllabus Version (same as above)

# 4. Create Schedule
curl -X POST "https://api.breatheco.de/v1/admissions/academy/schedule" \
  -H "Authorization: Token your_token" \
  -H "Academy: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Full-Time Schedule",
    "schedule_type": "FULL-TIME",
    "description": "Monday to Friday, 9 AM to 5 PM",
    "syllabus": 1,
    "academy": 1
  }'

# 5. Create Cohort with Schedule
curl -X POST "https://api.breatheco.de/v1/admissions/academy/cohort" \
  -H "Authorization: Token your_token" \
  -H "Academy: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Full Stack Web Development - Miami 2024",
    "slug": "full-stack-miami-2024",
    "syllabus": "web-dev-basics.vlatest",
    "kickoff_date": "2024-02-15T09:00:00Z",
    "ending_date": "2024-06-15T18:00:00Z",
    "stage": "INACTIVE",
    "language": "en",
    "timezone": "America/New_York",
    "remote_available": true,
    "online_meeting_url": "https://zoom.us/j/123456789",
    "never_ends": false,
    "private": false,
    "available_as_saas": true,
    "schedule": 1
  }'
```

---

## 🔧 Field Reference

### Academy Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | ✅ | Unique identifier |
| `name` | string | ✅ | Display name |
| `logo_url` | string | ✅ | Logo URL |
| `street_address` | string | ✅ | Physical address |
| `city` | integer | ✅ | City ID |
| `country` | string | ✅ | Country code |
| `timezone` | string | ❌ | Default timezone |

### Syllabus Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | ✅ | Unique identifier |
| `name` | string | ✅ | Display name |
| `main_technologies` | string | ❌ | Comma-separated technologies |
| `duration_in_hours` | integer | ❌ | Total hours |
| `duration_in_days` | integer | ❌ | Total days |
| `week_hours` | integer | ❌ | Hours per week |
| `logo` | string | ❌ | Logo URL |
| `academy_owner` | integer | ❌ | Academy ID (for private syllabi) |

### Syllabus Version Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `json` | object | ✅ | Syllabus content |
| `status` | string | ✅ | "PUBLISHED" or "DRAFT" |
| `change_log_details` | string | ❌ | Change description |

### Schedule Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Schedule name |
| `schedule_type` | string | ✅ | "FULL-TIME" or "PART-TIME" |
| `description` | string | ✅ | Schedule description |
| `syllabus` | integer | ✅ | Syllabus ID |
| `academy` | integer | ✅ | Academy ID |

### Cohort Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Cohort display name |
| `slug` | string | ✅ | Unique identifier |
| `syllabus` | string | ✅ | "slug.vversion" format |
| `kickoff_date` | datetime | ✅ | Start date/time |
| `ending_date` | datetime | ❌ | End date/time |
| `stage` | string | ❌ | Cohort stage |
| `language` | string | ❌ | Language code |
| `timezone` | string | ❌ | Timezone |
| `remote_available` | boolean | ❌ | Allow remote students |
| `online_meeting_url` | string | ❌ | Meeting URL |
| `never_ends` | boolean | ❌ | No end date |
| `private` | boolean | ❌ | Hide from public API |
| `available_as_saas` | boolean | ❌ | Available for SAAS plans |
| `schedule` | integer | ❌ | Schedule ID |

---

## 🎭 Cohort Stages

| Stage | Description | Use Case |
|-------|-------------|----------|
| `INACTIVE` | Default - Not started | New cohorts |
| `PREWORK` | Pre-work phase | Before official start |
| `STARTED` | Active cohort | Currently running |
| `FINAL_PROJECT` | Final project phase | Near completion |
| `ENDED` | Completed | Finished cohorts |
| `DELETED` | Soft deleted | Removed cohorts |

---

## ⚠️ Important Notes

### Syllabus Version Rules
- **Version 1**: Only for marketing purposes, cannot be assigned to cohorts
- **Version 2+**: Can be assigned to cohorts
- **Status**: Must be "PUBLISHED" for cohorts
- **Latest**: Use "syllabus_slug.vlatest" to get the latest published version

### Academy Context
- Academy ID is automatically set from the URL path for academy-scoped endpoints
- Use `Academy` header for academy-scoped requests
- Academy owner is automatically set to the creator

### Timezone Handling
- If not provided, uses academy's default timezone
- All datetime fields should be in ISO format
- Timezone conversion is handled automatically

### Schedule Integration
- If schedule is provided, time slots are automatically created
- Schedule is optional but recommended for structured cohorts
- Time slots can be created separately after cohort creation

---

## 🚨 Troubleshooting

### Common Errors

#### 1. "Syllabus field malformed"
**Error:** `Syllabus field malformed(syllabus.slug.vsyllabus_version.version)`
**Solution:** Use format `"syllabus_slug.vversion_number"` or `"syllabus_slug.vlatest"`

#### 2. "Syllabus version not found"
**Error:** `Syllabus {version} doesn't exist`
**Solution:** Ensure syllabus version exists and is published

#### 3. "Academy not found"
**Error:** `Academy {id} not found`
**Solution:** Verify academy exists and you have access

#### 4. "Missing syllabus field"
**Error:** `syllabus field is missing`
**Solution:** Include syllabus field in cohort creation

#### 5. "Invalid cohort stage"
**Error:** `Invalid cohort stage {stage}`
**Solution:** Use valid stage: INACTIVE, PREWORK, STARTED, FINAL_PROJECT, ENDED, DELETED

### Validation Tips

1. **Check Dependencies**: Ensure academy, syllabus, and syllabus version exist
2. **Verify Permissions**: Ensure you have proper permissions for academy-scoped operations
3. **Validate Dates**: Ensure kickoff_date is not in the past
4. **Check Timezone**: Ensure timezone is valid and matches academy
5. **Unique Slugs**: Ensure cohort slug is unique

### Debug Steps

1. **List Academies**: `GET /v1/admissions/academy`
2. **List Syllabi**: `GET /v1/admissions/syllabus`
3. **List Syllabus Versions**: `GET /v1/admissions/syllabus/{id}/version`
4. **List Schedules**: `GET /v1/admissions/academy/schedule`
5. **List Cohorts**: `GET /v1/admissions/academy/cohort`

---

## 📞 Support

For additional help:
- Check API documentation: `/docs/`
- Review error messages for specific guidance
- Ensure all required fields are provided
- Verify permissions and academy context

---

*This guide covers the complete flow for creating cohorts with all dependencies. Follow the steps in order for successful cohort creation.*
