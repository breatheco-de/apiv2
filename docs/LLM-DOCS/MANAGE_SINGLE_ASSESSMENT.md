# Managing Assessments (Quizzes) - Complete Guide

This document provides comprehensive guidance on creating, editing, and managing assessments (quizzes) in the BreatheCode platform. Assessments bridge both the `registry` app (for asset management and syllabus integration) and the `assessment` app (for quiz functionality and student submissions).

## Table of Contents

1. [Overview](#overview)
2. [Dual App Architecture](#dual-app-architecture)
3. [Creating a New Assessment](#creating-a-new-assessment)
4. [Managing Questions & Options](#managing-questions--options)
5. [Editing Assessment Metadata](#editing-assessment-metadata)
6. [Asset Integration](#asset-integration)
7. [GitHub Integration](#github-integration)
8. [Translations](#translations)
9. [Thresholds & Scoring](#thresholds--scoring)
10. [Assessment Layouts](#assessment-layouts)
11. [Student Submissions](#student-submissions)
12. [Archiving vs Deleting](#archiving-vs-deleting)
13. [Testing & Quality](#testing--quality)
14. [Status & Visibility](#status--visibility)
15. [Complete Workflows](#complete-workflows)
16. [API Reference](#api-reference)

---

## Overview

Assessments (quizzes) in BreatheCode serve a dual purpose:
1. **Educational Content**: Part of the curriculum, integrated into syllabi
2. **Student Evaluation**: Track student progress and understanding

### Key Concepts

- **Assessment**: The quiz container with metadata and settings
- **Question**: Individual quiz questions with multiple options
- **Option**: Answer choices for questions (with scores)
- **UserAssessment**: A student's attempt at taking the quiz
- **Answer**: Individual answers within a UserAssessment
- **Asset**: The registry representation for syllabus integration
- **Threshold**: Score-based success/fail criteria

### Base URLs

```
Production: https://breathecode.herokuapp.com
Development: http://localhost:8000
```

---

## Dual App Architecture

Assessments exist in TWO Django apps simultaneously:

### 1. Assessment App (`breathecode.assessment`)

**Purpose**: Quiz functionality and student submissions

**Models**:
- `Assessment` - Core quiz with questions
- `Question` - Individual questions
- `Option` - Answer choices
- `UserAssessment` - Student attempts
- `Answer` - Individual student answers
- `AssessmentThreshold` - Score thresholds

**Endpoints**: `/v1/assessment/*`

### 2. Registry App (`breathecode.registry`)

**Purpose**: Content management and syllabus integration

**Models**:
- `Asset` - Content representation (with `asset_type="QUIZ"`)
- Links to `Assessment` via foreign key

**Endpoints**: `/v1/registry/academy/{academy_id}/asset/*`

### How They Connect

```
Asset (registry)
  ├─ asset_type: "QUIZ"
  ├─ slug: "python-basics-quiz"
  └─ assessment (FK) → Assessment (assessment app)
                         ├─ slug: "python-basics-quiz"
                         ├─ questions: [Question, Question, ...]
                         └─ user submissions: [UserAssessment, ...]
```

**Why Two Apps?**
- **Registry/Asset**: For content management, GitHub sync, syllabus integration, SEO
- **Assessment**: For quiz logic, scoring, student submissions, instant feedback

---

## Creating a New Assessment

There are TWO ways to create an assessment, depending on your starting point.

### Method 1: Create from Scratch (Assessment First)

Create the assessment directly in the assessment app, then optionally create an asset wrapper.

**Endpoint:** `PUT /v1/assessment/{assessment_slug}`

**Headers:**
```http
Authorization: Token {your-token}
Academy: {academy_id}
Content-Type: application/json
```

**Request Body:**

```json
{
  "title": "Python Basics Quiz",
  "lang": "us",
  "is_instant_feedback": true,
  "max_session_duration": "00:30:00",
  "private": false,
  "questions": [
    {
      "title": "What is Python?",
      "question_type": "SELECT",
      "position": 1,
      "options": [
        {
          "title": "A programming language",
          "score": 1.0,
          "position": 1
        },
        {
          "title": "A snake",
          "score": 0.0,
          "position": 2
        },
        {
          "title": "A software",
          "score": 0.5,
          "position": 3
        }
      ]
    },
    {
      "title": "Is Python compiled or interpreted?",
      "question_type": "SELECT",
      "position": 2,
      "options": [
        {
          "title": "Compiled",
          "score": 0.0,
          "position": 1
        },
        {
          "title": "Interpreted",
          "score": 1.0,
          "position": 2
        },
        {
          "title": "Both",
          "score": 0.5,
          "position": 3
        }
      ]
    }
  ]
}
```

**Response (200 OK):**

```json
{
  "id": 123,
  "slug": "python-basics-quiz",
  "title": "Python Basics Quiz",
  "lang": "us",
  "is_instant_feedback": true,
  "max_session_duration": "00:30:00",
  "private": false,
  "is_archived": false,
  "academy": {
    "id": 1,
    "name": "4Geeks Academy"
  },
  "questions": [
    {
      "id": 456,
      "title": "What is Python?",
      "question_type": "SELECT",
      "position": 1,
      "options": [
        {
          "id": 789,
          "title": "A programming language",
          "score": 1.0,
          "position": 1
        },
        {
          "id": 790,
          "title": "A snake",
          "score": 0.0,
          "position": 2
        }
      ]
    }
  ],
  "created_at": "2024-02-20T10:00:00Z",
  "updated_at": "2024-02-20T10:00:00Z"
}
```

**Field Descriptions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | ✅ Yes | Quiz title |
| `lang` | string | ❌ No | Language (us, es, it) - default: "en" |
| `is_instant_feedback` | boolean | ❌ No | Show correct answers immediately - default: true |
| `max_session_duration` | string | ❌ No | Time limit (HH:MM:SS) - default: "00:30:00" |
| `private` | boolean | ❌ No | Private to academy - default: false |
| `questions` | array | ✅ Yes | Array of question objects |

**Question Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | ✅ Yes | Question text |
| `question_type` | string | ❌ No | TEXT, NUMBER, SELECT, SELECT_MULTIPLE - default: SELECT |
| `position` | integer | ❌ No | Order position |
| `help_text` | string | ❌ No | Additional help text |
| `options` | array | ✅ Yes (for SELECT) | Answer options |

**Option Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | ✅ Yes | Option text |
| `score` | float | ✅ Yes | Points awarded (0.0 to 1.0 typically) |
| `position` | integer | ❌ No | Display order |
| `help_text` | string | ❌ No | Additional context |

**Important Rules:**
- At least ONE option per question must have `score > 0`
- Total score of all positive options should equal 1.0 (for percentage scoring)
- Questions with type TEXT don't need options

### Method 2: Create as Asset (Asset First)

Create the quiz as an asset first, then populate questions.

**Step 1: Create Asset**

**Endpoint:** `POST /v1/registry/academy/{academy_id}/asset`

```json
{
  "slug": "python-basics-quiz",
  "title": "Python Basics Quiz",
  "asset_type": "QUIZ",
  "lang": "us",
  "description": "Test your Python knowledge",
  "category": 1,
  "technologies": ["python"],
  "visibility": "PUBLIC",
  "status": "DRAFT"
}
```

**Step 2: Create Assessment and Link**

**Endpoint:** `PUT /v1/assessment/python-basics-quiz`

**Headers:**
```http
Authorization: Token {your-token}
Academy: {academy_id}
Content-Type: application/json
```

**Payload:**
```json
{
  "title": "Python Basics Quiz",
  "questions": [
    {
      "title": "What is Python?",
      "question_type": "SELECT",
      "options": [
        { "title": "A programming language", "score": 1.0 },
        { "title": "A snake", "score": 0.0 }
      ]
    }
  ]
}
```

---

## Managing Questions & Options

### Overview of Question/Option Endpoints

There are **two approaches** to manage questions and options:

#### Approach 1: Bulk Operations (Legacy)
- `PUT /v1/assessment/{slug}` - Update entire assessment with all questions
- ⚠️ **Less efficient**: Must send entire questions array
- ✅ **Use when**: Creating new assessment or updating multiple questions at once

#### Approach 2: Granular Operations (Recommended) ⭐
- `PUT /v1/assessment/{slug}/question/{id}` - Update single question
- `POST /v1/assessment/{slug}/question/{id}/option` - Add option to question
- ✅ **More efficient**: Only send what you're changing
- ✅ **Use when**: Updating individual questions or adding options

---

### Add New Question (Bulk Method)

**Endpoint:** `PUT /v1/assessment/{assessment_slug}`

**Headers:**
```http
Authorization: Token {your-token}
Academy: {academy_id}
Content-Type: application/json
```

**Payload:**
```json
{
  "questions": [
    {
      "title": "What is a Python list?",
      "question_type": "SELECT",
      "position": 3,
      "options": [
        {
          "title": "An ordered collection",
          "score": 1.0,
          "position": 1
        },
        {
          "title": "A dictionary",
          "score": 0.0,
          "position": 2
        }
      ]
    }
  ]
}
```

**⚠️ Important:** Include existing questions in the array if you want to preserve them, or fetch current assessment first and append to the questions array.

### Update Existing Question (Bulk Method)

**Endpoint:** `PUT /v1/assessment/{assessment_slug}`

**Payload:**
```json
{
  "questions": [
    {
      "id": 456,
      "title": "Updated question text",
      "question_type": "SELECT",
      "position": 1
    }
  ]
}
```

**Note:** Include the question `id` to update an existing question.

**⚠️ Limitation:** Must include ALL questions you want to keep in the array.

### Update Single Question (Recommended) ⭐

**Endpoint:** `PUT /v1/assessment/{assessment_slug}/question/{question_id}`

**Headers:**
```http
Authorization: Token {your-token}
Academy: {academy_id}
Content-Type: application/json
```

**Use Case 1: Update question metadata only**

```json
{
  "title": "Updated question text",
  "help_text": "Optional hint for students",
  "position": 2
}
```

**Use Case 2: Update question and modify existing options**

```json
{
  "title": "Updated question text",
  "options": [
    {
      "id": 789,
      "title": "Updated existing option",
      "score": 1.0,
      "position": 1
    },
    {
      "id": 790,
      "title": "Another updated option",
      "score": 0.0,
      "position": 2
    }
  ]
}
```

**Use Case 3: Update question and add new options simultaneously**

```json
{
  "title": "Updated question text",
  "options": [
    {
      "id": 789,
      "title": "Keep this existing option",
      "score": 1.0
    },
    {
      "title": "Create this new option",
      "score": 0.0
    }
  ]
}
```

**Key Behavior:**
- **Option with `id` field**: Updates the existing option
- **Option without `id` field**: Creates a new option
- **Partial updates**: Only send fields you want to change
- **Validation**: Ensures at least one option has positive score (when options provided)

**Benefits:**
- ✅ More efficient than bulk update
- ✅ Partial update support - only send what changes
- ✅ Single request for question + options
- ✅ Mix updates and creates in one call
- ✅ No need to fetch entire assessment first

**Example Response:**
```json
{
  "id": 456,
  "title": "Updated question text",
  "help_text": "Optional hint for students",
  "question_type": "SELECT",
  "position": 2,
  "lang": "en",
  "is_deleted": false,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T14:45:00Z"
}
```

### Update Question Options (Bulk Method)

**Endpoint:** `PUT /v1/assessment/{assessment_slug}`

**Payload:**
```json
{
  "questions": [
    {
      "id": 456,
      "options": [
        {
          "id": 789,
          "title": "Updated option text",
          "score": 1.0,
          "position": 1
        }
      ]
    }
  ]
}
```

**Note:** Include option `id` to update existing options.

**⚠️ Limitation:** Must include ALL questions and options you want to keep.

### Reorder Options

**Method 1: Update single question (Recommended)** ⭐

**Endpoint:** `PUT /v1/assessment/{assessment_slug}/question/{question_id}`

**Payload:**
```json
{
  "options": [
    {
      "id": 790,
      "position": 1
    },
    {
      "id": 791,
      "position": 2
    },
    {
      "id": 789,
      "position": 3
    }
  ]
}
```

**Method 2: Bulk update**

**Endpoint:** `PUT /v1/assessment/{assessment_slug}`

**Payload:**
```json
{
  "questions": [
    {
      "id": 456,
      "options": [
        {
          "id": 790,
          "position": 1
        },
        {
          "id": 791,
          "position": 2
        },
        {
          "id": 789,
          "position": 3
        }
      ]
    }
  ]
}
```

**Note:** The `position` property determines display order. Options are displayed according to their `position` value, not array order.

### Add New Option to Question (Recommended) ⭐

**Endpoint:** `POST /v1/assessment/{assessment_slug}/question/{question_id}/option`

**Headers:**
```http
Authorization: Token {your-token}
Academy: {academy_id}
Content-Type: application/json
```

**Payload:**
```json
{
  "title": "New answer option",
  "help_text": "Optional hint for this option",
  "score": 0.5,
  "position": 3
}
```

**Example Response (201 Created):**
```json
{
  "id": 123,
  "title": "New answer option",
  "help_text": "Optional hint for this option",
  "score": 0.5,
  "position": 3,
  "lang": "en",
  "is_deleted": false,
  "created_at": "2024-01-15T15:30:00Z",
  "updated_at": "2024-01-15T15:30:00Z"
}
```

**When to Use:**
- Adding a single new option to existing question
- Building questions incrementally
- Simple, focused operation

**Benefits:**
- ✅ Proper REST resource nesting (`/question/{id}/option`)
- ✅ Single focused operation
- ✅ Returns created option with ID
- ✅ No need to send existing options
- ✅ Clean and simple payload

**Alternative:** You can also add options via `PUT /question/{id}` with options array (see above).

### Delete Question

**Endpoint:** `DELETE /v1/assessment/{assessment_slug}/question/{question_id}`

**Headers:**
```http
Authorization: Token {your-token}
Academy: {academy_id}
```

**Note:** Questions with collected answers cannot be deleted, they will be marked as `is_deleted=true` instead.

**Response:** `204 No Content` on success.

### Delete Option

**Endpoint:** `DELETE /v1/assessment/{assessment_slug}/option/{option_id}`

**Headers:**
```http
Authorization: Token {your-token}
Academy: {academy_id}
```

**Note:** Options with collected answers cannot be deleted, they will be marked as `is_deleted=true` instead.

**Response:** `204 No Content` on success.

### Question Types

| Type | Description | Use Case | Requires Options |
|------|-------------|----------|------------------|
| `SELECT` | Single choice | Multiple choice questions | ✅ Yes |
| `SELECT_MULTIPLE` | Multiple choices | "Select all that apply" | ✅ Yes |
| `TEXT` | Free text | Short answer questions | ❌ No |
| `NUMBER` | Numeric input | Mathematical answers | ❌ No |

---

## Editing Assessment Metadata

### Update Assessment Settings

**Endpoint:** `PUT /v1/assessment/{assessment_slug}`

Update only the assessment metadata without touching questions:

```json
{
  "title": "Updated Quiz Title",
  "is_instant_feedback": false,
  "max_session_duration": "01:00:00",
  "private": true
}
```

### Update via Asset (Registry)

You can also update the asset representation:

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/python-basics-quiz`

```json
{
  "title": "Python Basics Quiz (Updated)",
  "description": "Updated description",
  "status": "PUBLISHED",
  "difficulty": "INTERMEDIATE"
}
```

**What can be updated via Asset:**
- Title, description
- Status, visibility
- Technologies, category
- README content
- Difficulty, duration
- SEO metadata

**What must be updated via Assessment:**
- Questions and options
- Is_instant_feedback
- Max_session_duration
- Score thresholds

---

## Asset Integration

Every quiz should have both an Assessment (for quiz logic) and an Asset (for content management).

### Create Asset for Existing Assessment

**Endpoint:** `POST /v1/registry/academy/{academy_id}/asset`

```json
{
  "slug": "python-basics-quiz",
  "title": "Python Basics Quiz",
  "asset_type": "QUIZ",
  "assessment": 123,
  "readme_url": "https://github.com/.../python-quiz.md",
  "technologies": ["python"],
  "category": 1,
  "status": "PUBLISHED"
}
```

### Link Existing Asset to Assessment

The connection happens automatically when:
1. Asset slug matches Assessment slug
2. Asset type is "QUIZ"

The system auto-links them on save.

### View Asset-Assessment Connection

**Get Asset:**

**Endpoint:** `GET /v1/registry/academy/{academy_id}/asset/python-basics-quiz`

**Headers:**
```http
Authorization: Token {your-token}
Academy: {academy_id}
```

**Response includes `assessment` field:**
```json
{
  "id": 123,
  "slug": "python-basics-quiz",
  "assessment": {
    "id": 456,
    "slug": "python-basics-quiz"
  }
}
```

**Get Assessment:**

**Endpoint:** `GET /v1/assessment/python-basics-quiz`

**Headers:**
```http
Authorization: Token {your-token}
```

**Response includes `asset_set` field** with related assets.

---

## GitHub Integration

Quiz assessments can sync with GitHub for version control and content management.

### ⚠️ Important: GitHub Sync Limitations

**Critical:** When pulling a QUIZ asset from GitHub, the behavior differs based on whether the assessment already has questions:

#### First Pull (No Assessment Exists)

When you pull for the first time:

✅ **Creates Assessment** with all questions from `learn.json`
✅ **Asset.config and Assessment are in sync**
✅ **All questions and options created**

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/{asset_slug}/action/pull`

**Result:** Asset created, Assessment created with all questions from config.

#### Subsequent Pulls (Assessment Has Questions)

When you pull after questions exist:

✅ **Updates `asset.config`** with latest from GitHub
❌ **Does NOT update Assessment** questions/options
⚠️ **Asset and Assessment become out of sync**

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/{asset_slug}/action/pull`

**Result:** `asset.config` updated, but Assessment questions remain unchanged.

**Why This Limitation?**

To protect student submission data. Updating questions would invalidate existing student answers and corrupt historical data.

#### How to Update Existing Assessment Questions

If you need to update questions after students have taken the quiz:

**Option 1: Create New Version (Recommended)**

Step 1: Create new asset with updated slug

**Endpoint:** `POST /v1/registry/academy/{academy_id}/asset`

**Payload:**
```json
{
  "slug": "python-quiz-v2",
  "title": "Python Quiz (Updated 2024)",
  "asset_type": "QUIZ",
  "readme_url": "https://github.com/.../learn.json"
}
```

Step 2: Pull to create new assessment

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/python-quiz-v2/action/pull`

Step 3: Mark old version as superseded

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/python-quiz`

**Payload:**
```json
{
  "superseded_by": 789,
  "status": "DRAFT"
}
```

**Option 2: Manual Update via API**

Step 1: Pull to get latest `asset.config`

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/{asset_slug}/action/pull`

Step 2: Get updated config

**Endpoint:** `GET /v1/registry/academy/{academy_id}/asset/{asset_slug}`

Step 3: Update assessment with transformed questions

**Endpoint:** `PUT /v1/assessment/{assessment_slug}`

**Payload:**
```json
{
  "questions": [
    // Transform asset.config.questions to assessment format
  ]
}
```

**Option 3: Delete and Recreate (Only if NO student submissions)**

Step 1: Delete all questions via Django admin or API

Step 2: Pull from GitHub again

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/{asset_slug}/action/pull`

Questions will be recreated from config.

### Store Quiz in GitHub (learn.json format)

Quizzes are typically stored as `learn.json` in a LearnPack repository:

```json
{
  "info": {
    "slug": "python-basics-quiz",
    "title": "Python Basics Quiz",
    "main": "Python quiz for beginners"
  },
  "questions": [
    {
      "q": "What is Python?",
      "a": [
        {
          "option": "A programming language",
          "correct": true
        },
        {
          "option": "A snake",
          "correct": false
        }
      ]
    }
  ]
}
```

### Pull from GitHub

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/{asset_slug}/action/pull`

**Headers:**
```http
Authorization: Token {your-token}
Academy: {academy_id}
```

**Purpose:** Pull quiz questions from GitHub `learn.json`

**What Gets Synced:**
- Questions and options from `learn.json` (only if assessment doesn't exist yet)
- Quiz metadata (title, description, technologies)
- Asset config updated
- README content (if exists)

### Push to GitHub

**Note:** Currently, quiz questions are typically managed in GitHub directly. The pull action is more common than push for quizzes.

---

## Translations

Assessments support multiple language translations.

### View Translations

**Endpoint:** `GET /v1/assessment/{assessment_slug}?lang={lang_code}`

**Headers:**
```http
Authorization: Token {your-token}
```

**Example:** `GET /v1/assessment/python-basics-quiz?lang=es`

Returns the Spanish translation of the assessment if it exists.

### Create Translation

**Endpoint:** `PUT /v1/assessment/{assessment_slug}`

**Payload:**
```json
{
  "slug": "python-basics-quiz-es",
  "title": "Cuestionario de Python Básico",
  "lang": "es",
  "original": 123,
  "questions": [
    {
      "title": "¿Qué es Python?",
      "options": [
        { "title": "Un lenguaje de programación", "score": 1.0 },
        { "title": "Una serpiente", "score": 0.0 }
      ]
    }
  ]
}
```

Link to original via `original` field (assessment ID).

### Link Asset Translations

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/python-basics-quiz`

**Payload:**
```json
{
  "all_translations": ["python-basics-quiz", "python-basics-quiz-es"]
}
```

Repeat for each translation asset to create bidirectional links.

---

## Thresholds & Scoring

Thresholds define success/failure criteria based on student scores.

### Create Threshold

**Endpoint:** `POST /v1/assessment/{assessment_slug}/threshold`

```json
{
  "title": "Passing Grade",
  "score_threshold": 70,
  "success_message": "Congratulations! You passed the quiz.",
  "fail_message": "Keep studying and try again.",
  "success_next": "https://learn.4geeks.com/next-lesson",
  "fail_next": "https://learn.4geeks.com/study-guide",
  "tags": "beginner,python"
}
```

**Response (201 Created):**

```json
{
  "id": 1,
  "assessment": {
    "id": 123,
    "slug": "python-basics-quiz"
  },
  "title": "Passing Grade",
  "score_threshold": 70,
  "success_message": "Congratulations! You passed the quiz.",
  "fail_message": "Keep studying and try again.",
  "success_next": "https://learn.4geeks.com/next-lesson",
  "fail_next": "https://learn.4geeks.com/study-guide",
  "tags": "beginner,python",
  "academy": null
}
```

### Multiple Thresholds with Tags

You can have multiple threshold groups for different use cases:

```json
// Beginner threshold
{
  "score_threshold": 60,
  "tags": "beginner",
  "success_message": "Good job for a beginner!"
}

// Advanced threshold
{
  "score_threshold": 85,
  "tags": "advanced",
  "success_message": "Excellent work!"
}
```

### View Thresholds

**Endpoint:** `GET /v1/assessment/{assessment_slug}/threshold`

**Headers:**
```http
Authorization: Token {your-token}
```

Returns array of all thresholds for the assessment.

### Update Threshold

**Endpoint:** `PUT /v1/assessment/{assessment_slug}/threshold/{threshold_id}`

**Headers:**
```http
Authorization: Token {your-token}
Academy: {academy_id}
Content-Type: application/json
```

**Payload:**
```json
{
  "score_threshold": 80,
  "success_message": "Updated message"
}
```

### Delete Threshold

**Endpoint:** `DELETE /v1/assessment/{assessment_slug}/threshold/{threshold_id}`

**Headers:**
```http
Authorization: Token {your-token}
Academy: {academy_id}
```

**Response:** `204 No Content` on success.

---

## Assessment Layouts

Layouts allow customizing the visual presentation of assessments.

### Create Layout

**Endpoint:** `POST /v1/assessment/academy/layout`

```json
{
  "slug": "dark-theme-layout",
  "additional_styles": ".quiz-container { background: #1a1a1a; color: #fff; }",
  "variables": {
    "primary_color": "#007bff",
    "font_family": "Roboto, sans-serif",
    "logo_url": "https://..."
  }
}
```

### Assign Layout to Assessment

Link the layout when creating/updating an assessment:

```json
{
  "slug": "python-basics-quiz",
  "layout": "dark-theme-layout"
}
```

### View Layout

**Endpoint:** `GET /v1/assessment/layout/{layout_slug}`

---

## Student Submissions

### View Student Attempts (UserAssessments)

**Endpoint:** `GET /v1/assessment/academy/user/assessment`

**Headers:**
```http
Authorization: Token {your-token}
Academy: {academy_id}
```

**Query Parameters:**
- `assessment` - Filter by assessment ID
- `status` - Filter by status (DRAFT, SENT, ANSWERED, ERROR, EXPIRED)
- `user` - Filter by user ID

**Example:** `GET /v1/assessment/academy/user/assessment?assessment=123`

**Response:**

```json
[
  {
    "id": 789,
    "assessment": {
      "id": 123,
      "slug": "python-basics-quiz",
      "title": "Python Basics Quiz"
    },
    "owner": {
      "id": 456,
      "email": "student@example.com",
      "first_name": "John"
    },
    "total_score": 85.0,
    "status": "ANSWERED",
    "started_at": "2024-02-20T10:00:00Z",
    "finished_at": "2024-02-20T10:25:00Z",
    "created_at": "2024-02-20T09:55:00Z"
  }
]
```

### View Individual Submission Details

**Endpoint:** `GET /v1/assessment/academy/user/assessment/{user_assessment_id}`

Includes all answers and scoring details.

### View Student Answers

**Endpoint:** `GET /v1/assessment/academy/user/assessment/{user_assessment_id}/answer/{answer_id}`

---

## Archiving vs Deleting

### Soft Delete (Archive)

Assessments with student submissions cannot be hard deleted. They are automatically archived.

**What happens:**
- `is_archived` = true
- Hidden from default queries
- Student data preserved
- Can be restored

**Archive an Assessment:**

```python
# In Django admin or via code
assessment = Assessment.objects.get(slug='old-quiz')
assessment.delete()  # Automatically archives if has submissions
```

### View Archived Assessments

**Endpoint:** `GET /v1/assessment?include_archived=true`

**Headers:**
```http
Authorization: Token {your-token}
```

Returns all assessments including archived ones.

### Hard Delete

Only possible if NO student submissions exist. Hard deletion must be done via Django admin or database directly. Assessments with submissions are automatically soft-deleted (archived) instead.

---

## Testing & Quality

### Test Quiz Integrity

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/{asset_slug}/action/test`

**Headers:**
```http
Authorization: Token {your-token}
Academy: {academy_id}
```

**What It Checks:**
- Each question has at least one correct answer (score > 0)
- Question positions are valid
- Option scores sum correctly
- No orphaned questions/options
- README links work

**Response:**

```json
{
  "test_status": "OK",
  "errors": [],
  "warnings": [
    {
      "type": "scoring",
      "message": "Question 3 options sum to 1.5 (expected 1.0)",
      "question_id": 789
    }
  ]
}
```

---

## Status & Visibility

### Assessment Status (Assessment App)

| Field | Values | Description |
|-------|--------|-------------|
| `is_archived` | true/false | Archived assessments are hidden |
| `private` | true/false | Private to academy only |

### Asset Status (Registry App)

| Status | Description | Visible to Students |
|--------|-------------|---------------------|
| `NOT_STARTED` | Not yet created | ❌ No |
| `DRAFT` | Work in progress | ❌ No |
| `PUBLISHED` | Ready for students | ✅ Yes |
| `OPTIMIZED` | SEO optimized | ✅ Yes |
| `DELETED` | Soft deleted | ❌ No |

### Update Status

**Archive Assessment:**

**Endpoint:** `PUT /v1/assessment/old-quiz`

**Payload:**
```json
{
  "is_archived": true
}
```

**Publish Asset:**

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/python-basics-quiz`

**Payload:**
```json
{
  "status": "PUBLISHED"
}
```

---

## Complete Workflows

### Workflow 1: Create Quiz from Scratch

**Step 1: Create Assessment**

**Endpoint:** `PUT /v1/assessment/javascript-fundamentals`

**Payload:**
```json
{
  "slug": "javascript-fundamentals",
  "title": "JavaScript Fundamentals Quiz",
  "lang": "us",
  "is_instant_feedback": true,
  "max_session_duration": "00:45:00",
  "questions": [
    {
      "title": "What is a variable?",
      "question_type": "SELECT",
      "options": [
        { "title": "A container for data", "score": 1.0 },
        { "title": "A function", "score": 0.0 }
      ]
    }
  ]
}
```

**Step 2: Create Asset Wrapper**

**Endpoint:** `POST /v1/registry/academy/1/asset`

**Payload:**
```json
{
  "slug": "javascript-fundamentals",
  "title": "JavaScript Fundamentals Quiz",
  "asset_type": "QUIZ",
  "description": "Test your JavaScript knowledge",
  "technologies": ["javascript"],
  "category": 1,
  "status": "DRAFT"
}
```

**Step 3: Set Threshold**

**Endpoint:** `POST /v1/assessment/javascript-fundamentals/threshold`

**Payload:**
```json
{
  "score_threshold": 70,
  "success_message": "Great job! You understand JavaScript basics.",
  "fail_message": "Review the material and try again."
}
```

**Step 4: Test Integrity**

**Endpoint:** `PUT /v1/registry/academy/1/asset/javascript-fundamentals/action/test`

**Step 5: Publish** (if tests pass)

**Endpoint:** `PUT /v1/registry/academy/1/asset/javascript-fundamentals`

**Payload:**
```json
{
  "status": "PUBLISHED",
  "visibility": "PUBLIC"
}
```

### Workflow 2: Sync Quiz from GitHub

**Step 1: Create Asset**

**Endpoint:** `POST /v1/registry/academy/1/asset`

**Payload:**
```json
{
  "slug": "python-advanced-quiz",
  "title": "Advanced Python Quiz",
  "asset_type": "QUIZ",
  "readme_url": "https://github.com/4GeeksAcademy/python-quiz/blob/master/learn.json",
  "technologies": ["python"],
  "status": "DRAFT"
}
```

**Step 2: Pull from GitHub**

**Endpoint:** `PUT /v1/registry/academy/1/asset/python-advanced-quiz/action/pull`

Assessment is auto-created from `learn.json`.

**Step 3: Verify Import**

**Endpoint:** `GET /v1/assessment/python-advanced-quiz`

Check that questions were imported correctly.

**Step 4: Add Threshold**

**Endpoint:** `POST /v1/assessment/python-advanced-quiz/threshold`

**Payload:**
```json
{
  "score_threshold": 80,
  "success_message": "Excellent! You mastered advanced Python."
}
```

**Step 5: Publish**

**Endpoint:** `PUT /v1/registry/academy/1/asset/python-advanced-quiz`

**Payload:**
```json
{
  "status": "PUBLISHED"
}
```

### Workflow 3: Create Translation

**Step 1: Get Original Quiz**

**Endpoint:** `GET /v1/assessment/react-basics-quiz`

Note the original assessment ID.

**Step 2: Create Spanish Assessment**

**Endpoint:** `PUT /v1/assessment/react-basics-quiz-es`

**Payload:**
```json
{
  "slug": "react-basics-quiz-es",
  "title": "Cuestionario de React Básico",
  "lang": "es",
  "original": 123,
  "is_instant_feedback": true,
  "questions": [
    {
      "title": "¿Qué es React?",
      "question_type": "SELECT",
      "options": [
        { "title": "Una librería de JavaScript", "score": 1.0 },
        { "title": "Un lenguaje de programación", "score": 0.0 }
      ]
    }
  ]
}
```

**Step 3: Create Spanish Asset**

**Endpoint:** `POST /v1/registry/academy/1/asset`

**Payload:**
```json
{
  "slug": "react-basics-quiz-es",
  "title": "Cuestionario de React Básico",
  "asset_type": "QUIZ",
  "lang": "es",
  "technologies": ["react"]
}
```

**Step 4: Link Translations (English Asset)**

**Endpoint:** `PUT /v1/registry/academy/1/asset/react-basics-quiz`

**Payload:**
```json
{
  "all_translations": ["react-basics-quiz", "react-basics-quiz-es"]
}
```

**Step 5: Link Translations (Spanish Asset)**

**Endpoint:** `PUT /v1/registry/academy/1/asset/react-basics-quiz-es`

**Payload:**
```json
{
  "all_translations": ["react-basics-quiz", "react-basics-quiz-es"]
}
```

---

## API Reference

### Assessment Endpoints

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/v1/assessment` | GET | List assessments | ❌ Public |
| `/v1/assessment/{slug}` | GET | Get single assessment | ❌ Public |
| `/v1/assessment/{slug}` | PUT | Create/update assessment | ✅ crud_assessment |
| `/v1/assessment/{slug}/question/{id}` | PUT | Update single question | ✅ crud_assessment |
| `/v1/assessment/{slug}/question/{id}` | DELETE | Delete question | ✅ crud_assessment |
| `/v1/assessment/{slug}/question/{id}/option` | POST | Add new option to question | ✅ crud_assessment |
| `/v1/assessment/{slug}/option/{id}` | DELETE | Delete option | ✅ crud_assessment |
| `/v1/assessment/{slug}/threshold` | GET | List thresholds | ❌ Public |
| `/v1/assessment/{slug}/threshold` | POST | Create threshold | ✅ crud_assessment |
| `/v1/assessment/{slug}/threshold/{id}` | PUT | Update threshold | ✅ crud_assessment |
| `/v1/assessment/{slug}/threshold/{id}` | DELETE | Delete threshold | ✅ crud_assessment |
| `/v1/assessment/layout/{slug}` | GET | Get layout | ❌ Public |
| `/v1/assessment/academy/layout` | GET | List academy layouts | ✅ read_assessment |
| `/v1/assessment/academy/layout` | POST | Create layout | ✅ crud_assessment |
| `/v1/assessment/academy/user/assessment` | GET | List student attempts | ✅ read_assessment |
| `/v1/assessment/academy/user/assessment/{id}` | GET | Get student attempt | ✅ read_assessment |

### Asset (Quiz) Endpoints

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/v1/registry/academy/{academy_id}/asset` | POST | Create quiz asset | ✅ crud_asset |
| `/v1/registry/academy/{academy_id}/asset/{slug}` | GET | Get quiz asset | ✅ read_asset |
| `/v1/registry/academy/{academy_id}/asset/{slug}` | PUT | Update quiz asset | ✅ crud_asset |
| `/v1/registry/academy/{academy_id}/asset/{slug}/action/pull` | PUT | Pull from GitHub | ✅ crud_asset |
| `/v1/registry/academy/{academy_id}/asset/{slug}/action/test` | PUT | Test integrity | ✅ crud_asset |
| `/v1/registry/academy/{academy_id}/asset/{slug}/action/clean` | PUT | Clean/regenerate | ✅ crud_asset |
| `/v1/registry/academy/{academy_id}/asset/{slug}/thumbnail` | POST | Generate thumbnail | ✅ crud_asset |

### Query Parameters

**List Assessments** (`GET /v1/assessment`):

| Parameter | Example | Description |
|-----------|---------|-------------|
| `academy` | `?academy=1` | Filter by academy |
| `lang` | `?lang=us` | Filter by language |
| `include_archived` | `?include_archived=true` | Include archived |
| `no_asset` | `?no_asset=true` | Only assessments without assets |
| `author` | `?author=123` | Filter by author |

**List Assets** (`GET /v1/registry/academy/{academy_id}/asset`):

| Parameter | Example | Description |
|-----------|---------|-------------|
| `asset_type` | `?asset_type=QUIZ` | Only quizzes |
| `status` | `?status=PUBLISHED` | Filter by status |
| `technologies` | `?technologies=python` | Filter by tech |
| `category` | `?category=programming` | Filter by category |
| `lang` | `?lang=us` | Filter by language |

---

## Best Practices

### 1. Use Granular Endpoints for Updates ⭐

**Prefer:**
- `PUT /v1/assessment/{slug}/question/{id}` - Update single question
- `POST /v1/assessment/{slug}/question/{id}/option` - Add option

**Over:**
- `PUT /v1/assessment/{slug}` with entire questions array

**Why?**
- ✅ Fewer bytes transferred
- ✅ No risk of accidentally removing questions
- ✅ Clearer intent
- ✅ Easier to debug

### 2. Always Link Asset and Assessment

Create both for every quiz:
- Assessment via `PUT /v1/assessment/{slug}`
- Asset via `POST /v1/registry/academy/{academy_id}/asset` with matching slug and `asset_type: "QUIZ"`

### 3. Validate Scoring

Ensure questions have valid scoring:
- At least ONE option per question must have `score > 0`
- Total positive scores should ideally equal 1.0 (for percentage scoring)
- The API validates this automatically when using `PUT /question/{id}` with options

### 4. Use Thresholds

Always define success criteria using `POST /v1/assessment/{slug}/threshold` with appropriate `score_threshold` value.

### 5. Test Before Publishing

1. Test: `PUT /v1/registry/academy/{academy_id}/asset/{slug}/action/test`
2. Check `test_status` in response
3. Only publish if status is `OK` or `WARNING`
4. Publish: `PUT /v1/registry/academy/{academy_id}/asset/{slug}` with `status: "PUBLISHED"`

### 6. Handle Translations Properly

Link translations bidirectionally:
- Update each asset with `all_translations` array containing all translation slugs
- Repeat for every translation to ensure bidirectional linking

### 7. When to Use Each Endpoint

**Creating new assessment:**
```bash
PUT /v1/assessment/{slug}  # With full questions array
```

**Adding a question:**
```bash
PUT /v1/assessment/{slug}  # Include existing + new questions
```

**Updating one question:**
```bash
PUT /v1/assessment/{slug}/question/{id}  # ⭐ More efficient
```

**Adding an option:**
```bash
POST /v1/assessment/{slug}/question/{id}/option  # ⭐ Cleanest
# OR
PUT /v1/assessment/{slug}/question/{id}  # With options array, omit id for new
```

**Updating an option:**
```bash
PUT /v1/assessment/{slug}/question/{id}  # Include option with id
```

---

## Troubleshooting

### Common Issues

#### Issue: "Assessment already exists"

**Cause:** Trying to create assessment with existing slug.

**Solution:** Use PUT to update instead, or check for archived assessments via `GET /v1/assessment?include_archived=true`

#### Issue: "Question total score must be greater than 0"

**Cause:** All options have `score: 0` or no positive scores.

**Solution:** Ensure at least one option has `score > 0`:

```json
{
  "options": [
    { "title": "Correct answer", "score": 1.0 },
    { "title": "Wrong answer", "score": 0.0 }
  ]
}
```

#### Issue: "Cannot delete question/option"

**Cause:** Question/option has student answers.

**Solution:** Questions with answers are soft-deleted (`is_deleted=true`), not removed.

#### Issue: "Assessment not linked to asset"

**Cause:** Slugs don't match or asset type isn't "QUIZ".

**Solution:** Ensure:
- Asset slug === Assessment slug
- Asset `asset_type` = "QUIZ"

---

## Related Documentation

- [MANAGE_SINGLE_ASSET.md](./MANAGE_SINGLE_ASSET.md) - Asset management
- [BUILD_SYLLABUS.md](./BUILD_SYLLABUS.md) - Adding quizzes to syllabi
- [STUDENT_REPORT.md](./STUDENT_REPORT.md) - Student progress tracking
- [AUTHENTICATION.md](./AUTHENTICATION.md) - API authentication

---

## Support

For questions or issues with assessment management:
- Verify both assessment and asset exist
- Check scoring rules (positive scores required)
- Review student submissions before deleting
- Test integrity before publishing
- Contact development team for API issues

**Last Updated:** October 2024

