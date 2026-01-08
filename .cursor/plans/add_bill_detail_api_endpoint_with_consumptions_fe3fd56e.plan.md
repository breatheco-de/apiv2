---
name: Add Bill Detail API Endpoint with Separate Consumptions Endpoint
overview: Enhance the GET endpoint for provisioning bills (`v1/provisioning/academy/bill/<int:bill_id>`) to return all necessary data for frontend rendering, including academy information and status display mappings. Create a separate endpoint (`v1/provisioning/academy/bill/<int:bill_id>/consumptions`) for fetching paginated consumptions.
todos:
  - id: create-academy-bill-detail-serializer
    content: Create AcademyBillDetailSerializer with feedback_email, legal_name, logo_url fields
    status: pending
  - id: create-bill-detail-serializer
    content: Create GetProvisioningBillDetailSerializer with academy, status_display, and upload_task_status fields
    status: pending
    dependencies:
      - create-academy-bill-detail-serializer
  - id: create-consumption-serializer
    content: Create GetProvisioningUserConsumptionDetailSerializer for API consumptions response
    status: pending
  - id: create-consumptions-view
    content: Create AcademyBillConsumptionsView class with GET method using APIViewExtensions(paginate=True) for pagination
    status: pending
    dependencies:
      - create-consumption-serializer
  - id: add-consumptions-url
    content: Add URL route for /academy/bill/<int:bill_id>/consumptions endpoint
    status: pending
    dependencies:
      - create-consumptions-view
  - id: update-bill-view
    content: Update AcademyBillView.get() to use GetProvisioningBillDetailSerializer for bill detail
    status: pending
    dependencies:
      - create-bill-detail-serializer
  - id: add-tests
    content: Add tests for both bill detail and consumptions endpoints
    status: pending
    dependencies:
      - update-bill-view
      - add-consumptions-url
---

# Add Bill Detail API Endpoint with Separate Consumptions Endpoint

## Overview

Enhance the `GET /v1/provisioning/academy/bill/<int:bill_id>` endpoint to return bill data with academy information and status display mappings. Create a separate `GET /v1/provisioning/academy/bill/<int:bill_id>/consumptions` endpoint for fetching paginated consumptions, replacing the current HTML rendering approach.

## Current State

- The bill endpoint uses `GetProvisioningBillSerializer` which returns basic bill information
- The HTML rendering (`render_html_bill`) includes: bill details, academy info (name, feedback_email, legal_name, logo_url), paginated consumptions, status mappings, and pagination metadata
- Consumptions use `ProvisioningUserConsumptionHTMLResumeSerializer` for HTML rendering
- No separate API endpoint exists for fetching bill consumptions

## Implementation Steps

### 1. Create Enhanced Academy Serializer

**File**: [breathecode/provisioning/serializers.py](breathecode/provisioning/serializers.py)

- Create `AcademyBillDetailSerializer` extending or complementing the existing `AcademySerializer` (line 12)
- Include fields needed for bill rendering:
- `id`, `name`, `slug` (already in AcademySerializer)
- `feedback_email` (for contact info)
- `legal_name` (for invoice header)
- `logo_url` (for branding)

### 2. Create Bill Detail Serializer

**File**: [breathecode/provisioning/serializers.py](breathecode/provisioning/serializers.py)

- Create `GetProvisioningBillDetailSerializer` based on `GetProvisioningBillSerializer` (line 69)
- Add fields:
- `academy`: Use the new `AcademyBillDetailSerializer`
- `status_display`: Computed field mapping status codes to display text using the status_map from `render_html_bill` (line 638)
- `upload_task_status`: MethodField that queries TaskManager to get the processing status of the upload task
- Query: `TaskManager.objects.filter(task_module='breathecode.provisioning.tasks', task_name='upload', arguments__args__0=obj.hash).first()`
- Return the `status` field from the TaskManager record (or `None` if not found)
- This shows the processing status of the CSV upload task (PENDING, DONE, ERROR, etc.)
- Keep all existing fields from `GetProvisioningBillSerializer`

### 3. Create Consumption Detail Serializer

**File**: [breathecode/provisioning/serializers.py](breathecode/provisioning/serializers.py)

- Create `GetProvisioningUserConsumptionDetailSerializer` for API responses (similar to `ProvisioningUserConsumptionHTMLResumeSerializer`)
- Ensure it includes: `username`, `status`, `status_text`, `amount`, `kind` (with `product_name`, `sku`)
- Use consistent field naming with existing API serializers

### 4. Create Bill Consumptions View

**File**: [breathecode/provisioning/views.py](breathecode/provisioning/views.py)

- Create new `AcademyBillConsumptionsView` class extending `APIView`
- Use `APIViewExtensions` with `paginate=True` (following the pattern in `AcademyBillView`, line 686)
- Add `@capable_of("read_provisioning_bill")` decorator to GET method
- Implement GET method that:
- Validates bill exists and belongs to academy (from `academy_id` in URL)
- Fetches consumptions filtered by bill: `ProvisioningUserConsumption.objects.filter(bills=bill)`
- Orders consumptions by `username` (matching HTML version line 649)
- Uses `APIViewExtensions` handler to paginate the queryset automatically
- Serializes paginated results using `GetProvisioningUserConsumptionDetailSerializer`
- Returns response using `handler.response()` which handles pagination envelope automatically

### 5. Use Existing Pagination Infrastructure

**File**: [breathecode/provisioning/views.py](breathecode/provisioning/views.py)

- The `APIViewExtensions` with `paginate=True` will automatically:
- Parse `limit` query parameter (default: 20 per `PaginationExtension`, but can be overridden to 10 to match `LIMIT_PER_PAGE_HTML`)
- Parse `offset` query parameter (default: 0)
- Calculate total count
- Apply slicing to queryset
- Build pagination URLs using `request.build_absolute_uri()` and `replace_query_param`/`remove_query_param`
- Return standard pagination response format with `count`, `first`, `next`, `previous`, `last`, `results`
- Handle envelope based on query parameter (enabled by default when limit/offset are present)

### 6. Update Bill View Method

**File**: [breathecode/provisioning/views.py](breathecode/provisioning/views.py)

- Modify `AcademyBillView.get()` (line 689) to:
- Use `GetProvisioningBillDetailSerializer` instead of `GetProvisioningBillSerializer` when `bill_id` is provided
- Remove any consumption-related logic (consumptions now handled by separate endpoint)
- Keep bill detail focused on bill and academy information only

### 7. Add URL Route

**File**: [breathecode/provisioning/urls.py](breathecode/provisioning/urls.py)

- Add new URL pattern for consumptions endpoint:
- Path: `academy/bill/<int:bill_id>/consumptions`
- View: `AcademyBillConsumptionsView.as_view()`
- Name: `academy_bill_consumptions`
- Place after the existing `academy/bill/<int:bill_id>` route (order matters)

### 8. Response Structures

#### Bill Detail Endpoint Response

`GET /v1/provisioning/academy/bill/<int:bill_id>` should return:

```json
{
  "id": 1,
  "vendor": {...},
  "total_amount": "...",
  "status": "DUE",
  "status_display": "UNDER_REVIEW",
  "status_details": "...",
  "paid_at": null,
  "fee": "...",
  "stripe_url": "...",
  "created_at": "...",
  "title": "...",
  "academy": {
    "id": 1,
    "name": "...",
    "slug": "...",
    "feedback_email": "...",
    "legal_name": "...",
    "logo_url": "..."
  }
}
```



#### Consumptions Endpoint Response

`GET /v1/provisioning/academy/bill/<int:bill_id>/consumptions?limit=10&offset=0` should return:

```json
{
  "count": 50,
  "first": null,
  "next": "https://breathecode.herokuapp.com/v1/provisioning/academy/bill/1/consumptions?limit=10&offset=10",
  "previous": null,
  "last": "https://breathecode.herokuapp.com/v1/provisioning/academy/bill/1/consumptions?limit=10&offset=40",
  "results": [
    {
      "username": "...",
      "status": "...",
      "status_text": "...",
      "amount": "...",
      "kind": {
        "product_name": "...",
        "sku": "..."
      }
    }
  ]
}
```



### 9. Update Tests

**File**: [breathecode/provisioning/tests/urls/tests_academy_bill_id.py](breathecode/provisioning/tests/urls/tests_academy_bill_id.py)

- Add tests for bill detail endpoint:
- Bill detail response includes academy information with all required fields (feedback_email, legal_name, logo_url)
- Status display mapping is correct
- `upload_task_status` field is included and returns correct TaskManager status when task exists
- `upload_task_status` returns `None` when no matching TaskManager record exists
- Response does not include consumptions
- Create new test file or add tests for consumptions endpoint:
- `breathecode/provisioning/tests/urls/tests_academy_bill_consumptions.py`
- Test consumptions endpoint returns paginated results in standard format
- Test pagination fields: `count`, `first`, `next`, `previous`, `last`, `results`
- Test limit/offset pagination works correctly
- Test pagination URLs are generated correctly
- Test `first`, `next`, `previous`, `last` are null when appropriate
- Test consumptions are ordered by username
- Test endpoint requires proper permissions (`read_provisioning_bill`)
- Test 404 when bill doesn't exist
- Test 404 when bill doesn't belong to academy

## Notes

- The status mapping uses: `{"DUE": "UNDER_REVIEW", "APPROVED": "READY_TO_PAY", "PAID": "ALREADY PAID", "PENDING": "PENDING"}` (line 638)
- Pagination uses the existing `APIViewExtensions` with `paginate=True` which provides the standard pagination format automatically
- The HTML version uses `LIMIT_PER_PAGE_HTML = 10` (line 585), but the API uses default limit of 20 from `PaginationExtension`. Consider if we need to override default to 10, or document that API uses different default
- Pagination response format follows the codebase standard with `count`, `first`, `next`, `previous`, `last`, and `results` fields (implemented by `PaginationExtension`)
- URLs in pagination fields are automatically generated using `request.build_absolute_uri()` and `replace_query_param`/`remove_query_param` from DRF
- The `APIViewExtensions` pattern is already used in `AcademyBillView` (line 686) - follow the same pattern for consistency
- Edge cases (negative offsets, offsets beyond total count, invalid limits) are handled by the existing `PaginationExtension` implementation
- The consumptions endpoint should validate that the bill exists and belongs to the specified academy
- Consumptions are filtered using: `ProvisioningUserConsumption.objects.filter(bills=bill)` (many-to-many relationship)
- Both endpoints should use the same permission decorator: `@capable_of("read_provisioning_bill")`
- TaskManager query for upload task status:
- Filter by: `task_module='breathecode.provisioning.tasks'`, `task_name='upload'`
- Match bill hash: `arguments__args__0=obj.hash` (hash is the first argument to `tasks.upload.delay()`)