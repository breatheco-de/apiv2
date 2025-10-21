# Add Students to Academy and Cohorts

This document explains how to add students individually or in bulk to an academy and cohort.

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
- `cohort` is an array of cohort IDs - students will be added to all specified cohorts
- `invite: true` will send invitation emails to the students
- All students will be created with `INVITED` status
- The system automatically creates user accounts and ProfileAcademy records

### Adding Students with Payment Plans

When adding **new students** (not existing users), you can specify payment plans:

**Request with Plans:**
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

**How It Works:**
1. Plans are linked to the `UserInvite` record
2. When the student accepts the invitation:
   - A free `Bag` is created (type `INVITED`, status `PAID`)
   - A `$0` invoice is generated (status `FULFILLED`)
   - `build_plan_financing` task creates the subscription
   - Student capabilities are automatically granted

**Requirements:**
- ✅ Plans can only be added for **new students** (when `invite: true` and user doesn't exist)
- ✅ Cohort must have `available_as_saas=true` (or inherit from academy)
- ✅ Academy must have `main_currency` set
- ✅ Plan must include the cohort in its `cohort_set`
- ❌ **Cannot add plans to existing users** - will return 400 error

**Error Response (if trying to add plans to existing user):**
```json
{
    "detail": "cannot-add-plans-to-existing-user",
    "status_code": 400
}
```

**To Find Available Plans:**
```bash
GET /v1/payments/academy/plan?cohort={cohort_id}
Headers:
  Academy: {academy_id}
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