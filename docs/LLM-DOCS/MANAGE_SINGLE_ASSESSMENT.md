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

After creating the asset, use the assessment endpoint to create questions:

```javascript
// Create questions via assessment endpoint
await fetch(
  `https://breathecode.herokuapp.com/v1/assessment/python-basics-quiz`,
  {
    method: 'PUT',
    headers: {
      'Authorization': `Token ${token}`,
      'Academy': academyId,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      title: 'Python Basics Quiz',
      questions: [/* questions array */]
    })
  }
);
```

### Example: Create Assessment with JavaScript

```javascript
const createAssessment = async (academyId, assessmentData) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/assessment/${assessmentData.slug}`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Token ${token}`,
        'Academy': academyId,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(assessmentData)
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create assessment');
  }

  return await response.json();
};

// Usage
const quiz = await createAssessment(1, {
  slug: 'python-basics-quiz',
  title: 'Python Basics Quiz',
  lang: 'us',
  is_instant_feedback: true,
  questions: [
    {
      title: 'What is Python?',
      question_type: 'SELECT',
      options: [
        { title: 'A programming language', score: 1.0 },
        { title: 'A snake', score: 0.0 }
      ]
    }
  ]
});
```

---

## Managing Questions & Options

### Add New Question

Add a question to an existing assessment:

```javascript
const addQuestion = async (academyId, assessmentSlug, questionData) => {
  const token = localStorage.getItem('authToken');
  
  // Get current assessment
  const assessment = await fetch(
    `https://breathecode.herokuapp.com/v1/assessment/${assessmentSlug}`,
    {
      headers: { 'Authorization': `Token ${token}` }
    }
  ).then(r => r.json());

  // Add new question
  assessment.questions.push(questionData);

  // Update assessment
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/assessment/${assessmentSlug}`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Token ${token}`,
        'Academy': academyId,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(assessment)
    }
  );

  return await response.json();
};

// Usage
await addQuestion(1, 'python-basics-quiz', {
  title: 'What is a Python list?',
  question_type: 'SELECT',
  position: 3,
  options: [
    { title: 'An ordered collection', score: 1.0 },
    { title: 'A dictionary', score: 0.0 }
  ]
});
```

### Update Existing Question

Update a question by including its `id` in the request:

```json
{
  "questions": [
    {
      "id": 456,
      "title": "Updated question text",
      "options": [
        {
          "id": 789,
          "title": "Updated option",
          "score": 1.0
        }
      ]
    }
  ]
}
```

### Delete Question

**Endpoint:** `DELETE /v1/assessment/{assessment_slug}/question/{question_id}`

**Note:** Questions with collected answers cannot be deleted, they will be marked as `is_deleted=true` instead.

```javascript
const deleteQuestion = async (assessmentSlug, questionId) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/assessment/${assessmentSlug}/question/${questionId}`,
    {
      method: 'DELETE',
      headers: {
        'Authorization': `Token ${token}`,
        'Academy': academyId
      }
    }
  );

  if (response.status === 204) {
    console.log('Question deleted successfully');
  }
};
```

### Delete Option

**Endpoint:** `DELETE /v1/assessment/{assessment_slug}/option/{option_id}`

```javascript
const deleteOption = async (assessmentSlug, optionId) => {
  const token = localStorage.getItem('authToken');
  
  await fetch(
    `https://breathecode.herokuapp.com/v1/assessment/${assessmentSlug}/option/${optionId}`,
    {
      method: 'DELETE',
      headers: {
        'Authorization': `Token ${token}`,
        'Academy': academyId
      }
    }
  );
};
```

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
```javascript
const asset = await fetch(
  `/v1/registry/academy/1/asset/python-basics-quiz`,
  { headers: { 'Authorization': `Token ${token}`, 'Academy': '1' } }
).then(r => r.json());

console.log(asset.assessment);  // Assessment object
```

**Get Assessment:**
```javascript
const assessment = await fetch(
  `/v1/assessment/python-basics-quiz`,
  { headers: { 'Authorization': `Token ${token}` } }
).then(r => r.json());

console.log(assessment.asset_set);  // Related assets
```

---

## GitHub Integration

Quiz assessments can sync with GitHub for version control and content management.

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

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/python-basics-quiz/action/pull`

**Purpose:** Pull quiz questions from GitHub `learn.json`

```javascript
const pullQuizFromGitHub = async (academyId, assetSlug) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/registry/academy/${academyId}/asset/${assetSlug}/action/pull`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Token ${token}`,
        'Academy': academyId
      }
    }
  );

  return await response.json();
};
```

**What Gets Synced:**
- Questions and options from `learn.json`
- Quiz metadata (title, description)
- README content (if exists)

### Push to GitHub

**Note:** Currently, quiz questions are typically managed in GitHub directly. The pull action is more common than push for quizzes.

---

## Translations

Assessments support multiple language translations.

### View Translations

**Endpoint:** `GET /v1/assessment/{assessment_slug}?lang={lang_code}`

```javascript
// Get Spanish translation
const spanishQuiz = await fetch(
  '/v1/assessment/python-basics-quiz?lang=es',
  { headers: { 'Authorization': `Token ${token}` } }
).then(r => r.json());
```

### Create Translation

1. Create a new assessment with different `lang` code
2. Link it to original via `original` field

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

### Link Assets for Translations

If you have assets for each translation, link them:

```javascript
// Link English and Spanish assets
await updateAsset(1, 'python-basics-quiz', {
  all_translations: ['python-basics-quiz', 'python-basics-quiz-es']
});

await updateAsset(1, 'python-basics-quiz-es', {
  all_translations: ['python-basics-quiz', 'python-basics-quiz-es']
});
```

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

```javascript
const getThresholds = async (assessmentSlug) => {
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/assessment/${assessmentSlug}/threshold`
  );
  
  return await response.json();
};
```

### Update Threshold

**Endpoint:** `PUT /v1/assessment/{assessment_slug}/threshold/{threshold_id}`

### Delete Threshold

**Endpoint:** `DELETE /v1/assessment/{assessment_slug}/threshold/{threshold_id}`

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

**Query Parameters:**
- `assessment` - Filter by assessment ID
- `status` - Filter by status (DRAFT, SENT, ANSWERED, ERROR, EXPIRED)
- `user` - Filter by user ID

```javascript
const getStudentAttempts = async (academyId, assessmentId) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/assessment/academy/user/assessment?assessment=${assessmentId}`,
    {
      headers: {
        'Authorization': `Token ${token}`,
        'Academy': academyId
      }
    }
  );

  return await response.json();
};
```

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

```javascript
const getArchivedQuizzes = async () => {
  const response = await fetch(
    '/v1/assessment?include_archived=true',
    { headers: { 'Authorization': `Token ${token}` } }
  );
  
  return await response.json();
};
```

### Hard Delete

Only possible if NO student submissions exist:

```python
assessment = Assessment.objects.get(slug='unused-quiz')
if assessment.userassessment_set.count() == 0:
    assessment.delete()  # Truly deletes
```

---

## Testing & Quality

### Test Quiz Integrity

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/python-basics-quiz/action/test`

**What It Checks:**
- Each question has at least one correct answer (score > 0)
- Question positions are valid
- Option scores sum correctly
- No orphaned questions/options
- README links work

```javascript
const testQuiz = async (academyId, assetSlug) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/registry/academy/${academyId}/asset/${assetSlug}/action/test`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Token ${token}`,
        'Academy': academyId
      }
    }
  );

  return await response.json();
};
```

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

```javascript
// Archive assessment
await updateAssessment(1, 'old-quiz', {
  is_archived: true
});

// Publish asset
await updateAsset(1, 'python-basics-quiz', {
  status: 'PUBLISHED'
});
```

---

## Complete Workflows

### Workflow 1: Create Quiz from Scratch

```javascript
// Step 1: Create assessment with questions
const assessment = await createAssessment(1, {
  slug: 'javascript-fundamentals',
  title: 'JavaScript Fundamentals Quiz',
  lang: 'us',
  is_instant_feedback: true,
  max_session_duration: '00:45:00',
  questions: [
    {
      title: 'What is a variable?',
      question_type: 'SELECT',
      options: [
        { title: 'A container for data', score: 1.0 },
        { title: 'A function', score: 0.0 },
        { title: 'A loop', score: 0.0 }
      ]
    },
    {
      title: 'What keyword declares a constant?',
      question_type: 'SELECT',
      options: [
        { title: 'const', score: 1.0 },
        { title: 'let', score: 0.0 },
        { title: 'var', score: 0.0 }
      ]
    }
  ]
});

// Step 2: Create asset wrapper
const asset = await createAsset(1, {
  slug: 'javascript-fundamentals',
  title: 'JavaScript Fundamentals Quiz',
  asset_type: 'QUIZ',
  description: 'Test your JavaScript knowledge',
  technologies: ['javascript'],
  category: 1,
  status: 'DRAFT'
});

// Step 3: Set threshold
await createThreshold('javascript-fundamentals', {
  score_threshold: 70,
  success_message: 'Great job! You understand JavaScript basics.',
  fail_message: 'Review the material and try again.'
});

// Step 4: Test integrity
const testResults = await testQuiz(1, 'javascript-fundamentals');

if (testResults.test_status === 'OK') {
  // Step 5: Publish
  await updateAsset(1, 'javascript-fundamentals', {
    status: 'PUBLISHED',
    visibility: 'PUBLIC'
  });
  
  console.log('✅ Quiz published!');
}
```

### Workflow 2: Sync Quiz from GitHub

```javascript
// Step 1: Create asset pointing to GitHub
const asset = await createAsset(1, {
  slug: 'python-advanced-quiz',
  title: 'Advanced Python Quiz',
  asset_type: 'QUIZ',
  readme_url: 'https://github.com/4GeeksAcademy/python-quiz/blob/master/learn.json',
  technologies: ['python'],
  status: 'DRAFT'
});

// Step 2: Pull questions from GitHub
await pullFromGitHub(1, 'python-advanced-quiz');

// Step 3: The assessment is auto-created from learn.json
const assessment = await fetch(
  '/v1/assessment/python-advanced-quiz'
).then(r => r.json());

console.log(`Imported ${assessment.questions.length} questions`);

// Step 4: Add custom threshold
await createThreshold('python-advanced-quiz', {
  score_threshold: 80,
  success_message: 'Excellent! You mastered advanced Python.'
});

// Step 5: Publish
await updateAsset(1, 'python-advanced-quiz', {
  status: 'PUBLISHED'
});
```

### Workflow 3: Create Translation

```javascript
// Step 1: Get original quiz
const originalQuiz = await fetch(
  '/v1/assessment/react-basics-quiz'
).then(r => r.json());

// Step 2: Create Spanish version
const spanishQuiz = await createAssessment(1, {
  slug: 'react-basics-quiz-es',
  title: 'Cuestionario de React Básico',
  lang: 'es',
  original: originalQuiz.id,
  is_instant_feedback: originalQuiz.is_instant_feedback,
  questions: [
    {
      title: '¿Qué es React?',
      question_type: 'SELECT',
      options: [
        { title: 'Una librería de JavaScript', score: 1.0 },
        { title: 'Un lenguaje de programación', score: 0.0 }
      ]
    }
  ]
});

// Step 3: Create Spanish asset
const spanishAsset = await createAsset(1, {
  slug: 'react-basics-quiz-es',
  title: 'Cuestionario de React Básico',
  asset_type: 'QUIZ',
  lang: 'es',
  technologies: ['react']
});

// Step 4: Link translations (bidirectional)
await updateAsset(1, 'react-basics-quiz', {
  all_translations: ['react-basics-quiz', 'react-basics-quiz-es']
});

await updateAsset(1, 'react-basics-quiz-es', {
  all_translations: ['react-basics-quiz', 'react-basics-quiz-es']
});

console.log('✅ Translation created and linked!');
```

---

## API Reference

### Assessment Endpoints

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/v1/assessment` | GET | List assessments | ❌ Public |
| `/v1/assessment/{slug}` | GET | Get single assessment | ❌ Public |
| `/v1/assessment/{slug}` | PUT | Create/update assessment | ✅ crud_assessment |
| `/v1/assessment/{slug}/question/{id}` | DELETE | Delete question | ✅ crud_assessment |
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

### 1. Always Link Asset and Assessment

```javascript
// Create both for every quiz
const assessment = await createAssessment(/*...*/);
const asset = await createAsset({
  slug: assessment.slug,
  asset_type: 'QUIZ'
  // ...
});
```

### 2. Validate Scoring

Ensure questions have valid scoring:

```javascript
const validateQuestionScoring = (question) => {
  const totalPositiveScore = question.options
    .filter(o => o.score > 0)
    .reduce((sum, o) => sum + o.score, 0);
  
  if (totalPositiveScore === 0) {
    throw new Error('Question must have at least one correct answer');
  }
  
  return true;
};
```

### 3. Use Thresholds

Always define success criteria:

```javascript
// Set passing threshold
await createThreshold(assessmentSlug, {
  score_threshold: 70,
  success_message: 'You passed!',
  fail_message: 'Try again'
});
```

### 4. Test Before Publishing

```javascript
const safePublish = async (academyId, assetSlug) => {
  // Test first
  const testResults = await testQuiz(academyId, assetSlug);
  
  if (testResults.test_status === 'ERROR') {
    throw new Error('Cannot publish: quiz has errors');
  }
  
  // Then publish
  await updateAsset(academyId, assetSlug, {
    status: 'PUBLISHED'
  });
};
```

### 5. Handle Translations Properly

Link translations bidirectionally:

```javascript
const linkQuizTranslations = async (academyId, slugs) => {
  for (const slug of slugs) {
    await updateAsset(academyId, slug, {
      all_translations: slugs
    });
  }
};
```

---

## Troubleshooting

### Common Issues

#### Issue: "Assessment already exists"

**Cause:** Trying to create assessment with existing slug.

**Solution:** Use PUT to update instead, or check for archived assessments:

```javascript
const assessment = await fetch(
  '/v1/assessment?include_archived=true'
).then(r => r.json());
```

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

