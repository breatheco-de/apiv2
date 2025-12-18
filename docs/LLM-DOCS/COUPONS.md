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

## Models

### Coupon

The core model representing a discount or referral coupon.

```python
class Coupon(models.Model):
    # Identification
    slug = models.SlugField()  # Unique identifier (e.g., "new-year-50")
    
    # Discount Configuration
    discount_type = models.CharField(choices=Discount)  # PERCENT_OFF, FIXED_PRICE, NO_DISCOUNT, HAGGLING
    discount_value = models.FloatField()  # Percentage (0-1) or fixed amount
    
    # Referral Configuration
    referral_type = models.CharField(choices=Referral)  # NO_REFERRAL, PERCENTAGE, FIXED_PRICE
    referral_value = models.FloatField(default=0)  # Commission amount for seller
    
    # Behavior
    auto = models.BooleanField(default=False)  # Automatically apply during checkout
    how_many_offers = models.IntegerField(default=-1)  # -1 = unlimited, 0 = disabled, >0 = limit
    
    # Relationships
    seller = models.ForeignKey(Seller, null=True)  # Referral seller
    allowed_user = models.ForeignKey(User, null=True)  # User restriction
    referred_buyer = models.ForeignKey(User, null=True)  # Buyer who activated reward
    plans = models.ManyToManyField(Plan, blank=True)  # Plan restrictions
    
    # Validity
    offered_at = models.DateTimeField(null=True)  # When offer becomes available
    expires_at = models.DateTimeField(null=True)  # When offer expires
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Discount Types:**
- `PERCENT_OFF`: Percentage discount (discount_value is 0-1, e.g., 0.5 = 50% off)
- `FIXED_PRICE`: Fixed price discount (discount_value is absolute amount)
- `NO_DISCOUNT`: No discount applied
- `HAGGLING`: Special haggling type

**Referral Types:**
- `NO_REFERRAL`: Regular coupon, no seller commission
- `PERCENTAGE`: Seller receives percentage commission
- `FIXED_PRICE`: Seller receives fixed commission amount

**Key Behaviors:**
- Slug uniqueness validated (no duplicate active coupons)
- Auto-updates `offered_at` when `how_many_offers` changes
- Validates discount/referral value consistency
- Prevents auto-apply with NO_DISCOUNT type

**Validation Rules:**
- `discount_value` must be positive
- `referral_value` must be positive
- If `referral_type != NO_REFERRAL`, `referral_value` must be set
- If `referral_type == NO_REFERRAL`, `referral_value` must be 0
- If `auto == True`, `discount_type` cannot be `NO_DISCOUNT`
- If `referral_type != NO_REFERRAL`, `plans` should be empty (applies to all plans)

**Static Method:**
```python
Coupon.generate_coupon_key(length=8, prefix=None)
```
Generates a unique, readable coupon slug using ambiguity-free characters.

### Seller

Represents a referral partner who can earn commissions.

```python
class Seller(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, null=True)
    type = models.CharField(choices=Partner)  # INDIVIDUAL, COMPANY
    is_active = models.BooleanField(default=True)
```

**Partner Types:**
- `INDIVIDUAL`: Individual referral partner
- `COMPANY`: Company referral partner

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

## Actions

Located in `actions.py`, these functions encapsulate core coupon business logic.

### `get_available_coupons(plan, coupons=None, user=None, only_sent_coupons=False)`

Validates and filters coupons for a specific plan.

**Parameters:**
- `plan`: Plan instance
- `coupons`: Optional list of coupon slugs to validate
- `user`: Optional user for ownership/restriction checks
- `only_sent_coupons`: If True, only return coupons that were sent to users

**Process:**
1. Filters by expiration (`expires_at` is None or in future)
2. Filters by offer date (`offered_at` is None or in past)
3. Checks usage limits (`how_many_offers`)
4. Validates plan restrictions:
   - If coupon has plans, plan must be in the list
   - If coupon has no plans, it's global (applies to all)
5. Excludes coupons where user is the seller
6. Validates user restrictions (`allowed_user`)
7. Validates referral program exclusions

**Returns**: List of valid `Coupon` objects

### `get_discounted_price(price, coupons)`

Calculates final price after applying coupons.

**Process:**
1. Filters coupons eligible for the plan
2. Applies discounts in order:
   - Percentage discounts applied first
   - Fixed price discounts applied after
3. Ensures price doesn't go below 0

**Returns**: Final discounted price (float)

**Example:**
```python
price = 100.0
coupons = [Coupon(discount_type="PERCENT_OFF", discount_value=0.2)]  # 20% off
final_price = get_discounted_price(price, coupons)  # 80.0
```

### `get_coupons_for_plan(plan, coupons)`

Filters coupons that are eligible for a given plan.

**Rules:**
- If `coupon.plans` is empty → global coupon, applies to all plans
- If `coupon.plans` is not empty → applies only if plan is in the list

**Returns**: List of eligible coupons

### `max_coupons_allowed()`

Returns the maximum number of coupons that can be applied to a single purchase.

**Default**: 1 (can be configured via environment or settings)

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

```python
discounted_price = original_price * (1 - discount_value)
```

**Example:**
- Original: $100
- Discount: 20% (discount_value = 0.2)
- Final: $80

### Fixed Price Discount

```python
discounted_price = original_price - discount_value
```

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
```python
commission = purchase_amount * referral_value
```

**Fixed Commission:**
```python
commission = referral_value
```

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
```python
coupon.plans.add(plan1, plan2)  # Only works for plan1 and plan2
```

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

## Serializers

### Read Serializers (Serpy)

**GetCouponSerializer:**
```python
{
    "slug": "new-year-50",
    "discount_type": "PERCENT_OFF",
    "discount_value": 0.5,
    "referral_type": "NO_REFERRAL",
    "referral_value": 0.0,
    "auto": true,
    "allowed_user": {...},  // Optional
    "offered_at": "2025-02-04T22:04:29Z",
    "expires_at": "2026-10-06T17:52:36Z"
}
```

**GetCouponWithPlansSerializer:**
Includes `plans` array with plan details.

### Write Serializers (DRF)

**CouponSerializer:**
- Handles ManyToMany `plans` field
- Validates all coupon fields
- Supports create and update operations

**Fields:**
- `slug` (required)
- `discount_type` (required)
- `discount_value` (required)
- `referral_type` (required)
- `referral_value` (required)
- `auto` (optional)
- `how_many_offers` (optional)
- `plans` (optional, list of plan IDs/slugs)
- `offered_at` (optional)
- `expires_at` (optional)
- `allowed_user` (optional)
- `seller` (optional)
- `referred_buyer` (optional)

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

## Usage Examples

### Example 1: Create a Percentage Discount Coupon

```python
from breathecode.payments.models import Coupon, Plan

coupon = Coupon.objects.create(
    slug="summer-2025",
    discount_type=Coupon.Discount.PERCENT_OFF,
    discount_value=0.25,  # 25% off
    referral_type=Coupon.Referral.NO_REFERRAL,
    referral_value=0.0,
    auto=False,
    how_many_offers=100,  # Limit to 100 uses
    offered_at=timezone.now(),
    expires_at=timezone.now() + timedelta(days=90)
)

# Restrict to specific plans
plan1 = Plan.objects.get(slug="4geeks-plus-subscription")
plan2 = Plan.objects.get(slug="4geeks-pro-subscription")
coupon.plans.add(plan1, plan2)
```

### Example 2: Create an Auto-Applied Promotional Coupon

```python
coupon = Coupon.objects.create(
    slug="new-year-50",
    discount_type=Coupon.Discount.PERCENT_OFF,
    discount_value=0.5,  # 50% off
    referral_type=Coupon.Referral.NO_REFERRAL,
    referral_value=0.0,
    auto=True,  # Auto-apply during checkout
    how_many_offers=-1,  # Unlimited
    expires_at=timezone.now() + timedelta(days=30)
)
# No plans restriction = applies to all plans
```

### Example 3: Create a Referral Coupon

```python
from breathecode.payments.models import Seller

seller = Seller.objects.get(user=user)
coupon = Coupon.objects.create(
    slug=f"referral-{user.id}",
    discount_type=Coupon.Discount.PERCENT_OFF,
    discount_value=0.1,  # 10% discount for buyer
    referral_type=Coupon.Referral.PERCENTAGE,
    referral_value=0.1,  # 10% commission for seller
    auto=False,
    seller=seller,
    how_many_offers=-1
)
# No plans restriction = applies to all plans (unless plan excludes referrals)
```

### Example 4: Create a User-Specific Reward Coupon

```python
user = User.objects.get(email="student@example.com")
coupon = Coupon.objects.create(
    slug="reward-student-123",
    discount_type=Coupon.Discount.FIXED_PRICE,
    discount_value=50.0,  # $50 off
    referral_type=Coupon.Referral.NO_REFERRAL,
    referral_value=0.0,
    allowed_user=user,  # Only this user can use it
    auto=False,
    how_many_offers=1  # One-time use
)
```

### Example 5: Validate and Apply Coupon via API

```bash
# 1. Validate coupon
curl "https://api.4geeks.com/v1/payments/coupon?coupons=summer-2025&plan=4geeks-plus-subscription"

# 2. Apply to bag
curl -X PUT "https://api.4geeks.com/v1/payments/bag/123/coupon?coupons=summer-2025&plan=4geeks-plus-subscription" \
  -H "Authorization: Token abc123"
```

### Example 6: Academy Creates Coupon

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

### Example 7: Calculate Discounted Price

```python
from breathecode.payments.actions import get_discounted_price, get_available_coupons
from breathecode.payments.models import Plan, Coupon

plan = Plan.objects.get(slug="4geeks-plus-subscription")
original_price = 100.0

# Get valid coupons
coupons = get_available_coupons(
    plan=plan,
    coupons=["summer-2025"],
    user=request.user
)

# Calculate discounted price
discounted_price = get_discounted_price(original_price, coupons)
print(f"Original: ${original_price}, Discounted: ${discounted_price}")
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

1. **Caching**: Coupon validation results can be cached
2. **Query Optimization**: Use `select_related` for plan lookups
3. **Batch Operations**: Validate multiple coupons in single query

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
3. `get_discounted_price` called correctly?
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

## Frontend Integration Guide

### React/TypeScript Example

```typescript
// Coupon validation hook
const useCouponValidation = () => {
  const validateCoupon = async (couponCode: string, planSlug: string) => {
    try {
      const response = await fetch(
        `/v1/payments/coupon?coupons=${couponCode}&plan=${planSlug}`
      );
      const coupons = await response.json();
      
      if (coupons.length === 0) {
        return {
          valid: false,
          error: "This coupon is invalid or doesn't work for this plan."
        };
      }
      
      return {
        valid: true,
        coupon: coupons[0]
      };
    } catch (error) {
      return {
        valid: false,
        error: "Failed to validate coupon. Please try again."
      };
    }
  };
  
  return { validateCoupon };
};

// Apply coupon to bag
const applyCouponToBag = async (
  bagId: number,
  couponCode: string,
  planSlug: string
) => {
  const response = await fetch(
    `/v1/payments/bag/${bagId}/coupon?coupons=${couponCode}&plan=${planSlug}`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Token ${userToken}`
      }
    }
  );
  
  if (!response.ok) {
    throw new Error('Failed to apply coupon');
  }
  
  return await response.json();
};

// Component example
const CouponInput = ({ bagId, planSlug, onCouponApplied }) => {
  const [couponCode, setCouponCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { validateCoupon } = useCouponValidation();
  
  const handleApply = async () => {
    setLoading(true);
    setError(null);
    
    // Step 1: Validate
    const validation = await validateCoupon(couponCode, planSlug);
    
    if (!validation.valid) {
      setError(validation.error);
      setLoading(false);
      return;
    }
    
    // Step 2: Apply to bag
    try {
      const bag = await applyCouponToBag(bagId, couponCode, planSlug);
      onCouponApplied(bag);
      setCouponCode('');
    } catch (err) {
      setError('Failed to apply coupon');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div>
      <input
        value={couponCode}
        onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
        placeholder="Enter coupon code"
      />
      <button onClick={handleApply} disabled={loading}>
        {loading ? 'Applying...' : 'Apply Coupon'}
      </button>
      {error && <div className="error">{error}</div>}
    </div>
  );
};
```

### Vue.js Example

```javascript
// Composable for coupon management
export const useCoupons = () => {
  const validateCoupon = async (code, planSlug) => {
    const { data } = await $fetch(
      `/v1/payments/coupon?coupons=${code}&plan=${planSlug}`
    );
    return data.length > 0;
  };
  
  const applyCoupon = async (bagId, code, planSlug) => {
    return await $fetch(
      `/v1/payments/bag/${bagId}/coupon?coupons=${code}&plan=${planSlug}`,
      { method: 'PUT' }
    );
  };
  
  return { validateCoupon, applyCoupon };
};

// Component
<template>
  <div class="coupon-input">
    <input
      v-model="couponCode"
      @keyup.enter="handleApply"
      placeholder="Coupon code"
    />
    <button @click="handleApply" :disabled="loading">
      Apply
    </button>
    <div v-if="error" class="error">{{ error }}</div>
  </div>
</template>

<script setup>
const couponCode = ref('');
const loading = ref(false);
const error = ref(null);
const { validateCoupon, applyCoupon } = useCoupons();

const handleApply = async () => {
  loading.value = true;
  error.value = null;
  
  const isValid = await validateCoupon(couponCode.value, planSlug.value);
  if (!isValid) {
    error.value = "Invalid coupon code";
    loading.value = false;
    return;
  }
  
  try {
    await applyCoupon(bagId.value, couponCode.value, planSlug.value);
    couponCode.value = '';
  } catch (err) {
    error.value = "Failed to apply coupon";
  } finally {
    loading.value = false;
  }
};
</script>
```

### Error Handling Best Practices

```typescript
// Centralized error handling
const COUPON_ERRORS = {
  'not-found': 'Coupon not found',
  'plan-not-found': 'Plan not found',
  'plan-not-belonging-to-academy': 'This coupon is not available for this plan',
  'invalid-referral-coupon-with-plans': 'Referral coupons cannot be restricted to specific plans',
  'bag-not-found': 'Shopping bag not found',
  'timeout': 'Request timed out. Please try again.'
};

const handleCouponError = (error: any) => {
  const slug = error?.slug || 'unknown';
  return COUPON_ERRORS[slug] || 'An error occurred. Please try again.';
};
```

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

