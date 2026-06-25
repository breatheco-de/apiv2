---
name: bc-authenticate-staff-invites
description: Use when inviting, listing, resending, accepting, updating, or removing academy staff members (non-student ProfileAcademy); do NOT use for student enrollment, staff login/capability checks, or custom role CRUD.
requires:
  - bc-authenticate-staff-authentication
---

# Skill: Staff Member Invitations and Management

## When to Use

Use this skill when academy staff need to **invite** a teacher or admin, **list or update** staff members, **resend** pending invitations, **accept** an invitation (invitee onboarding), or **remove** a staff member from an academy. Load [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md) first for login, `Academy` header, and capability checks. Do not use this skill for student enrollment (`/academy/student`), staff login-only tasks, or custom academy role CRUD (future `bc-authenticate-manage-academy-roles` skill).

## Concepts

- **Staff member**: `ProfileAcademy` row with a non-`student` role (`teacher`, `staff`, `admin`, custom `{slug}_{academy_id}`, etc.).
- **Invitation**: `UserInvite` with `status=PENDING` plus `ProfileAcademy` with `status=INVITED` until the invitee accepts.
- **Academy header**: All `/academy/*` admin routes require `Authorization: Token <token>` and **`Academy: <numeric_id>`**.
- **Assignable roles**: Discover via `GET /v1/auth/role` (public). The `student`, `academy_token`, and `admin` slugs are hidden from that list.
- **Student role blocked**: `POST`/`PUT` `/academy/member` reject `role=student` (`cannot-create-student-role` / `cannot-update-student-role`).

## Workflow

1. **Authenticate and verify capabilities.** Complete [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md) Track A, then Track B for the target academy. Typical capabilities: `crud_member` (invite/update/delete), `read_member` (list/get), `invite_resend` (resend), `read_invite` / `crud_invite` (invite admin).

2. **Fetch assignable roles (before inviting).** Call `GET /v1/auth/role` (no auth). Optionally `GET /v1/auth/role/<slug>` for capability list on one role. Save the `slug` for the invite body.

3. **Invite a new user by email.** Call `POST /v1/auth/academy/member` with `first_name`, `last_name`, `email`, `role` (slug), and `invite: true`. Response `201` with `status: "INVITED"` when email is sent.

4. **Add an existing user without email.** Same `POST` with `user` (numeric id) and `invite: false`. Response `201` with `status: "ACTIVE"` when the user already exists.

5. **List staff members.** Call `GET /v1/auth/academy/member` (paginated). Default excludes `student` role and `DELETED` status. Filter with `roles`, `status`, `like`.

6. **Get one member.** Call `GET /v1/auth/academy/member/<user_id_or_email>`.

7. **Update member role.** Call `PUT /v1/auth/academy/member/<user_id>` with `role` (slug or id). **`user_id` must be numeric.**

8. **Remove member (soft delete).** Call `DELETE /v1/auth/academy/member/<user_id_or_email>`. Sets `status=DELETED`.

9. **Resend invitation.** Call `PUT /v1/auth/academy/member/<profileacademy_id>/invite` **or** `PUT /v1/auth/academy/invite/<invite_id>`. Wait at least 2 minutes between resends (`sent-at-diff-less-two-minutes`).

10. **List pending invites (admin).** Call `GET /v1/auth/academy/user/invite` (paginated). Filter: `status`, `role`, `like`, `user_id`, `invite_id`, `profile_academy_id`.

11. **Get one pending invite.** Call `GET /v1/auth/academy/invite/<invite_id>`.

12. **Update invite status.** Call `PATCH /v1/auth/academy/invite/<invite_id>` with `status`. Setting `PENDING` regenerates the invite token.

13. **Delete invites (bulk).** Call `DELETE /v1/auth/academy/user/invite?id=1&id=2`.

14. **Accept invitation (invitee, often no prior login).** User opens `GET /v1/auth/member/invite/<token>` (HTML form). Submit `POST /v1/auth/member/invite/<token>` with `first_name`, `last_name`, `password`, `repeat_password` for new users. On success, save returned login `token` and continue with staff-authentication Track A.

15. **Pending invites for logged-in user.** Call `GET /v1/auth/profile/invite/me` to list pending `UserInvite` and `ProfileAcademy` rows for the current user.

## Endpoints

All paths below are under `/v1/auth`. Send `Accept-Language` (`en`, `es`) for translated errors where applicable.

| Action | Method | Path | Required headers | Capability | Paginated |
|--------|--------|------|------------------|------------|-----------|
| List assignable roles | GET | `/v1/auth/role` | None | — | No |
| Get one role + capabilities | GET | `/v1/auth/role/<slug>` | None | — | No |
| Invite / add staff | POST | `/v1/auth/academy/member` | `Authorization`, **`Academy: <id>`** | `crud_member` | No |
| List staff | GET | `/v1/auth/academy/member` | `Authorization`, **`Academy: <id>`** | `read_member` | **Yes** |
| Get one staff member | GET | `/v1/auth/academy/member/<user_id_or_email>` | `Authorization`, **`Academy: <id>`** | `read_member` | No |
| Update staff role | PUT | `/v1/auth/academy/member/<user_id>` | `Authorization`, **`Academy: <id>`** | `crud_member` | No |
| Remove staff (soft delete) | DELETE | `/v1/auth/academy/member/<user_id_or_email>` | `Authorization`, **`Academy: <id>`** | `crud_member` | No |
| Resend by ProfileAcademy id | PUT | `/v1/auth/academy/member/<profileacademy_id>/invite` | `Authorization`, **`Academy: <id>`** | `invite_resend` | No |
| Resend by invite id | PUT | `/v1/auth/academy/invite/<invite_id>` | `Authorization`, **`Academy: <id>`** | `invite_resend` | No |
| List academy invites | GET | `/v1/auth/academy/user/invite` | `Authorization`, **`Academy: <id>`** | `read_invite` | **Yes** |
| Get one pending invite | GET | `/v1/auth/academy/invite/<invite_id>` | `Authorization`, **`Academy: <id>`** | `read_invite` | No |
| Update invite | PATCH | `/v1/auth/academy/invite/<invite_id>` | `Authorization`, **`Academy: <id>`** | `crud_invite` | No |
| Delete invites (bulk) | DELETE | `/v1/auth/academy/user/invite?id=<id>&id=<id>` | `Authorization`, **`Academy: <id>`** | `crud_invite` | No |
| Accept invite (form) | GET | `/v1/auth/member/invite/<token>` | None | — | No |
| Accept invite (submit) | POST | `/v1/auth/member/invite/<token>` | `Content-Type: application/json` | — | No |
| Pending invites for current user | GET | `/v1/auth/profile/invite/me` | `Authorization` | — | No |

### Invite new staff — request sample

```json
{
  "first_name": "Sarah",
  "last_name": "Johnson",
  "email": "sarah.johnson@example.com",
  "role": "teacher",
  "invite": true
}
```

### Invite new staff — response sample (201)

```json
{
  "id": 123,
  "user": null,
  "email": "sarah.johnson@example.com",
  "first_name": "Sarah",
  "last_name": "Johnson",
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

### Add existing user — request sample

```json
{
  "user": 456,
  "role": "teacher",
  "invite": false
}
```

### Add existing user — response sample (201)

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

### List staff — response sample (200, paginated)

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

### Resend invitation — response sample (200)

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

### Accept invitation — request sample (POST, new user)

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "password": "securePassword123!",
  "repeat_password": "securePassword123!"
}
```

### Accept invitation — response sample (200)

```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
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

### Pending invites for current user — response sample

```json
{
  "invites": [
    {
      "id": 789,
      "email": "john.doe@example.com",
      "status": "PENDING",
      "role": {
        "slug": "teacher",
        "name": "Teacher"
      }
    }
  ],
  "profile_academies": [
    {
      "id": 123,
      "email": "john.doe@example.com",
      "status": "INVITED",
      "role": {
        "slug": "teacher",
        "name": "Teacher"
      },
      "academy": {
        "id": 4,
        "slug": "downtown-miami",
        "name": "Downtown Miami"
      }
    }
  ],
  "mentor_profiles": []
}
```

### Common error samples

```json
{
  "detail": "There is a member already in this academy with this email, or with invitation to this email pending",
  "status_code": 400,
  "slug": "already-exists-with-this-email"
}
```

```json
{
  "detail": "Role not found",
  "status_code": 400,
  "slug": "role-not-found"
}
```

```json
{
  "detail": "This endpoint cannot create student profiles.",
  "status_code": 400,
  "slug": "cannot-create-student-role"
}
```

```json
{
  "detail": "Impossible to resend invitation",
  "status_code": 400,
  "slug": "sent-at-diff-less-two-minutes"
}
```

```json
{
  "detail": "No pending invite was found for this user and academy",
  "status_code": 404,
  "slug": "user-invite-not-found"
}
```

## Edge Cases

- **Missing `Academy` header** on `/academy/*` routes: request fails before capability check.
- **403 capability error**: caller lacks `crud_member`, `read_member`, `invite_resend`, or `read_invite` — re-check capabilities via staff-authentication Track B.
- **Cannot assign `student`**: use `/v1/auth/academy/student` flows instead; member endpoint rejects student role.
- **PUT update requires numeric user id**: email is not accepted on `PUT /academy/member/<id>`.
- **Resend cooldown**: wait 2+ minutes after last send before resending.
- **Duplicate email in academy**: `already-exists-with-this-email` on invite when pending or active member exists.
- **Invitee with existing account**: accept flow may only require password fields if user already exists; still use POST on `/member/invite/<token>`.
- **Soft delete only**: `DELETE` sets `status=DELETED`; member no longer appears in default list (use `include=deleted` on GET list if needed).

## Checklist

1. Load [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md) and confirm required capabilities for the academy.
2. Call `GET /v1/auth/role` to pick a valid non-student `role` slug.
3. Send `POST /v1/auth/academy/member` with `Academy` header to invite or add the user.
4. Verify with `GET /v1/auth/academy/member?status=INVITED` or `GET /v1/auth/academy/user/invite`.
5. If invite not accepted, resend with `PUT .../member/<profileacademy_id>/invite` after 2 minutes.
6. Invitee accepts via `POST /v1/auth/member/invite/<token>` and receives login `token`.
7. After accept, continue staff workflows with the new token via staff-authentication Track B.
