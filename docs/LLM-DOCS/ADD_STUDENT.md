# Add Students to Academy and Cohorts

This document explains how to add students individually or in bulk to an academy and cohort.

> **Note:** As of October 2024, the `/v1/auth/academy/student` endpoint now properly supports bulk student creation by sending an array of student objects.

## Search for Existing Users

Before adding students, check if they already exist in the database:

**Endpoint:** `GET /v1/auth/user/?like={email}`

**Example:**
```
GET https://breathecode.herokuapp.com/v1/auth/user/?like=aalejo@gmail.com
```

**Response:**
```json
[
    {
        "id": 1,
        "email": "aalejo@gmail.com",
        "first_name": "Alejandro",
        "last_name": "Sanchez",
        "github": {
            "avatar_url": "https://avatars.githubusercontent.com/u/426452?v=4",
            "name": "Alejandro Sanchez",
            "username": "alesanchezr"
        },
        "profile": {
            "avatar_url": "https://techhubsouthflorida.org/wp-content/uploads/2023/09/Alejandro-Sanchez.jpeg"
        }
    }
]
```

---

## Option A: Add Students to Academy (New Users)

Use this when students **don't exist** in the system yet. This will create both the user and add them to the academy/cohort.

### Single Student

**Endpoint:** `POST /v1/auth/academy/student`

**Headers:**
- `Authorization: Token {your-token}`
- `Academy: {academy_id}`

**Request Body:**
```json
{
    "cohort": [1429],
    "email": "christianalopez@bcp.com.pe",
    "first_name": "CHRISTIAN",
    "last_name": "LÓPEZ",
    "phone": "0000000000",
    "invite": true
}
```

**Important Field Notes:**
- `cohort`: Array of valid cohort IDs. Use `[]` for no cohorts, or omit entirely. **Never use `[null]`**
- `plans`: Array of valid plan IDs. Use `[]` for no plans, or omit entirely. **Never use `[null]`**
  - ⚠️ **RESTRICTION:** Plans can **ONLY** be added for new users (`invite: true` with non-existent email)
  - ❌ **CANNOT** add plans to existing users - will return `cannot-add-plans-to-existing-user` error
  - Plans are linked to the `UserInvite` and processed when invitation is accepted
- `email`: Required, will be converted to lowercase
- `first_name`, `last_name`: Required for new students
- `phone`: Optional, defaults to empty string
- `invite`: Set to `true` to send invitation email

**Response:**
```json
{
    "id": 18396,
    "first_name": "CHRISTIAN",
    "last_name": "LÓPEZ",
    "user": {
        "id": 18731,
        "email": "christianalopez@bcp.com.pe",
        "first_name": "CHRISTIAN",
        "last_name": "LÓPEZ",
        "profile": null
    },
    "academy": {
        "id": 55,
        "name": "Banco de Crédito del Perú",
        "slug": "bcp"
    },
    "role": {
        "id": "student",
        "slug": "student",
        "name": "Student"
    },
    "created_at": "2025-10-20T18:27:46.722458Z",
    "email": "christianalopez@bcp.com.pe",
    "address": null,
    "phone": "0000000000",
    "status": "INVITED"
}
```

### Bulk Students

Add multiple students at once by sending an array:

**Endpoint:** `POST /v1/auth/academy/student`

**Headers:**
- `Authorization: Token {your-token}`
- `Academy: {academy_id}`

**Request Body (Array):**
```json
[
    {
        "cohort": [1429],
        "email": "student1@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "phone": "1234567890",
        "invite": true
    },
    {
        "cohort": [1429],
        "email": "student2@example.com",
        "first_name": "Jane",
        "last_name": "Smith",
        "phone": "0987654321",
        "invite": true
    },
    {
        "cohort": [1429, 1430],
        "email": "student3@example.com",
        "first_name": "Bob",
        "last_name": "Johnson",
        "phone": "5555555555",
        "invite": true
    }
]
```

**Response (Array):**
```json
[
    {
        "id": 18396,
        "first_name": "John",
        "last_name": "Doe",
        "email": "student1@example.com",
        "status": "INVITED",
        ...
    },
    {
        "id": 18397,
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "student2@example.com",
        "status": "INVITED",
        ...
    },
    {
        "id": 18398,
        "first_name": "Bob",
        "last_name": "Johnson",
        "email": "student3@example.com",
        "status": "INVITED",
        ...
    }
]
```

**Notes:**
- ✅ The endpoint automatically detects bulk requests by checking if data is an array
- `cohort` is an array of cohort IDs - students will be added to all specified cohorts
- `invite: true` will send invitation emails to the students
- All students will be created with `INVITED` status
- The system automatically creates user accounts and ProfileAcademy records
- Uses `StudentPOSTListSerializer` internally for efficient bulk creation

**Common Errors:**

1. **`"Invalid data. Expected a dictionary, but got list."`**
   - **Cause:** Outdated API version (pre-October 2024)
   - **Solution:** Ensure you're using the latest API version

2. **`"Cohort not found"`**
   - **Cause:** Invalid cohort ID in the `cohort` array
   - **Solution:** Verify cohort IDs exist and academy has access

3. **Validation fails with `cohort` field**
   - **Cause:** Using `"cohort": [null]` instead of `"cohort": []`
   - **Solution:** Use empty array `[]` or omit field entirely if no cohorts

### Adding Students with Payment Plans

When adding **new students** (not existing users), you can specify payment plans using the `plans` array field.

**Single Student with Plans:**
```json
{
    "cohort": [1429],
    "email": "student@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "1234567890",
    "invite": true,
    "plans": [5, 12]  // Array of Plan IDs
}
```

**Bulk Students with Plans:**
```json
[
    {
        "cohort": [1429],
        "email": "student1@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "invite": true,
        "plans": [5]
    },
    {
        "cohort": [1429],
        "email": "student2@example.com",
        "first_name": "Jane",
        "last_name": "Smith",
        "invite": true,
        "plans": [5, 12]  // Different student can have different plans
    },
    {
        "cohort": [1429],
        "email": "student3@example.com",
        "first_name": "Bob",
        "last_name": "Johnson",
        "invite": true,
        "plans": []  // Or no plans at all
    }
]
```

**How It Works:**
1. Plans are linked to the `UserInvite` record (lines 1181-1182 in serializer)
2. Each plan in the array is validated to exist (error if plan not found)
3. When the student accepts the invitation:
   - A free `Bag` is created (type `INVITED`, status `PAID`)
   - A `$0` invoice is generated (status `FULFILLED`)
   - `build_plan_financing` task creates the subscription
   - Student capabilities are automatically granted based on plan

**Requirements:**
- ✅ Plans can only be added for **new students** (when `invite: true` and user doesn't exist)
- ✅ Cohort must have `available_as_saas=true` (or inherit from academy)
- ✅ Academy must have `main_currency` set
- ✅ Plan must include the cohort in its `cohort_set`
- ✅ Each plan ID must exist, otherwise returns `plan-not-found` error
- ❌ **Cannot add plans to existing users** - will return 400 error

**Error Responses:**

If trying to add plans to existing user:
```json
{
    "detail": "Cannot add payment plans when user already exists. User 123 (user@example.com) should be enrolled through their existing account or payment system.",
    "status_code": 400,
    "slug": "cannot-add-plans-to-existing-user"
}
```

If plan doesn't exist:
```json
{
    "detail": "Plan not found",
    "status_code": 400,
    "slug": "plan-not-found"
}
```

**To Find Available Plans:**
```bash
GET /v1/payments/academy/plan?cohort={cohort_id}
Headers:
  Authorization: Token {your-token}
  Academy: {academy_id}
```

**Example Response:**
```json
[
    {
        "id": 5,
        "slug": "basic-bootcamp",
        "title": "Basic Bootcamp Plan",
        "price_per_month": 299.00,
        "cohort_set": [1429, 1430]
    },
    {
        "id": 12,
        "slug": "premium-bootcamp",
        "title": "Premium Bootcamp Plan",
        "price_per_month": 499.00,
        "cohort_set": [1429, 1430, 1431]
    }
]
```

---

## Option B: Add Existing Users to Cohort

Use this when users **already exist** in the system and you just need to add them to a cohort.

### Single User

**Endpoint:** `POST /v1/admissions/cohort/{cohort_id}/user`

**Request Body:**
```json
{
    "user": 1,
    "role": "STUDENT",
    "finantial_status": null,
    "educational_status": "ACTIVE"
}
```

**Response:**
```json
{
    "id": 42487,
    "user": {
        "id": 1,
        "first_name": "Alejandro",
        "last_name": "Sanchez",
        "email": "aalejo@gmail.com",
        "last_login": "2025-09-17T16:52:08.171695Z",
        "profile": {
            "id": 2,
            "avatar_url": "https://techhubsouthflorida.org/wp-content/uploads/2023/09/Alejandro-Sanchez.jpeg",
            "show_tutorial": false,
            "github_username": null
        }
    },
    "cohort": {
        "id": 1429,
        "slug": "bcp-react-native-1",
        "name": "bcp-react-native-1",
        "kickoff_date": "2025-10-22T20:00:00Z",
        "ending_date": "2025-12-10T22:00:00Z",
        "stage": "PREWORK",
        "available_as_saas": false,
        "shortcuts": null
    },
    "role": "STUDENT",
    "finantial_status": null,
    "educational_status": "ACTIVE",
    "watching": false,
    "created_at": "2025-10-20T18:32:22.713896Z",
    "updated_at": "2025-10-20T18:32:22.713914Z",
    "profile_academy": {
        "id": 18388,
        "first_name": "Alejandro",
        "last_name": "Sanchez",
        "email": "aalejo@gmail.com",
        "phone": ""
    }
}
```

### Bulk Add Users to Cohort

Add multiple existing users to a cohort at once:

**Endpoint:** `POST /v1/admissions/cohort/{cohort_id}/user`

**Request Body (Array):**
```json
[
    {
        "user": 1,
        "role": "STUDENT",
        "finantial_status": null,
        "educational_status": "ACTIVE"
    },
    {
        "user": 2,
        "role": "STUDENT",
        "finantial_status": "FULLY_PAID",
        "educational_status": "ACTIVE"
    },
    {
        "user": 3,
        "role": "STUDENT",
        "finantial_status": "UP_TO_DATE",
        "educational_status": "ACTIVE"
    }
]
```

**Response (Array):**
```json
[
    {
        "id": 42487,
        "user": {...},
        "cohort": {...},
        "role": "STUDENT",
        "educational_status": "ACTIVE",
        ...
    },
    {
        "id": 42488,
        "user": {...},
        "cohort": {...},
        "role": "STUDENT",
        "educational_status": "ACTIVE",
        ...
    },
    {
        "id": 42489,
        "user": {...},
        "cohort": {...},
        "role": "STUDENT",
        "educational_status": "ACTIVE",
        ...
    }
]
```

**Field Options:**
- `role`: `STUDENT`, `TEACHER`, `ASSISTANT`, `REVIEWER`
- `educational_status`: `ACTIVE`, `POSTPONED`, `SUSPENDED`, `GRADUATED`, `DROPPED`, `NOT_COMPLETING`
- `finantial_status`: `FULLY_PAID`, `UP_TO_DATE`, `LATE`, or `null`

---

## Summary

### When to Use Each Method

| Scenario | Endpoint | Method |
|----------|----------|--------|
| New student(s) not in system | `/v1/auth/academy/student` | Option A |
| Existing user(s) → add to cohort | `/v1/admissions/cohort/{cohort_id}/user` | Option B |
| Bulk import new students | `/v1/auth/academy/student` (array) | Option A Bulk |
| Bulk add existing users | `/v1/admissions/cohort/{cohort_id}/user` (array) | Option B Bulk |

### Tips for Bulk Operations

1. **Validation**: All items in the array must be valid or the entire request fails
2. **Performance**: Bulk operations use `bulk_create()` internally for better performance
3. **Error Handling**: If one item fails validation, check the error response for details
4. **Size Limits**: Consider breaking very large imports (500+ students) into smaller batches
5. **Invitations**: When using Option A with `invite: true`, invitation emails are sent to all students
6. **Multiple Cohorts**: In Option A, you can add students to multiple cohorts by providing an array of cohort IDs

---

## Best Practices & Troubleshooting

### ⚠️ Common Pitfall: Null Values in Arrays

**This is a VERY common mistake across multiple endpoints!**

Many API endpoints accept arrays (like `cohort`, `plans`, `service_item`, etc.) and will crash if you send `null` values inside the array:

```json
// ❌ NEVER DO THIS - Will cause 500 errors
{
  "cohort": [null],
  "plans": [null],
  "service_item": [null]
}

// ✅ CORRECT - Use empty arrays or omit the field
{
  "cohort": [],
  "plans": []
}
// Or simply omit the fields entirely
```

**Affected Endpoints:**
- `POST /v1/auth/academy/student` - cohort, plans arrays
- `POST /v1/admissions/cohort/{cohort_id}/user` - cohort array
- `POST /v1/payments/academy/plan/serviceitem` - service_item array
- And potentially others...

**Why This Happens:**
CSV exports or spreadsheet tools often convert empty cells to `null`, which then gets included in API requests. Always clean your data before sending!

### Before Bulk Import

1. **Validate your data structure:**
   ```json
   // ✅ CORRECT - Arrays with valid IDs or empty arrays
   [
     {"email": "user1@example.com", "first_name": "John", "cohort": [123], "plans": [5]},
     {"email": "user2@example.com", "first_name": "Jane", "cohort": [], "plans": []},
     {"email": "user3@example.com", "first_name": "Bob", "cohort": [123, 456]}
     // Note: omitting cohort/plans is also fine
   ]

   // ❌ WRONG - Never use null values
   [
     {"email": "user1@example.com", "cohort": [null]},     // Don't use null
     {"email": "user2@example.com", "cohort": null},       // Don't use null
     {"email": "user3@example.com", "plans": [null]},      // Don't use null
     {"email": "user4@example.com", "plans": null}         // Don't use null
   ]
   ```

2. **Check for existing users** using the search endpoint to avoid duplicates

3. **Verify cohort IDs** are valid and accessible to your academy

4. **Verify plan IDs** if using the `plans` field:
   - Use `GET /v1/payments/academy/plan?cohort={cohort_id}` to list available plans
   - Ensure plans are compatible with the cohorts you're assigning
   - Remember: plans can **only** be used for new users (invitations)

5. **Test with a small batch** (2-3 students) before running large imports

### Field Requirements

| Field | Required? | Type | Notes |
|-------|-----------|------|-------|
| `email` | ✅ Yes | String | Will be lowercased automatically |
| `first_name` | ✅ Yes | String | Required for new students |
| `last_name` | ✅ Yes | String | Required for new students |
| `phone` | ⚠️ Optional | String | Defaults to `""` if not provided |
| `invite` | ⚠️ Optional | Boolean | Default is `false`, set to `true` to send emails |
| `cohort` | ⚠️ Optional | Array[Int] | Array of cohort IDs, use `[]` for none |
| `plans` | ⚠️ Optional | Array[Int] | Only for new users, ignored for existing |
| `address` | ⚠️ Optional | String | Student address |

### Common Scenarios

**Scenario 1: Import students without cohorts**
```json
{
  "email": "student@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "1234567890",
  "invite": true
}
// Note: No cohort field, or use "cohort": []
```

**Scenario 2: Import students to multiple cohorts**
```json
{
  "email": "student@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "cohort": [1429, 1430, 1431],
  "invite": true
}
```

**Scenario 3: Import students with plans (SaaS/Subscriptions)**
```json
// Single student with multiple plans
{
  "email": "student@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "cohort": [1429],
  "plans": [5, 12],  // Multiple plans can be assigned
  "invite": true
}

// Bulk import with mixed plan assignments
[
  {
    "email": "premium@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "cohort": [1429],
    "plans": [12],  // Premium plan
    "invite": true
  },
  {
    "email": "basic@example.com",
    "first_name": "Jane",
    "last_name": "Smith",
    "cohort": [1429],
    "plans": [5],  // Basic plan
    "invite": true
  },
  {
    "email": "free@example.com",
    "first_name": "Bob",
    "last_name": "Johnson",
    "cohort": [1429],
    "plans": [],  // No plans (free access or manual enrollment)
    "invite": true
  }
]
```

**Important Notes:**
- Plans are processed when the invitation is accepted
- A free $0 bag/invoice is created automatically
- The subscription is built via the `build_plan_financing` background task
- Student gets capabilities based on their assigned plan(s)
- You can assign multiple plans to a single student

### Error Reference

| Error | Meaning | Solution |
|-------|---------|----------|
| `Invalid data. Expected a dictionary, but got list.` | Endpoint not detecting array | Update API/contact support |
| `already-exists-with-this-email` | ProfileAcademy exists with email | Use different email or update existing |
| `already-exists` | User already member of academy | User is already a student, update instead |
| `already-invited` | Duplicate invitation | User already has pending invitation for this cohort |
| `Cohort not found` | Invalid cohort ID in array | Verify cohort exists and academy has access |
| `Plan not found` | Invalid plan ID in array | Verify plan ID exists using plan list endpoint |
| `role-not-found` | Role 'student' doesn't exist | Run academy setup/migrations |
| `cannot-add-plans-to-existing-user` | Plans provided for existing user | Remove `plans` field - existing users must enroll via payment system |
| `no-email-or-id` | Missing required identifier | Provide valid email address |
| `user-not-found` | User doesn't exist and invite=false | Set `invite: true` or provide existing user ID |
| `Academy not found` | Invalid academy_id in header | Verify Academy header value matches your academy |

### Performance Considerations

- **Batch Size**: Recommended batch size is 100-200 students per request
- **Large Imports**: For 1000+ students, split into multiple batches
- **Rate Limiting**: Wait 1-2 seconds between batch requests
- **Timeout**: Very large batches may timeout; reduce size if this occurs
