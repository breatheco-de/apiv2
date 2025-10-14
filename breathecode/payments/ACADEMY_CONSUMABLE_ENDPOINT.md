# Academy Consumable Endpoint

## Overview
A new endpoint has been created to allow academies to view consumables for their users.

## Endpoint
**URL:** `GET /v1/payments/academy/service/consumable`

**Capability Required:** `read_consumable`

## Features
- Automatically filters by academy_id (from request header)
- Returns consumables from subscriptions and plan financings belonging to the academy
- Excludes expired consumables (where `valid_until` < now)
- Excludes empty consumables (where `how_many` = 0)

## Query Parameters

### 1. `users` (optional)
Filter by user IDs (comma-separated list of integers)

**Example:**
```
GET /v1/payments/academy/service/consumable?users=123
GET /v1/payments/academy/service/consumable?users=123,456,789
```

### 2. `service` (optional)
Filter by service slugs (comma-separated list of strings)

**Example:**
```
GET /v1/payments/academy/service/consumable?service=mentorship-service
GET /v1/payments/academy/service/consumable?service=service-1,service-2
```

## Response Format
The response follows the same structure as `/v1/payments/me/service/consumable`:

```json
{
  "cohort_sets": [
    {
      "id": 1,
      "slug": "cohort-slug",
      "balance": {
        "unit": 10,
        "credit": 5
      },
      "items": [
        {
          "id": 123,
          "how_many": 10,
          "unit_type": "UNIT",
          "valid_until": "2025-12-31T23:59:59Z",
          "subscription": 45,
          "plan_financing": null,
          "user": 789,
          "subscription_seat": null,
          "subscription_billing_team": null
        }
      ]
    }
  ],
  "mentorship_service_sets": [...],
  "event_type_sets": [...],
  "voids": [...]
}
```

## Implementation Details

### Files Modified
1. **`breathecode/payments/views.py`**
   - Added `AcademyConsumableView` class at line 665

2. **`breathecode/payments/urls/v1.py`**
   - Added import for `AcademyConsumableView`
   - Added route at line 65: `path("academy/service/consumable", AcademyConsumableView.as_view(), name="academy_service_consumable")`

3. **`breathecode/payments/tests/urls/tests_academy_service_consumable.py`**
   - Created test file with comprehensive test cases

### Key Implementation Points

1. **Academy Filtering:**
```python
items = Consumable.objects.filter(
    Q(valid_until__gte=utc_now) | Q(valid_until=None),
    Q(subscription__academy_id=academy_id) | Q(plan_financing__academy_id=academy_id),
).exclude(how_many=0)
```

2. **User Filtering:**
```python
if users := request.GET.get("users"):
    user_ids = [int(x.strip()) for x in users.split(",") if x.strip()]
    items = items.filter(user_id__in=user_ids)
```

3. **Service Filtering:**
```python
if service_slugs := request.GET.get("service"):
    slugs = [s.strip() for s in service_slugs.split(",") if s.strip()]
    items = items.filter(service_item__service__slug__in=slugs)
```

## Usage Examples

### Get all consumables for the academy
```bash
curl -X GET "https://api.4geeks.com/v1/payments/academy/service/consumable" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 1"
```

### Get consumables for specific users
```bash
curl -X GET "https://api.4geeks.com/v1/payments/academy/service/consumable?users=123,456" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 1"
```

### Get consumables for specific services
```bash
curl -X GET "https://api.4geeks.com/v1/payments/academy/service/consumable?service=mentorship-service,code-review" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 1"
```

### Combine filters
```bash
curl -X GET "https://api.4geeks.com/v1/payments/academy/service/consumable?users=123&service=mentorship-service" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 1"
```

## Security
- Requires `read_consumable` capability
- Academy ID is taken from request header and cannot be overridden
- Only shows consumables from subscriptions/plan financings belonging to the authenticated academy

## Error Responses

### 401 Unauthorized
No authentication provided

### 403 Forbidden
- User doesn't have `read_consumable` capability for the academy
- Missing Academy header

### 400 Bad Request
- Invalid `users` parameter (not comma-separated integers)

Example error:
```json
{
  "detail": "users parameter must contain comma-separated integers",
  "status_code": 400
}
```

## Testing

Tests are located in: `breathecode/payments/tests/urls/tests_academy_service_consumable.py`

Run tests with:
```bash
poetry run pytest breathecode/payments/tests/urls/tests_academy_service_consumable.py -v
```

**Note:** Some tests may need adjustment to include proper Academy headers in requests.

