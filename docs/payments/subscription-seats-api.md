# API Documentation & Postman Collection

## Overview

This directory contains comprehensive API documentation for the 4Geeks Subscription & Seats API in two formats:
- **OpenAPI 3.0 Specification** (`openapi.yaml`)
- **Postman Collection** (`postman_collection.json`)

## Files

### 1. openapi.yaml
OpenAPI 3.0 specification that can be imported into:
- Postman
- Swagger UI
- Insomnia
- Any OpenAPI-compatible tool

### 2. postman_collection.json
Ready-to-use Postman collection with:
- Pre-configured requests
- Environment variables
- Test scripts
- Request examples

## Import to Postman

### Method 1: Import OpenAPI File

1. Open Postman
2. Click **Import** button (top left)
3. Select **File** tab
4. Choose `openapi.yaml`
5. Click **Import**

### Method 2: Import Postman Collection

1. Open Postman
2. Click **Import** button (top left)
3. Select **File** tab
4. Choose `postman_collection.json`
5. Click **Import**

## Setup Environment Variables

After importing, set up your environment:

1. Click **Environments** (left sidebar)
2. Create new environment: **4Geeks API**
3. Add variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `base_url` | API base URL | `https://breathecode.herokuapp.com` |
| `user_token_1` | Owner token | `eyJhbGc...` |
| `user_token_2` | Second user token | `eyJhbGc...` |
| `academy_id` | Academy ID | `1` |
| `academy_slug` | Academy slug | `4geeks` |
| `plan_slug` | Plan slug | `4geeks-premium` |
| `subscription_id` | Subscription ID (auto-set) | `123` |
| `bag_token` | Bag token (auto-set) | `bag_abc123` |

### Getting Tokens

Set environment variables before running fttest:

```bash
export FTT_API_URL="https://breathecode.herokuapp.com"
export FTT_USER_TOKEN1="your_token_here"
export FTT_USER_TOKEN2="second_user_token"
export FTT_ACADEMY="1"
export FTT_ACADEMY_SLUG="4geeks"
```

## API Flows

### Flow 1: Pay PER_SEAT Plan

```
1. Get Plan Details
   GET /v1/payments/plan/{plan_slug}

2. Preview Plan with Seats
   POST /v1/payments/checking
   Body: {"type": "PREVIEW", "plans": [1], "team_seats": 3}

3. Create Bag
   POST /v1/payments/checking
   Body: {"type": "BAG", "plans": [1], "team_seats": 3}
   → Saves bag_token

4. Add Payment Card
   PUT /v1/payments/card
   Body: {"card_number": "4242...", "cvc": "123", ...}

5. Pay Plan
   POST /v1/payments/pay
   Body: {"token": "{{bag_token}}", "chosen_period": "MONTH"}

6. Get My Subscriptions
   GET /v1/payments/me/subscription
   → Note subscription_id

7. Get My Consumables
   GET /v1/provisioning/me/consumables
```

### Flow 2: Manage Seats

```
1. Get Seats
   GET /v2/payments/subscription/{subscription_id}/billing-team/seat

2. Add Seat
   PUT /v2/payments/subscription/{subscription_id}/billing-team/seat
   Body: {"add_seats": [{"email": "...", "seat_multiplier": 1}]}

3. Replace Seat
   PUT /v2/payments/subscription/{subscription_id}/billing-team/seat
   Body: {"replace_seats": [{"from_email": "...", "to_email": "..."}]}

4. Delete Seat
   DELETE /v2/payments/subscription/{subscription_id}/billing-team/seat/{seat_id}
### Flow 3: Consumable Checkout

1. Get My Subscriptions
   GET /v1/payments/me/subscription

2. Consumable Checkout (Add Seats)
   POST /v2/payments/consumable/checkout
   Body: {"service": "seat-service", "how_many": 3, "subscription": 123}

3. Get Billing Team
   GET /v2/payments/subscription/{subscription_id}/billing-team

4. Get Seats
   GET /v2/payments/subscription/{subscription_id}/billing-team/seat

**Response**: 200 OK
```json
{
  "id": 1,
  "subscription": 123,
  "seats_limit": 3,
  "consumption_strategy": "PER_SEAT"
}
```

### Flow 3: Consumable Checkout

1. Get My Subscriptions
   GET /v1/payments/me/subscription

2. Consumable Checkout (Add Seats)
   POST /v2/payments/consumable/checkout
   Body: {"service": "seat-service", "how_many": 3, "subscription": 123}

3. Get Billing Team
   GET /v2/payments/subscription/{subscription_id}/billing-team

4. Get Seats
   GET /v2/payments/subscription/{subscription_id}/billing-team/seat

**Response**: 200 OK

```http
POST /v1/payments/checking
Authorization: Bearer {{user_token_1}}
Content-Type: application/json

{
  "type": "PREVIEW",
  "plans": [1],
  "team_seats": 3
}
```

**Response**:
```json
{
  "amount": 149.00,
  "seat_service_item": {
    "id": 10,
    "how_many": 3
  }
}
```

### Add Seat

```http
PUT /v2/payments/subscription/123/billing-team/seat
Authorization: Bearer {{user_token_1}}
Content-Type: application/json

{
  "add_seats": [
    {
      "email": "lord@valomero.com",
      "seat_multiplier": 1,
      "first_name": "Lord",
      "last_name": "Valomero"
    }
  ]
}
```

**Response**:
```json
[
  {
    "id": 1,
    "user": 456,
    "email": "owner@example.com",
    "is_active": true,
    "seat_multiplier": 1
  },
  {
    "id": 2,
    "user": null,
    "email": "lord@valomero.com",
    "is_active": true,
    "seat_multiplier": 1
  }
]
```

### Enable Auto-Recharge

```http
PATCH /v2/payments/subscription/123/billing-team
Authorization: Bearer {{user_token_1}}
Content-Type: application/json

{
  "auto_recharge_enabled": true,
  "recharge_threshold_amount": "10.00",
  "recharge_amount": "20.00",
  "max_monthly_spend": "100.00"
}
```

**Response**:
```json
{
  "id": 1,
  "subscription": 123,
  "name": "Team 123",
  "seats_limit": 3,
  "consumption_strategy": "PER_TEAM",
  "auto_recharge_enabled": true,
  "recharge_threshold_amount": "10.00",
  "recharge_amount": "20.00",
  "max_monthly_spend": "100.00",
  "current_month_spend": "0.00",
  "last_recharge_reset_at": null
}
```

## Testing with Postman

### 1. Run Complete Flow

1. Set environment variables
2. Run requests in order from **2. Payment Flow** folder
3. Check responses and auto-set variables
4. Continue with **4. Seat Management**

### 2. Test Auto-Recharge

1. Complete payment flow
2. Enable auto-recharge via **3. Billing Team & Auto-Recharge**
3. Consume services via **6. Assets**
4. Check consumables via **5. Consumables**

### 3. Test PER_SEAT vs PER_TEAM

**PER_SEAT**:
- Use plan: `4geeks-premium`
- Consumables have `subscription_seat` set
- Each seat holder gets isolated consumables

**PER_TEAM**:
- Use plan: `hack-30-machines-in-30-days`
- Consumables have `user: null`, `subscription_billing_team` set
- All team members share consumables

## Postman Scripts

The collection includes test scripts that automatically:

### Extract Bag Token
```javascript
const response = pm.response.json();
pm.collectionVariables.set('bag_token', response.token);
```

### Extract Subscription ID
```javascript
const response = pm.response.json();
if (response.subscriptions && response.subscriptions.length > 0) {
  pm.collectionVariables.set('subscription_id', response.subscriptions[0].id);
}
```

## Swagger UI

To view the API in Swagger UI:

1. Go to https://editor.swagger.io/
2. Click **File → Import file**
3. Select `openapi.yaml`
4. Explore endpoints with interactive documentation

## Insomnia

To import into Insomnia:

1. Open Insomnia
2. Click **Create → Import From → File**
3. Select `openapi.yaml`
4. Configure environment variables

## cURL Examples

### Get Plan
```bash
curl -X GET "https://breathecode.herokuapp.com/v1/payments/plan/4geeks-premium" \
  -H "Authorization: Bearer $FTT_USER_TOKEN1"
```

### Preview Plan
```bash
curl -X POST "https://breathecode.herokuapp.com/v1/payments/checking" \
  -H "Authorization: Bearer $FTT_USER_TOKEN1" \
  -H "Content-Type: application/json" \
  -d '{"type":"PREVIEW","plans":[1],"team_seats":3}'
```

### Add Seat
```bash
curl -X PUT "https://breathecode.herokuapp.com/v2/payments/subscription/123/billing-team/seat" \
  -H "Authorization: Bearer $FTT_USER_TOKEN1" \
  -H "Content-Type: application/json" \
  -d '{"add_seats":[{"email":"lord@valomero.com","seat_multiplier":1}]}'
```

## Troubleshooting

### 401 Unauthorized
- Check token is valid
- Ensure `Authorization: Bearer <token>` header is set
- Verify token hasn't expired

### 404 Not Found
- Check `subscription_id` is set correctly
- Verify plan slug exists
- Ensure academy ID is correct

### 400 Bad Request
- Validate request body matches schema
- Check required fields are present
- Verify data types (integers, strings, etc.)

### Subscription Not Created
- Wait 10-30 seconds after payment
- Check Celery workers are running
- Poll `/v1/payments/me/subscription` endpoint

## Related Documentation

- **README_pay_per_seat.md**: PER_SEAT flow details
- **README_pay_per_team.md**: PER_TEAM flow details
- **README_consumable_checkout_per_seat.md**: Consumable checkout (PER_SEAT)
- **README_consumable_checkout_per_team.md**: Consumable checkout (PER_TEAM)
- **AUTO_RECHARGE_IMPLEMENTATION.md**: Auto-recharge system

## Support

For issues or questions:
- Check README files for detailed flow documentation
- Review OpenAPI schema for request/response formats
- Run functional tests: `poetry run python3 -m scripts.fttests subscription_seats:<test_name>`
