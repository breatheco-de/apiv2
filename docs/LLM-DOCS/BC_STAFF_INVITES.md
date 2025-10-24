# Staff Member Invitations

This document covers how to invite staff members to an academy, including how to fetch available roles and manage invitations.

## Overview

Staff members are non-student members of an academy who have administrative, teaching, or support roles. Unlike students, staff members are assigned specific roles that grant them capabilities to perform various actions within the academy.

## Table of Contents

1. [Fetch Available Roles](#fetch-available-roles)
2. [Invite Staff Member](#invite-staff-member)
3. [Add Existing User as Staff](#add-existing-user-as-staff)
4. [List Staff Members](#list-staff-members)
5. [Resend Staff Invitation](#resend-staff-invitation)
6. [Accept Staff Invitation](#accept-staff-invitation)
7. [Common Use Cases](#common-use-cases)

---

## Fetch Available Roles

Before inviting a staff member, you need to know which roles are available.

### Get All Roles

**Endpoint:** `GET /v1/auth/role`

**Authentication:** Not required (public endpoint)

**Response:**
```json
[
  {
    "id": 1,
    "slug": "admin",
    "name": "Admin"
  },
  {
    "id": 2,
    "slug": "teacher",
    "name": "Teacher"
  },
  {
    "id": 3,
    "slug": "academy_coordinator",
    "name": "Mentor in residence"
  }
]
```

### Get Specific Role Details

**Endpoint:** `GET /v1/auth/role/{role_slug}`

**Authentication:** Not required (public endpoint)

**Response:**
```json
{
  "id": 2,
  "slug": "teacher",
  "name": "Teacher",
  "capabilities": [
    {
      "slug": "read_assignment",
      "description": "Read assignment information"
    },
    {
      "slug": "crud_assignment",
      "description": "Create, update or delete assignments"
    }
  ]
}
```

### Available Staff Roles

Here are the main roles available for staff members:

| Role Slug | Role Name | Description |
|-----------|-----------|-------------|
| `admin` | Admin | Full access to all academy features |
| `staff` | Staff (Base) | Base staff role with read access to most features |
| `read_only` | Read Only (Base) | Read-only access to academy resources |
| `basic` | Basic (Base) | Minimal staff access |
| `academy_token` | Academy Token | Token-based access for integrations |
| `teacher` | Teacher | Can manage cohorts, students, and assignments |
| `assistant` | Teacher Assistant | Can assist with cohorts and assignments |
| `academy_coordinator` | Mentor in residence | Advanced teaching role with additional permissions |
| `career_support` | Career Support | Career services and job placement support |
| `admissions_developer` | Admissions Developer | Manage admissions and student lifecycle |
| `country_manager` | Country Manager | Manage academy operations at country level |
| `syllabus_coordinator` | Syllabus Coordinator | Manage curriculum and content |
| `community_manager` | Community Manager | Manage events, content, and community |
| `growth_manager` | Growth Manager | Marketing and growth operations |
| `culture_and_recruitment` | Culture and Recruitment | HR and recruitment |
| `homework_reviewer` | Homework Reviewer | Review student assignments |

---

## Invite Staff Member

Invite a new user to join your academy as a staff member.

### Endpoint

**POST** `/v1/auth/academy/member`

**Headers:**
```
Authorization: Token <your_token>
Academy: <academy_id>
```

**Required Capability:** `crud_member`

### Request Body

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "role": "teacher",
  "invite": true
}
```

### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `first_name` | string | Yes | Staff member's first name |
| `last_name` | string | Yes | Staff member's last name |
| `email` | string | Yes | Staff member's email address (must be unique) |
| `role` | string | Yes | Role slug (e.g., "teacher", "admin", "staff") |
| `invite` | boolean | No | If true, sends invitation email (default: true) |
| `phone` | string | No | Staff member's phone number |
| `address` | string | No | Staff member's address |

### Response

**Status Code:** `201 Created`

```json
{
  "id": 123,
  "user": null,
  "email": "john.doe@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": {
    "id": 2,
    "slug": "teacher",
    "name": "Teacher"
  },
  "academy": {
    "id": 4,
    "slug": "downtown-miami",
    "name": "Downtown Miami"
  },
  "status": "INVITED",
  "phone": null,
  "address": null,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Example Request

```bash
curl -X POST "https://breathecode.herokuapp.com/v1/auth/academy/member" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 4" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Sarah",
    "last_name": "Johnson",
    "email": "sarah.johnson@example.com",
    "role": "academy_coordinator",
    "invite": true
  }'
```

---

## Add Existing User as Staff

If the user already exists in the system, they will be immediately added to the academy without sending an invitation email.

### Endpoint

**POST** `/v1/auth/academy/member`

**Request Body:**

```json
{
  "user": 456,
  "role": "teacher",
  "invite": false
}
```

### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user` | integer | Yes | Existing user's ID |
| `role` | string | Yes | Role slug to assign |
| `invite` | boolean | No | Set to false to skip invitation email |

### Response

**Status Code:** `201 Created`

```json
{
  "id": 124,
  "user": {
    "id": 456,
    "email": "existing.user@example.com",
    "first_name": "Mike",
    "last_name": "Smith"
  },
  "email": "existing.user@example.com",
  "first_name": "Mike",
  "last_name": "Smith",
  "role": {
    "id": 2,
    "slug": "teacher",
    "name": "Teacher"
  },
  "academy": {
    "id": 4,
    "slug": "downtown-miami",
    "name": "Downtown Miami"
  },
  "status": "ACTIVE",
  "created_at": "2024-01-15T10:35:00Z"
}
```

---

## List Staff Members

Retrieve a list of all staff members in your academy.

### Endpoint

**GET** `/v1/auth/academy/member`

**Headers:**
```
Authorization: Token <your_token>
Academy: <academy_id>
```

**Required Capability:** `read_member`

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `roles` | string | Filter by role slugs (comma-separated), e.g., `roles=teacher,admin` |
| `status` | string | Filter by status: `INVITED`, `ACTIVE` |
| `like` | string | Search by name or email |
| `limit` | integer | Number of results per page (default: 10) |
| `offset` | integer | Pagination offset |

### Response

**Status Code:** `200 OK`

```json
{
  "count": 25,
  "first": null,
  "next": "https://breathecode.herokuapp.com/v1/auth/academy/member?limit=10&offset=10",
  "previous": null,
  "last": null,
  "results": [
    {
      "id": 123,
      "user": {
        "id": 456,
        "email": "john.doe@example.com",
        "first_name": "John",
        "last_name": "Doe"
      },
      "email": "john.doe@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": {
        "id": 2,
        "slug": "teacher",
        "name": "Teacher"
      },
      "status": "ACTIVE",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Example Requests

```bash
# Get all staff members (excluding students)
curl "https://breathecode.herokuapp.com/v1/auth/academy/member" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 4"

# Get only teachers
curl "https://breathecode.herokuapp.com/v1/auth/academy/member?roles=teacher" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 4"

# Get invited but not yet active staff
curl "https://breathecode.herokuapp.com/v1/auth/academy/member?status=INVITED" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 4"

# Search for staff by name
curl "https://breathecode.herokuapp.com/v1/auth/academy/member?like=john" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 4"
```

---

## Resend Staff Invitation

Resend an invitation email to a staff member who hasn't accepted yet.

### Endpoint

**PUT** `/v1/auth/academy/member/{profileacademy_id}/invite`

**Headers:**
```
Authorization: Token <your_token>
Academy: <academy_id>
```

**Required Capability:** `invite_resend`

### Response

**Status Code:** `200 OK`

```json
{
  "id": 789,
  "email": "john.doe@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": {
    "slug": "teacher",
    "name": "Teacher"
  },
  "academy": {
    "id": 4,
    "slug": "downtown-miami",
    "name": "Downtown Miami"
  },
  "status": "PENDING",
  "sent_at": "2024-01-15T10:45:00Z",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Rate Limiting

Invitations can only be resent after 2 minutes from the last send. If you try to resend before this time, you'll receive an error:

```json
{
  "detail": "Impossible to resend invitation",
  "status_code": 400,
  "slug": "sent-at-diff-less-two-minutes"
}
```

### Example Request

```bash
curl -X PUT "https://breathecode.herokuapp.com/v1/auth/academy/member/123/invite" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 4"
```

---

## Accept Staff Invitation

When a staff member receives an invitation email, they need to accept it to join the academy.

### Accept Invitation Flow

1. **User clicks invitation link** in email
2. **User is redirected** to: `/v1/auth/member/invite/{token}`
3. **User provides information** (if new user):
   - Password
   - Confirms email
4. **System creates/updates** user account and profile

### Invitation Token Endpoint

**GET** `/v1/auth/member/invite/{token}`

This endpoint displays a form for the user to accept the invitation.

### Accept Invitation API

**POST** `/v1/auth/member/invite/{token}`

**Request Body (for new users):**

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "password": "securePassword123!",
  "repeat_password": "securePassword123!"
}
```

### Response

**Status Code:** `200 OK`

```json
{
  "token": "new_authentication_token_here",
  "user": {
    "id": 456,
    "email": "john.doe@example.com",
    "first_name": "John",
    "last_name": "Doe"
  },
  "profile": {
    "id": 123,
    "role": {
      "slug": "teacher",
      "name": "Teacher"
    },
    "academy": {
      "id": 4,
      "slug": "downtown-miami",
      "name": "Downtown Miami"
    },
    "status": "ACTIVE"
  }
}
```

---

## Common Use Cases

### 1. Invite a New Teacher

```bash
curl -X POST "https://breathecode.herokuapp.com/v1/auth/academy/member" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 4" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Maria",
    "last_name": "Garcia",
    "email": "maria.garcia@example.com",
    "role": "teacher",
    "invite": true
  }'
```

### 2. Promote Existing User to Admin

```bash
curl -X POST "https://breathecode.herokuapp.com/v1/auth/academy/member" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 4" \
  -H "Content-Type: application/json" \
  -d '{
    "user": 789,
    "role": "admin",
    "invite": false
  }'
```

### 3. List All Teachers and Coordinators

```bash
curl "https://breathecode.herokuapp.com/v1/auth/academy/member?roles=teacher,academy_coordinator" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 4"
```

### 4. Find Pending Staff Invitations

```bash
curl "https://breathecode.herokuapp.com/v1/auth/academy/member?status=INVITED" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 4"
```

### 5. Bulk Invite Staff Members

```bash
# Invite multiple staff members
for email in "teacher1@example.com" "teacher2@example.com" "admin@example.com"; do
  curl -X POST "https://breathecode.herokuapp.com/v1/auth/academy/member" \
    -H "Authorization: Token YOUR_TOKEN" \
    -H "Academy: 4" \
    -H "Content-Type: application/json" \
    -d "{
      \"first_name\": \"Staff\",
      \"last_name\": \"Member\",
      \"email\": \"$email\",
      \"role\": \"teacher\",
      \"invite\": true
    }"
done
```

---

## Error Handling

### Common Errors

#### Email Already Exists

```json
{
  "detail": "User with this email already exists in this academy",
  "status_code": 400,
  "slug": "user-exists"
}
```

#### Invalid Role

```json
{
  "detail": "Role not found",
  "status_code": 404,
  "slug": "role-not-found"
}
```

#### Missing Permissions

```json
{
  "detail": "You don't have permission to perform this action",
  "status_code": 403,
  "slug": "permission-denied"
}
```

#### Invitation Not Found

```json
{
  "detail": "No pending invite was found for this user and academy",
  "status_code": 404,
  "slug": "user-invite-not-found"
}
```

---

## Best Practices

1. **Choose the Right Role**: Select the role with the minimum permissions needed for the staff member's responsibilities.

2. **Verify Email Addresses**: Ensure email addresses are correct before sending invitations to avoid bounced emails.

3. **Use Descriptive Names**: Provide full first and last names for better identification in the system.

4. **Check Existing Members**: Before inviting, check if the user already exists to avoid duplicate invitations.

5. **Monitor Pending Invitations**: Regularly check for pending invitations and resend if necessary.

6. **Document Permissions**: Keep track of which roles have which capabilities for your organization.

7. **Onboarding Process**: Have a documented onboarding process for new staff members after they accept invitations.

---

## Related Endpoints

- **List Roles**: `GET /v1/auth/role` - Get all available roles
- **Update Member**: `PUT /v1/auth/academy/member/{id}` - Update staff member details
- **Remove Member**: `DELETE /v1/auth/academy/member/{id}` - Remove staff member from academy
- **Get Member**: `GET /v1/auth/academy/member/{id}` - Get specific staff member details

---

## Notes

- Staff members cannot be students at the same academy simultaneously
- The `student` role is handled separately through the student enrollment process
- Invitations expire after a certain period (check your academy settings)
- Staff members can be assigned to specific cohorts with different roles
- Email whitelabeling is applied automatically using the academy's branding

---

## Support

For additional support or questions about staff invitations, please contact the 4Geeks development team or refer to the main API documentation.
