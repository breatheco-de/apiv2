# Academy Plans Management API

This document provides comprehensive information about managing payment plans, services, and service items in BreatheCode. Plans are the foundation of the payment system, allowing academies to sell access to cohorts, mentorships, events, and other resources.

## Overview

### What are Plans?

**Plans** are subscription or financing packages that bundle multiple services together for purchase. They define:
- What services students get access to
- How much it costs
- Payment frequency (monthly, quarterly, yearly)
- Whether it's a subscription (renewable) or one-time financing
- Trial periods and lifetime limits

### Core Concepts

```
Academy
  └── Plan
      ├── Service Items (what's included)
      │   └── Service (e.g., "Mentorship", "AI Chat", "Code Reviews")
      ├── Financing Options (payment methods)
      ├── Cohort Set (which cohorts)
      ├── Pricing (by time period and country)
      └── Subscription/Financing (how customers pay)
```

### Business Models

1. **Subscription** (`is_renewable=true`)
   - Auto-renewing monthly/quarterly/yearly
   - Continuous access as long as paid
   - Can be canceled anytime
   - Example: Monthly SaaS subscription

2. **Plan Financing** (`is_renewable=false`)
   - Fixed number of installments
   - Access until completion
   - Certificate after final payment
   - Example: Bootcamp tuition in 12 monthly payments

---

## Plan Management Endpoints

### 1. List Plans

**Endpoint:** `GET /v1/payments/academy/plan`

**Authentication:** Required - `read_subscription` capability

**Headers:**
- `Academy: {academy_id}` - Required
- `Authorization: Token {your-token}` - Required

**Query Parameters:**
- `cohort={cohort_id}` - Filter by cohort
- `syllabus={syllabus_slug}` - Filter by syllabus  
- `service_slug={slug}` - Filter by service
- `currency__code={code}` - Filter by currency (e.g., "USD", "EUR")
- `is_onboarding={true/false}` - Filter onboarding plans
- `country_code={code}` - Get pricing adjusted for country (e.g., "US", "ES")
- `status={status}` - Filter by status (DRAFT, ACTIVE, UNLISTED, DELETED)
- `limit={number}` - Results per page
- `offset={number}` - Pagination offset

**Response:**
```json
[
  {
    "id": 123,
    "slug": "premium-bootcamp",
    "title": "Premium Web Development Bootcamp",
    "status": "ACTIVE",
    "is_renewable": false,
    "is_onboarding": true,
    "has_waiting_list": false,
    "time_of_life": 6,
    "time_of_life_unit": "MONTH",
    "trial_duration": 7,
    "trial_duration_unit": "DAY",
    "price_per_half": 3500.00,
    "price_per_month": 299.00,
    "price_per_quarter": 799.00,
    "price_per_year": 2999.00,
    "currency": {
      "code": "USD",
      "name": "US Dollar"
    },
    "owner": {
      "id": 1,
      "name": "4Geeks Academy",
      "slug": "4geeks"
    },
    "service_items": [
      {
        "id": 45,
        "unit_type": "UNIT",
        "how_many": -1,
        "sort_priority": 1,
        "service": {
          "id": 12,
          "slug": "course-certificates",
          "title": "Earn course certificates",
          "type": "COHORT_SET",
          "consumer": "NO_SET"
        }
      }
    ],
    "financing_options": [
      {
        "id": 10,
        "monthly_price": 299.00,
        "how_many_months": 12,
        "currency": {
          "code": "USD"
        }
      }
    ],
    "cohort_set": {
      "id": 5,
      "slug": "full-stack-bootcamp",
      "cohorts": [...]
    }
  }
]
```

**Example Requests:**

Get all active plans:
```bash
GET /v1/payments/academy/plan?status=ACTIVE
Headers:
  Academy: 1
  Authorization: Token {token}
```

Get plans for specific cohort:
```bash
GET /v1/payments/academy/plan?cohort=123
Headers:
  Academy: 1
```

Get pricing for Spain:
```bash
GET /v1/payments/academy/plan?country_code=ES
Headers:
  Academy: 1
```

---

### 2. Get Single Plan

**Endpoint:** `GET /v1/payments/academy/plan/{plan_id}`  
**Or:** `GET /v1/payments/academy/plan/{plan_slug}`

**Authentication:** Required - `read_subscription` capability

**Response:** Single plan object (same structure as list)

**Example:**
```bash
GET /v1/payments/academy/plan/premium-bootcamp
Headers:
  Academy: 1
  Authorization: Token {token}
```

---

### 3. Create Plan

**Endpoint:** `POST /v1/payments/academy/plan`

**Authentication:** Required - `crud_subscription` capability

**Headers:**
- `Academy: {academy_id}` - Required
- `Authorization: Token {your-token}` - Required

**Request Body:**
```json
{
  "slug": "premium-bootcamp-2025",
  "title": "Premium Web Development Bootcamp 2025",
  "currency": "USD",
  "status": "DRAFT",
  "is_renewable": false,
  "is_onboarding": true,
  "has_waiting_list": false,
  "time_of_life": 6,
  "time_of_life_unit": "MONTH",
  "trial_duration": 7,
  "trial_duration_unit": "DAY",
  "price_per_half": 3500.00,
  "price_per_month": 299.00,
  "price_per_quarter": 799.00,
  "price_per_year": 2999.00,
  "cohort_set": 5,
  "financing_options": [10, 11],
  "consumption_strategy": "PER_SEAT"
}
```

**Required Fields:**
- `slug` (string) - Unique identifier (letters, numbers, hyphens only)
- `currency` (string) - Currency code (e.g., "USD", "EUR")

**Optional Fields:**
- `title` (string) - Display name
- `status` (string) - DRAFT, ACTIVE, UNLISTED, DELETED (default: DRAFT)
- `is_renewable` (boolean) - True for subscriptions, false for financing (default: true)
- `is_onboarding` (boolean) - Onboarding plan flag (default: false)
- `has_waiting_list` (boolean) - Enable waiting list (default: false)
- `exclude_from_referral_program` (boolean) - Disable referral coupons (default: true)
- `time_of_life` (integer) - How long plan lasts (default: 1)
- `time_of_life_unit` (string) - DAY, WEEK, MONTH, YEAR (default: MONTH)
- `trial_duration` (integer) - Trial period length (default: 1)
- `trial_duration_unit` (string) - DAY, WEEK, MONTH, YEAR (default: MONTH)
- `price_per_half` (float) - Semi-annual price
- `price_per_month` (float) - Monthly price
- `price_per_quarter` (float) - Quarterly price
- `price_per_year` (float) - Annual price
- `cohort_set` (integer) - CohortSet ID
- `mentorship_service_set` (integer) - MentorshipServiceSet ID
- `event_type_set` (integer) - EventTypeSet ID
- `financing_options` (array) - Array of FinancingOption IDs
- `consumption_strategy` (string) - PER_TEAM, PER_SEAT, BOTH (default: PER_SEAT)
- `seat_service_price` (integer) - AcademyService ID for seat pricing
- `pricing_ratio_exceptions` (object) - Country-specific pricing adjustments

**Response:** Created plan object (201 status)

**Notes:**
- `owner` is automatically set to the academy from the header
- Cannot set `owner` or `owner_id` manually
- Plan starts in DRAFT status unless specified
- Set status to ACTIVE when ready to sell

---

### 4. Update Plan

**Endpoint:** `PUT /v1/payments/academy/plan/{plan_id}`  
**Or:** `PUT /v1/payments/academy/plan/{plan_slug}`

**Authentication:** Required - `crud_subscription` capability

**Request Body:** Same fields as POST (partial updates supported)

**Example - Activate a Plan:**
```bash
PUT /v1/payments/academy/plan/premium-bootcamp-2025
Headers:
  Academy: 1
  Authorization: Token {token}

Body:
{
  "status": "ACTIVE"
}
```

**Example - Update Pricing:**
```bash
PUT /v1/payments/academy/plan/123
Body:
{
  "price_per_month": 349.00,
  "price_per_year": 3499.00
}
```

**Restrictions:**
- Cannot change `owner` (plan remains with academy)
- Can only update plans owned by your academy or global plans

**Response:** Updated plan object (200 status)

---

### 5. Delete Plan (Soft Delete)

**Endpoint:** `DELETE /v1/payments/academy/plan/{plan_id}`  
**Or:** `DELETE /v1/payments/academy/plan/{plan_slug}`

**Authentication:** Required - `crud_subscription` capability

**Behavior:**
- Sets `status="DELETED"` (soft delete)
- Plan remains in database
- No longer visible in active listings
- Existing subscriptions continue

**Response:** 204 No Content

**Example:**
```bash
DELETE /v1/payments/academy/plan/old-plan-2024
Headers:
  Academy: 1
  Authorization: Token {token}
```

---

## Service Items Management

### What are Service Items?

Service Items define **what's included** in a plan:
- **How many units** of a service (e.g., 5 mentorships, unlimited AI chats)
- **What service** it provides (e.g., code reviews, live classes)
- **How it renews** (if renewable)

### Service Types

| Type | Description | Example |
|------|-------------|---------|
| `COHORT_SET` | Access to cohorts/courses | "Full Stack Bootcamp" |
| `MENTORSHIP_SERVICE_SET` | Mentorship sessions | "1-on-1 Expert Mentorship" |
| `EVENT_TYPE_SET` | Event access | "Workshops & Webinars" |
| `VOID` | Feature flags/capabilities | "AI Chat", "Code Reviews" |
| `SEAT` | Team seat pricing | "Team Member Seat" |

### Consumer Types (How Services Are Used)

| Consumer | Triggers When | Example |
|----------|--------------|---------|
| `ADD_CODE_REVIEW` | Requesting code review | Review on project |
| `LIVE_CLASS_JOIN` | Joining live class | Class attendance |
| `EVENT_JOIN` | Joining event | Workshop registration |
| `JOIN_MENTORSHIP` | Booking mentorship | Schedule session |
| `READ_LESSON` | Opening lesson | Lesson access |
| `AI_INTERACTION` | Using AI features | Chat, generation |
| `NO_SET` | Not consumed | Feature unlock |

### Unit Quantities

- **`-1`** = Unlimited/infinite
- **`0`** = None/disabled
- **Positive number** = Specific quantity (e.g., `5` = 5 units)

---

### 6. Add Service Items to Plan

**Endpoint:** `POST /v1/payments/academy/plan/serviceitem`

**Authentication:** Required - `crud_plan` capability

**Headers:**
- `Academy: {academy_id}` - Required
- `Authorization: Token {your-token}` - Required

**Request Body:**
```json
{
  "plan": 123,  // Plan ID or slug
  "service_item": 456  // ServiceItem ID, array, or comma-separated
}
```

**Variations:**

Single service item:
```json
{
  "plan": "premium-bootcamp",
  "service_item": 456
}
```

Multiple service items (array):
```json
{
  "plan": 123,
  "service_item": [456, 789, 101]
}
```

Multiple service items (comma-separated):
```json
{
  "plan": 123,
  "service_item": "456,789,101"
}
```

**Response:**
```json
{
  "status": "ok",
  "created_items": [
    {
      "plan_service_item_id": 1,
      "service_item_id": 456,
      "created": true
    },
    {
      "plan_service_item_id": 2,
      "service_item_id": 789,
      "created": false  // Already existed
    },
    {
      "plan_service_item_id": 3,
      "service_item_id": 101,
      "created": true
    }
  ],
  "total_created": 2
}
```

**Notes:**
- Uses `get_or_create()` - won't duplicate if already linked
- `created: false` means the link already existed

---

### 7. Remove Service Items from Plan

**Endpoint:** `DELETE /v1/payments/academy/plan/serviceitem`

**Authentication:** Required - `crud_plan` capability

**Request Body:**
```json
{
  "plan_service_item": 123  // PlanServiceItem ID(s)
}
```

**Variations:**

Single item:
```json
{
  "plan_service_item": 123
}
```

Multiple items (array):
```json
{
  "plan_service_item": [123, 456, 789]
}
```

Multiple items (comma-separated):
```json
{
  "plan_service_item": "123,456,789"
}
```

**Response:**
```json
{
  "status": "ok",
  "deleted_count": 3
}
```

---

### 8. View Service Items

**Endpoint:** `GET /v1/payments/serviceitem`

**Authentication:** Public (no auth required)

**Query Parameters:**
- `plan={plan_id or slug}` - Get items for specific plan
- `service_slug={slug}` - Filter by service
- `unit_type={type}` - Filter by unit type

**Response:**
```json
[
  {
    "id": 456,
    "unit_type": "UNIT",
    "how_many": -1,
    "sort_priority": 1,
    "is_renewable": true,
    "renew_at": 1,
    "renew_at_unit": "MONTH",
    "is_team_allowed": false,
    "service": {
      "id": 12,
      "slug": "ai-conversation-message",
      "title": "AI Chat Messages",
      "icon_url": "https://...",
      "type": "VOID",
      "consumer": "AI_INTERACTION",
      "private": true
    },
    "features": [
      {
        "lang": "en",
        "one_line_desc": "Chat with AI mentors",
        "description": "Get unlimited AI assistance..."
      }
    ]
  }
]
```

**Example:**
```bash
GET /v1/payments/serviceitem?plan=premium-bootcamp
```

---

## Pricing Configuration

### Price Fields

Plans support multiple pricing periods:

| Field | Description | Use Case |
|-------|-------------|----------|
| `price_per_month` | Monthly rate | Monthly subscriptions |
| `price_per_quarter` | Quarterly rate (3 months) | Quarterly billing |
| `price_per_half` | Semi-annual rate (6 months) | Semi-annual billing |
| `price_per_year` | Annual rate (12 months) | Yearly subscriptions |

**Example:**
```json
{
  "price_per_month": 299.00,
  "price_per_quarter": 799.00,    // ~11% discount
  "price_per_half": 1499.00,      // ~16% discount
  "price_per_year": 2999.00       // ~17% discount
}
```

### Country-Specific Pricing

Use `pricing_ratio_exceptions` for regional pricing:

```json
{
  "slug": "premium-bootcamp",
  "price_per_month": 299.00,
  "currency": "USD",
  "pricing_ratio_exceptions": {
    "ES": 0.85,  // 15% discount for Spain
    "MX": 0.70,  // 30% discount for Mexico
    "IN": 0.50   // 50% discount for India
  }
}
```

**How it works:**
- Base price: `$299/month`
- Spain: `$299 × 0.85 = $254.15/month`
- Mexico: `$299 × 0.70 = $209.30/month`
- India: `$299 × 0.50 = $149.50/month`

**Retrieving adjusted prices:**
```bash
GET /v1/payments/academy/plan?country_code=ES
```

---

## Financing Options

### What are Financing Options?

Financing options allow customers to pay in **installments** instead of upfront. Each academy can create and manage their own financing options.

### Ownership Model
- Each financing option belongs to a specific academy
- Academies can only view, edit, and delete their own financing options
- Global financing options (academy=None) can be viewed by all but only managed by staff

**Model Structure:**
```json
{
  "id": 10,
  "academy": {
    "id": 1,
    "name": "4Geeks Academy",
    "slug": "4geeks"
  },
  "monthly_price": 299.00,
  "how_many_months": 12,
  "currency": {
    "code": "USD",
    "name": "US Dollar"
  },
  "pricing_ratio_exceptions": {
    "MX": 0.70,
    "ES": 0.85
  }
}
```

### Managing Financing Options

#### List Financing Options
```bash
GET /v1/payments/academy/financingoption
  ?currency=USD           # Optional: filter by currency
  &how_many_months=12     # Optional: filter by months
Header: academy: 1
```

**Required Capability:** `read_subscription`

**Response:** Array of financing options (academy-owned + global)

#### Create Financing Option
```bash
POST /v1/payments/academy/financingoption
Header: academy: 1
Body:
{
  "monthly_price": 299.00,
  "how_many_months": 12,
  "currency": "USD",
  "pricing_ratio_exceptions": {
    "MX": 0.70,
    "ES": 0.85
  }
}
```

**Required Capability:** `crud_subscription`

**Notes:**
- Academy is set automatically based on header
- Currency must be a valid currency code

#### Update Financing Option
```bash
PUT /v1/payments/academy/financingoption/{financing_option_id}
Header: academy: 1
Body:
{
  "monthly_price": 349.00
}
```

**Required Capability:** `crud_subscription`

**Notes:**
- Can only update financing options owned by your academy
- Partial updates supported

#### Delete Financing Option
```bash
DELETE /v1/payments/academy/financingoption/{financing_option_id}
Header: academy: 1
```

**Required Capability:** `crud_subscription`

**Notes:**
- Can only delete financing options owned by your academy
- Cannot delete if used by any plans (returns 400 error)

### Common Configurations

**6-month financing:**
```json
{
  "monthly_price": 499.00,
  "how_many_months": 6,
  "currency": "USD"
}
```

**12-month financing with country pricing:**
```json
{
  "monthly_price": 299.00,
  "how_many_months": 12,
  "currency": "USD",
  "pricing_ratio_exceptions": {
    "MX": 0.70,  // 30% discount for Mexico
    "ES": 0.85   // 15% discount for Spain
  }
}
```

### Linking Financing Options to Plan

Include in plan creation/update:
```json
{
  "slug": "premium-bootcamp",
  "financing_options": [10, 11, 12],
  "is_renewable": false
}
```

**Customer selects at checkout:**
- System creates `PlanFinancing` record
- Monthly charges scheduled automatically
- Certificate issued after final payment

---

## Complete Plan Creation Workflow

### Step 1: Create Service Items (if needed)

Service items are usually pre-created by admins. To view available ones:

```bash
GET /v1/payments/serviceitem
```

### Step 2: Create the Plan

```bash
POST /v1/payments/academy/plan
Headers:
  Academy: 1
  Authorization: Token {token}

Body:
{
  "slug": "web-dev-bootcamp-2025",
  "title": "Web Development Bootcamp 2025",
  "currency": "USD",
  "status": "DRAFT",
  "is_renewable": false,
  "is_onboarding": true,
  "time_of_life": 6,
  "time_of_life_unit": "MONTH",
  "trial_duration": 0,
  "trial_duration_unit": "DAY",
  "price_per_month": 299.00,
  "price_per_quarter": 799.00,
  "price_per_year": 2499.00,
  "cohort_set": 5,
  "consumption_strategy": "PER_SEAT"
}
```

### Step 3: Add Service Items

```bash
POST /v1/payments/academy/plan/serviceitem
Headers:
  Academy: 1

Body:
{
  "plan": "web-dev-bootcamp-2025",
  "service_item": [45, 52, 93, 106]
}
```

### Step 4: Link Financing Options (Optional)

```bash
PUT /v1/payments/academy/plan/web-dev-bootcamp-2025
Body:
{
  "financing_options": [10, 11]
}
```

### Step 5: Activate the Plan

```bash
PUT /v1/payments/academy/plan/web-dev-bootcamp-2025
Body:
{
  "status": "ACTIVE"
}
```

### Step 6: Add Students with Plan

```bash
POST /v1/auth/academy/student
Headers:
  Academy: 1

Body:
{
  "email": "student@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "cohort": [1429],
  "invite": true,
  "plans": [123]  // Your plan ID
}
```

---

## Cohort Sets & Resource Linking

### What are Cohort Sets?

**Cohort Sets** group cohorts together so they can be sold as a package.

**Example:**
- CohortSet: "Full Stack Program"
  - Cohort: "Web Development Fundamentals"
  - Cohort: "Advanced JavaScript"
  - Cohort: "React & Backend"

### Manage Cohorts in Set

**Endpoint:** `PUT /v1/payments/academy/cohortset/{cohort_set_id}/cohort`

**Authentication:** Required - `crud_plan` capability

**Request Body:**
```json
{
  "cohorts": [123, 456, 789]  // Array of cohort IDs
}
```

**Use Case:**
When a student purchases a plan with this cohort set, they get access to all included cohorts.

---

## Service Management

BreatheCode uses a **two-tier service system**:

1. **Service** - Base service definitions (what services exist)
2. **AcademyService** - Academy-specific pricing and configuration (how to sell them)

This separation allows services to be shared across academies while maintaining academy-specific pricing.

### 🔄 Creation Flow (Important!)

**You must create Services BEFORE AcademyServices:**

```
Step 1: Service exists
   ├── Created by your academy (owner=your_academy)
   ├── Created by another academy (owner=other_academy) ← You can still use it!
   └── Global service (owner=None) ← Shared across all academies
        ↓
Step 2: Create AcademyService
   └── Links the Service to your academy with your pricing
```

**Example:**
- Academy A creates Service "AI Chat" (owner=Academy A)
- Academy B can create AcademyService using that same "AI Chat" service
- Each academy sets their own price, bundle size, and discounts

---

### Public Service Catalog

**Endpoint:** `GET /v1/payments/service`

This is a **public, unauthenticated endpoint** for browsing available services.

**Authentication:** ❌ Not required (but capability affects results)

**Query Parameters:**
- `group` - Filter by permission group name
- `cohort_slug` - Filter by cohort
- `mentorship_service_slug` - Filter by mentorship service
- `academy` - Optional academy ID (enables private service viewing if user has capability)

**Privacy Filtering:**
- **Without auth or capability:** Returns only `private=false` services
- **With `read_service` capability + academy ID:** Returns all services (including private)

**Example - Public Access:**
```bash
GET /v1/payments/service
# Returns only public services
```

**Example - With Capability:**
```bash
GET /v1/payments/service?academy=1
Authorization: Token {token}
# Returns all services if user has read_service capability
```

**Response:**
```json
[
  {
    "title": "AI Chat Messages",
    "slug": "ai-conversation-message",
    "owner": {
      "id": 1,
      "name": "4Geeks Academy",
      "slug": "4geeks"
    },
    "private": false,
    "groups": []
  }
]
```

**Use Case:**
- Students browsing available features
- Building public service catalogs
- Checking which services exist before creating AcademyService

---

### Part 1: Service Management (Base Services)

Services define **what features or resources** are available. They can be owned by an academy, another academy, or be global (owner=None).

**Key Points:**
- ✅ Services can be **reused across academies**
- ✅ One Service → Many AcademyServices (different academies, different pricing)
- ✅ Academy B can use services created by Academy A
- ✅ Global services (owner=None) are available to all academies

#### List Services

**Endpoint:** `GET /v1/payments/academy/service`

**Authentication:** Required - `read_service` capability

**Query Parameters:**
- `group` - Filter by permission group codename
- `cohort_slug` - Filter by cohort
- `mentorship_service_slug` - Filter by mentorship service

**Response:**
```json
[
  {
    "id": 12,
    "slug": "code-review-service",
    "title": "Code Review Service",
    "icon_url": "https://...",
    "type": "VOID",
    "consumer": "ADD_CODE_REVIEW",
    "private": true,
    "session_duration": null,
    "groups": [
      {
        "name": "Student",
        "permissions": [
          {
            "codename": "can_request_code_review",
            "name": "Can request code review"
          }
        ]
      }
    ]
  }
]
```

#### Get Single Service

**Endpoint:** `GET /v1/payments/academy/service/{service_slug}`

**Authentication:** Required - `read_service` capability

**Response:** Single service object (same structure as list)

#### Create Service

**Endpoint:** `POST /v1/payments/academy/service`

**Authentication:** Required - `crud_service` capability

**Request Body:**
```json
{
  "slug": "premium-mentorship",
  "title": "Premium Mentorship Sessions",
  "icon_url": "https://...",
  "type": "MENTORSHIP_SERVICE_SET",
  "consumer": "JOIN_MENTORSHIP",
  "private": true,
  "session_duration": "3600"
}
```

**Notes:**
- `owner` is automatically set to the academy from the header
- `slug` must be unique
- Service types: `COHORT_SET`, `MENTORSHIP_SERVICE_SET`, `EVENT_TYPE_SET`, `VOID`, `SEAT`

#### Update Service

**Endpoint:** `PUT /v1/payments/academy/service/{service_slug}`

**Authentication:** Required - `crud_service` capability

**Request Body:** Same fields as POST (partial updates supported)

**Notes:**
- Can only update services owned by your academy or global services

---

### Part 2: AcademyService Management (Pricing Configuration)

**AcademyService** defines **how an academy prices and sells** a specific service. It includes pricing, bundle sizes, discounts, and availability.

#### What is AcademyService?

AcademyService connects a Service to an Academy with specific pricing rules:
- **Price per unit** - How much one unit costs
- **Bundle size** - Minimum units that can be purchased
- **Max items** - Maximum quantity limit
- **Discount ratio** - Bulk purchase discounts
- **Country pricing** - Regional price adjustments
- **Availability** - Which mentorship/event/cohort sets can use it

#### List Academy Services

**Endpoint:** `GET /v1/payments/academy/academyservice`

**Authentication:** Required - `read_academyservice` capability

**Query Parameters:**
- `currency__code` - Filter by currency code (e.g., "USD")
- `mentorship_service_set` - Filter by mentorship set slug
- `event_type_set` - Filter by event type set slug
- `country_code` - Get country-adjusted pricing

**Response:**
```json
[
  {
    "id": 1,
    "academy": {
      "id": 1,
      "name": "4Geeks Academy",
      "slug": "4geeks"
    },
    "service": {
      "id": 12,
      "slug": "ai-conversation-message",
      "title": "AI Chat Messages",
      "type": "VOID",
      "consumer": "AI_INTERACTION"
    },
    "currency": {
      "code": "USD",
      "name": "US Dollar"
    },
    "price_per_unit": 0.10,
    "bundle_size": 100,
    "max_items": 10000,
    "max_amount": 1000.00,
    "discount_ratio": 0.90,
    "pricing_ratio_exceptions": {
      "MX": 0.70,
      "ES": 0.85
    },
    "available_mentorship_service_sets": [
      {
        "id": 1,
        "slug": "standard-mentorship",
        "name": "Standard Mentorship"
      }
    ],
    "available_event_type_sets": [],
    "available_cohort_sets": []
  }
]
```

#### Get Single Academy Service

**Endpoint:** `GET /v1/payments/academy/academyservice/{service_slug}`

**Authentication:** Required - `read_academyservice` capability

**Query Parameters:**
- `currency__code` - Specify currency (required if service has multiple)
- `country_code` - Get adjusted pricing for specific country

**Example:**
```bash
GET /v1/payments/academy/academyservice/ai-conversation-message
  ?currency__code=USD
  &country_code=ES
Headers:
  Academy: 1
  Authorization: Token {token}
```

#### Create Academy Service

**Endpoint:** `POST /v1/payments/academy/academyservice`

**Authentication:** Required - `crud_academyservice` capability

**Request Body:**
```json
{
  "service": 12,
  "currency": "USD",
  "price_per_unit": 0.10,
  "bundle_size": 100,
  "max_items": 10000,
  "max_amount": 1000.00,
  "discount_ratio": 0.90,
  "pricing_ratio_exceptions": {
    "MX": 0.70,
    "ES": 0.85
  },
  "available_mentorship_service_sets": [1, 2],
  "available_event_type_sets": [5],
  "available_cohort_sets": [10, 11]
}
```

**Field Descriptions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `service` | integer | ✅ Yes | Service ID to price |
| `currency` | string | ✅ Yes | Currency code (e.g., "USD") |
| `price_per_unit` | float | ✅ Yes | Price per single unit |
| `bundle_size` | float | No | Minimum units (default: 1) |
| `max_items` | float | No | Max quantity limit (default: 1) |
| `max_amount` | float | No | Max price limit (default: 1) |
| `discount_ratio` | float | No | Discount multiplier (default: 1.0) |
| `pricing_ratio_exceptions` | object | No | Country-specific ratios |
| `available_mentorship_service_sets` | array | No | Mentorship set IDs |
| `available_event_type_sets` | array | No | Event type set IDs |
| `available_cohort_sets` | array | No | Cohort set IDs |

**Notes:**
- `academy` is automatically set from the header
- `service` must be OneToOne per academy (one AcademyService per Service per Academy)

**Response:** `201 CREATED` with created AcademyService object

#### Update Academy Service

**Endpoint:** `PUT /v1/payments/academy/academyservice/{service_slug}`

**Authentication:** Required - `crud_academyservice` capability

**Request Body (partial updates supported):**
```json
{
  "price_per_unit": 0.12,
  "discount_ratio": 0.85,
  "pricing_ratio_exceptions": {
    "MX": 0.65,
    "ES": 0.80,
    "CO": 0.75
  }
}
```

**Example - Update Pricing:**
```bash
PUT /v1/payments/academy/academyservice/ai-conversation-message
Headers:
  Academy: 1
  Authorization: Token {token}

Body:
{
  "price_per_unit": 0.15,
  "max_items": 20000
}
```

---

### AcademyService Pricing Examples

#### Example 1: AI Chat Messages (Pay-per-use)
```json
{
  "service": 12,
  "currency": "USD",
  "price_per_unit": 0.01,
  "bundle_size": 100,
  "max_items": 50000,
  "max_amount": 500.00,
  "discount_ratio": 1.0
}
```
- Students buy in bundles of 100 messages
- Each message costs $0.01
- 100 messages = $1.00
- Maximum 50,000 messages ($500 limit)

#### Example 2: Mentorship Sessions (Bulk Discount)
```json
{
  "service": 25,
  "currency": "USD",
  "price_per_unit": 50.00,
  "bundle_size": 1,
  "max_items": 20,
  "max_amount": 800.00,
  "discount_ratio": 0.90
}
```
- Each session: $50
- Buy 10 sessions: $500 × 0.90 = $450 (10% discount)
- Maximum 20 sessions

#### Example 3: Regional Pricing
```json
{
  "service": 12,
  "currency": "USD",
  "price_per_unit": 1.00,
  "bundle_size": 10,
  "pricing_ratio_exceptions": {
    "MX": 0.70,
    "ES": 0.85,
    "IN": 0.50,
    "BR": 0.60
  }
}
```
- Base: $1.00 per unit
- Mexico: $0.70 (30% off)
- Spain: $0.85 (15% off)
- India: $0.50 (50% off)
- Brazil: $0.60 (40% off)

---

### Three Endpoints Comparison

| Aspect | Public `/service` | Academy `/academy/service` | Academy `/academy/academyservice` |
|--------|-------------------|---------------------------|-----------------------------------|
| **Purpose** | Browse available services | Manage service definitions | Configure academy pricing |
| **Auth Required** | ❌ No | ✅ Yes | ✅ Yes |
| **Capability** | Optional: `read_service` | `read_service` / `crud_service` | `read_academyservice` / `crud_academyservice` |
| **Shows Private** | Only with capability | ✅ Yes | N/A |
| **Has Pricing** | ❌ No | ❌ No | ✅ Yes |
| **Has Discounts** | ❌ No | ❌ No | ✅ Yes |
| **Can Create** | ❌ No | ✅ Yes | ✅ Yes |
| **Ownership** | Shows all public | Academy-owned or global | Always academy-specific |
| **Use Case** | Public catalog | Define services | Price services |

### Service → AcademyService Relationship

```
Service (Platform-wide)
├── ID: 12
├── Slug: "ai-conversation-message"
├── Owner: Academy A (or None for global)
├── Private: false
│
├── AcademyService (Academy A)
│   ├── Price: $0.01/unit
│   ├── Bundle: 100
│   └── Currency: USD
│
├── AcademyService (Academy B)
│   ├── Price: €0.015/unit
│   ├── Bundle: 50
│   └── Currency: EUR
│
└── AcademyService (Academy C)
    ├── Price: $0.02/unit
    ├── Bundle: 200
    └── Currency: USD
```

**Key Point:** One Service can have multiple AcademyServices (one per academy), each with different pricing!

---

### Complete Workflow

**Scenario:** Sell AI chat messages at your academy

#### Option A: Using Existing Service (Recommended)

1. **Browse available services (public endpoint):**
```bash
GET /v1/payments/service
# Check if "ai-conversation-message" already exists
```

2. **If service exists, create AcademyService with your pricing:**
```bash
POST /v1/payments/academy/academyservice
Headers:
  Academy: 1
  Authorization: Token {token}

Body: {
  "service": 12,  // Use existing service ID
  "currency": "USD",
  "price_per_unit": 0.01,
  "bundle_size": 100,
  "max_items": 50000
}
```

**Note:** The service can be owned by ANY academy or be global. You're just setting YOUR pricing!

---

#### Option B: Creating New Service

1. **Check if Service exists:**
```bash
GET /v1/payments/academy/service/ai-conversation-message
Headers:
  Academy: 1
  Authorization: Token {token}
```

2. **Create Service if it doesn't exist:**
```bash
POST /v1/payments/academy/service
Headers:
  Academy: 1
  Authorization: Token {token}

Body: {
  "slug": "ai-conversation-message",
  "title": "AI Chat Messages",
  "type": "VOID",
  "consumer": "AI_INTERACTION",
  "private": false  // Make it available to other academies
}
```

**Important:** `owner` is automatically set to YOUR academy, but other academies can still use it!

3. **Now create AcademyService (your pricing):**
```bash
POST /v1/payments/academy/academyservice
Body: {
  "service": 12,  // ID from service you just created
  "currency": "USD",
  "price_per_unit": 0.01,
  "bundle_size": 100,
  "max_items": 50000
}
```

---

#### Remaining Steps (Both Options)

4. **Create ServiceItem (define quantity):**
```bash
# ServiceItems define "how many" units in a plan
# Typically created by platform staff via Django admin
# Links Service → Plan with quantity (-1 = unlimited)
```

5. **Add ServiceItem to Plan:**
```bash
POST /v1/payments/academy/plan/serviceitem
Body: {
  "plan": "premium-plan",
  "service_item": [45, 93]
}
```

6. **Students purchase plan → Get consumables**

---

### Cross-Academy Service Sharing Example

**Academy A creates a service:**
```bash
# Academy A
POST /v1/payments/academy/service
Headers: {Academy: 1}
Body: {
  "slug": "live-code-review",
  "title": "Live Code Review Sessions",
  "type": "VOID",
  "consumer": "ADD_CODE_REVIEW",
  "private": false
}
# → Service ID: 50, owner: Academy A
```

**Academy B uses the same service with different pricing:**
```bash
# Academy B (different academy!)
POST /v1/payments/academy/academyservice
Headers: {Academy: 2}
Body: {
  "service": 50,  // ← Using Academy A's service!
  "currency": "EUR",
  "price_per_unit": 25.00,
  "bundle_size": 1
}
```

**Academy C also uses it:**
```bash
# Academy C
POST /v1/payments/academy/academyservice
Headers: {Academy: 3}
Body: {
  "service": 50,  // ← Same service, different academy pricing
  "currency": "USD",
  "price_per_unit": 30.00,
  "bundle_size": 1
}
```

**Result:**
- One Service (ID: 50, owned by Academy A)
- Three AcademyServices (Academy A, B, C each with own pricing)
- Students at each academy pay their academy's rate

---

## Plan Status Lifecycle

### Status Flow

```
DRAFT → ACTIVE → UNLISTED → DELETED
  ↓       ↓
  └───────┘
(can publish anytime)
```

### Status Definitions

| Status | Visible to Customers | Can Purchase | Use Case |
|--------|---------------------|--------------|----------|
| `DRAFT` | ❌ No | ❌ No | Work in progress |
| `ACTIVE` | ✅ Yes | ✅ Yes | Currently selling |
| `UNLISTED` | ❌ No (direct link only) | ✅ Yes | Private offers |
| `DELETED` | ❌ No | ❌ No | Discontinued |
| `DISCONTINUED` | ❌ No | ❌ No | Deprecated |

### Workflow Examples

**Launch new plan:**
```bash
# 1. Create in DRAFT
POST /v1/payments/academy/plan
Body: {"slug": "...", "status": "DRAFT"}

# 2. Add service items, test

# 3. Activate when ready
PUT /v1/payments/academy/plan/123
Body: {"status": "ACTIVE"}
```

**Limited time offer:**
```bash
# 1. Create ACTIVE plan
# 2. After promotion ends:
PUT /v1/payments/academy/plan/black-friday-2025
Body: {"status": "UNLISTED"}  // Existing customers keep access
```

**Retire old plan:**
```bash
DELETE /v1/payments/academy/plan/old-plan-2024
# Sets status="DELETED"
```

---

## Consumption Strategies

### What is Consumption Strategy?

Defines how service items are consumed in team scenarios.

| Strategy | Behavior | Use Case |
|----------|----------|----------|
| `PER_SEAT` | Each team member consumes separately | Individual student plans |
| `PER_TEAM` | Entire team shares consumables | Corporate team plans |
| `BOTH` | Mix of shared and individual | Hybrid plans |

**Example - Per Seat:**
```json
{
  "consumption_strategy": "PER_SEAT",
  "service_items": [
    {"service": "ai-chat", "how_many": 1000}
  ]
}
```
- 5 team members = 5,000 total messages (1,000 each)

**Example - Per Team:**
```json
{
  "consumption_strategy": "PER_TEAM",
  "service_items": [
    {"service": "mentorship", "how_many": 10}
  ]
}
```
- 5 team members = 10 total mentorships (shared pool)

---

## Trial Periods

### Configuring Trials

```json
{
  "trial_duration": 14,
  "trial_duration_unit": "DAY"
}
```

**Common configurations:**
- **7-day trial:** `{"trial_duration": 7, "trial_duration_unit": "DAY"}`
- **1-month trial:** `{"trial_duration": 1, "trial_duration_unit": "MONTH"}`
- **No trial:** `{"trial_duration": 0, "trial_duration_unit": "DAY"}`

**How trials work:**
1. Customer subscribes without immediate charge
2. Trial period begins
3. First charge occurs after trial ends
4. Can cancel during trial with no charge

---

## Plan Lifetime Configuration

### Time of Life

Defines how long a plan provides access:

```json
{
  "time_of_life": 6,
  "time_of_life_unit": "MONTH"
}
```

**Use Cases:**

**Bootcamp (6 months):**
```json
{
  "is_renewable": false,
  "time_of_life": 6,
  "time_of_life_unit": "MONTH"
}
```

**Ongoing subscription (infinite):**
```json
{
  "is_renewable": true,
  "time_of_life": 1,
  "time_of_life_unit": "MONTH"  // Renews monthly
}
```

**Annual plan:**
```json
{
  "is_renewable": true,
  "time_of_life": 1,
  "time_of_life_unit": "YEAR"  // Renews yearly
}
```

---

## Complete Examples

### Example 1: Monthly SaaS Subscription

```json
{
  "slug": "4geeks-plus-monthly",
  "title": "4Geeks Plus - Monthly",
  "currency": "USD",
  "status": "ACTIVE",
  "is_renewable": true,
  "is_onboarding": false,
  "time_of_life": 1,
  "time_of_life_unit": "MONTH",
  "trial_duration": 7,
  "trial_duration_unit": "DAY",
  "price_per_month": 39.00,
  "cohort_set": 5,
  "consumption_strategy": "PER_SEAT"
}
```

**Then add service items:**
```json
{
  "plan": "4geeks-plus-monthly",
  "service_item": [
    45,  // Unlimited cohort access
    93,  // 5000 AI chat messages
    52   // 2 mentorship sessions
  ]
}
```

---

### Example 2: Bootcamp with Financing

```json
{
  "slug": "full-stack-bootcamp-2025",
  "title": "Full Stack Development Bootcamp",
  "currency": "USD",
  "status": "ACTIVE",
  "is_renewable": false,
  "is_onboarding": true,
  "has_waiting_list": true,
  "time_of_life": 6,
  "time_of_life_unit": "MONTH",
  "trial_duration": 0,
  "trial_duration_unit": "DAY",
  "price_per_month": 8999.00,  // Full price upfront
  "financing_options": [10, 11],  // Or pay in installments
  "cohort_set": 8,
  "consumption_strategy": "PER_SEAT"
}
```

**Financing options:**
- Option 10: `$799/month × 12 months` ($9,588 total)
- Option 11: `$1,599/month × 6 months` ($9,594 total)

---

### Example 3: Team/Corporate Plan

```json
{
  "slug": "corporate-training-team",
  "title": "Corporate Team Training",
  "currency": "USD",
  "status": "ACTIVE",
  "is_renewable": true,
  "time_of_life": 1,
  "time_of_life_unit": "MONTH",
  "price_per_month": 2999.00,  // Base team price
  "consumption_strategy": "BOTH",
  "seat_service_price": 456,  // $199 per additional seat
  "cohort_set": 12
}
```

**Pricing:**
- Base: $2,999/month (includes 5 seats)
- Each additional seat: $199/month
- 10 seats total = $2,999 + (5 × $199) = $3,994/month

---

### Example 4: Free Community Plan

```json
{
  "slug": "community-free",
  "title": "Free Community Access",
  "currency": "USD",
  "status": "ACTIVE",
  "is_renewable": true,
  "time_of_life": 1,
  "time_of_life_unit": "MONTH",
  "price_per_month": 0.00,
  "price_per_year": 0.00,
  "cohort_set": 15,
  "consumption_strategy": "PER_SEAT"
}
```

**Service items (limited):**
- 50 AI chat messages/month
- 1 mentorship session/month
- Access to free courses only

---

## Validation Rules

### Plan Validation

1. ✅ `slug` must be unique across all plans
2. ✅ `slug` can only contain: letters, numbers, hyphens
3. ✅ `currency` must be valid currency code
4. ✅ At least one price field should be set
5. ✅ `time_of_life` and `time_of_life_unit` must be together
6. ✅ `trial_duration` must be ≥ 0
7. ❌ Cannot change `owner` after creation
8. ❌ Cannot delete plan with active subscriptions (use UNLISTED)

### Service Item Validation

1. ✅ `how_many` must be -1 (unlimited) or positive integer
2. ✅ `sort_priority` determines display order
3. ❌ Cannot change core fields after creation (immutable):
   - `unit_type`
   - `how_many`
   - `service`
   - `is_renewable`
   - `renew_at`
   - `renew_at_unit`
4. ✅ CAN change: `is_team_allowed`

---

## Error Handling

### Common Errors

**404 - Plan Not Found**
```json
{
  "detail": "Plan not found",
  "slug": "not-found",
  "status_code": 404
}
```

**400 - Currency Not Found**
```json
{
  "detail": "Currency not found",
  "slug": "currency-not-found",
  "status_code": 400
}
```

**400 - Service Item Not Found**
```json
{
  "detail": "Service items not found: [456, 789]",
  "slug": "service-item-not-found",
  "status_code": 404
}
```

**400 - Cannot Add Plans to Existing User**
```json
{
  "detail": "cannot-add-plans-to-existing-user",
  "status_code": 400
}
```

---

## Integration with Student Enrollment

### Adding Students with Plans

When inviting **new students**, attach payment plans:

```bash
POST /v1/auth/academy/student
Headers:
  Academy: 1

Body:
{
  "email": "student@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "cohort": [1429],
  "invite": true,
  "plans": [123]  // Plan ID
}
```

**What happens:**
1. `UserInvite` created with linked plan
2. Student receives invitation email
3. When accepted:
   - Free `Bag` created (type: INVITED)
   - `$0` invoice generated
   - `PlanFinancing` or `Subscription` created
   - Student gets access to all service items
   - Capabilities granted automatically

**Important:**
- ❌ Cannot add plans to existing users
- ✅ Only works with `invite: true`
- ✅ Cohort must have `available_as_saas=true`
- ✅ Academy must have `main_currency` set

See [ADD_STUDENT.md](./ADD_STUDENT.md) for full enrollment documentation.

---

## Query Examples

### Get All Active Plans
```bash
GET /v1/payments/academy/plan?status=ACTIVE&limit=50
Headers:
  Academy: 1
```

### Get Plans for Specific Cohort
```bash
GET /v1/payments/academy/plan?cohort=1429
Headers:
  Academy: 1
```

### Get Onboarding Plans Only
```bash
GET /v1/payments/academy/plan?is_onboarding=true
Headers:
  Academy: 1
```

### Get Plans with Financing Options
```bash
GET /v1/payments/academy/plan?status=ACTIVE
# Filter response where financing_options.length > 0
```

### Get Service Items for Plan
```bash
GET /v1/payments/serviceitem?plan=premium-bootcamp
```

---

## Field Reference

### Plan Model Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | String(60) | ✅ Yes | Unique identifier |
| `title` | String(100) | No | Display name |
| `currency` | ForeignKey | ✅ Yes | Currency code |
| `status` | String | No | DRAFT, ACTIVE, UNLISTED, DELETED |
| `owner` | ForeignKey | Auto | Academy (set automatically) |
| `is_renewable` | Boolean | No | True=Subscription, False=Financing |
| `is_onboarding` | Boolean | No | Onboarding plan flag |
| `has_waiting_list` | Boolean | No | Enable waiting list |
| `exclude_from_referral_program` | Boolean | No | Disable referrals |
| `time_of_life` | Integer | No | Plan lifetime value |
| `time_of_life_unit` | String | No | DAY, WEEK, MONTH, YEAR |
| `trial_duration` | Integer | No | Trial period length |
| `trial_duration_unit` | String | No | DAY, WEEK, MONTH, YEAR |
| `price_per_half` | Float | No | 6-month price |
| `price_per_month` | Float | No | Monthly price |
| `price_per_quarter` | Float | No | 3-month price |
| `price_per_year` | Float | No | 12-month price |
| `consumption_strategy` | String | No | PER_SEAT, PER_TEAM, BOTH |
| `cohort_set` | ForeignKey | No | Linked cohort set |
| `mentorship_service_set` | ForeignKey | No | Linked mentorship set |
| `event_type_set` | ForeignKey | No | Linked event type set |
| `financing_options` | ManyToMany | No | Available financing |
| `service_items` | ManyToMany | No | Included services |
| `seat_service_price` | ForeignKey | No | Seat pricing service |
| `add_ons` | ManyToMany | No | Optional add-ons |
| `pricing_ratio_exceptions` | JSON | No | Country pricing adjustments |

### Service Model Fields

| Field | Type | Description |
|-------|------|-------------|
| `slug` | String | Unique identifier |
| `title` | String | Display name |
| `icon_url` | URL | Service icon |
| `type` | String | COHORT_SET, MENTORSHIP_SERVICE_SET, etc. |
| `consumer` | String | How it's consumed |
| `private` | Boolean | Private/public service |
| `groups` | ManyToMany | Django groups granted access |
| `session_duration` | Duration | Session time limit |

### ServiceItem Model Fields

| Field | Type | Immutable | Description |
|-------|------|-----------|-------------|
| `service` | ForeignKey | ✅ Yes | Parent service |
| `unit_type` | String | ✅ Yes | Always "UNIT" |
| `how_many` | Integer | ✅ Yes | -1=unlimited, N=quantity |
| `sort_priority` | Integer | No | Display order |
| `is_renewable` | Boolean | ✅ Yes | Auto-renew consumables |
| `renew_at` | Integer | ✅ Yes | Renewal interval |
| `renew_at_unit` | String | ✅ Yes | Renewal unit |
| `is_team_allowed` | Boolean | No | Team seat eligibility |

### FinancingOption Model Fields

| Field | Type | Description |
|-------|------|-------------|
| `monthly_price` | Float | Monthly payment amount |
| `how_many_months` | Integer | Number of installments |
| `currency` | ForeignKey | Payment currency |
| `pricing_ratio_exceptions` | JSON | Country adjustments |

---

## Best Practices

### Plan Design

1. ✅ **Start with DRAFT status** - test before activating
2. ✅ **Use clear slugs** - e.g., `web-dev-monthly-2025`
3. ✅ **Set meaningful titles** - shown to customers
4. ✅ **Include trial for subscriptions** - increases conversions
5. ✅ **Offer multiple payment periods** - flexibility drives sales
6. ❌ **Don't delete active plans** - use UNLISTED instead

### Service Item Strategy

1. ✅ **Use -1 for core features** - unlimited access
2. ✅ **Set limits for premium features** - e.g., 100 AI chats
3. ✅ **Prioritize sorting** - most important features first
4. ✅ **Enable team sharing selectively** - not all items need team access
5. ❌ **Don't modify after creation** - create new instead

### Pricing Strategy

1. ✅ **Offer annual discount** - typically 15-20% off
2. ✅ **Use country pricing** - adjust for local markets
3. ✅ **Round to clean numbers** - $299 not $297.84
4. ✅ **Multiple financing options** - flexibility for customers
5. ✅ **Price in academy's main currency** - consistent billing

### Student Enrollment

1. ✅ **Only assign plans to new students** - validation enforced
2. ✅ **Use for SaaS cohorts only** - `available_as_saas=true`
3. ✅ **Set main_currency first** - required for plan financings
4. ✅ **Link cohort to plan's cohort_set** - automatic access
5. ❌ **Don't add plans to existing users** - use payment system directly

---

## Security & Permissions

### Required Capabilities

| Operation | Capability | Description |
|-----------|-----------|-------------|
| View plans | `read_subscription` | Read-only access |
| Create plan | `crud_subscription` | Full CRUD on plans |
| Update plan | `crud_subscription` | Modify existing plans |
| Delete plan | `crud_subscription` | Soft delete plans |
| Manage service items | `crud_plan` | Link/unlink services |
| Manage cohort sets | `crud_plan` | Configure cohorts |
| View services | `read_service` | Read services |
| Manage services | `crud_service` | CRUD services |
| View consumables | `read_consumable` | View usage |
| View invoices | `read_invoice` | Access billing |

### Recommended Roles

**Billing Administrator:**
- `read_subscription`
- `crud_subscription`
- `crud_plan`
- `read_invoice`

**Academy Admin (Full Access):**
- All payment capabilities
- Plus academy management capabilities

**Support Staff (Read-Only):**
- `read_subscription`
- `read_invoice`
- `read_consumable`

---

## Advanced Features

### Add-Ons

Plans can have optional add-ons purchasable during checkout:

```json
{
  "slug": "basic-plan",
  "add_ons": [15, 16]  // AcademyService IDs
}
```

**Customer can add:**
- Extra mentorship sessions
- Additional storage
- Premium support

### Seat-Based Pricing

For team plans with per-seat charges:

```json
{
  "consumption_strategy": "PER_TEAM",
  "seat_service_price": 20  // AcademyService with seat pricing
}
```

### Waiting Lists

Enable for high-demand plans:

```json
{
  "has_waiting_list": true
}
```

**When plan at capacity:**
- New purchasers added to waiting list
- Notified when spots available

### Referral Program

Control referral coupon eligibility:

```json
{
  "exclude_from_referral_program": false  // Allow referrals
}
```

---

## Troubleshooting

### Plan Not Showing for Students

**Checklist:**
1. ✅ Status is `ACTIVE`
2. ✅ Cohort is in plan's `cohort_set`
3. ✅ Cohort has `available_as_saas=true`
4. ✅ Academy has `main_currency` set
5. ✅ Service items are linked

**Solution:**
```bash
# Check plan details
GET /v1/payments/academy/plan/{slug}

# Verify cohort in set
GET /v1/payments/academy/cohortset/{id}/cohort
```

---

### Cannot Add Plan to Student

**Error:** `cannot-add-plans-to-existing-user`

**Cause:** Trying to add plan to user that already exists

**Solution:**
- Only add plans when inviting NEW students
- For existing users, they must purchase through checkout
- See [BC_CHECKOUT.md](./BC_CHECKOUT.md) for purchase flow

---

### Service Items Not Appearing

**Checklist:**
1. ✅ Service items are linked to plan
2. ✅ Service is not `private=true` (or customer has permission)
3. ✅ `how_many` is not `0`

**Solution:**
```bash
# Check linked items
GET /v1/payments/serviceitem?plan={plan_slug}

# Add missing items
POST /v1/payments/academy/plan/serviceitem
Body: {"plan": 123, "service_item": [45, 52]}
```

---

### Financing Not Creating

**Checklist:**
1. ✅ Plan has `is_renewable=false`
2. ✅ Plan has financing options linked
3. ✅ Academy has `main_currency` set
4. ✅ Invoice status is `FULFILLED`
5. ✅ Bag status is `PAID`
6. ✅ Celery workers are running

**Solution:**
```bash
# Check if task failed
# View logs for build_plan_financing task
poetry run python manage.py check_task_status
```

---

## Related Documentation

- [BC_CHECKOUT.md](./BC_CHECKOUT.md) - Customer purchase flow
- [BC_INVOICE.md](./BC_INVOICE.md) - Invoice management
- [BC_COUPONS.md](./BC_COUPONS.md) - Discount coupons
- [ADD_STUDENT.md](./ADD_STUDENT.md) - Student enrollment with plans
- [BC_CHECKOUT_CONSUMABLE.md](./BC_CHECKOUT_CONSUMABLE.md) - Consumable purchases

---

## Quick Reference

### Common Workflows

**Create basic monthly plan:**
```bash
# 1. Create plan
POST /v1/payments/academy/plan
Body: {
  "slug": "basic-monthly",
  "currency": "USD",
  "price_per_month": 39.00,
  "is_renewable": true
}

# 2. Add services
POST /v1/payments/academy/plan/serviceitem
Body: {"plan": "basic-monthly", "service_item": [45, 93]}

# 3. Activate
PUT /v1/payments/academy/plan/basic-monthly
Body: {"status": "ACTIVE"}
```

**Create bootcamp with financing:**
```bash
# 1. Create plan
POST /v1/payments/academy/plan
Body: {
  "slug": "bootcamp-2025",
  "currency": "USD",
  "is_renewable": false,
  "time_of_life": 6,
  "time_of_life_unit": "MONTH",
  "financing_options": [10, 11],
  "cohort_set": 8
}

# 2. Add comprehensive services
POST /v1/payments/academy/plan/serviceitem
Body: {"plan": "bootcamp-2025", "service_item": [45,52,93,106]}

# 3. Activate
PUT /v1/payments/academy/plan/bootcamp-2025
Body: {"status": "ACTIVE"}
```

**Enroll student with plan:**
```bash
POST /v1/auth/academy/student
Body: {
  "email": "new.student@example.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "cohort": [1429],
  "invite": true,
  "plans": [123]
}
```

---

## Summary

Academy Plans provide a flexible payment system for selling educational services:

1. **Create plans** with pricing, trial periods, and lifetime
2. **Add service items** to define what's included
3. **Configure financing** for installment payments
4. **Link cohort sets** to grant course access
5. **Activate and sell** through invitation or checkout
6. **Track subscriptions** and financings automatically

The system handles automatic renewals, consumable allocation, capability grants, and certificate issuance - you just define the packages! 🎯

