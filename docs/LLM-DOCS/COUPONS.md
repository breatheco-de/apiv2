# Payment Coupons Documentation

## Overview

The **Coupon** system in the BreatheCode payments app enables flexible discount and referral management for subscriptions and plan financings. Coupons can provide percentage-based or fixed-price discounts, support referral programs with seller commissions, and can be automatically applied or manually entered by users.

### Primary Purposes

1. **Discount Management**: Apply discounts to subscription plans and services
2. **Referral Programs**: Track and reward sellers for referrals
3. **Promotional Campaigns**: Create time-limited or usage-limited promotional codes
4. **User-Specific Offers**: Restrict coupons to specific users
5. **Auto-Applied Offers**: Automatically apply special offers during checkout

### Key Features

- **Multiple Discount Types**: Percentage off, fixed price, or no discount
- **Referral Tracking**: Percentage or fixed commission for sellers
- **Plan Scoping**: Coupons can be global or restricted to specific plans
- **Usage Limits**: Control how many times a coupon can be used
- **Time-Based Validity**: Set offer and expiration dates
- **Auto-Application**: Automatically apply coupons during checkout
- **User Restrictions**: Limit coupon usage to specific users
- **Academy Management**: Academies can manage coupons for their plans

---

## Coupon Data Structure

### Coupon Fields

**Identification:**
- `slug` (string, required): Unique identifier (e.g., "new-year-50")

**Discount Configuration:**
- `discount_type` (string, required): `PERCENT_OFF`, `FIXED_PRICE`, `NO_DISCOUNT`, or `HAGGLING`
- `discount_value` (number, required): 
  - For `PERCENT_OFF`: Percentage as decimal (0-1, e.g., 0.5 = 50% off)
  - For `FIXED_PRICE`: Absolute discount amount

**Referral Configuration:**
- `referral_type` (string, required): `NO_REFERRAL`, `PERCENTAGE`, or `FIXED_PRICE`
- `referral_value` (number, default: 0): Commission amount for seller

**Behavior:**
- `auto` (boolean, default: false): Automatically apply during checkout
- `how_many_offers` (integer, default: -1): 
  - `-1` = unlimited uses
  - `0` = disabled (nobody can use)
  - `>0` = maximum number of uses

**Relationships:**
- `seller` (integer, optional): Seller ID for referral coupons
- `allowed_user` (integer, optional): User ID restriction
- `referred_buyer` (integer, optional): Buyer who activated reward
- `plans` (array of integers, optional): Plan IDs this coupon applies to

**Validity:**
- `offered_at` (datetime, optional): When offer becomes available
- `expires_at` (datetime, optional): When offer expires

**Metadata:**
- `created_at` (datetime, read-only): Creation timestamp
- `updated_at` (datetime, read-only): Last update timestamp

### Discount Types

- `PERCENT_OFF`: Percentage discount (discount_value is 0-1, e.g., 0.5 = 50% off)
- `FIXED_PRICE`: Fixed price discount (discount_value is absolute amount)
- `NO_DISCOUNT`: No discount applied
- `HAGGLING`: Special haggling type

### Referral Types

- `NO_REFERRAL`: Regular coupon, no seller commission
- `PERCENTAGE`: Seller receives percentage commission
- `FIXED_PRICE`: Seller receives fixed commission amount

### Validation Rules

- `discount_value` must be positive
- `referral_value` must be positive
- If `referral_type != NO_REFERRAL`, `referral_value` must be set
- If `referral_type == NO_REFERRAL`, `referral_value` must be 0
- If `auto == True`, `discount_type` cannot be `NO_DISCOUNT`
- If `referral_type != NO_REFERRAL`, `plans` should be empty (applies to all plans)
- Slug must be unique (no duplicate active coupons)

---

## API Quick Reference

### Endpoint Summary

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/v1/payments/coupon` | GET | Public | Validate coupons for a plan |
| `/v1/payments/bag/{id}/coupon` | PUT | User | Apply/remove coupons from bag |
| `/v1/payments/me/coupon` | GET | User | Get user's referral coupons |
| `/v1/payments/me/user/coupons` | GET | User | Get user's restricted coupons |
| `/v1/payments/me/user/coupons/{slug}` | PUT | User | Toggle auto-apply for user coupon |
| `/v1/payments/academy/coupon` | GET | Academy | List academy coupons |
| `/v1/payments/academy/coupon` | POST | Academy | Create coupon |
| `/v1/payments/academy/coupon/{slug}` | GET | Academy | Get specific coupon |
| `/v1/payments/academy/coupon/{slug}` | PUT | Academy | Update coupon |
| `/v1/payments/academy/coupon/{slug}` | DELETE | Academy | Delete coupon |

### Common Query Parameters

- `coupons`: Comma-separated coupon slugs (e.g., `"CODE1,CODE2"`)
- `plan`: Plan slug or ID
- `like`: Search filter for coupon slug
- Standard pagination: `limit`, `offset`
- Standard sorting: `sort` (e.g., `"-id"` for descending)

---

## API Endpoints

### Public Endpoints

#### `GET /v1/payments/coupon`
**Purpose**: Validate coupons for a specific plan  
**Permissions**: `AllowAny`  
**Query Parameters:**
- `coupons` (optional): Comma-separated coupon slugs (e.g., `"new-year-50,fakevalid"`)
- `plan` (required): Plan slug or ID

**Response**: Array of valid coupon objects
```json
[
    {
        "slug": "new-year-50",
        "discount_type": "PERCENT_OFF",
        "discount_value": 0.5,
        "referral_type": "NO_REFERRAL",
        "referral_value": 0.0,
        "auto": true,
        "offered_at": "2025-02-04T22:04:29Z",
        "expires_at": "2026-10-06T17:52:36Z"
    }
]
```

**Behavior:**
- Returns only coupons valid for the specified plan
- Filters by expiration, usage limits, and plan restrictions
- Excludes coupons where user is the seller
- Excludes user-restricted coupons not owned by the user

### User Endpoints

#### `GET /v1/payments/me/coupon`
**Purpose**: Get referral coupons for the authenticated user (as a seller)  
**Permissions**: Authenticated user  
**Response**: Array of coupon objects with associated plans

**Behavior:**
- Auto-creates a Seller if user doesn't have one
- Auto-creates a referral coupon if none exists
- Returns all coupons associated with the user's seller account

#### `GET /v1/payments/me/user/coupons`
**Purpose**: Get coupons restricted to the current user  
**Permissions**: Authenticated user  
**Query Parameters:**
- `plan` (optional): Plan slug to check validity against

**Response**: Array of coupon objects with `is_valid` field
```json
[
    {
        "slug": "my-special-coupon",
        "discount_type": "PERCENT_OFF",
        "discount_value": 0.2,
        "is_valid": true,
        ...
    }
]
```

#### `PUT /v1/payments/me/user/coupons/<coupon_slug>`
**Purpose**: Toggle auto-apply for a user's restricted coupon  
**Permissions**: Authenticated user  
**Response**:
```json
{
    "coupon_slug": "my-special-coupon",
    "auto": true
}
```

#### `PUT /v1/payments/bag/<bag_id>/coupon`
**Purpose**: Apply or remove coupons from a shopping bag  
**Permissions**: Authenticated user  
**Query Parameters:**
- `coupons` (optional): Comma-separated coupon slugs (empty to remove all)
- `plan` (required): Plan slug or ID

**Behavior:**
- Validates coupons are valid for the plan
- Only works on bags in `CHECKING` status
- Uses Redis lock to prevent concurrent modifications
- Updates bag with validated coupons

### Academy Endpoints

#### `GET /v1/payments/academy/coupon`
**Permission**: `read_subscription`  
**Query Parameters:**
- `plan` (optional): Filter by plan ID or slug
- `like` (optional): Search by coupon slug
- Standard pagination and sorting

**Response**: Array of coupon objects associated with academy plans

**Filtering:**
- Shows coupons linked to academy-owned plans or global plans
- If `plan` parameter provided, filters to coupons for that specific plan
- Validates plan belongs to academy

#### `POST /v1/payments/academy/coupon`
**Permission**: `crud_subscription`  
**Payload**:
```json
{
    "slug": "summer-2025",
    "discount_type": "PERCENT_OFF",
    "discount_value": 0.25,
    "referral_type": "NO_REFERRAL",
    "referral_value": 0.0,
    "auto": false,
    "how_many_offers": 100,
    "plans": [1, 2, 3],  // Plan IDs or slugs
    "offered_at": "2025-06-01T00:00:00Z",
    "expires_at": "2025-08-31T23:59:59Z"
}
```

**Validations:**
- All plans must belong to the academy (or be global)
- If `referral_type != NO_REFERRAL`, `plans` must be empty
- Slug must be unique
- Discount/referral values must be positive

#### `PUT /v1/payments/academy/coupon/<coupon_slug>`
**Permission**: `crud_subscription`  
**Behavior**: Partial updates supported  
**Validations**: Same as POST

#### `DELETE /v1/payments/academy/coupon/<coupon_slug>`
**Permission**: `crud_subscription`  
**Response**: 204 No Content

**Restrictions:**
- Only allows deleting coupons associated with academy plans

---

## Coupon Validation Logic

The API validates coupons based on the following criteria:

### Validation Rules

1. **Expiration Check**: Coupon must not be expired (`expires_at` is None or in future)
2. **Offer Date Check**: Coupon must be available (`offered_at` is None or in past)
3. **Usage Limits**: Coupon must have remaining uses (`how_many_offers` > 0 or -1 for unlimited)
4. **Plan Restrictions**:
   - If coupon has plans, the specified plan must be in the list
   - If coupon has no plans, it's global and applies to all plans
5. **Seller Exclusion**: User cannot use their own referral coupons
6. **User Restrictions**: If `allowed_user` is set, only that user can use the coupon
7. **Referral Program Exclusions**: Plans with `exclude_from_referral_program=True` cannot use referral coupons

### Discount Calculation

When coupons are applied to a price:

1. **Percentage Discounts**: Applied first (cumulative)
   - Formula: `price = price * (1 - discount_value)`
   - Example: $100 with 20% off = $80

2. **Fixed Price Discounts**: Applied after percentage discounts
   - Formula: `price = price - discount_value`
   - Example: $80 with $25 off = $55

3. **Price Floor**: Final price cannot go below $0

### Multiple Coupons

The system supports applying multiple coupons (if `max_coupons_allowed() > 1`). Default is 1 coupon per purchase.

**Example Calculation:**
- Original: $100
- Coupon 1 (10% off): $90
- Coupon 2 ($25 off): $65
- Final: $65

---

## Coupon Application Flow

### 1. User Applies Coupon During Checkout

```
1. User enters coupon code in frontend
2. Frontend calls: GET /v1/payments/coupon?coupons=CODE&plan=PLAN_SLUG
3. API validates coupon and returns valid coupons
4. If valid, frontend calls: PUT /v1/payments/bag/BAG_ID/coupon?coupons=CODE&plan=PLAN_SLUG
5. Bag is updated with coupon
6. Price is recalculated with discount
```

### 2. Auto-Applied Coupons

```
1. User adds plan to bag
2. System checks for auto-applied coupons (auto=True)
3. Validates coupons for the plan
4. Automatically adds to bag
5. User sees discount in checkout
```

### 3. Coupon Persistence

```
1. Coupons are stored on Bag during checkout
2. When payment succeeds, coupons are copied to:
   - Subscription.coupons (for subscriptions)
   - PlanFinancing.coupons (for plan financings)
3. Coupons persist for renewals
4. Coupons are excluded from renewals if:
   - Expired
   - User is the seller
   - Referral type is not NO_REFERRAL
```

---

## Discount Calculation

### Percentage Discount

**Formula**: `discounted_price = original_price * (1 - discount_value)`

**Example:**
- Original: $100
- Discount: 20% (discount_value = 0.2)
- Final: $80

### Fixed Price Discount

**Formula**: `discounted_price = original_price - discount_value`

**Example:**
- Original: $100
- Discount: $25 (discount_value = 25)
- Final: $75

### Multiple Coupons

When multiple coupons are applied:
1. Percentage discounts are applied first (cumulative)
2. Fixed price discounts are applied after
3. Price cannot go below 0

**Example:**
- Original: $100
- Coupon 1: 10% off → $90
- Coupon 2: $20 off → $70
- Final: $70

---

## Referral System

### How Referral Coupons Work

1. **Seller Creation**: User becomes a seller (auto-created via `/me/coupon`)
2. **Coupon Generation**: System creates referral coupon for seller
3. **Coupon Sharing**: Seller shares their coupon code
4. **Purchase**: Buyer uses seller's coupon
5. **Commission**: Seller earns commission based on `referral_value`

### Referral Coupon Rules

- `referral_type != NO_REFERRAL` means coupon is for referrals
- Referral coupons should have empty `plans` (apply to all plans)
- Individual plans can opt-out via `plan.exclude_from_referral_program`
- Sellers cannot use their own referral coupons
- Referral coupons are excluded from renewals

### Commission Calculation

**Percentage Commission:**
- Formula: `commission = purchase_amount * referral_value`
- Example: $100 purchase with 10% commission = $10 commission

**Fixed Commission:**
- Formula: `commission = referral_value`
- Example: Fixed commission of $25 = $25 commission regardless of purchase amount

---

## Usage Limits

### `how_many_offers` Field

- **-1**: Unlimited uses (default)
- **0**: Coupon disabled (nobody can use it)
- **>0**: Maximum number of uses

### Usage Tracking

System tracks usage by counting:
- Subscriptions using the coupon
- Plan financings using the coupon

**Note**: Usage is counted per purchase, not per user. A single user can use a coupon multiple times if `how_many_offers` allows.

---

## User Restrictions

### `allowed_user` Field

When set, only the specified user can use the coupon.

**Use Cases:**
- Personalized offers
- Reward coupons for specific users
- Test coupons for specific accounts

**Behavior:**
- Coupon is invisible to other users
- Only appears in `/me/user/coupons` for the allowed user
- Validation fails if different user tries to use it

---

## Auto-Applied Coupons

### `auto` Field

When `auto=True`, the coupon is automatically applied during checkout if:
1. Coupon is valid for the plan
2. Coupon hasn't expired
3. Usage limit hasn't been reached
4. User restrictions are met (if any)

**Use Cases:**
- Promotional campaigns
- Special offers
- Seasonal discounts

**Note**: Auto-applied coupons are shown in the bag response but cannot be removed by the user.

---

## Plan Restrictions

### Global Coupons

If `coupon.plans` is empty:
- Coupon applies to ALL plans
- No plan-specific restrictions
- Typically used for referral coupons

### Scoped Coupons

If `coupon.plans` has entries:
- Coupon only applies to listed plans
- Validation checks if plan is in the list
- Used for plan-specific promotions

**Example:**
- Coupon with `plans: [1, 2]` only works for plans with ID 1 and 2
- Coupon with `plans: []` works for all plans

---

## Time-Based Validity

### `offered_at`

When the coupon becomes available. If `None`, coupon is always available.

**Use Cases:**
- Future promotions
- Scheduled campaigns

### `expires_at`

When the coupon expires. If `None`, coupon never expires.

**Use Cases:**
- Limited-time offers
- Seasonal promotions
- Campaign deadlines

**Validation:**
- Coupons with `expires_at` in the past are invalid
- Coupons with `offered_at` in the future are invalid

---

## Response Formats

### Coupon Response Object

**Standard Coupon Response:**
```json
{
    "slug": "new-year-50",
    "discount_type": "PERCENT_OFF",
    "discount_value": 0.5,
    "referral_type": "NO_REFERRAL",
    "referral_value": 0.0,
    "auto": true,
    "allowed_user": {
        "id": 123,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com"
    },
    "offered_at": "2025-02-04T22:04:29Z",
    "expires_at": "2026-10-06T17:52:36Z"
}
```

**Coupon with Plans:**
Includes `plans` array with plan details when using endpoints that return plan associations.

### Request Payload (POST/PUT)

**Required Fields:**
- `slug` (string)
- `discount_type` (string)
- `discount_value` (number)
- `referral_type` (string)
- `referral_value` (number)

**Optional Fields:**
- `auto` (boolean)
- `how_many_offers` (integer)
- `plans` (array of integers or strings - plan IDs or slugs)
- `offered_at` (datetime string)
- `expires_at` (datetime string)
- `allowed_user` (integer - user ID)
- `seller` (integer - seller ID)
- `referred_buyer` (integer - user ID)

---

## API Use Cases

This section provides detailed, step-by-step use cases for common coupon scenarios with complete API request/response examples.

### Use Case 1: User Applies Coupon During Checkout

**Scenario**: A user wants to apply a promotional coupon code during checkout.

**Step 1: Validate the Coupon**

```bash
GET /v1/payments/coupon?coupons=SUMMER2025&plan=4geeks-plus-subscription
```

**Request:**
```bash
curl -X GET "https://api.4geeks.com/v1/payments/coupon?coupons=SUMMER2025&plan=4geeks-plus-subscription"
```

**Response (200 OK):**
```json
[
    {
        "slug": "SUMMER2025",
        "discount_type": "PERCENT_OFF",
        "discount_value": 0.25,
        "referral_type": "NO_REFERRAL",
        "referral_value": 0.0,
        "auto": false,
        "offered_at": "2025-06-01T00:00:00Z",
        "expires_at": "2025-08-31T23:59:59Z"
    }
]
```

**Response (Empty Array - Invalid Coupon):**
```json
[]
```

**Error Handling:**
- If coupon is invalid, returns empty array
- Frontend should show: "This coupon is invalid or doesn't work for the 4Geeks Plus Subscription plan. If you think this is an error, contact support@learnpack.co"

**Step 2: Apply Coupon to Bag**

```bash
PUT /v1/payments/bag/{bag_id}/coupon?coupons=SUMMER2025&plan=4geeks-plus-subscription
```

**Request:**
```bash
curl -X PUT "https://api.4geeks.com/v1/payments/bag/12345/coupon?coupons=SUMMER2025&plan=4geeks-plus-subscription" \
  -H "Authorization: Token abc123def456" \
  -H "Content-Type: application/json"
```

**Response (200 OK):**
```json
{
    "id": 12345,
    "status": "CHECKING",
    "type": "BAG",
    "plans": [...],
    "coupons": [
        {
            "slug": "SUMMER2025",
            "discount_type": "PERCENT_OFF",
            "discount_value": 0.25,
            "referral_type": "NO_REFERRAL",
            "referral_value": 0.0,
            "auto": false,
            "offered_at": "2025-06-01T00:00:00Z",
            "expires_at": "2025-08-31T23:59:59Z"
        }
    ],
    "amount_per_month": 75.00,
    "amount_per_year": 600.00
}
```

**Step 3: Remove Coupon from Bag**

```bash
PUT /v1/payments/bag/{bag_id}/coupon?coupons=&plan=4geeks-plus-subscription
```

**Request:**
```bash
curl -X PUT "https://api.4geeks.com/v1/payments/bag/12345/coupon?coupons=&plan=4geeks-plus-subscription" \
  -H "Authorization: Token abc123def456"
```

**Note**: Empty `coupons` parameter removes all manually applied coupons (auto-applied coupons remain).

---

### Use Case 2: Academy Creates a Promotional Coupon

**Scenario**: An academy wants to create a limited-time promotional coupon for a specific plan.

**Step 1: Create the Coupon**

```bash
POST /v1/payments/academy/coupon
```

**Request:**
```bash
curl -X POST "https://api.4geeks.com/v1/payments/academy/coupon" \
  -H "Authorization: Token academy_token" \
  -H "Academy: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "black-friday-2025",
    "discount_type": "PERCENT_OFF",
    "discount_value": 0.4,
    "referral_type": "NO_REFERRAL",
    "referral_value": 0.0,
    "auto": false,
    "how_many_offers": 50,
    "plans": [1, 2],
    "offered_at": "2025-11-25T00:00:00Z",
    "expires_at": "2025-11-30T23:59:59Z"
  }'
```

**Response (201 Created):**
```json
{
    "slug": "black-friday-2025",
    "discount_type": "PERCENT_OFF",
    "discount_value": 0.4,
    "referral_type": "NO_REFERRAL",
    "referral_value": 0.0,
    "auto": false,
    "offered_at": "2025-11-25T00:00:00Z",
    "expires_at": "2025-11-30T23:59:59Z"
}
```

**Error Responses:**

**400 Bad Request - Invalid Plan:**
```json
{
    "detail": "Plan 999 does not belong to this academy",
    "slug": "plan-not-belonging-to-academy"
}
```

**400 Bad Request - Invalid Referral Type:**
```json
{
    "detail": "If referral_type is not NO_REFERRAL, plans must be empty",
    "slug": "invalid-referral-coupon-with-plans"
}
```

**Step 2: List Academy Coupons**

```bash
GET /v1/payments/academy/coupon
```

**Request:**
```bash
curl -X GET "https://api.4geeks.com/v1/payments/academy/coupon" \
  -H "Authorization: Token academy_token" \
  -H "Academy: 1"
```

**Response (200 OK):**
```json
{
    "count": 5,
    "next": null,
    "previous": null,
    "results": [
        {
            "slug": "black-friday-2025",
            "discount_type": "PERCENT_OFF",
            "discount_value": 0.4,
            ...
        },
        ...
    ]
}
```

**Step 3: Filter Coupons by Plan**

```bash
GET /v1/payments/academy/coupon?plan=4geeks-plus-subscription
```

**Request:**
```bash
curl -X GET "https://api.4geeks.com/v1/payments/academy/coupon?plan=4geeks-plus-subscription" \
  -H "Authorization: Token academy_token" \
  -H "Academy: 1"
```

**Response**: Returns only coupons valid for the specified plan.

---

### Use Case 3: User Gets Their Referral Coupon

**Scenario**: A user wants to get their referral coupon code to share with others.

**Step 1: Get User's Referral Coupon**

```bash
GET /v1/payments/me/coupon
```

**Request:**
```bash
curl -X GET "https://api.4geeks.com/v1/payments/me/coupon" \
  -H "Authorization: Token user_token"
```

**Response (200 OK):**
```json
[
    {
        "slug": "referral-ABC123-456",
        "discount_type": "PERCENT_OFF",
        "discount_value": 0.1,
        "referral_type": "PERCENTAGE",
        "referral_value": 0.1,
        "auto": false,
        "plans": []
    }
]
```

**Behavior:**
- Auto-creates Seller if user doesn't have one
- Auto-creates referral coupon if none exists
- Returns all coupons associated with user's seller account

**Step 2: Share the Coupon Code**

The user can share the `slug` (e.g., "referral-ABC123-456") with others. When someone uses it:
- Buyer gets 10% discount
- User (seller) earns 10% commission

---

### Use Case 4: User Views Their Restricted Coupons

**Scenario**: A user wants to see coupons that were specifically created for them.

**Step 1: Get User's Restricted Coupons**

```bash
GET /v1/payments/me/user/coupons?plan=4geeks-plus-subscription
```

**Request:**
```bash
curl -X GET "https://api.4geeks.com/v1/payments/me/user/coupons?plan=4geeks-plus-subscription" \
  -H "Authorization: Token user_token"
```

**Response (200 OK):**
```json
{
    "count": 2,
    "results": [
        {
            "slug": "welcome-bonus-123",
            "discount_type": "FIXED_PRICE",
            "discount_value": 50.0,
            "referral_type": "NO_REFERRAL",
            "referral_value": 0.0,
            "auto": false,
            "is_valid": true,
            "offered_at": "2025-01-01T00:00:00Z",
            "expires_at": "2025-12-31T23:59:59Z"
        },
        {
            "slug": "loyalty-reward-456",
            "discount_type": "PERCENT_OFF",
            "discount_value": 0.15,
            "referral_type": "NO_REFERRAL",
            "referral_value": 0.0,
            "auto": true,
            "is_valid": true,
            "offered_at": "2025-06-01T00:00:00Z",
            "expires_at": null
        }
    ]
}
```

**Note**: The `is_valid` field indicates if the coupon is valid for the specified plan.

**Step 2: Toggle Auto-Apply**

```bash
PUT /v1/payments/me/user/coupons/welcome-bonus-123
```

**Request:**
```bash
curl -X PUT "https://api.4geeks.com/v1/payments/me/user/coupons/welcome-bonus-123" \
  -H "Authorization: Token user_token"
```

**Response (200 OK):**
```json
{
    "coupon_slug": "welcome-bonus-123",
    "auto": true
}
```

---

### Use Case 5: Academy Updates a Coupon

**Scenario**: An academy wants to extend a coupon's expiration date.

**Step 1: Update the Coupon**

```bash
PUT /v1/payments/academy/coupon/black-friday-2025
```

**Request:**
```bash
curl -X PUT "https://api.4geeks.com/v1/payments/academy/coupon/black-friday-2025" \
  -H "Authorization: Token academy_token" \
  -H "Academy: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "expires_at": "2025-12-05T23:59:59Z"
  }'
```

**Response (200 OK):**
```json
{
    "slug": "black-friday-2025",
    "discount_type": "PERCENT_OFF",
    "discount_value": 0.4,
    "referral_type": "NO_REFERRAL",
    "referral_value": 0.0,
    "auto": false,
    "how_many_offers": 50,
    "offered_at": "2025-11-25T00:00:00Z",
    "expires_at": "2025-12-05T23:59:59Z"
}
```

**Note**: Partial updates are supported - only include fields you want to change.

---

### Use Case 6: Academy Deletes a Coupon

**Scenario**: An academy wants to remove a coupon that's no longer needed.

**Step 1: Delete the Coupon**

```bash
DELETE /v1/payments/academy/coupon/black-friday-2025
```

**Request:**
```bash
curl -X DELETE "https://api.4geeks.com/v1/payments/academy/coupon/black-friday-2025" \
  -H "Authorization: Token academy_token" \
  -H "Academy: 1"
```

**Response (204 No Content)**

**Error Response (404 Not Found):**
```json
{
    "detail": "Coupon not found",
    "slug": "not-found"
}
```

---

### Use Case 7: Complete Checkout Flow with Coupon

**Scenario**: End-to-end checkout process with coupon application.

**Step 1: User Adds Plan to Bag**

```bash
POST /v1/payments/bag
```

**Request:**
```bash
curl -X POST "https://api.4geeks.com/v1/payments/bag" \
  -H "Authorization: Token user_token" \
  -H "Content-Type: application/json" \
  -d '{
    "plans": ["4geeks-plus-subscription"],
    "chosen_period": "YEAR"
  }'
```

**Response (201 Created):**
```json
{
    "id": 12345,
    "status": "CHECKING",
    "plans": [...],
    "coupons": [
        {
            "slug": "auto-applied-special",
            "discount_type": "PERCENT_OFF",
            "discount_value": 0.1,
            "auto": true
        }
    ],
    "amount_per_year": 900.00
}
```

**Note**: Auto-applied coupons are automatically included.

**Step 2: User Enters Coupon Code**

Frontend calls validation endpoint (see Use Case 1, Step 1).

**Step 3: Apply User-Entered Coupon**

```bash
PUT /v1/payments/bag/12345/coupon?coupons=SUMMER2025&plan=4geeks-plus-subscription
```

**Response:**
```json
{
    "id": 12345,
    "coupons": [
        {
            "slug": "auto-applied-special",
            "auto": true
        },
        {
            "slug": "SUMMER2025",
            "auto": false
        }
    ],
    "amount_per_year": 675.00  // Discounted price
}
```

**Step 4: Complete Payment**

```bash
POST /v1/payments/pay
```

**Request:**
```bash
curl -X POST "https://api.4geeks.com/v1/payments/pay" \
  -H "Authorization: Token user_token" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "bag_token_12345",
    "payment_method": "stripe"
  }'
```

**Result**: Coupons are persisted to the Subscription and will be applied to renewals (if valid).

---

### Use Case 8: Multiple Coupons (If Allowed)

**Scenario**: System allows multiple coupons (if `max_coupons_allowed() > 1`).

**Step 1: Validate Multiple Coupons**

```bash
GET /v1/payments/coupon?coupons=COUPON1,COUPON2&plan=4geeks-plus-subscription
```

**Response:**
```json
[
    {
        "slug": "COUPON1",
        "discount_type": "PERCENT_OFF",
        "discount_value": 0.1
    },
    {
        "slug": "COUPON2",
        "discount_type": "FIXED_PRICE",
        "discount_value": 25.0
    }
]
```

**Step 2: Apply Multiple Coupons**

```bash
PUT /v1/payments/bag/12345/coupon?coupons=COUPON1,COUPON2&plan=4geeks-plus-subscription
```

**Discount Calculation:**
- Original: $100
- COUPON1 (10% off): $90
- COUPON2 ($25 off): $65
- Final: $65

---

### Use Case 9: Error Handling Examples

**Invalid Coupon Code:**

```bash
GET /v1/payments/coupon?coupons=INVALID&plan=4geeks-plus-subscription
```

**Response (200 OK - Empty Array):**
```json
[]
```

**Frontend should show**: "This coupon is invalid or doesn't work for the 4Geeks Plus Subscription plan."

**Expired Coupon:**

```bash
GET /v1/payments/coupon?coupons=EXPIRED2024&plan=4geeks-plus-subscription
```

**Response (200 OK - Empty Array):**
```json
[]
```

**Coupon Usage Limit Reached:**

```bash
GET /v1/payments/coupon?coupons=LIMITED50&plan=4geeks-plus-subscription
```

**Response (200 OK - Empty Array):**
```json
[]
```

**Plan Doesn't Belong to Academy (Academy Endpoint):**

```bash
POST /v1/payments/academy/coupon
{
    "slug": "test",
    "plans": [999]  // Plan from different academy
}
```

**Response (403 Forbidden):**
```json
{
    "detail": "Plan 999 does not belong to this academy",
    "slug": "plan-not-belonging-to-academy"
}
```

**Bag Not Found:**

```bash
PUT /v1/payments/bag/99999/coupon?coupons=TEST&plan=4geeks-plus-subscription
```

**Response (404 Not Found):**
```json
{
    "detail": "Bag not found",
    "slug": "bag-not-found"
}
```

**Unauthorized Access:**

```bash
GET /v1/payments/academy/coupon
# Missing Academy header or insufficient permissions
```

**Response (403 Forbidden):**
```json
{
    "detail": "You don't have permission to perform this action."
}
```

---

## Additional API Examples

### Example 1: Validate and Apply Coupon

```bash
# 1. Validate coupon
curl "https://api.4geeks.com/v1/payments/coupon?coupons=summer-2025&plan=4geeks-plus-subscription"

# 2. Apply to bag
curl -X PUT "https://api.4geeks.com/v1/payments/bag/123/coupon?coupons=summer-2025&plan=4geeks-plus-subscription" \
  -H "Authorization: Token abc123"
```

### Example 2: Academy Creates Coupon

```bash
curl -X POST "https://api.4geeks.com/v1/payments/academy/coupon" \
  -H "Authorization: Token abc123" \
  -H "Academy: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "academy-special",
    "discount_type": "PERCENT_OFF",
    "discount_value": 0.15,
    "referral_type": "NO_REFERRAL",
    "referral_value": 0.0,
    "plans": [1, 2],
    "expires_at": "2025-12-31T23:59:59Z"
  }'
```

### Example 3: Academy Lists Coupons with Filtering

```bash
# List all academy coupons
curl -X GET "https://api.4geeks.com/v1/payments/academy/coupon" \
  -H "Authorization: Token abc123" \
  -H "Academy: 1"

# Filter by plan
curl -X GET "https://api.4geeks.com/v1/payments/academy/coupon?plan=4geeks-plus-subscription" \
  -H "Authorization: Token abc123" \
  -H "Academy: 1"

# Search by slug
curl -X GET "https://api.4geeks.com/v1/payments/academy/coupon?like=summer" \
  -H "Authorization: Token abc123" \
  -H "Academy: 1"
```

---

## Best Practices

### Coupon Design

1. **Use Descriptive Slugs**: Make slugs memorable and campaign-specific
   - Good: `summer-2025-25off`
   - Bad: `coupon-123`

2. **Set Expiration Dates**: Always set `expires_at` for promotional coupons
   - Prevents accidental long-term discounts
   - Creates urgency for users

3. **Limit Usage**: Set `how_many_offers` for limited promotions
   - Prevents abuse
   - Creates scarcity

4. **Plan Restrictions**: Use `plans` field for plan-specific offers
   - More targeted promotions
   - Better control over discount application

### Security

1. **Slug Uniqueness**: System validates slug uniqueness automatically
2. **User Restrictions**: Use `allowed_user` for personalized offers
3. **Seller Validation**: Sellers cannot use their own referral coupons
4. **Expiration Checks**: Always validate expiration before applying

### Performance

1. **Caching**: Coupon validation results can be cached on the client side
2. **Batch Validation**: Validate multiple coupons in a single API call (comma-separated slugs)
3. **Efficient Filtering**: Use query parameters to filter coupons server-side

### Referral Programs

1. **Empty Plans**: Referral coupons should have empty `plans` field
2. **Plan Exclusions**: Use `plan.exclude_from_referral_program` to opt-out
3. **Commission Tracking**: Track commissions separately from discounts
4. **Seller Management**: Auto-create sellers for users requesting referral coupons

---

## Troubleshooting

### Issue: Coupon Not Validating

**Checklist:**
1. Is coupon expired? (`expires_at` in past)
2. Has offer started? (`offered_at` in future)
3. Usage limit reached? (`how_many_offers` = 0)
4. Plan restriction? (Plan not in `coupon.plans`)
5. User restriction? (`allowed_user` set to different user)
6. User is seller? (Sellers can't use own coupons)

### Issue: Discount Not Applying

**Check:**
1. Coupon validated successfully?
2. Coupon added to bag?
3. Price calculation includes coupons?
4. Multiple coupons exceeding max allowed?

### Issue: Auto-Applied Coupon Not Showing

**Check:**
1. `auto=True` set?
2. Coupon valid for the plan?
3. Not expired?
4. Usage limit not reached?
5. User restrictions met?

### Issue: Referral Coupon Not Working

**Requirements:**
1. `referral_type != NO_REFERRAL`
2. `plans` field is empty
3. Plan doesn't have `exclude_from_referral_program=True`
4. User is not the seller
5. `referral_value` is set correctly

---

## Integration Points

### Bag System

- Coupons stored on `Bag.coupons` during checkout
- Applied during price calculation
- Persisted to Subscription/PlanFinancing on payment

### Subscription System

- Coupons copied from Bag to Subscription on creation
- Excluded from renewals if expired or referral type
- Used for renewal price calculations

### Plan Financing

- Coupons copied from Bag to PlanFinancing on creation
- Applied to initial payment
- Not applied to installments

### Notification System

- Coupon validation errors sent to users
- Referral commission notifications to sellers
- Expiration reminders (if implemented)

---

## Future Enhancements

### Potential Features

1. **Coupon Categories**
   - Group coupons by type
   - Category-based filtering

2. **Stacking Rules**
   - Define which coupons can be combined
   - Priority ordering

3. **Minimum Purchase Requirements**
   - Require minimum amount before coupon applies
   - Tiered discounts

4. **First-Time User Coupons**
   - Auto-apply for new users
   - One-time use enforcement

5. **Bulk Coupon Generation**
   - Generate multiple unique coupons
   - Campaign management

6. **Analytics Dashboard**
   - Usage statistics
   - Revenue impact
   - Conversion tracking

---

## Summary

The **Coupon** system provides a flexible, powerful discount and referral management solution for the BreatheCode platform. It supports:

- **Multiple discount types** (percentage, fixed, none)
- **Referral programs** with seller commissions
- **Time-based validity** with offer and expiration dates
- **Usage limits** for controlled promotions
- **User restrictions** for personalized offers
- **Auto-application** for seamless user experience
- **Plan scoping** for targeted discounts
- **Academy management** for plan-specific coupons

The system integrates seamlessly with the Bag, Subscription, and PlanFinancing systems, ensuring discounts are properly applied and tracked throughout the payment lifecycle.

