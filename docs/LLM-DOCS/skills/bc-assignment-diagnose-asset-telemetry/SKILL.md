---
name: bc-assignment-diagnose-asset-telemetry
description: Use when diagnosing assignment/package telemetry collection for an asset, user, or task and when interpreting telemetry stats usage patterns, and do NOT use for general assignment grading or non-telemetry workflows.
requires: []
---

# Skill: Diagnose Asset Telemetry Collection

## When to Use

Use this skill when you need to confirm if telemetry exists for an asset, user, or task, identify why it is missing, or interpret telemetry stats to understand package/asset usage patterns. Use it for ingestion validation, staff upsert/update validation, per-task telemetry retrieval checks, and aggregate telemetry-stats interpretation. Do NOT use this skill to grade assignments, manage code reviews, or modify non-telemetry task fields.

## Concepts

- **AssignmentTelemetry** is stored per `user + asset_slug`, not as one row per event.
- **Task telemetry retrieval** is per task/user via `GET /v1/assignment/task/{task_id}` and returns `assignment_telemetry`.
- **Ingestion** (`POST /v1/assignment/me/telemetry`) is accepted first, then processed asynchronously.
- **Asset-level aggregation** is stored in `Asset.telemetry_stats` (daily bucket under `days` plus `last_sync_at`). Staff can **queue** a recalculation via registry asset action `sync_telemetry_stats` (Celery); the HTTP response may still show pre-sync stats until the worker finishes.

## Workflow

1. Identify the telemetry question first:
   - "Is telemetry being ingested?" -> use `POST /v1/assignment/me/telemetry`.
   - "Is telemetry persisted for a given user+asset?" -> use staff upsert/update endpoint.
   - "Can I retrieve telemetry for a specific assignment task?" -> use `GET /v1/assignment/task/{task_id}`.

2. Validate request scope and headers before troubleshooting data:
   - Send `Authorization: Token <token>` (or bearer token used by your environment).
   - For `/academy/` paths, send `Academy: <academy_id>`.
   - Send `Accept-Language: en|es` when you need translated error messages.

3. Validate ingestion path if telemetry is "not arriving":
   - Call `POST /v1/assignment/me/telemetry` with LearnPack payload fields.
   - Expect plain text `ok` when accepted.
   - If accepted but still missing in reads, treat it as async processing delay first.

4. Inspect LearnPack webhook processing state (academy staff):
   - Call `GET /v1/assignment/academy/learnpack/webhook` to confirm webhook records are present after ingestion.
   - Filter by `student`, `event`, `asset_id`, and `learnpack_package_id` to narrow the queue.
   - Use webhook `status` (`PENDING`, `DONE`, `ERROR`) and `status_text` to explain why telemetry is delayed or failing.

5. Validate persistence for a specific user+asset:
   - Use `POST /v1/assignment/academy/asset/{asset_slug}/user/{user_id}/telemetry` for upsert.
   - Use `PUT /v1/assignment/academy/asset/{asset_slug}/user/{user_id}/telemetry` only when record should already exist.
   - Use response status (`201`, `200`, `404`) to determine create/update/not-found outcomes.

6. Validate retrieval from assignment task:
   - Call `GET /v1/assignment/task/{task_id}`.
   - Read `assignment_telemetry` from response.
   - If `assignment_telemetry` is `null`, telemetry for that task's `user + associated_slug` is not currently found.

7. Check canonical slug implications when telemetry appears split:
   - Translation variants can map to a canonical asset slug.
   - Missing telemetry under one slug may exist under canonical translation slug.
   - Diagnose by comparing task `associated_slug` and the slug used in telemetry upsert/update requests.

8. Queue recomputation of asset-level telemetry stats (staff):
   - Call `PUT /v1/registry/academy/asset/{asset_slug}/action/sync_telemetry_stats` with `crud_asset` scope.
   - Expect `200` with the serialized asset; `telemetry_stats` may update only after the background task runs.
   - Re-fetch the asset (registry GET) after a short delay to read updated `telemetry_stats`.

## Endpoints

### Ingest LearnPack telemetry

- **Method:** `POST`
- **Path:** `/v1/assignment/me/telemetry`
- **Required headers:** `Authorization`
- **Required body fields:** LearnPack-compatible payload including at least user and asset identifiers (`user_id`, and one of `asset_id` or slug field used by LearnPack)
- **Response that matters:** plain text `ok` when accepted for async processing
- **Pagination:** Not paginated

**Request example**
```json
{
  "event": "batch",
  "user_id": 1234,
  "asset_id": 987,
  "slug": "javascript-arrays-intro",
  "package_id": 555,
  "timestamp": "2026-04-15T10:30:00Z",
  "step": 14
}
```

**Response example**
```json
"ok"
```

### List LearnPack webhook logs (academy staff observability)

- **Method:** `GET`
- **Path:** `/v1/assignment/academy/learnpack/webhook`
- **Required headers:** `Authorization`, `Academy`
- **Required capability:** `read_assignment`
- **Required body fields:** none
- **Supported filters:** comma-separated values for `student`, `event`, `asset_id`, `learnpack_package_id`; optional `status`
- **Response that matters:** paginated webhook list with processing fields (`status`, `status_text`) and normalized ids (`asset_id`, `learnpack_package_id`)
- **Pagination:** Paginated
- **Translated errors:** optional `Accept-Language: en|es`

**Request example**
```json
GET /v1/assignment/academy/learnpack/webhook?student=123,456&event=batch,open_step&asset_id=10,20&learnpack_package_id=1000,2000&status=PENDING,DONE
```

**Response example**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 9011,
      "is_streaming": true,
      "event": "batch",
      "asset_id": 10,
      "learnpack_package_id": 1000,
      "payload": {
        "event": "batch",
        "user_id": 123,
        "asset_id": 10,
        "package_id": 1000
      },
      "status": "DONE",
      "status_text": "OK",
      "student": {
        "id": 123,
        "first_name": "Ada",
        "last_name": "Lovelace"
      },
      "created_at": "2026-04-15T10:30:00Z",
      "updated_at": "2026-04-15T10:30:03Z"
    },
    {
      "id": 9012,
      "is_streaming": true,
      "event": "open_step",
      "asset_id": 20,
      "learnpack_package_id": 2000,
      "payload": {
        "event": "open_step",
        "user_id": 456,
        "asset_id": 20,
        "package_id": 2000
      },
      "status": "ERROR",
      "status_text": "Learnpack telemetry event `open_step` is not implemented",
      "student": {
        "id": 456,
        "first_name": "Grace",
        "last_name": "Hopper"
      },
      "created_at": "2026-04-15T10:35:00Z",
      "updated_at": "2026-04-15T10:35:01Z"
    }
  ]
}
```

### Upsert telemetry for a user and asset (academy staff)

- **Method:** `POST`
- **Path:** `/v1/assignment/academy/asset/{asset_slug}/user/{user_id}/telemetry`
- **Required headers:** `Authorization`, `Academy`
- **Required body fields:** none globally required; include telemetry fields to set
- **Response that matters:** telemetry payload fields and status `201` (created) or `200` (updated)
- **Pagination:** Not paginated

**Request example**
```json
{
  "telemetry": {
    "event": "batch",
    "step": 3,
    "interactions": 21
  },
  "engagement_score": 82.5,
  "frustration_score": 14.2,
  "metrics_algo_version": 1.2,
  "metrics": {
    "global": {
      "metrics": {
        "total_time_on_platform": 1800,
        "completion_rate": 67.5
      }
    }
  },
  "total_time": "00:30:00",
  "completion_rate": 67.5
}
```

**Response example**
```json
{
  "id": 4512,
  "telemetry": {
    "event": "batch",
    "step": 3,
    "interactions": 21
  },
  "engagement_score": 82.5,
  "frustration_score": 14.2,
  "metrics_algo_version": 1.2,
  "metrics": {
    "global": {
      "metrics": {
        "total_time_on_platform": 1800,
        "completion_rate": 67.5
      }
    }
  },
  "total_time": "00:30:00",
  "completion_rate": 67.5
}
```

### Update telemetry for an existing user+asset record (academy staff)

- **Method:** `PUT`
- **Path:** `/v1/assignment/academy/asset/{asset_slug}/user/{user_id}/telemetry`
- **Required headers:** `Authorization`, `Academy`
- **Required body fields:** none globally required; include telemetry fields to change
- **Response that matters:** status `200` on update, `404` with slug `telemetry-not-found` if missing
- **Pagination:** Not paginated

**Request example**
```json
{
  "engagement_score": 91.0,
  "completion_rate": 95.0,
  "total_time": "00:45:00"
}
```

**Response example**
```json
{
  "id": 4512,
  "telemetry": {
    "event": "batch",
    "step": 8,
    "interactions": 55
  },
  "engagement_score": 91.0,
  "frustration_score": 8.1,
  "metrics_algo_version": 1.2,
  "metrics": {
    "global": {
      "metrics": {
        "total_time_on_platform": 2700,
        "completion_rate": 95.0
      }
    }
  },
  "total_time": "00:45:00",
  "completion_rate": 95.0
}
```

### Queue asset telemetry stats recalculation (registry academy)

- **Method:** `PUT`
- **Path:** `/v1/registry/academy/asset/{asset_slug}/action/sync_telemetry_stats`
- **Required headers:** `Authorization`, `Academy`
- **Required capability:** `crud_asset` (same as other registry asset actions)
- **Required body fields:** none; send `{}` if the client requires a JSON body
- **Response that matters:** `200` with full academy asset payload from `AcademyAssetSerializer`; `telemetry_stats` may still reflect the **previous** snapshot until Celery completes
- **Pagination:** Not paginated
- **Translated errors:** optional `Accept-Language: en|es`

**Request example**
```json
{}
```

**Response example (representative; full asset shape is large)**
```json
{
  "id": 301,
  "slug": "javascript-arrays-intro",
  "title": "JavaScript Arrays Intro",
  "asset_type": "EXERCISE",
  "academy": 1,
  "telemetry_stats": {
    "last_sync_at": "2026-04-15T09:00:00.123456+00:00",
    "days": {
      "2026-04-14": {
        "frustration_avg": 12.5,
        "engagement_avg": 78.3,
        "completion_avg": 45.2,
        "total_sessions": 120
      }
    }
  },
  "sync_status": "OK",
  "updated_at": "2026-04-15T10:12:00Z"
}
```

### Retrieve telemetry through a task (per user basis)

- **Method:** `GET`
- **Path:** `/v1/assignment/task/{task_id}`
- **Required headers:** `Authorization`
- **Required body fields:** none
- **Response that matters:** `assignment_telemetry` field in task object
- **Pagination:** Not paginated for single task endpoint

**Response example**
```json
{
  "id": 890699,
  "title": "Arrays Practice",
  "task_status": "PENDING",
  "associated_slug": "javascript-arrays-intro",
  "revision_status": "PENDING",
  "task_type": "EXERCISE",
  "assignment_telemetry": {
    "event": "batch",
    "step": 8,
    "interactions": 55
  },
  "created_at": "2026-04-15T09:20:00Z",
  "updated_at": "2026-04-15T10:35:00Z"
}
```

## Edge Cases

1. **Missing Academy header on staff endpoint**  
   Observation: `403` error about missing academy header/scope.  
   Action: resend request with `Academy: <academy_id>`.

2. **Missing capability for telemetry write**  
   Observation: `403` (for `crud_telemetry` or `upload_assignment_telemetry`).  
   Action: use a token with the required capability in the target academy.

3. **User does not exist for staff upsert/update**  
   Observation: `404` with slug `user-not-found`.  
   Action: correct `user_id` before retrying.

4. **PUT used before telemetry exists**  
   Observation: `404` with slug `telemetry-not-found`.  
   Action: call POST upsert first, then PUT for subsequent updates.

5. **Telemetry accepted but not immediately retrievable**  
   Observation: ingestion returns `ok` but task retrieval still shows `assignment_telemetry: null`.  
   Action: check webhook list endpoint and inspect `status`/`status_text`, then re-check after processing.

6. **Canonical slug mismatch**  
   Observation: telemetry appears missing for translated slug while existing for canonical slug.  
   Action: validate slug normalization/canonical translation and re-check using canonical asset context.

7. **No cross-user telemetry list endpoint**  
   Observation: no public endpoint returns telemetry for multiple users by asset in one request.  
   Action: rely on per-user telemetry retrieval and asset-level precomputed stats (`Asset.telemetry_stats`) for aggregate diagnostics.

8. **Stats sync queued but `telemetry_stats` unchanged in response**  
   Observation: `PUT .../action/sync_telemetry_stats` returns `200` but `telemetry_stats.last_sync_at` or today's `days` entry is unchanged.  
   Action: wait for Celery, then `GET` the asset again from registry; avoid tight retry loops.

9. **Invalid numeric filter token on webhook list**  
   Observation: `400` with slug `invalid-filter` when sending non-numeric ids in `student`, `asset_id`, or `learnpack_package_id`.  
   Action: send only comma-separated numeric ids on these filters.

## Checklist

1. Confirmed which telemetry path applies: ingestion, staff upsert/update, or task retrieval.
2. Confirmed required headers (`Authorization`, and `Academy` for `/academy/` endpoints).
3. Verified write endpoint outcome by expected status (`201`, `200`, `404`, `403`).
4. Verified task endpoint returns `assignment_telemetry` for the expected `task_id`.
5. Checked slug consistency between task `associated_slug` and telemetry asset slug used in writes.
6. Accounted for async delay before concluding telemetry is missing.
7. If asset-level trend is needed, confirmed data should be read from `Asset.telemetry_stats` (precomputed aggregate), not from a multi-user telemetry list endpoint.
8. If stats are stale or missing, used `PUT /v1/registry/academy/asset/{asset_slug}/action/sync_telemetry_stats` and re-fetched the asset after the background job had time to complete.
9. If ingestion accepted but telemetry is missing, checked `GET /v1/assignment/academy/learnpack/webhook` with filters to confirm webhook `status` and `status_text`.
