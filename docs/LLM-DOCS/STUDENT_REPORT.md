# Student Report API - Complete Guide

This document provides a comprehensive guide for academies to retrieve complete information about their students using the BreatheCode API.

## Table of Contents

1. [Overview](#overview)
2. [Authentication & Permissions](#authentication--permissions)
3. [Core Student Endpoints](#core-student-endpoints)
4. [Student Data by Category](#student-data-by-category)
5. [Complete Student Report Workflow](#complete-student-report-workflow)
6. [Query Parameters Reference](#query-parameters-reference)
7. [Response Examples](#response-examples)

---

## Overview

The BreatheCode API provides multiple endpoints to gather comprehensive information about students. This includes:

- **Basic Profile**: User information, contact details, GitHub profile
- **Enrollment Status**: Cohort assignments, educational status, financial status
- **Academic Progress**: Tasks, assignments, projects, code reviews
- **Mentorship**: Sessions, feedback, mentor interactions
- **Activity**: Learning activity, attendance, engagement metrics
- **History**: Cohort changes, status updates, timeline

---

## Authentication & Permissions

### Required Headers

All academy-scoped endpoints require:

```http
Authorization: Token {your-access-token}
Academy: {academy_id}
```

### Required Permissions

Different endpoints require different capabilities:

- **`read_student`** - View basic student information
- **`read_all_cohort`** - View cohort and enrollment data
- **`task_delivery_details`** - View student assignments and tasks
- **`read_mentorship_session`** - View mentorship sessions
- **`read_activity`** - View student activity logs

> **Note**: Academy staff with appropriate roles automatically have these permissions. See [create_academy_roles.py](mdc:breathecode/authenticate/management/commands/create_academy_roles.py) for full capability list.

---

## Core Student Endpoints

### 1. Get Basic Student Profile

**Endpoint:** `GET /v1/auth/academy/student/{user_id_or_email}`

**Purpose:** Get basic student information including profile, status, and academy role.

**Parameters:**
- `user_id_or_email` - Can be numeric user ID or email address

**Headers:**
```http
Authorization: Token {token}
Academy: {academy_id}
```

**Response includes:**
- User details: `id`, `first_name`, `last_name`, `email`
- Profile: `avatar_url`, `phone`, `bio`
- GitHub: `username`, `avatar_url`, `name`
- Role: Academy role and permissions
- Status: `ACTIVE`, `INVITED`, etc.

**Example:**
```bash
GET https://breathecode.herokuapp.com/v1/auth/academy/student/123
Authorization: Token abc123...
Academy: 4
```

**Response:**
```json
{
  "id": 123,
  "user": {
    "id": 123,
    "email": "student@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "github": {
      "username": "johndoe",
      "avatar_url": "https://avatars.githubusercontent.com/u/123?v=4"
    }
  },
  "role": {
    "slug": "student",
    "name": "Student"
  },
  "status": "ACTIVE",
  "phone": "+1234567890",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### 2. List All Academy Students

**Endpoint:** `GET /v1/auth/academy/student`

**Purpose:** Get list of all students in the academy with filtering options.

**Query Parameters:**
- `like={text}` - Search by name or email
- `status=ACTIVE|INVITED` - Filter by profile status
- `cohort={slug1,slug2}` - Filter by cohort slugs
- `limit={number}` - Pagination limit
- `offset={number}` - Pagination offset

**Example:**
```bash
GET https://breathecode.herokuapp.com/v1/auth/academy/student?cohort=web-dev-pt-01&status=ACTIVE
Authorization: Token abc123...
Academy: 4
```

---

## Student Data by Category

### A. Enrollment & Cohort Information

#### Get Student's Cohort Enrollments

**Endpoint:** `GET /v1/admissions/academy/cohort/user`

**Purpose:** Get detailed cohort enrollment information including educational and financial status.

**Query Parameters:**
- `users={user_id1,user_id2}` - Filter by specific user IDs
- `roles=STUDENT` - Filter by role (use STUDENT for students)
- `educational_status={status}` - Filter by educational status
  - Options: `ACTIVE`, `POSTPONED`, `SUSPENDED`, `GRADUATED`, `DROPPED`, `NOT_COMPLETING`
- `finantial_status={status}` - Filter by financial status
  - Options: `FULLY_PAID`, `UP_TO_DATE`, `LATE`
- `cohorts={slug1,slug2}` - Filter by cohort slugs
- `syllabus={slug}` - Filter by syllabus slug
- `like={name}` - Search by student name
- `distinct=true` - Get unique users only (if student in multiple cohorts)
- `sort={field}` - Sort results (default: `-created_at`)

**Example:**
```bash
GET https://breathecode.herokuapp.com/v1/admissions/academy/cohort/user?users=123&roles=STUDENT
Authorization: Token abc123...
Academy: 4
```

**Response:**
```json
[
  {
    "id": 456,
    "user": {
      "id": 123,
      "email": "student@example.com",
      "first_name": "John",
      "last_name": "Doe"
    },
    "cohort": {
      "id": 10,
      "slug": "web-dev-pt-01",
      "name": "Web Development Part-Time Cohort 01",
      "stage": "STARTED",
      "current_day": 45,
      "syllabus_version": {
        "name": "Full-Stack Software Development",
        "slug": "full-stack"
      }
    },
    "role": "STUDENT",
    "educational_status": "ACTIVE",
    "finantial_status": "UP_TO_DATE",
    "created_at": "2024-01-15T10:00:00Z",
    "watching": true
  }
]
```

---

#### Get Student in Specific Cohort

**Endpoint:** `GET /v1/admissions/academy/cohort/{cohort_id}/user/{user_id}`

**Purpose:** Get detailed information about a student in a specific cohort, including optional task data.

**Query Parameters:**
- `tasks=True` - Include task/assignment statistics

**Example:**
```bash
GET https://breathecode.herokuapp.com/v1/admissions/academy/cohort/10/user/123?tasks=True
Authorization: Token abc123...
Academy: 4
```

**Response with tasks=True:**
```json
{
  "id": 456,
  "user": {
    "id": 123,
    "email": "student@example.com",
    "first_name": "John",
    "last_name": "Doe"
  },
  "cohort": {
    "id": 10,
    "slug": "web-dev-pt-01",
    "name": "Web Development Part-Time Cohort 01"
  },
  "role": "STUDENT",
  "educational_status": "ACTIVE",
  "finantial_status": "UP_TO_DATE",
  "tasks": {
    "total": 50,
    "completed": 35,
    "pending": 10,
    "approved": 30,
    "rejected": 3
  }
}
```

---

#### Get Cohort Details

**Endpoint:** `GET /v1/admissions/academy/cohort/{cohort_id}`

**Purpose:** Get complete cohort information including syllabus, schedule, and settings.

**Example:**
```bash
GET https://breathecode.herokuapp.com/v1/admissions/academy/cohort/10
Authorization: Token abc123...
Academy: 4
```

---

### B. Tasks & Assignments

#### Get Student's Tasks

**Endpoint:** `GET /v1/assignments/user/{user_id}/task`

**Purpose:** Get all tasks/assignments for a specific student.

**Query Parameters:**
- `cohort={cohort_id}` - Filter by cohort
- `task_status={status}` - Filter by status
  - Options: `PENDING`, `DONE`, `APPROVED`, `REJECTED`
- `task_type={type}` - Filter by type
  - Options: `EXERCISE`, `PROJECT`, `QUIZ`, `LESSON`
- `revision_status={status}` - Filter by review status
- `limit={number}` - Pagination limit
- `offset={number}` - Pagination offset

**Example:**
```bash
GET https://breathecode.herokuapp.com/v1/assignments/user/123/task?task_type=PROJECT
Authorization: Token abc123...
Academy: 4
```

**Response:**
```json
[
  {
    "id": 789,
    "title": "Build a Todo App",
    "task_type": "PROJECT",
    "task_status": "DONE",
    "revision_status": "APPROVED",
    "github_url": "https://github.com/johndoe/todo-app",
    "live_url": "https://todo-app.vercel.app",
    "description": "A full-stack todo application",
    "opened_at": "2024-02-01T10:00:00Z",
    "delivered_at": "2024-02-10T15:30:00Z",
    "approved_at": "2024-02-11T09:00:00Z",
    "cohort": {
      "id": 10,
      "slug": "web-dev-pt-01"
    },
    "associated_slug": "build-todo-app-react"
  }
]
```

---

#### Get Specific Task Details

**Endpoint:** `GET /v1/assignments/user/{user_id}/task/{task_id}`

**Purpose:** Get detailed information about a specific task.

**Example:**
```bash
GET https://breathecode.herokuapp.com/v1/assignments/user/123/task/789
Authorization: Token abc123...
Academy: 4
```

---

#### Get Task Code Reviews

**Endpoint:** `GET /v1/assignments/academy/coderevision`

**Purpose:** Get code reviews for student tasks.

**Query Parameters:**
- `author={user_id}` - Filter by student (task author)
- `reviewer={user_id}` - Filter by reviewer
- `task={task_id}` - Filter by specific task
- `status={status}` - Filter by review status
  - Options: `PENDING`, `APPROVED`, `REJECTED`, `IGNORED`

**Example:**
```bash
GET https://breathecode.herokuapp.com/v1/assignments/academy/coderevision?author=123
Authorization: Token abc123...
Academy: 4
```

**Response:**
```json
[
  {
    "id": 101,
    "task": {
      "id": 789,
      "title": "Build a Todo App"
    },
    "author": {
      "id": 123,
      "first_name": "John",
      "last_name": "Doe"
    },
    "reviewer": {
      "id": 456,
      "first_name": "Jane",
      "last_name": "Smith"
    },
    "status": "APPROVED",
    "comments": "Great job! Clean code and good practices.",
    "created_at": "2024-02-11T08:30:00Z"
  }
]
```

---

#### Get Task Commit Files

**Endpoint:** `GET /v1/assignments/academy/task/{task_id}/commitfile`

**Purpose:** Get commit history and files for a task.

**Example:**
```bash
GET https://breathecode.herokuapp.com/v1/assignments/academy/task/789/commitfile
Authorization: Token abc123...
Academy: 4
```

---

#### Get Cohort Tasks Overview

**Endpoint:** `GET /v1/assignments/academy/cohort/{cohort_id}/task`

**Purpose:** Get all tasks for a cohort (useful for comparing student progress).

**Query Parameters:**
- `task_type={type}` - Filter by type
- `user={user_id}` - Filter by specific user

**Example:**
```bash
GET https://breathecode.herokuapp.com/v1/assignments/academy/cohort/10/task?user=123
Authorization: Token abc123...
Academy: 4
```

---

#### Get Student's Final Projects

**Endpoint:** `GET /v1/assignments/academy/cohort/{cohort_id}/final_project`

**Purpose:** Get final project submissions for cohort students.

**Query Parameters:**
- `user={user_id}` - Filter by specific student

**Example:**
```bash
GET https://breathecode.herokuapp.com/v1/assignments/academy/cohort/10/final_project?user=123
Authorization: Token abc123...
Academy: 4
```

---

### C. Mentorship Sessions

#### Get Student's Mentorship Sessions

**Endpoint:** `GET /v1/mentorship/academy/session`

**Purpose:** Get all mentorship sessions for a student.

**Query Parameters:**
- `student={name}` - Filter by student name (fuzzy search)
- `mentor={name}` - Filter by mentor name
- `status={status}` - Filter by session status
  - Options: `PENDING`, `STARTED`, `COMPLETED`, `FAILED`, `IGNORED`
- `with_feedback={true|false}` - Filter by feedback presence
- `mentee={user_id}` - Filter by student user ID
- `started_after={date}` - Filter sessions after date (ISO format)
- `ended_before={date}` - Filter sessions before date (ISO format)
- `limit={number}` - Pagination limit
- `offset={number}` - Pagination offset

**Example:**
```bash
GET https://breathecode.herokuapp.com/v1/mentorship/academy/session?student=John Doe&with_feedback=true
Authorization: Token abc123...
Academy: 4
```

**Response:**
```json
[
  {
    "id": 234,
    "mentor": {
      "id": 456,
      "user": {
        "first_name": "Jane",
        "last_name": "Smith"
      }
    },
    "mentee": {
      "id": 123,
      "first_name": "John",
      "last_name": "Doe",
      "email": "student@example.com"
    },
    "service": {
      "name": "Code Review Session",
      "slug": "code-review"
    },
    "status": "COMPLETED",
    "started_at": "2024-02-15T14:00:00Z",
    "ended_at": "2024-02-15T15:00:00Z",
    "summary": "Reviewed React component structure",
    "answer": {
      "score": 9,
      "comment": "Very helpful session, learned a lot about hooks",
      "lowest": "Time management",
      "highest": "Technical knowledge"
    }
  }
]
```

---

### D. Activity & Engagement

#### Get Student Activity

**Endpoint:** `GET /v1/activity/academy/student/{student_id}`

**Purpose:** Get activity log for a specific student.

**Query Parameters:**
- `cohort={cohort_id}` - Filter by cohort
- `start={date}` - Filter from date (ISO format)
- `end={date}` - Filter to date (ISO format)

**Example:**
```bash
GET https://breathecode.herokuapp.com/v1/activity/academy/student/123
Authorization: Token abc123...
Academy: 4
```

**Response:**
```json
[
  {
    "id": 567,
    "slug": "lesson_opened",
    "user": {
      "id": 123,
      "first_name": "John",
      "last_name": "Doe"
    },
    "cohort": {
      "id": 10,
      "slug": "web-dev-pt-01"
    },
    "day": 45,
    "created_at": "2024-02-20T10:30:00Z",
    "data": {
      "slug": "learn-react-hooks",
      "title": "Learn React Hooks"
    }
  },
  {
    "id": 568,
    "slug": "exercise_started",
    "user": {
      "id": 123,
      "first_name": "John",
      "last_name": "Doe"
    },
    "cohort": {
      "id": 10,
      "slug": "web-dev-pt-01"
    },
    "day": 45,
    "created_at": "2024-02-20T11:00:00Z",
    "data": {
      "slug": "react-hooks-practice"
    }
  }
]
```

---

#### Get Cohort Activity Report

**Endpoint:** `GET /v1/activity/academy/cohort/{cohort_id}`

**Purpose:** Get activity metrics for entire cohort (useful for comparing student engagement).

**Query Parameters:**
- `user={user_id}` - Filter by specific student

**Example:**
```bash
GET https://breathecode.herokuapp.com/v1/activity/academy/cohort/10?user=123
Authorization: Token abc123...
Academy: 4
```

---

### E. Student History & Timeline

#### Get Student's Cohort History

**Endpoint:** `GET /v1/admissions/academy/cohort/{cohort_id}/log`

**Purpose:** Get timeline of changes for a student in a cohort (status changes, drops, etc.).

**Example:**
```bash
GET https://breathecode.herokuapp.com/v1/admissions/academy/cohort/10/log
Authorization: Token abc123...
Academy: 4
```

**Response:**
```json
[
  {
    "id": 890,
    "cohort": {
      "id": 10,
      "slug": "web-dev-pt-01"
    },
    "user": {
      "id": 123,
      "first_name": "John",
      "last_name": "Doe"
    },
    "changes": {
      "educational_status": {
        "old": "ACTIVE",
        "new": "GRADUATED"
      }
    },
    "created_at": "2024-03-01T10:00:00Z",
    "created_by": {
      "id": 10,
      "first_name": "Admin",
      "last_name": "User"
    }
  }
]
```

---

## Complete Student Report Workflow

### Recommended Approach for Full Student Report

To get a complete picture of a student, follow this workflow:

```bash
# Step 1: Get basic profile and contact information
GET /v1/auth/academy/student/{user_id}

# Step 2: Get cohort enrollments and status
GET /v1/admissions/academy/cohort/user?users={user_id}&roles=STUDENT

# Step 3: For each cohort, get detailed enrollment with tasks
GET /v1/admissions/academy/cohort/{cohort_id}/user/{user_id}?tasks=True

# Step 4: Get all tasks and assignments
GET /v1/assignments/user/{user_id}/task

# Step 5: Get code reviews and feedback
GET /v1/assignments/academy/coderevision?author={user_id}

# Step 6: Get mentorship sessions
GET /v1/mentorship/academy/session?mentee={user_id}

# Step 7: Get activity log
GET /v1/activity/academy/student/{user_id}

# Step 8: Get change history
GET /v1/admissions/academy/cohort/{cohort_id}/log
```

### Example: Python Script to Generate Complete Report

```python
import requests

BASE_URL = "https://breathecode.herokuapp.com"
TOKEN = "your-token-here"
ACADEMY_ID = 4
USER_ID = 123

headers = {
    "Authorization": f"Token {TOKEN}",
    "Academy": str(ACADEMY_ID)
}

def get_student_report(user_id):
    report = {}
    
    # 1. Basic Profile
    response = requests.get(
        f"{BASE_URL}/v1/auth/academy/student/{user_id}",
        headers=headers
    )
    report['profile'] = response.json()
    
    # 2. Cohort Enrollments
    response = requests.get(
        f"{BASE_URL}/v1/admissions/academy/cohort/user",
        params={"users": user_id, "roles": "STUDENT"},
        headers=headers
    )
    report['enrollments'] = response.json()
    
    # 3. Tasks
    response = requests.get(
        f"{BASE_URL}/v1/assignments/user/{user_id}/task",
        headers=headers
    )
    report['tasks'] = response.json()
    
    # 4. Code Reviews
    response = requests.get(
        f"{BASE_URL}/v1/assignments/academy/coderevision",
        params={"author": user_id},
        headers=headers
    )
    report['code_reviews'] = response.json()
    
    # 5. Mentorship Sessions
    response = requests.get(
        f"{BASE_URL}/v1/mentorship/academy/session",
        params={"mentee": user_id},
        headers=headers
    )
    report['mentorship'] = response.json()
    
    # 6. Activity
    response = requests.get(
        f"{BASE_URL}/v1/activity/academy/student/{user_id}",
        headers=headers
    )
    report['activity'] = response.json()
    
    return report

# Generate report
student_report = get_student_report(USER_ID)
print(f"Student: {student_report['profile']['user']['first_name']}")
print(f"Total Tasks: {len(student_report['tasks'])}")
print(f"Total Sessions: {len(student_report['mentorship'])}")
```

---

## Query Parameters Reference

### Educational Status Options
- `ACTIVE` - Currently enrolled and active
- `POSTPONED` - Temporarily postponed
- `SUSPENDED` - Suspended from cohort
- `GRADUATED` - Successfully completed
- `DROPPED` - Dropped out
- `NOT_COMPLETING` - Not planning to complete

### Financial Status Options
- `FULLY_PAID` - Fully paid tuition
- `UP_TO_DATE` - Payment up to date
- `LATE` - Payment overdue

### Task Status Options
- `PENDING` - Not started
- `DONE` - Submitted/delivered
- `APPROVED` - Approved by teacher
- `REJECTED` - Needs revision

### Task Type Options
- `EXERCISE` - Practice exercise
- `PROJECT` - Project assignment
- `QUIZ` - Quiz/assessment
- `LESSON` - Lesson reading

### Session Status Options
- `PENDING` - Scheduled but not started
- `STARTED` - Currently in progress
- `COMPLETED` - Successfully completed
- `FAILED` - Did not complete
- `IGNORED` - Cancelled/ignored

### Cohort Stage Options
- `INACTIVE` - Not yet started
- `PREWORK` - Prework phase
- `STARTED` - Active cohort
- `FINAL_PROJECT` - Final project phase
- `ENDED` - Cohort completed

---

## Response Examples

### Complete Student Profile Response

```json
{
  "basic_profile": {
    "id": 123,
    "email": "student@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "github": {
      "username": "johndoe",
      "avatar_url": "https://avatars.githubusercontent.com/u/123?v=4"
    },
    "status": "ACTIVE"
  },
  "enrollments": [
    {
      "cohort": {
        "id": 10,
        "slug": "web-dev-pt-01",
        "name": "Web Development Part-Time 01",
        "stage": "STARTED",
        "current_day": 45,
        "syllabus": "Full-Stack Software Development"
      },
      "educational_status": "ACTIVE",
      "finantial_status": "UP_TO_DATE",
      "joined_at": "2024-01-15T10:00:00Z"
    }
  ],
  "task_summary": {
    "total": 50,
    "pending": 10,
    "done": 25,
    "approved": 30,
    "rejected": 3,
    "completion_rate": 70.0
  },
  "mentorship_summary": {
    "total_sessions": 8,
    "completed": 7,
    "pending": 1,
    "average_rating": 9.2
  },
  "activity_summary": {
    "last_activity": "2024-02-20T15:30:00Z",
    "total_activities": 450,
    "lessons_opened": 120,
    "exercises_completed": 85
  }
}
```

---

## Best Practices

### 1. Caching
Many endpoints support caching. For frequently accessed data, implement client-side caching to reduce API calls.

### 2. Pagination
Always use pagination for large datasets:
```bash
GET /v1/assignments/user/123/task?limit=50&offset=0
```

### 3. Filtering
Use specific filters to reduce response size:
```bash
# Get only active student's pending tasks
GET /v1/assignments/user/123/task?task_status=PENDING
```

### 4. Batch Requests
When getting data for multiple students, consider batching:
```bash
GET /v1/admissions/academy/cohort/user?users=123,124,125&roles=STUDENT
```

### 5. Error Handling
Always handle common errors:
- `404` - Student/resource not found
- `403` - Insufficient permissions
- `401` - Invalid/expired token
- `400` - Invalid parameters

---

## Related Documentation

- [ADD_STUDENT.md](./ADD_STUDENT.md) - How to add students to academy
- [COHORTS.md](./COHORTS.md) - Cohort management
- [ACADEMY_PLANS.md](./ACADEMY_PLANS.md) - Student plans and subscriptions
- [BC_AUTH_FIRST_PARTY_APPS.md](./BC_AUTH_FIRST_PARTY_APPS.md) - Authentication details

---

## Support

For additional help or questions about the Student Report API:
- Check the main API documentation
- Review permission requirements in `create_academy_roles.py`
- Contact the development team

**Last Updated:** October 2024

