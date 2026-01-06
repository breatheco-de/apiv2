# Assignment Telemetry API - Complete Guide

This document provides comprehensive guidance on creating and updating assignment telemetry records for individual users and assets in the BreatheCode platform.

## Table of Contents

1. [Overview](#overview)
2. [Authentication & Permissions](#authentication--permissions)
3. [Creating or Updating Telemetry (POST)](#creating-or-updating-telemetry-post)
4. [Updating Existing Telemetry (PUT)](#updating-existing-telemetry-put)
5. [Field Reference](#field-reference)
6. [Error Handling](#error-handling)
7. [Examples](#examples)

---

## Overview

Assignment telemetry tracks detailed learning analytics for students working on specific assets (exercises, projects, etc.). This includes:

- **Raw Telemetry Data**: JSON data from LearnPack with detailed interaction information
- **Engagement Metrics**: Calculated engagement scores (0-100)
- **Frustration Metrics**: Calculated frustration scores (0-100)
- **Completion Data**: Completion rates, total time spent, and other metrics
- **Algorithm Versioning**: Track which version of the calculation algorithm was used

### Key Concepts

- **Asset Slug**: Unique identifier for the learning asset (e.g., "intro-to-python", "todo-list-project")
- **User ID**: The numeric ID of the student/user
- **Upsert Behavior**: POST endpoint creates new telemetry if it doesn't exist, or updates existing telemetry
- **Update Only**: PUT endpoint only updates existing telemetry (returns 404 if not found)

### Base URL

```
Production: https://breathecode.herokuapp.com
Development: http://localhost:8000
```

---

## Authentication & Permissions

### Required Headers

All endpoints require:

```http
Authorization: Token {your-access-token}
Academy: {academy_id}
Content-Type: application/json
```

### Required Capability

**`crud_telemetry`** - Create, update or delete assignment telemetry

> **Note**: This capability must be assigned to your role in the academy. Academy staff with appropriate roles automatically have this permission. See [create_academy_roles.py](mdc:breathecode/authenticate/management/commands/create_academy_roles.py) for full capability list.

---

## Creating or Updating Telemetry (POST)

The POST endpoint provides **upsert** functionality - it will create a new telemetry record if one doesn't exist, or update an existing one if it does.

### Endpoint

**`POST /v1/assignment/academy/asset/{asset_slug}/user/{user_id}/telemetry`**

### URL Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `asset_slug` | string | Yes | The slug identifier of the asset (e.g., "intro-to-python") |
| `user_id` | integer | Yes | The numeric ID of the user/student |

### Headers

```http
Authorization: Token {your-token}
Academy: {academy_id}
Content-Type: application/json
```

### Request Body

All fields are optional. Include only the fields you want to set or update:

```json
{
  "telemetry": {
    "events": [...],
    "interactions": [...],
    "timestamps": [...]
  },
  "engagement_score": 85.5,
  "frustration_score": 12.3,
  "metrics_algo_version": 1.2,
  "metrics": {
    "total_time_on_platform": 3600,
    "completion_rate": 95.5,
    "interactions_count": 150
  },
  "total_time": "01:00:00",
  "completion_rate": 95.5
}
```

### Response Codes

- **201 Created**: New telemetry record was created
- **200 OK**: Existing telemetry record was updated
- **400 Bad Request**: Validation error (invalid data format)
- **404 Not Found**: User with the specified ID doesn't exist
- **403 Forbidden**: Missing `crud_telemetry` capability or invalid academy

### Response Body (Success)

Returns the created or updated telemetry object:

```json
{
  "id": 123,
  "user": 456,
  "asset_slug": "intro-to-python",
  "telemetry": {
    "events": [...],
    "interactions": [...]
  },
  "engagement_score": 85.5,
  "frustration_score": 12.3,
  "metrics_algo_version": 1.2,
  "metrics": {
    "total_time_on_platform": 3600,
    "completion_rate": 95.5
  },
  "total_time": "01:00:00",
  "completion_rate": 95.5,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:45:00Z"
}
```

### Example: Create New Telemetry

```bash
curl -X POST \
  "https://breathecode.herokuapp.com/v1/assignment/academy/asset/intro-to-python/user/123/telemetry" \
  -H "Authorization: Token your-token-here" \
  -H "Academy: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "telemetry": {
      "events": ["start", "code_edit", "test_run", "complete"],
      "total_interactions": 45
    },
    "engagement_score": 88.5,
    "completion_rate": 100.0
  }'
```

### Example: Update Existing Telemetry

```bash
# Same endpoint - automatically updates if telemetry exists
curl -X POST \
  "https://breathecode.herokuapp.com/v1/assignment/academy/asset/intro-to-python/user/123/telemetry" \
  -H "Authorization: Token your-token-here" \
  -H "Academy: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "engagement_score": 92.0,
    "completion_rate": 100.0
  }'
```

---

## Updating Existing Telemetry (PUT)

The PUT endpoint **only updates** existing telemetry records. It will return a 404 error if the telemetry doesn't exist.

### Endpoint

**`PUT /v1/assignment/academy/asset/{asset_slug}/user/{user_id}/telemetry`**

### URL Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `asset_slug` | string | Yes | The slug identifier of the asset |
| `user_id` | integer | Yes | The numeric ID of the user/student |

### Headers

```http
Authorization: Token {your-token}
Academy: {academy_id}
Content-Type: application/json
```

### Request Body

All fields are optional. Include only the fields you want to update:

```json
{
  "engagement_score": 90.0,
  "frustration_score": 8.5,
  "completion_rate": 98.5,
  "total_time": "01:30:00"
}
```

### Response Codes

- **200 OK**: Telemetry was successfully updated
- **400 Bad Request**: Validation error (invalid data format)
- **404 Not Found**: Telemetry record doesn't exist for this asset and user
- **403 Forbidden**: Missing `crud_telemetry` capability or invalid academy

### Response Body (Success)

Returns the updated telemetry object (same format as POST).

### Example: Update Telemetry

```bash
curl -X PUT \
  "https://breathecode.herokuapp.com/v1/assignment/academy/asset/intro-to-python/user/123/telemetry" \
  -H "Authorization: Token your-token-here" \
  -H "Academy: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "engagement_score": 95.0,
    "completion_rate": 100.0
  }'
```

---

## Field Reference

### Request Fields

All fields are optional and can be included in both POST and PUT requests:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `telemetry` | JSON | Raw telemetry data from LearnPack with detailed interaction info | `{"events": [...], "interactions": [...]}` |
| `engagement_score` | float | Calculated engagement score (0-100) | `85.5` |
| `frustration_score` | float | Calculated frustration score (0-100) | `12.3` |
| `metrics_algo_version` | float | Version of the algorithm used to calculate metrics | `1.2` |
| `metrics` | JSON | Calculated metrics based on telemetry | `{"total_time_on_platform": 3600, "completion_rate": 95.5}` |
| `total_time` | duration | Total time spent on the exercise (ISO 8601 duration format) | `"01:00:00"` or `"PT1H"` |
| `completion_rate` | float | Completion rate from 0 to 100 (percentage) | `95.5` |

### Response Fields

In addition to the request fields, responses include:

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique telemetry record ID |
| `user` | integer | User ID (read-only) |
| `asset_slug` | string | Asset slug (read-only) |
| `created_at` | datetime | When the record was created (ISO 8601) |
| `updated_at` | datetime | When the record was last updated (ISO 8601) |

### Field Constraints

- **engagement_score**: Float value between 0 and 100
- **frustration_score**: Float value between 0 and 100
- **completion_rate**: Float value between 0 and 100 (percentage)
- **total_time**: Duration in ISO 8601 format (e.g., "PT1H30M" for 1 hour 30 minutes, or "01:30:00")
- **telemetry**: Valid JSON object (can be nested)
- **metrics**: Valid JSON object (can be nested)

---

## Error Handling

### Common Error Responses

#### 400 Bad Request - Validation Error

```json
{
  "engagement_score": ["Ensure this value is less than or equal to 100."],
  "total_time": ["Duration has wrong format. Use one of these formats instead: [HH:MM:SS, PT...]."]
}
```

#### 404 Not Found - User Not Found (POST)

```json
{
  "detail": "User with id 999 not found",
  "status_code": 404,
  "slug": "user-not-found"
}
```

#### 404 Not Found - Telemetry Not Found (PUT)

```json
{
  "detail": "Assignment telemetry not found for asset intro-to-python and user 123",
  "status_code": 404,
  "slug": "telemetry-not-found"
}
```

#### 403 Forbidden - Missing Capability

```json
{
  "detail": "You (user: 456) don't have this capability: crud_telemetry for academy 1",
  "status_code": 403
}
```

#### 403 Forbidden - Missing Academy Header

```json
{
  "detail": "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
  "status_code": 403
}
```

---

## Examples

### Complete Workflow Example

#### 1. Create Initial Telemetry (POST)

When a student starts an assignment:

```bash
curl -X POST \
  "https://breathecode.herokuapp.com/v1/assignment/academy/asset/todo-list-project/user/123/telemetry" \
  -H "Authorization: Token your-token-here" \
  -H "Academy: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "telemetry": {
      "started_at": "2024-01-15T10:00:00Z",
      "events": ["start"]
    },
    "engagement_score": 0,
    "completion_rate": 0
  }'
```

#### 2. Update Telemetry as Student Progresses (PUT)

```bash
curl -X PUT \
  "https://breathecode.herokuapp.com/v1/assignment/academy/asset/todo-list-project/user/123/telemetry" \
  -H "Authorization: Token your-token-here" \
  -H "Academy: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "telemetry": {
      "started_at": "2024-01-15T10:00:00Z",
      "events": ["start", "code_edit", "test_run"],
      "interactions": 25
    },
    "engagement_score": 65.5,
    "completion_rate": 45.0,
    "total_time": "00:30:00"
  }'
```

#### 3. Final Update When Student Completes (PUT)

```bash
curl -X PUT \
  "https://breathecode.herokuapp.com/v1/assignment/academy/asset/todo-list-project/user/123/telemetry" \
  -H "Authorization: Token your-token-here" \
  -H "Academy: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "telemetry": {
      "started_at": "2024-01-15T10:00:00Z",
      "completed_at": "2024-01-15T11:30:00Z",
      "events": ["start", "code_edit", "test_run", "complete"],
      "interactions": 150
    },
    "engagement_score": 92.5,
    "frustration_score": 8.0,
    "completion_rate": 100.0,
    "total_time": "01:30:00",
    "metrics": {
      "total_time_on_platform": 5400,
      "completion_rate": 100.0,
      "interactions_count": 150,
      "test_passes": 12,
      "test_failures": 0
    },
    "metrics_algo_version": 1.2
  }'
```

### Additional cURL Examples

#### Create or Update Telemetry with Full Data (POST)

```bash
curl -X POST \
  "https://breathecode.herokuapp.com/v1/assignment/academy/asset/intro-to-python/user/123/telemetry" \
  -H "Authorization: Token your-token-here" \
  -H "Academy: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "telemetry": {
      "events": ["start", "code_edit", "test_run"],
      "interactions": 45
    },
    "engagement_score": 85.5,
    "completion_rate": 95.0,
    "total_time": "01:00:00"
  }'
```

#### Partial Update (PUT)

```bash
curl -X PUT \
  "https://breathecode.herokuapp.com/v1/assignment/academy/asset/intro-to-python/user/123/telemetry" \
  -H "Authorization: Token your-token-here" \
  -H "Academy: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "engagement_score": 90.0,
    "completion_rate": 100.0
  }'
```

---

## Best Practices

1. **Use POST for Upsert**: If you're unsure whether telemetry exists, use POST which will create or update automatically.

2. **Use PUT for Updates Only**: Use PUT when you're certain the telemetry exists and want to ensure it fails if it doesn't.

3. **Partial Updates**: Both endpoints support partial updates - only include the fields you want to change.

4. **Duration Format**: Use ISO 8601 duration format (e.g., "PT1H30M") or time format (e.g., "01:30:00") for `total_time`.

5. **Score Validation**: Ensure engagement_score, frustration_score, and completion_rate are between 0 and 100.

6. **Error Handling**: Always check for 404 errors (user not found, telemetry not found) and handle them appropriately.

7. **Academy Header**: Always include the `Academy` header with the academy ID, even though it's also in the URL path.

---

## Related Documentation

- [Managing Single Asset](MANAGE_SINGLE_ASSET.md) - Learn about assets and asset slugs
- [Student Report](STUDENT_REPORT.md) - View student information and progress
- [Authentication](AUTHENTICATION.md) - Learn about authentication and tokens

---

## Support

For issues or questions:
- Check error messages for specific validation errors
- Verify you have the `crud_telemetry` capability in your academy role
- Ensure the user ID and asset slug are correct
- Verify the Academy header matches the academy ID in the URL

