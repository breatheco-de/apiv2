# Managing Assets - Complete Guide

This document provides comprehensive guidance on creating, editing, and managing individual assets in the BreatheCode platform. Assets include lessons, exercises, projects, articles, quizzes, and videos.

## Table of Contents

1. [Overview](#overview)
2. [Asset Types](#asset-types)
3. [Creating a New Asset](#creating-a-new-asset)
4. [Editing Asset Metadata](#editing-asset-metadata)
5. [GitHub Integration](#github-integration)
6. [Content Management](#content-management)
7. [Asset Versions](#asset-versions)
8. [Technologies Management](#technologies-management)
9. [Translations](#translations)
10. [Categories](#categories)
11. [Testing & Quality](#testing--quality)
12. [Repository Subscriptions](#repository-subscriptions)
13. [Status & Visibility](#status--visibility)
14. [Thumbnails & Preview Images](#thumbnails--preview-images)
15. [API Reference](#api-reference)

---

## Overview

Assets are the core learning materials in the BreatheCode platform. Each asset represents a piece of educational content that can be synced with GitHub, translated to multiple languages, categorized, and versioned.

### Key Concepts

- **Asset Slug**: Unique identifier for the asset across the entire platform
- **Asset Type**: The type of content (LESSON, EXERCISE, PROJECT, ARTICLE, QUIZ, VIDEO)
- **Visibility**: Controls who can see the asset (PUBLIC, UNLISTED, PRIVATE)
- **Status**: Publication status (NOT_STARTED, DRAFT, PUBLISHED, OPTIMIZED, DELETED)
- **Sync Status**: GitHub synchronization state (OK, ERROR, PENDING, NEEDS_RESYNC)
- **Test Status**: Integrity test results (OK, ERROR, WARNING, PENDING)

### Base URL

```
Production: https://breathecode.herokuapp.com
Development: http://localhost:8000
```

---

## Asset Types

BreatheCode supports the following asset types:

| Type | Description | GitHub Sync | Interactive |
|------|-------------|-------------|-------------|
| `LESSON` | Educational article/tutorial | ✅ Yes | ❌ No |
| `EXERCISE` | Coding exercise | ✅ Yes | ✅ Yes (LearnPack) |
| `PROJECT` | Larger coding project | ✅ Yes | ✅ Yes (LearnPack) |
| `ARTICLE` | Blog post or article | ✅ Yes | ❌ No |
| `QUIZ` | Assessment quiz | ✅ Yes | ❌ No |
| `VIDEO` | Video content | ❌ No | ❌ No |

---

## Creating a New Asset

### Endpoint

**`POST /v1/registry/academy/{academy_id}/asset`**

### Authentication

Requires `crud_asset` capability in the academy.

### Headers

```http
Authorization: Token {your-token}
Academy: {academy_id}
Content-Type: application/json
```

### Request Body

```json
{
  "slug": "my-first-lesson",
  "title": "My First Lesson",
  "asset_type": "LESSON",
  "lang": "us",
  "description": "A comprehensive introduction to Python programming",
  "category": 1,
  "technologies": ["python", "flask"],
  "readme_url": "https://github.com/4GeeksAcademy/content/blob/master/src/content/lesson/my-first-lesson.md",
  "visibility": "PUBLIC",
  "status": "DRAFT"
}
```

### Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | ✅ Yes | Unique identifier (lowercase, hyphens only) |
| `title` | string | ✅ Yes | Display title |
| `asset_type` | string | ✅ Yes | One of: LESSON, EXERCISE, PROJECT, ARTICLE, QUIZ, VIDEO |
| `lang` | string | ❌ No | Language code (us, es, it) - defaults to "us" |
| `description` | string | ❌ No | SEO-friendly description |
| `category` | integer | ❌ No | Category ID |
| `technologies` | array | ❌ No | Array of technology slugs |
| `readme_url` | string | ❌ No | GitHub URL to markdown file |
| `visibility` | string | ❌ No | PUBLIC, UNLISTED, or PRIVATE (default: PUBLIC) |
| `status` | string | ❌ No | NOT_STARTED, DRAFT, PUBLISHED (default: DRAFT) |
| `external` | boolean | ❌ No | If true, opens in new window |
| `interactive` | boolean | ❌ No | LearnPack enabled |
| `graded` | boolean | ❌ No | Has grading |
| `with_video` | boolean | ❌ No | Includes video |
| `with_solutions` | boolean | ❌ No | Has solution |

### Response (201 Created)

```json
{
  "id": 123,
  "slug": "my-first-lesson",
  "title": "My First Lesson",
  "asset_type": "LESSON",
  "lang": "us",
  "description": "A comprehensive introduction to Python programming",
  "category": {
    "id": 1,
    "slug": "programming",
    "title": "Programming"
  },
  "technologies": [
    {
      "slug": "python",
      "title": "Python"
    }
  ],
  "readme_url": "https://github.com/4GeeksAcademy/content/blob/master/src/content/lesson/my-first-lesson.md",
  "visibility": "PUBLIC",
  "status": "DRAFT",
  "sync_status": "PENDING",
  "test_status": "PENDING",
  "created_at": "2024-02-20T10:00:00Z",
  "updated_at": "2024-02-20T10:00:00Z"
}
```

### Example: Create Lesson with JavaScript

```javascript
const createAsset = async (academyId, assetData) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/registry/academy/${academyId}/asset`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Token ${token}`,
        'Academy': academyId,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(assetData)
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create asset');
  }

  return await response.json();
};

// Usage
const newAsset = await createAsset(1, {
  slug: 'intro-to-python',
  title: 'Introduction to Python',
  asset_type: 'LESSON',
  lang: 'us',
  technologies: ['python']
});
```

---

## Editing Asset Metadata

### Endpoint

**`PUT /v1/registry/academy/{academy_id}/asset/{asset_slug_or_id}`**

### Authentication

Requires `crud_asset` capability.

### Headers

```http
Authorization: Token {your-token}
Academy: {academy_id}
Content-Type: application/json
```

### Request Body

You can update any field from the asset. Only include fields you want to change:

```json
{
  "title": "Updated Lesson Title",
  "description": "Updated description",
  "status": "PUBLISHED",
  "visibility": "PUBLIC",
  "technologies": ["python", "django"],
  "category": 2
}
```

### Updatable Fields

| Field | Description | Example |
|-------|-------------|---------|
| `title` | Asset title | "Advanced Python Programming" |
| `description` | SEO description | "Learn advanced Python concepts" |
| `lang` | Language code | "us", "es", "it" |
| `status` | Publication status | "DRAFT", "PUBLISHED" |
| `visibility` | Access control | "PUBLIC", "UNLISTED", "PRIVATE" |
| `category` | Category ID | 1 |
| `technologies` | Technology slugs | ["python", "django"] |
| `all_translations` | Translation slugs | ["intro-python-es", "intro-python-it"] |
| `preview` | Social media preview URL | "https://..." |
| `readme_url` | GitHub markdown URL | "https://github.com/..." |
| `url` | External URL | "https://..." |
| `intro_video_url` | Introduction video | "https://youtube.com/..." |
| `solution_video_url` | Solution video | "https://youtube.com/..." |
| `difficulty` | BEGINNER, EASY, INTERMEDIATE, HARD | "INTERMEDIATE" |
| `duration` | Hours | 4 |
| `graded` | Has grading | true |
| `with_video` | Includes video | true |
| `with_solutions` | Has solution | true |
| `interactive` | LearnPack enabled | true |
| `gitpod` | Gitpod compatible | true |
| `external` | External asset | false |

### Response (200 OK)

Returns the updated asset object.

### Example: Update Asset

```javascript
const updateAsset = async (academyId, assetSlug, updates) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/registry/academy/${academyId}/asset/${assetSlug}`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Token ${token}`,
        'Academy': academyId,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(updates)
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to update asset');
  }

  return await response.json();
};

// Usage
await updateAsset(1, 'intro-to-python', {
  status: 'PUBLISHED',
  description: 'Comprehensive Python introduction for beginners'
});
```

---

## GitHub Integration

Assets can be synchronized with GitHub repositories to pull content and push changes.

### Pull from GitHub

Synchronize asset content from GitHub repository.

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/{asset_slug}/action/pull`

**Purpose:** Pull latest content from GitHub and update the asset's README.

#### Query Parameters

- `override_meta` (optional, default: false) - If true, overwrites asset metadata with data from GitHub

#### Request Body

```json
{
  "override_meta": false
}
```

#### Example

```javascript
const pullFromGitHub = async (academyId, assetSlug, overrideMeta = false) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/registry/academy/${academyId}/asset/${assetSlug}/action/pull`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Token ${token}`,
        'Academy': academyId,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        override_meta: overrideMeta
      })
    }
  );

  if (!response.ok) {
    throw new Error('Failed to pull from GitHub');
  }

  return await response.json();
};

// Pull without overriding metadata
await pullFromGitHub(1, 'intro-to-python', false);
```

#### What Gets Pulled

- **Always**: README content (markdown)
- **With override_meta=true**: Title, description, duration, difficulty, technologies

### Push to GitHub

Publish asset changes back to the GitHub repository.

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/{asset_slug}/action/push`

**Purpose:** Push local changes to GitHub repository.

**Note:** Only works for LESSON, ARTICLE, and QUIZ types. Projects and exercises must be updated manually in GitHub.

#### Example

```javascript
const pushToGitHub = async (academyId, assetSlug) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/registry/academy/${academyId}/asset/${assetSlug}/action/push`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Token ${token}`,
        'Academy': academyId
      }
    }
  );

  if (!response.ok) {
    throw new Error('Failed to push to GitHub');
  }

  return await response.json();
};
```

### Create GitHub Repository

Create a new GitHub repository for the asset.

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/{asset_slug}/action/create_repo`

**Purpose:** Create a new repository in the academy's GitHub organization.

#### Request Body

```json
{
  "organization": "4GeeksAcademy",
  "repo_name": "my-first-lesson"
}
```

---

## Content Management

### Save Markdown Only

Update only the README content without changing metadata.

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/{asset_slug}`

```json
{
  "readme_raw": "# My Updated Content\n\nThis is the new markdown content..."
}
```

### Clean/Regenerate README

Clean and regenerate the asset's README from the raw markdown.

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/{asset_slug}/action/clean`

**Purpose:** Process the raw markdown, extract metadata, and regenerate HTML.

#### What It Does

- Extracts frontmatter metadata
- Processes markdown to HTML
- Updates SEO keywords
- Regenerates table of contents
- Optimizes images

#### Example

```javascript
const cleanAsset = async (academyId, assetSlug) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/registry/academy/${academyId}/asset/${assetSlug}/action/clean`,
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

---

## Asset Versions

Assets can have multiple versions to handle technology updates and deprecation.

### View Superseding Asset (Newer Version)

**Endpoint:** `GET /v1/registry/asset/{asset_slug}/supersedes`

**Purpose:** Get the asset that supersedes (replaces) this one.

**Response:**

```json
{
  "id": 456,
  "slug": "intro-to-python-v2",
  "title": "Introduction to Python (Updated for Python 3.11)",
  "asset_type": "LESSON",
  "superseded_by": null,
  "previous_version": {
    "id": 123,
    "slug": "intro-to-python"
  }
}
```

### View Previous Version

**Endpoint:** `GET /v1/registry/academy/{academy_id}/asset/{asset_slug}`

The asset object includes `superseded_by` and `previous_version` fields:

```json
{
  "id": 123,
  "slug": "intro-to-python",
  "superseded_by": {
    "id": 456,
    "slug": "intro-to-python-v2",
    "title": "Introduction to Python (Updated)"
  },
  "previous_version": null
}
```

### Create New Version (Superseding)

To create a new version that supersedes an old one:

1. Create the new asset
2. Update the old asset with `superseded_by` field

```javascript
// Step 1: Create new version
const newVersion = await createAsset(1, {
  slug: 'intro-to-python-v2',
  title: 'Introduction to Python (Python 3.11)',
  asset_type: 'LESSON'
});

// Step 2: Mark old version as superseded
await updateAsset(1, 'intro-to-python', {
  superseded_by: newVersion.id
});
```

---

## Technologies Management

Technologies are tags that categorize assets by the tech stack they cover.

### View Available Technologies

**Endpoint:** `GET /v1/registry/academy/technology`

**Response:**

```json
[
  {
    "slug": "python",
    "title": "Python",
    "icon_url": "https://...",
    "description": "Python programming language",
    "is_deprecated": false,
    "parent": null
  },
  {
    "slug": "django",
    "title": "Django",
    "parent": {
      "slug": "python",
      "title": "Python"
    }
  }
]
```

### Add Technologies to Asset

Update the asset with technology slugs:

```javascript
await updateAsset(1, 'my-lesson', {
  technologies: ['python', 'django', 'postgresql']
});
```

### Remove Technologies

```javascript
await updateAsset(1, 'my-lesson', {
  technologies: ['python']  // Only keep Python
});
```

---

## Translations

Assets can be translated into multiple languages and linked together.

### View Asset Translations

**Endpoint:** `GET /v1/registry/academy/{academy_id}/asset/{asset_slug}`

The response includes `all_translations` field:

```json
{
  "id": 123,
  "slug": "intro-to-python",
  "lang": "us",
  "all_translations": [
    {
      "id": 123,
      "slug": "intro-to-python",
      "lang": "us",
      "title": "Introduction to Python"
    },
    {
      "id": 124,
      "slug": "introduccion-a-python",
      "lang": "es",
      "title": "Introducción a Python"
    }
  ]
}
```

### Create a Translation

1. Create a new asset with the translated content
2. Link it to the original asset

```javascript
// Step 1: Create Spanish translation
const spanishVersion = await createAsset(1, {
  slug: 'introduccion-a-python',
  title: 'Introducción a Python',
  asset_type: 'LESSON',
  lang: 'es',
  readme_url: 'https://github.com/.../README.es.md'
});

// Step 2: Link to original (English) asset
await updateAsset(1, 'intro-to-python', {
  all_translations: [
    'intro-to-python',  // Original
    'introduccion-a-python'  // Spanish translation
  ]
});

// Step 3: Link from Spanish to English
await updateAsset(1, 'introduccion-a-python', {
  all_translations: [
    'intro-to-python',
    'introduccion-a-python'
  ]
});
```

### Auto-Generate Translation (AI)

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/{asset_slug}/action/generate_translation`

**Purpose:** Use AI to generate a translation in another language.

```json
{
  "target_lang": "es"
}
```

---

## Categories

Categories organize assets into logical groups.

### View Categories

**Endpoint:** `GET /v1/registry/academy/{academy_id}/category`

**Response:**

```json
[
  {
    "id": 1,
    "slug": "web-development",
    "title": "Web Development",
    "lang": "us",
    "description": "Learn web development technologies",
    "visibility": "PUBLIC"
  }
]
```

### Assign Category to Asset

```javascript
await updateAsset(1, 'my-lesson', {
  category: 1  // Category ID
});
```

### Create New Category

**Endpoint:** `POST /v1/registry/academy/{academy_id}/category`

```json
{
  "slug": "machine-learning",
  "title": "Machine Learning",
  "lang": "us",
  "description": "AI and Machine Learning content",
  "visibility": "PUBLIC"
}
```

---

## Testing & Quality

### Test Asset Integrity

Run automated tests on the asset to check for issues.

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/{asset_slug}/action/test`

**Purpose:** Validate asset structure, links, images, and content quality.

#### What It Checks

- Broken links
- Missing images
- Invalid markdown
- SEO issues
- Missing metadata
- Readability score

#### Example

```javascript
const testAsset = async (academyId, assetSlug) => {
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

const result = await testAsset(1, 'intro-to-python');
```

#### Response

```json
{
  "test_status": "WARNING",
  "errors": [
    {
      "type": "broken_link",
      "message": "Link to https://example.com/broken returns 404",
      "line": 45
    }
  ],
  "warnings": [
    {
      "type": "low_readability",
      "message": "Readability score is 45 (target: 60+)",
      "suggestion": "Simplify complex sentences"
    }
  ]
}
```

### View Test Results

**Endpoint:** `GET /v1/registry/academy/{academy_id}/asset/{asset_slug}`

Check the `test_status` field:

- `PENDING`: Not yet tested
- `OK`: All tests passed
- `WARNING`: Has warnings but no critical errors
- `ERROR`: Has critical errors

### SEO Analysis

Run SEO optimization analysis on the asset.

**Endpoint:** `PUT /v1/registry/academy/{academy_id}/asset/{asset_slug}/action/analyze_seo`

**Purpose:** Analyze SEO quality and get improvement suggestions.

#### Response

```json
{
  "score": 85,
  "issues": [
    {
      "severity": "warning",
      "message": "Meta description too short (should be 150-160 chars)",
      "current": "Learn Python",
      "suggestion": "Learn Python programming from scratch with hands-on examples"
    }
  ],
  "keywords": ["python", "programming", "tutorial"],
  "readability": {
    "score": 72,
    "grade": "8th grade"
  }
}
```

### Originality Report

Check content originality and detect plagiarism.

**Endpoint:** `GET /v1/registry/academy/{academy_id}/asset/{asset_slug}/originality`

**Response:**

```json
{
  "originality_score": 95,
  "similar_content": [
    {
      "url": "https://example.com/similar",
      "similarity": 15,
      "matched_text": "Python is a high-level programming language"
    }
  ]
}
```

---

## Repository Subscriptions

Control whether the asset automatically syncs with GitHub on repository pushes.

### Check Subscription Status

**Endpoint:** `GET /v1/registry/academy/{academy_id}/asset/{asset_slug}`

Check the `is_auto_subscribed` field:

```json
{
  "id": 123,
  "slug": "intro-to-python",
  "is_auto_subscribed": true,
  "sync_status": "OK"
}
```

### Subscribe to Repository Updates

Enable automatic synchronization when GitHub repository is updated.

```javascript
await updateAsset(1, 'intro-to-python', {
  is_auto_subscribed: true
});
```

**What happens:** When GitHub sends a webhook on push, the asset will automatically pull the latest content.

### Unsubscribe from Repository Updates

Disable automatic synchronization.

```javascript
await updateAsset(1, 'intro-to-python', {
  is_auto_subscribed: false
});
```

**Use case:** Temporarily disable auto-sync while making manual edits to avoid conflicts.

---

## Status & Visibility

### Asset Status

Controls the publication lifecycle of the asset.

| Status | Description | Visible to Students |
|--------|-------------|---------------------|
| `NOT_STARTED` | Initial state, not yet written | ❌ No |
| `DRAFT` | Work in progress | ❌ No |
| `PUBLISHED` | Ready for students | ✅ Yes |
| `OPTIMIZED` | SEO optimized and ready | ✅ Yes |
| `DELETED` | Soft deleted | ❌ No |

#### Update Status

```javascript
// Publish asset
await updateAsset(1, 'intro-to-python', {
  status: 'PUBLISHED'
});

// Move to draft
await updateAsset(1, 'intro-to-python', {
  status: 'DRAFT'
});

// Soft delete
await updateAsset(1, 'intro-to-python', {
  status: 'DELETED'
});
```

### Asset Visibility

Controls who can see the asset within the academy.

| Visibility | Description | Access |
|------------|-------------|--------|
| `PUBLIC` | Visible to everyone | All academies |
| `UNLISTED` | Hidden from listings but accessible via direct link | Same academy |
| `PRIVATE` | Only visible to asset owner/author | Owner only |

#### Update Visibility

```javascript
// Make public
await updateAsset(1, 'intro-to-python', {
  visibility: 'PUBLIC'
});

// Make unlisted
await updateAsset(1, 'intro-to-python', {
  visibility: 'UNLISTED'
});

// Make private
await updateAsset(1, 'intro-to-python', {
  visibility: 'PRIVATE'
});
```

---

## Thumbnails & Preview Images

Assets can have preview images for social media sharing and tutorial introductions.

### Generate Thumbnail

Automatically generate a thumbnail from the asset content.

**Endpoint:** `POST /v1/registry/academy/{academy_id}/asset/{asset_slug}/thumbnail`

**Purpose:** Generate or regenerate the asset's social media preview image.

#### Example

```javascript
const generateThumbnail = async (academyId, assetSlug) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/registry/academy/${academyId}/asset/${assetSlug}/thumbnail`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Token ${token}`,
        'Academy': academyId
      }
    }
  );

  return await response.json();
};

const thumbnail = await generateThumbnail(1, 'intro-to-python');
// Returns: { preview: "https://...thumbnail.jpg" }
```

### Set Custom Thumbnail

Manually set a custom preview image.

```javascript
await updateAsset(1, 'intro-to-python', {
  preview: 'https://your-cdn.com/custom-thumbnail.jpg'
});
```

### Tutorial Preview Image

Set a different preview for use within the tutorial itself.

```javascript
await updateAsset(1, 'intro-to-python', {
  preview_in_tutorial: 'https://your-cdn.com/tutorial-preview.jpg'
});
```

---

## API Reference

### Complete Endpoint List

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/v1/registry/academy/{academy_id}/asset` | GET | List all assets | ✅ read_asset |
| `/v1/registry/academy/{academy_id}/asset` | POST | Create new asset | ✅ crud_asset |
| `/v1/registry/academy/{academy_id}/asset/{slug}` | GET | Get single asset | ✅ read_asset |
| `/v1/registry/academy/{academy_id}/asset/{slug}` | PUT | Update asset | ✅ crud_asset |
| `/v1/registry/academy/{academy_id}/asset/{slug}/action/pull` | PUT | Pull from GitHub | ✅ crud_asset |
| `/v1/registry/academy/{academy_id}/asset/{slug}/action/push` | PUT | Push to GitHub | ✅ crud_asset |
| `/v1/registry/academy/{academy_id}/asset/{slug}/action/test` | PUT | Test integrity | ✅ crud_asset |
| `/v1/registry/academy/{academy_id}/asset/{slug}/action/clean` | PUT | Clean/regenerate | ✅ crud_asset |
| `/v1/registry/academy/{academy_id}/asset/{slug}/action/analyze_seo` | PUT | SEO analysis | ✅ crud_asset |
| `/v1/registry/academy/{academy_id}/asset/{slug}/action/create_repo` | PUT | Create GitHub repo | ✅ crud_asset |
| `/v1/registry/academy/{academy_id}/asset/{slug}/thumbnail` | POST | Generate thumbnail | ✅ crud_asset |
| `/v1/registry/academy/{academy_id}/asset/{slug}/originality` | GET | Originality report | ✅ read_asset |
| `/v1/registry/asset/{slug}/supersedes` | GET | View versions | ❌ Public |
| `/v1/registry/academy/{academy_id}/category` | GET | List categories | ✅ read_asset |
| `/v1/registry/academy/technology` | GET | List technologies | ✅ read_asset |

### Query Parameters (List Assets)

When listing assets (`GET /v1/registry/academy/{academy_id}/asset`), you can filter using:

| Parameter | Example | Description |
|-----------|---------|-------------|
| `asset_type` | `?asset_type=LESSON` | Filter by type |
| `status` | `?status=PUBLISHED,DRAFT` | Filter by status |
| `visibility` | `?visibility=PUBLIC` | Filter by visibility |
| `lang` | `?lang=us` | Filter by language |
| `technologies` | `?technologies=python,django` | Filter by tech |
| `category` | `?category=web-dev` | Filter by category |
| `author` | `?author=123` | Filter by author ID |
| `owner` | `?owner=456` | Filter by owner ID |
| `like` | `?like=python` | Search in title/slug |
| `test_status` | `?test_status=OK` | Filter by test status |
| `sync_status` | `?sync_status=OK` | Filter by sync status |
| `superseded_by` | `?superseded_by=null` | Only latest versions |
| `need_translation` | `?need_translation=true` | Assets without translations |
| `external` | `?external=false` | Internal assets only |
| `interactive` | `?interactive=true` | LearnPack enabled only |
| `graded` | `?graded=true` | Graded assets only |
| `with_video` | `?with_video=true` | Assets with video |

---

## Complete Workflow Examples

### Example 1: Create and Publish a Lesson

```javascript
// 1. Create the lesson
const lesson = await createAsset(1, {
  slug: 'advanced-python-decorators',
  title: 'Advanced Python Decorators',
  asset_type: 'LESSON',
  lang: 'us',
  description: 'Master Python decorators with real-world examples',
  readme_url: 'https://github.com/4GeeksAcademy/content/blob/master/src/content/lesson/advanced-decorators.md',
  technologies: ['python'],
  category: 1,
  status: 'DRAFT',
  visibility: 'PRIVATE'
});

// 2. Pull content from GitHub
await pullFromGitHub(1, 'advanced-python-decorators', false);

// 3. Clean and process the content
await cleanAsset(1, 'advanced-python-decorators');

// 4. Test integrity
const testResults = await testAsset(1, 'advanced-python-decorators');

if (testResults.test_status === 'OK') {
  // 5. Generate thumbnail
  await generateThumbnail(1, 'advanced-python-decorators');
  
  // 6. Publish
  await updateAsset(1, 'advanced-python-decorators', {
    status: 'PUBLISHED',
    visibility: 'PUBLIC'
  });
  
  console.log('✅ Lesson published successfully!');
} else {
  console.error('❌ Tests failed:', testResults.errors);
}
```

### Example 2: Create Translation

```javascript
// 1. Get original asset
const originalAsset = await getAsset(1, 'intro-to-python');

// 2. Create Spanish version
const spanishAsset = await createAsset(1, {
  slug: 'introduccion-a-python',
  title: 'Introducción a Python',
  asset_type: originalAsset.asset_type,
  lang: 'es',
  readme_url: originalAsset.readme_url.replace('.md', '.es.md'),
  technologies: originalAsset.technologies.map(t => t.slug),
  category: originalAsset.category.id
});

// 3. Pull Spanish content
await pullFromGitHub(1, 'introduccion-a-python');

// 4. Link translations bidirectionally
await updateAsset(1, 'intro-to-python', {
  all_translations: ['intro-to-python', 'introduccion-a-python']
});

await updateAsset(1, 'introduccion-a-python', {
  all_translations: ['intro-to-python', 'introduccion-a-python']
});

console.log('✅ Translation created and linked!');
```

### Example 3: Update Asset from GitHub

```javascript
// When content is updated in GitHub:

// 1. Pull latest changes
await pullFromGitHub(1, 'intro-to-python', false);

// 2. Regenerate processed content
await cleanAsset(1, 'intro-to-python');

// 3. Re-test
const testResults = await testAsset(1, 'intro-to-python');

if (testResults.test_status !== 'OK') {
  console.warn('⚠️ Tests detected issues:', testResults.warnings);
}

// 4. Regenerate thumbnail if needed
await generateThumbnail(1, 'intro-to-python');

console.log('✅ Asset updated from GitHub!');
```

---

## Best Practices

### 1. Always Test Before Publishing

```javascript
const safePub lish = async (academyId, assetSlug) => {
  // Test first
  const testResults = await testAsset(academyId, assetSlug);
  
  if (testResults.test_status === 'ERROR') {
    throw new Error('Cannot publish: asset has errors');
  }
  
  // Then publish
  await updateAsset(academyId, assetSlug, {
    status: 'PUBLISHED'
  });
};
```

### 2. Use Drafts for Work in Progress

Keep assets in DRAFT status while editing:

```javascript
// Start as draft
await createAsset(1, {
  slug: 'new-lesson',
  title: 'New Lesson',
  status: 'DRAFT',
  visibility: 'PRIVATE'
});

// Edit freely...

// Publish when ready
await updateAsset(1, 'new-lesson', {
  status: 'PUBLISHED',
  visibility: 'PUBLIC'
});
```

### 3. Link Translations Properly

Always link translations bidirectionally:

```javascript
const linkTranslations = async (academyId, slugs) => {
  for (const slug of slugs) {
    await updateAsset(academyId, slug, {
      all_translations: slugs
    });
  }
};

await linkTranslations(1, ['lesson-en', 'lesson-es', 'lesson-it']);
```

### 4. Subscribe to Auto-Sync for Active Content

Enable auto-sync for content actively maintained in GitHub:

```javascript
await updateAsset(1, 'active-lesson', {
  is_auto_subscribed: true
});
```

Disable for stable content to prevent unwanted updates:

```javascript
await updateAsset(1, 'stable-lesson', {
  is_auto_subscribed: false
});
```

### 5. Version Management

When creating a new version:

```javascript
// Create new version
const newVersion = await createAsset(1, {
  slug: 'python-intro-2024',
  title: 'Introduction to Python (2024 Edition)'
});

// Mark old version as superseded
await updateAsset(1, 'python-intro-2020', {
  superseded_by: newVersion.id,
  status: 'DRAFT'  // Optionally unpublish old version
});
```

---

## Troubleshooting

### Common Issues

#### Issue: "Asset not found for this academy"

**Cause:** The asset doesn't belong to the specified academy.

**Solution:** Check that you're using the correct academy_id and the asset exists.

#### Issue: "Technology not found"

**Cause:** Invalid technology slug in the request.

**Solution:** Get valid technology slugs first:

```javascript
const techs = await fetch('/v1/registry/academy/technology')
  .then(r => r.json());
console.log(techs.map(t => t.slug));
```

#### Issue: "Pull from GitHub failed"

**Cause:** Invalid GitHub URL or authentication issues.

**Solutions:**
- Verify `readme_url` is correct
- Check GitHub repository is accessible
- Ensure GitHub webhook is configured
- Try `override_meta: true` if stuck

#### Issue: "Test status shows ERROR"

**Cause:** Asset has integrity issues.

**Solution:** View detailed test results:

```javascript
const asset = await getAsset(1, 'my-lesson');
console.log(asset.test_status_details);
```

Fix reported issues and retest.

---

## Related Documentation

- [BUILD_SYLLABUS.md](./BUILD_SYLLABUS.md) - Managing syllabi and courses
- [AUTHENTICATION.md](./AUTHENTICATION.md) - API authentication
- [ACADEMY_PLANS.md](./ACADEMY_PLANS.md) - Academy plans and permissions

---

## Support

For questions or issues with asset management:
- Check test results and error messages
- Verify GitHub URLs and authentication
- Review permission capabilities
- Contact development team for API issues

**Last Updated:** October 2024

