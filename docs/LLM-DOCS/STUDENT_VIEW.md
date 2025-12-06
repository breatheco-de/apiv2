# Student View API Documentation

Complete guide to the `/v1/auth/academy/student` endpoint, including single and bulk student creation, updates, queries, and payment method integration.

## Overview

The `StudentView` API endpoint provides comprehensive student management capabilities for academies, supporting:
- ✅ Single and bulk student creation
- ✅ Student profile queries with filtering
- ✅ Student profile updates
- ✅ Payment plans and payment methods assignment
- ✅ Multiple cohort assignments
- ✅ Automatic invitation emails
- ✅ Automatic invoice creation with payment methods

**Base Endpoint:** `/v1/auth/academy/student`

---

## Authentication & Headers

All requests require:

```http
Authorization: Token {your-token}
Academy: {academy_id}
```

---

## GET - List and Query Students

### List All Students

**Endpoint:** `GET /v1/auth/academy/student`

**Query Parameters:**
- `like={text}` - Search by full name or email (case-insensitive)
- `status={ACTIVE|INVITED}` - Filter by profile status
- `cohort={slug1,slug2}` - Filter by cohort slugs (comma-separated)
- `limit={number}` - Pagination limit (default: 10)
- `offset={number}` - Pagination offset

**Example:**
```bash
GET /v1/auth/academy/student?cohort=web-dev-pt-01&status=ACTIVE&like=john
```

**Response:**
```json
[
  {
    "id": 123,
    "user": {
      "id": 123,
      "email": "student@example.com",
      "first_name": "John",
      "last_name": "Doe"
    },
    "role": {
      "slug": "student",
      "name": "Student"
    },
    "status": "ACTIVE",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

### Get Single Student

**Endpoint:** `GET /v1/auth/academy/student/{user_id_or_email}`

**Parameters:**
- `user_id_or_email` - Can be numeric user ID or email address

**Example:**
```bash
GET /v1/auth/academy/student/123
# or
GET /v1/auth/academy/student/student@example.com
```

**Response:**
```json
{
  "id": 123,
  "user": {
    "id": 123,
    "email": "student@example.com",
    "first_name": "John",
    "last_name": "Doe"
  },
  "role": {
    "slug": "student",
    "name": "Student"
  },
  "status": "ACTIVE",
  "phone": "+1234567890",
  "address": "123 Main St",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

## POST - Create Students

### Single Student Creation

**Endpoint:** `POST /v1/auth/academy/student`

**Request Body:**
```json
{
  "email": "student@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "1234567890",
  "address": "123 Main St",
  "cohort": [1429, 1430],
  "plans": [5, 12],
  "payment_method": 123,
  "invite": true
}
```

**Field Descriptions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | String | ✅ Yes | Student email (will be lowercased) |
| `first_name` | String | ✅ Yes* | First name (required for new users) |
| `last_name` | String | ✅ Yes* | Last name (required for new users) |
| `phone` | String | ⚠️ Optional | Phone number |
| `address` | String | ⚠️ Optional | Student address |
| `cohort` | Array[Int] | ⚠️ Optional | Array of cohort IDs. Use `[]` for none, never `[null]` |
| `plans` | Array[Int] | ⚠️ Optional | Array of plan IDs. **Only for new users** (when `invite: true`) |
| `payment_method` | Integer | ⚠️ Optional | Payment method ID. Must belong to the academy |
| `invite` | Boolean | ⚠️ Optional | Send invitation email (default: `false`) |
| `user` | Integer | ⚠️ Optional | Existing user ID (alternative to email) |

**Response:**
```json
{
  "id": 18396,
  "email": "student@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "status": "INVITED",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Bulk Student Creation

The endpoint **automatically detects bulk requests** when the request body is an array. Each student in the array is processed independently.

**Endpoint:** `POST /v1/auth/academy/student`

**Request Body (Array):**
```json
[
  {
    "email": "student1@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "cohort": [1429],
    "plans": [5],
    "payment_method": 123,
    "invite": true
  },
  {
    "email": "student2@example.com",
    "first_name": "Jane",
    "last_name": "Smith",
    "cohort": [1429, 1430],
    "plans": [5, 12],
    "payment_method": 123,
    "invite": true
  },
  {
    "email": "student3@example.com",
    "first_name": "Bob",
    "last_name": "Johnson",
    "cohort": [],
    "invite": true
  }
]
```

**Response (Array):**
```json
[
  {
    "id": 18396,
    "email": "student1@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "status": "INVITED"
  },
  {
    "id": 18397,
    "email": "student2@example.com",
    "first_name": "Jane",
    "last_name": "Smith",
    "status": "INVITED"
  },
  {
    "id": 18398,
    "email": "student3@example.com",
    "first_name": "Bob",
    "last_name": "Johnson",
    "status": "INVITED"
  }
]
```

**Bulk Creation Notes:**
- ✅ Each student is validated and created independently
- ✅ If one student fails, others may still succeed
- ✅ Uses `StudentPOSTListSerializer` internally
- ✅ All students are created with `INVITED` status
- ✅ Each student can have different cohorts, plans, and payment methods

---

## Payment Methods

### Overview

The `payment_method` field allows you to specify which payment method should be used when creating invoices for students with payment plans.

**How It Works:**
1. When a student is created with `plans` and `payment_method`
2. The `payment_method` is saved to the `UserInvite` record
3. When the student accepts the invitation:
   - A `Bag` is created (type `INVITED`, status `PAID`)
   - An `Invoice` is created with the specified `payment_method`
   - The invoice is marked as `externally_managed=True` automatically
   - A `ProofOfPayment` is automatically created (if payment method is not crypto)
   - The proof is created by the invite `author` (staff member who created the invite)

### Requirements

- ✅ `payment_method` must belong to the academy
- ✅ Only works with new users (when `invite: true` and user doesn't exist)
- ✅ When `payment_method` is set, the invoice is automatically marked as `externally_managed=True`
- ✅ If `payment_method` is not crypto, a `ProofOfPayment` is automatically created
- ✅ The invite must have an `author` (staff member) when `payment_method` is set

### Example with Payment Method

```json
{
  "email": "student@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "cohort": [1429],
  "plans": [5],
  "payment_method": 123,
  "invite": true
}
```

**What Happens:**
1. User account is created (if doesn't exist)
2. `UserInvite` is created with `payment_method=123` and `author=request.user`
3. Plans are linked to the invite
4. When student accepts:
   - Invoice is created with `payment_method=123` and `externally_managed=True`
   - `ProofOfPayment` is created (if not crypto) with `created_by=invite.author`
   - Subscription/financing is created automatically

### Payment Method Validation

**Error: Payment Method Not Found**
```json
{
  "detail": "Payment method not found or does not belong to this academy",
  "status_code": 404,
  "slug": "payment-method-not-found"
}
```

**Error: Invite Author Required**
```json
{
  "detail": "Invite author is required when payment method is set. The author is the staff member who created the invitation.",
  "status_code": 400,
  "slug": "invite-author-required-for-payment-method"
}
```

This error occurs when trying to accept an invite with a payment method but the invite doesn't have an `author`. The `author` is automatically set when creating students through the API (it's the authenticated user making the request).

---

## Payment Plans

### Overview

Payment plans can be assigned to students during creation, but **only for new users**.

### Restrictions

- ❌ **Cannot** add plans to existing users
- ✅ **Can** add plans when `invite: true` and user doesn't exist
- ✅ Plans are linked to the `UserInvite` record
- ✅ Multiple plans can be assigned per student

### Example with Plans

```json
{
  "email": "new.student@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "cohort": [1429],
  "plans": [5, 12],
  "payment_method": 123,
  "invite": true
}
```

**What Happens:**
1. Plans are validated to exist
2. Plans are linked to the `UserInvite`
3. When student accepts:
   - Free `Bag` is created (type `INVITED`, status `PAID`)
   - `$0` invoice is generated (status `FULFILLED`)
   - `ProofOfPayment` is created (if payment method is not crypto)
   - `build_plan_financing` task creates the subscription
   - Student capabilities are automatically granted

### Error: Cannot Add Plans to Existing User

**Error:** `cannot-add-plans-to-existing-user`

**Cause:** Trying to add plans when user already exists

**Solution:**
- Only add plans when `invite: true` and user doesn't exist
- For existing users, they must purchase through checkout

---

## Multiple Cohorts

Students can be assigned to multiple cohorts simultaneously.

**Example:**
```json
{
  "email": "student@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "cohort": [1429, 1430, 1431],
  "invite": true
}
```

**What Happens:**
- Student is added to all three cohorts
- Multiple `CohortUser` records are created
- One `UserInvite` is created per cohort (if `invite: true`)

**Note:** If no cohorts are specified, use `"cohort": []` or omit the field entirely. **Never use `[null]`**.

---

## PUT - Update Student

**Endpoint:** `PUT /v1/auth/academy/student/{user_id}`

**Note:** `user_id_or_email` must be numeric for PUT requests.

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe Updated",
  "phone": "9876543210",
  "address": "456 New St"
}
```

**Restrictions:**
- ❌ Cannot update `role` (use `/member` endpoint instead)
- ❌ Cannot update `email` or `user`
- ✅ Can update: `first_name`, `last_name`, `phone`, `address`

**Response:**
```json
{
  "id": 123,
  "user": 123,
  "first_name": "John",
  "last_name": "Doe Updated",
  "phone": "9876543210",
  "address": "456 New St",
  "role": "student",
  "academy": 4
}
```

---

## DELETE - Remove Student

**Endpoint:** `DELETE /v1/auth/academy/student/{user_id}`

**Status:** ⚠️ **Currently disabled** - Returns 403 error

**Error Response:**
```json
{
  "detail": "This functionality is under maintenance and it's not working"
}
```

---

## Common Scenarios

### Scenario 1: Import New Students Without Cohorts

```json
{
  "email": "student@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "1234567890",
  "invite": true
}
```

### Scenario 2: Import Students to Multiple Cohorts

```json
{
  "email": "student@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "cohort": [1429, 1430, 1431],
  "invite": true
}
```

### Scenario 3: Import Students with Payment Plans and Payment Method

```json
{
  "email": "student@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "cohort": [1429],
  "plans": [5, 12],
  "payment_method": 123,
  "invite": true
}
```

**What Happens:**
1. Student is created with plans and payment method
2. When student accepts invite:
   - Invoice is created with payment method
   - Proof of payment is created (if not crypto)
   - Subscription is created automatically

### Scenario 4: Add Existing User to Academy

```json
{
  "user": 123,
  "cohort": [1429],
  "invite": true
}
```

**Note:** Cannot add plans to existing users.

### Scenario 5: Bulk Import with Mixed Configurations

```json
[
  {
    "email": "premium@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "cohort": [1429],
    "plans": [5],
    "payment_method": 123,
    "invite": true
  },
  {
    "email": "free@example.com",
    "first_name": "Jane",
    "last_name": "Smith",
    "cohort": [1429, 1430],
    "invite": true
  },
  {
    "user": 456,
    "cohort": [1429],
    "invite": true
  }
]
```

---

## Validation Rules

### Email Validation
- Email is automatically lowercased
- Must be unique per academy (no duplicate invites)
- If user exists, `user` field is automatically populated

### User vs Email
- Use `email` for new users
- Use `user` (ID) for existing users
- Cannot use both in the same request

### Plans Validation
- Plans must exist in the system
- Can only be added to new users (`invite: true` + user doesn't exist)
- Plans are validated before creation

### Payment Method Validation
- Payment method must exist
- Must belong to the academy
- Validated before creation
- Requires invite `author` when used (automatically set by API)

### Cohort Validation
- Cohorts must exist
- Can assign to multiple cohorts
- Use `[]` for no cohorts, never `[null]`

---

## Error Responses

### Common Errors

**1. User Not Found**
```json
{
  "detail": "User does not exists, do you want to invite it?",
  "status_code": 400,
  "slug": "user-not-found"
}
```

**2. Already Exists**
```json
{
  "detail": "There is a student already in this academy, or with invitation pending",
  "status_code": 400,
  "slug": "already-exists-with-this-email"
}
```

**3. Cohort Not Found**
```json
{
  "detail": "Cohort not found",
  "status_code": 400,
  "slug": "cohort-not-found"
}
```

**4. Plan Not Found**
```json
{
  "detail": "Plan not found",
  "status_code": 400,
  "slug": "plan-not-found"
}
```

**5. Payment Method Not Found**
```json
{
  "detail": "Payment method not found or does not belong to this academy",
  "status_code": 404,
  "slug": "payment-method-not-found"
}
```

**6. Cannot Add Plans to Existing User**
```json
{
  "detail": "Cannot add payment plans when user already exists. User 123 (user@example.com) should be enrolled through their existing account or payment system.",
  "status_code": 400,
  "slug": "cannot-add-plans-to-existing-user"
}
```

**7. Already Invited**
```json
{
  "detail": "You already invited this user",
  "status_code": 400,
  "slug": "already-invited"
}
```

**8. Invite Author Required**
```json
{
  "detail": "Invite author is required when payment method is set. The author is the staff member who created the invitation.",
  "status_code": 400,
  "slug": "invite-author-required-for-payment-method"
}
```

---

## Internal Flow

### New User Creation Flow

1. **Validation Phase:**
   - Email is lowercased
   - User existence is checked
   - Cohorts, plans, and payment_method are validated
   - Duplicate checks are performed

2. **User Creation:**
   - User account is created (if doesn't exist)
   - `UserInvite` is created with:
     - User reference
     - Academy reference
     - Cohort(s) reference
     - Payment method (if provided)
     - Author (automatically set to `request.user`)
     - Plans linked via many-to-many

3. **Profile Creation:**
   - `ProfileAcademy` is created with `INVITED` status
   - `CohortUser` records are created for each cohort

4. **Email Notification:**
   - Invitation email is sent (if `invite: true`)
   - Email contains invitation link with token

5. **On Invite Acceptance:**
   - User status changes to `ACCEPTED`
   - If plans exist:
     - `Bag` is created (type `INVITED`, status `PAID`)
     - `Invoice` is created with:
       - `payment_method` from invite
       - `externally_managed=True` (if payment_method exists)
       - Status `FULFILLED`
     - `ProofOfPayment` is created (if payment_method exists and is not crypto):
       - `created_by` = invite author (staff member)
       - `status` = DONE
       - `reference` = INVITE-{invite.id}
       - `provided_payment_details` = description of payment method
     - `build_plan_financing` task is triggered
     - Subscription/financing is created automatically

### Existing User Flow

1. **Validation:**
   - User ID is validated
   - Plans cannot be added (error if attempted)
   - Duplicate checks are performed

2. **Profile Creation:**
   - `ProfileAcademy` is created
   - `CohortUser` records are created

3. **Email Notification:**
   - Invitation email is sent (if `invite: true`)

---

## Best Practices

### Bulk Import Tips

1. **Batch Size:** Process in batches of 50-100 students for optimal performance
2. **Error Handling:** Check response for partial failures
3. **Validation:** Pre-validate emails, cohorts, and plans before bulk import
4. **Testing:** Test with small batches (2-3 students) before large imports

### Payment Methods

1. **Verify Payment Methods:** Use `GET /v1/payments/academy/paymentmethod` to list available methods
2. **Academy Ownership:** Ensure payment method belongs to the academy
3. **Currency Compatibility:** Verify payment method currency matches academy currency
4. **Author Requirement:** The invite author is automatically set when creating through the API

### Plans Management

1. **Verify Plans:** Use `GET /v1/payments/academy/plan?cohort={cohort_id}` to list available plans
2. **Compatibility:** Ensure plans are compatible with assigned cohorts
3. **New Users Only:** Remember plans can only be added to new users

### Data Quality

1. **Email Format:** Ensure emails are valid and properly formatted
2. **Required Fields:** Always include `first_name` and `last_name` for new users
3. **Cohort Arrays:** Use `[]` for empty arrays, never `[null]`

---

## Technical Details

### Serializers

- **StudentPOSTSerializer:** Handles single student creation
- **StudentPOSTListSerializer:** Handles bulk student creation (extends ListSerializer)
- **GetProfileAcademySerializer:** Used for GET responses
- **GetProfileAcademySmallSerializer:** Used for list responses

### Permissions

- **GET:** Requires `read_student` capability
- **POST:** Requires `crud_student` capability
- **PUT:** Requires `crud_student` capability
- **DELETE:** Currently disabled

### Database Models

- **User:** Django User model
- **ProfileAcademy:** Student profile in academy
- **UserInvite:** Invitation record with plans and payment_method
- **CohortUser:** Many-to-many relationship between users and cohorts
- **Plan:** Payment plan model
- **PaymentMethod:** Payment method model
- **Invoice:** Created when invite is accepted with plans
- **ProofOfPayment:** Created automatically when invoice has payment_method (non-crypto)

---

## Related Endpoints

- **List Payment Methods:** `GET /v1/payments/academy/paymentmethod`
- **List Plans:** `GET /v1/payments/academy/plan`
- **List Cohorts:** `GET /v1/admissions/academy/cohort`
- **Update Member:** `PUT /v1/auth/academy/member/{user_id}`

---

## Changelog

### 2024 - Payment Method Support
- ✅ Added `payment_method` field to student creation
- ✅ Payment method is saved to `UserInvite`
- ✅ Invoice automatically uses payment method when invite is accepted
- ✅ Invoice is marked as `externally_managed=True` when payment_method is set
- ✅ `ProofOfPayment` is automatically created when payment_method is set (non-crypto)
- ✅ Proof is created by invite `author` (staff member)

### 2024 - Bulk Creation Support
- ✅ Added automatic bulk detection (array vs object)
- ✅ Uses `StudentPOSTListSerializer` for efficient bulk processing
- ✅ Each student is processed independently

---

## Examples

### Complete Example: Bulk Import with Plans and Payment Methods

```bash
POST /v1/auth/academy/student
Headers:
  Authorization: Token abc123...
  Academy: 4

Body:
[
  {
    "email": "premium.student@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "cohort": [1429],
    "plans": [5],
    "payment_method": 123,
    "invite": true
  },
  {
    "email": "free.student@example.com",
    "first_name": "Jane",
    "last_name": "Smith",
    "cohort": [1429, 1430],
    "invite": true
  }
]
```

This will:
1. Create two new users
2. Assign first student to cohort 1429 with plan 5 and payment method 123
3. Assign second student to cohorts 1429 and 1430 (no plans)
4. Send invitation emails to both
5. When they accept:
   - First student will get invoice with payment method 123 and proof of payment
   - Second student will just be added to cohorts
