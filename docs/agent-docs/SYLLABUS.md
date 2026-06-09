# Syllabus Creation - Complete Guide

This guide covers the entire flow to create a syllabus, including all dependencies, validation, and versioning.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Step-by-Step Flow](#step-by-step-flow)
3. [Syllabus JSON Structure](#syllabus-json-structure) (includes [macro cohort overrides](#macro-cohort-syllabus-overrides-per-micro-slug))
4. [API Endpoints Reference](#api-endpoints-reference)
5. [Complete Examples](#complete-examples)
6. [Validation and Testing](#validation-and-testing)
7. [Troubleshooting](#troubleshooting)


---

## 🎯 Prerequisites

Before creating a syllabus, you need to have the following dependencies in place:

### 1. **Academy** (Optional but Recommended)
- An academy can own private syllabi
- Academy provides context for syllabus ownership
- Public syllabi can be used by any academy

### 2. **Assets** (Required for Content)
- **Lessons**: Educational content assets
- **Quizzes**: Assessment assets
- **Replits**: Interactive coding exercises
- **Assignments**: Project-based learning assets

---

## 🚀 Step-by-Step Flow

### Step 1: Create or Verify Academy (Optional)

**Endpoint:** `POST /v1/admissions/academy`

**Required Fields:**
- `slug` - Unique academy identifier
- `name` - Academy display name
- `logo_url` - Academy logo URL
- `street_address` - Physical address
- `city` - City ID (from catalog)
- `country` - Country code

**Example:**
```bash
curl -X POST "https://your-api.com/v1/admissions/academy" \
  -H "Authorization: Token your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "miami-academy",
    "name": "Miami Academy",
    "logo_url": "https://example.com/logo.png",
    "street_address": "123 Main St",
    "city": 1,
    "country": "us",
    "timezone": "America/New_York"
  }'
```

**Response:**
```json
{
  "id": 1,
  "slug": "miami-academy",
  "name": "Miami Academy",
  "owner": {
    "id": 123,
    "email": "admin@miami-academy.com"
  },
  "timezone": "America/New_York",
  "status": "ACTIVE"
}
```

### Step 2: Create Syllabus

**Endpoint:** `POST /v1/admissions/syllabus`

**Required Fields:**
- `slug` - Unique syllabus identifier
- `name` - Syllabus display name

**Example:**
```bash
curl -X POST "https://your-api.com/v1/admissions/syllabus" \
  -H "Authorization: Token your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "full-stack-web-development",
    "name": "Full Stack Web Development",
    "main_technologies": "HTML, CSS, JavaScript, React, Node.js",
    "duration_in_hours": 400,
    "duration_in_days": 16,
    "week_hours": 25,
    "logo": "https://example.com/syllabus-logo.png",
    "github_url": "https://github.com/4geeksacademy/full-stack-syllabus",
    "academy_owner": 1,
    "private": false,
    "is_documentation": false
  }'
```

**Response:**
```json
{
  "id": 1,
  "slug": "full-stack-web-development",
  "name": "Full Stack Web Development",
  "main_technologies": "HTML, CSS, JavaScript, React, Node.js",
  "duration_in_hours": 400,
  "duration_in_days": 16,
  "week_hours": 25,
  "logo": "https://example.com/syllabus-logo.png",
  "github_url": "https://github.com/4geeksacademy/full-stack-syllabus",
  "academy_owner": 1,
  "private": false,
  "is_documentation": false,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

**Note:** A signal automatically creates version 1 when a syllabus is created.

### Step 3: Create Syllabus Version

**Endpoint:** `POST /v1/admissions/syllabus/{syllabus_id}/version`

**Required Fields:**
- `json` - Syllabus content in JSON format
- `status` - Must be "PUBLISHED" for cohorts

**Example:**
```bash
curl -X POST "https://your-api.com/v1/admissions/syllabus/1/version" \
  -H "Authorization: Token your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "json": {
      "days": [
        {
          "id": 1,
          "label": "HTML/CSS Fundamentals",
          "lessons": [
            {
              "slug": "intro-to-html",
              "title": "Introduction to HTML"
            },
            {
              "slug": "css-basics",
              "title": "CSS Fundamentals"
            }
          ],
          "quizzes": [
            {
              "slug": "html-quiz",
              "title": "HTML Knowledge Check",
              "mandatory": true
            }
          ],
          "replits": [
            {
              "slug": "html-exercises",
              "title": "HTML Practice Exercises"
            }
          ],
          "assignments": [
            {
              "slug": "build-a-website",
              "title": "Build Your First Website"
            }
          ],
          "project": {
            "title": "Personal Portfolio Website",
            "instructions": "Create a personal portfolio using HTML and CSS"
          },
          "teacher_instructions": "Focus on semantic HTML and responsive CSS design principles."
        }
      ]
    },
    "status": "PUBLISHED",
    "change_log_details": "Initial version with HTML/CSS fundamentals"
  }'
```

**Response:**
```json
{
  "id": 1,
  "version": 2,
  "syllabus": 1,
  "status": "PUBLISHED",
  "change_log_details": "Initial version with HTML/CSS fundamentals",
  "integrity_status": "PENDING",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

## 📚 Syllabus JSON Structure

### **Root Structure**
```json
{
  "days": [
    {
      "id": 1,
      "label": "Module Name",
      "lessons": [...],
      "quizzes": [...],
      "replits": [...],
      "assignments": [...],
      "project": {...},
      "teacher_instructions": "Instructions for teachers"
    }
  ]
}
```

### **Day/Module Structure**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | integer | ✅ | Unique day/module identifier |
| `label` | string | ✅ | Module name/title |
| `lessons` | array | ❌ | List of lesson assets |
| `quizzes` | array | ❌ | List of quiz assets |
| `replits` | array | ❌ | List of replit assets |
| `assignments` | array | ❌ | List of assignment assets |
| `project` | object | ❌ | Project information |
| `teacher_instructions` | string | ❌ | Instructions for teachers |

### **Asset Structure**

#### **Lessons**
```json
{
  "slug": "lesson-slug",
  "title": "Lesson Title"
}
```

#### **Quizzes**
```json
{
  "slug": "quiz-slug",
  "title": "Quiz Title",
  "url": "https://quiz-url.com",
  "target": "self",
  "mandatory": true
}
```

#### **Replits**
```json
{
  "slug": "replit-slug",
  "title": "Replit Title"
}
```

#### **Assignments**
```json
{
  "slug": "assignment-slug",
  "title": "Assignment Title"
}
```

#### **Project**
```json
{
  "title": "Project Title",
  "instructions": "Project instructions or URL"
}
```

### **Complete Example**
```json
{
  "days": [
    {
      "id": 1,
      "label": "HTML/CSS Fundamentals",
      "lessons": [
        {
          "slug": "intro-to-html",
          "title": "Introduction to HTML"
        },
        {
          "slug": "css-basics",
          "title": "CSS Fundamentals"
        }
      ],
      "quizzes": [
        {
          "slug": "html-quiz",
          "title": "HTML Knowledge Check",
          "mandatory": true
        }
      ],
      "replits": [
        {
          "slug": "html-exercises",
          "title": "HTML Practice Exercises"
        }
      ],
      "assignments": [
        {
          "slug": "build-a-website",
          "title": "Build Your First Website"
        }
      ],
      "project": {
        "title": "Personal Portfolio Website",
        "instructions": "Create a personal portfolio using HTML and CSS"
      },
      "teacher_instructions": "Focus on semantic HTML and responsive CSS design principles."
    },
    {
      "id": 2,
      "label": "JavaScript Basics",
      "lessons": [
        {
          "slug": "intro-to-javascript",
          "title": "Introduction to JavaScript"
        }
      ],
      "quizzes": [
        {
          "slug": "javascript-quiz",
          "title": "JavaScript Fundamentals Quiz",
          "mandatory": true
        }
      ],
      "replits": [
        {
          "slug": "javascript-exercises",
          "title": "JavaScript Practice"
        }
      ],
      "assignments": [],
      "project": {
        "title": "Interactive Calculator",
        "instructions": "Build a calculator using JavaScript"
      },
      "teacher_instructions": "Emphasize DOM manipulation and event handling."
    }
  ]
}
```

### Macro cohort syllabus overrides (per-micro slug)

A macro cohort’s **`SyllabusVersion.json`** may include extra keys shaped like **`<micro-syllabus-slug>.v<version>`** or **`<position>:<micro-syllabus-slug>.v<version>`** (examples: `jumpstart.v2`, `0:jumpstart.v2`, `1:basics-of-front-end-development.v2`). When the API resolves that micro syllabus with macro context, it **merges** the block into the micro JSON. See `resolve_syllabus_json` / `apply_reference_override` in `breathecode.admissions.actions`.

| Rule | Behavior |
|------|----------|
| **`days`** | Merged **by array index** (`days[0]` with the first day of the micro, etc.). |
| **`lessons`**, **`quizzes`**, **`replits`**, **`assignments`** | Merged **by index inside each day** (same as days). |
| **Skip a slot** | Use **`null`** at that index (no change to the base item). |
| **Remove an item** | Use **`{ "status": "DELETED" }`** at that index; it is dropped after merge. |
| **Other day fields** | Shallow-merged into the base day (e.g. `teacher_instructions`, `extended_instructions`). |

`teacher_instructions` alone do **not** add lessons; you must include a **`lessons`** array in the override day when you want to add or change lesson entries.

#### Replacing the **first** lesson with a new one (`DELETED` + append)

Because the merge is positional, you cannot “insert before” the first lesson without touching index `0`. A supported pattern when the day has **exactly one** lesson in the base micro syllabus:

1. At **`lessons[0]`**, set **`{ "status": "DELETED" }`** so the original first lesson is removed.
2. At **`lessons[1]`**, put the **full new** lesson object (`slug`, `title`, `url`, `target`, `mandatory`, etc.).

After merge, that day ends up with only the new lesson (the old one is gone and the new one is appended after the deleted slot, then `null` entries are stripped).

```json
"lessons": [
  { "status": "DELETED" },
  {
    "slug": "my-new-lesson",
    "title": "My new lesson",
    "url": "https://github.com/org/repo",
    "target": "self",
    "mandatory": true
  }
]
```

**Caveat:** If the base day has **more than one** lesson, `DELETED` at `0` plus a new object at `1` will **merge into the second base lesson**, not “replace first + keep the rest” in one shot. For multi-lesson days, either build the **full intended `lessons` list** explicitly (with `DELETED`, `{}`, and objects as needed) or publish a **new micro syllabus version** with the correct order.

---

## Macro cohort syllabus overrides

Macro cohorts can carry a **`SyllabusVersion`** whose JSON is not only the usual root **`days`** list. It may also include **reference keys** so that, when someone reads a **micro** syllabus in the context of that macro, the API merges overrides from the macro into the micro.

#### Reference keys

- Pattern (legacy): **`<micro-syllabus-slug>.v<version>`** (examples: `front-end.v1`, `data-science.v3`).
- Pattern (ordered): **`<position>:<micro-syllabus-slug>.v<version>`** (examples: `0:front-end.v1`, `1:data-science.v3`).
- Backward compatibility: both formats are accepted. If both formats point to the same canonical reference (`slug.vN`) in one JSON object, validation reports it as duplicated.
- Ordering: when a numeric prefix is present, the prefix is the authoritative order metadata for reference processing.
- Each key maps to an **object** (typically with a **`days`** array) that is merged into the **micro** syllabus JSON for that slug/version.
- The backend resolves which block to apply using the **micro** syllabus’s `slug` and `version` being requested.

#### Merge rules (high level)

- **`days`**: merged **by index** (day 0 with day 0, etc.). Changing the order of days in the micro syllabus is not supported via overrides alone; publish a **new micro syllabus version** if the base order must change.
- **Asset lists** `lessons`, `quizzes`, `replits`, `assignments`: merged **by index** within each day.
- **Logical deletion**: an asset (or a whole day) can be marked with **`"status": "DELETED"`** so it does not appear after merge.
- Other day-level fields are merged with the base day where applicable.

#### API: read a micro syllabus version with macro overrides

When fetching an **academy-scoped** syllabus version, pass the macro cohort **slug** as a query parameter. The response’s **`json`** field is the **effective** syllabus (micro + merge).

- **Query parameter:** `macro-cohort=<macro_cohort_slug>`
- **Example:**  
  `GET /v1/admissions/academy/{academy_id}/syllabus/{syllabus_slug}/version/{version}?macro-cohort=ai-engineering-1`
- **Requirements:**
  - A **Cohort** with that `slug` must exist for the same **academy** (`academy_id`).
  - That cohort must have a **`syllabus_version`** (the macro syllabus JSON used as the override source).

**Errors (examples):** `macro-cohort-not-found`, `macro-cohort-missing-syllabus-version`.

#### Example: macro `SyllabusVersion.json` (fragment)

```json
{
  "days": [],

  "0:front-end.v1": {
    "days": [
      {},
      {},
      {},
      {
        "label": "Day 4 — custom for this macro only",
        "assignments": [
          {},
          { "slug": "custom-project", "title": "Macro-only project" }
        ]
      }
    ]
  }
}
```

The fourth element of `days` (index `3`) merges into **day 4** of `front-end` **v1**; the second assignment (index `1`) overrides the second assignment slot for that day.

For implementation details, see `resolve_syllabus_json` and related helpers in `breathecode.admissions.actions`.

---

## 📚 API Endpoints Reference

### Syllabus Management

| Method | Endpoint | Description | Required Headers |
|--------|----------|-------------|------------------|
| `GET` | `/v1/admissions/syllabus` | List all syllabi | None |
| `POST` | `/v1/admissions/syllabus` | Create syllabus | `Authorization` |
| `GET` | `/v1/admissions/syllabus/{id}` | Get syllabus details | None |
| `PUT` | `/v1/admissions/syllabus/{id}` | Update syllabus | `Authorization` |
| `GET` | `/v1/admissions/syllabus/{slug}` | Get syllabus by slug | None |

### Academy-Scoped Syllabus Management

| Method | Endpoint | Description | Required Headers |
|--------|----------|-------------|------------------|
| `GET` | `/v1/admissions/academy/{id}/syllabus` | List academy syllabi | None |
| `POST` | `/v1/admissions/academy/{id}/syllabus` | Create academy syllabus | `Authorization` |
| `GET` | `/v1/admissions/academy/{id}/syllabus/{id}` | Get academy syllabus | None |
| `PUT` | `/v1/admissions/academy/{id}/syllabus/{id}` | Update academy syllabus | `Authorization` |

### Syllabus Version Management

| Method | Endpoint | Description | Required Headers |
|--------|----------|-------------|------------------|
| `GET` | `/v1/admissions/syllabus/{id}/version` | List syllabus versions | None |
| `POST` | `/v1/admissions/syllabus/{id}/version` | Create syllabus version | `Authorization` |
| `GET` | `/v1/admissions/syllabus/{id}/version/{version}` | Get specific version | None |
| `PUT` | `/v1/admissions/syllabus/{id}/version/{version}` | Update version | `Authorization` |

### Academy syllabus version (optional macro overrides)

| Method | Endpoint | Description | Query / notes |
|--------|----------|-------------|----------------|
| `GET` | `/v1/admissions/academy/{academy_id}/syllabus/{syllabus_slug}/version/{version}` | Get one published syllabus version for an academy | Optional **`macro-cohort={macro_cohort_slug}`**: response `json` is merged with the macro cohort’s `SyllabusVersion` (see [Macro cohort syllabus overrides](#macro-cohort-syllabus-overrides)). Same `Academy` header as other academy-scoped routes. |

### Syllabus Testing

| Method | Endpoint | Description | Required Headers |
|--------|----------|-------------|------------------|
| `POST` | `/v1/admissions/syllabus/test` | Test syllabus JSON | `Authorization` |

---

## 🎯 Complete Examples

### Example 1: Minimal Syllabus Creation

```bash
# 1. Create Syllabus
curl -X POST "https://api.breatheco.de/v1/admissions/syllabus" \
  -H "Authorization: Token your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "web-dev-basics",
    "name": "Web Development Basics"
  }'

# 2. Create Syllabus Version
curl -X POST "https://api.breatheco.de/v1/admissions/syllabus/1/version" \
  -H "Authorization: Token your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "json": {
      "days": [
        {
          "id": 1,
          "label": "Introduction",
          "lessons": [
            {
              "slug": "intro-to-web",
              "title": "Introduction to Web Development"
            }
          ],
          "teacher_instructions": "Welcome students to web development"
        }
      ]
    },
    "status": "PUBLISHED"
  }'
```

### Example 2: Complete Syllabus with All Content Types

```bash
# 1. Create Syllabus
curl -X POST "https://api.breatheco.de/v1/admissions/syllabus" \
  -H "Authorization: Token your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "full-stack-bootcamp",
    "name": "Full Stack Development Bootcamp",
    "main_technologies": "HTML, CSS, JavaScript, React, Node.js, MongoDB",
    "duration_in_hours": 400,
    "duration_in_days": 16,
    "week_hours": 25,
    "logo": "https://example.com/logo.png",
    "github_url": "https://github.com/academy/full-stack-syllabus",
    "academy_owner": 1,
    "private": false
  }'

# 2. Create Comprehensive Syllabus Version
curl -X POST "https://api.breatheco.de/v1/admissions/syllabus/1/version" \
  -H "Authorization: Token your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "json": {
      "days": [
        {
          "id": 1,
          "label": "HTML/CSS Fundamentals",
          "lessons": [
            {
              "slug": "intro-to-html",
              "title": "Introduction to HTML"
            },
            {
              "slug": "css-basics",
              "title": "CSS Fundamentals"
            },
            {
              "slug": "responsive-design",
              "title": "Responsive Web Design"
            }
          ],
          "quizzes": [
            {
              "slug": "html-css-quiz",
              "title": "HTML/CSS Knowledge Check",
              "mandatory": true
            }
          ],
          "replits": [
            {
              "slug": "html-exercises",
              "title": "HTML Practice Exercises"
            },
            {
              "slug": "css-exercises",
              "title": "CSS Practice Exercises"
            }
          ],
          "assignments": [
            {
              "slug": "build-portfolio",
              "title": "Build a Personal Portfolio"
            }
          ],
          "project": {
            "title": "Personal Portfolio Website",
            "instructions": "Create a responsive personal portfolio using HTML and CSS"
          },
          "teacher_instructions": "Focus on semantic HTML, CSS Grid, Flexbox, and responsive design principles. Ensure students understand the box model and CSS specificity."
        },
        {
          "id": 2,
          "label": "JavaScript Fundamentals",
          "lessons": [
            {
              "slug": "intro-to-javascript",
              "title": "Introduction to JavaScript"
            },
            {
              "slug": "dom-manipulation",
              "title": "DOM Manipulation"
            },
            {
              "slug": "async-javascript",
              "title": "Asynchronous JavaScript"
            }
          ],
          "quizzes": [
            {
              "slug": "javascript-quiz",
              "title": "JavaScript Fundamentals Quiz",
              "mandatory": true
            }
          ],
          "replits": [
            {
              "slug": "javascript-exercises",
              "title": "JavaScript Practice"
            }
          ],
          "assignments": [
            {
              "slug": "interactive-calculator",
              "title": "Build an Interactive Calculator"
            }
          ],
          "project": {
            "title": "Interactive Web Application",
            "instructions": "Build an interactive web application using vanilla JavaScript"
          },
          "teacher_instructions": "Emphasize DOM manipulation, event handling, and asynchronous programming. Cover ES6+ features and modern JavaScript practices."
        }
      ]
    },
    "status": "PUBLISHED",
    "change_log_details": "Initial comprehensive version with HTML/CSS and JavaScript modules"
  }'
```

### Example 3: Academy-Scoped Syllabus

```bash
# 1. Create Academy-Scoped Syllabus
curl -X POST "https://api.breatheco.de/v1/admissions/academy/1/syllabus" \
  -H "Authorization: Token your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "miami-web-dev",
    "name": "Miami Web Development Program",
    "main_technologies": "HTML, CSS, JavaScript, React",
    "duration_in_hours": 300,
    "academy_owner": 1,
    "private": true
  }'

# 2. Create Version for Academy Syllabus
curl -X POST "https://api.breatheco.de/v1/admissions/syllabus/2/version" \
  -H "Authorization: Token your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "json": {
      "days": [
        {
          "id": 1,
          "label": "Miami-Specific Web Development",
          "lessons": [
            {
              "slug": "miami-tech-scene",
              "title": "Miami Tech Scene Overview"
            }
          ],
          "teacher_instructions": "Focus on local Miami tech opportunities and networking"
        }
      ]
    },
    "status": "PUBLISHED"
  }'
```

---

## 🔧 Field Reference

### Syllabus Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | ✅ | Unique identifier |
| `name` | string | ✅ | Display name |
| `main_technologies` | string | ❌ | Comma-separated technologies |
| `duration_in_hours` | integer | ❌ | Total hours |
| `duration_in_days` | integer | ❌ | Total days |
| `week_hours` | integer | ❌ | Hours per week |
| `logo` | string | ❌ | Logo URL |
| `github_url` | string | ❌ | GitHub repository URL |
| `academy_owner` | integer | ❌ | Academy ID (for private syllabi) |
| `private` | boolean | ❌ | Private to academy owner |
| `is_documentation` | boolean | ❌ | Documentation-only syllabus |

### Syllabus Version Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `json` | object | ✅ | Syllabus content |
| `status` | string | ✅ | "PUBLISHED" or "DRAFT" |
| `change_log_details` | string | ❌ | Change description |

### Version Status Options

| Status | Description |
|--------|-------------|
| `PUBLISHED` | Available for cohorts |
| `DRAFT` | Work in progress |

---

## 🧪 Validation and Testing

### **Syllabus Validation**

The system automatically validates syllabus JSON when creating versions:

1. **Structure Validation**: Ensures `days` array exists
2. **Asset Validation**: Checks that referenced assets exist
3. **Content Validation**: Validates lesson, quiz, replit, and assignment slugs
4. **Teacher Instructions**: Warns if missing or empty

### **Test Syllabus Endpoint**

**Endpoint:** `POST /v1/admissions/syllabus/test`

**Example:**
```bash
curl -X POST "https://api.breatheco.de/v1/admissions/syllabus/test" \
  -H "Authorization: Token your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "json": {
      "days": [
        {
          "id": 1,
          "label": "Test Module",
          "lessons": [
            {
              "slug": "test-lesson",
              "title": "Test Lesson"
            }
          ],
          "teacher_instructions": "Test instructions"
        }
      ]
    }
  }'
```

**Response:**
```json
{
  "status": "OK",
  "errors": [],
  "warnings": []
}
```

### **Validation Rules**

1. **Required Fields**: Each day must have `id` and `label`
2. **Asset Slugs**: All asset slugs must be strings
3. **Asset Existence**: Referenced assets must exist in the system
4. **Teacher Instructions**: Should not be empty (warning only)
5. **Unique IDs**: Day IDs should be unique within the syllabus

---

## ⚠️ Important Notes

### **Version Management**
- **Version 1**: Automatically created when syllabus is created (marketing only)
- **Version 2+**: Can be assigned to cohorts
- **Status**: Must be "PUBLISHED" for cohorts
- **Auto-increment**: Versions are automatically incremented

### **Academy Ownership**
- **Public Syllabi**: Can be used by any academy (`private=false`)
- **Private Syllabi**: Only accessible by academy owner (`private=true`)
- **Academy Owner**: Set via `academy_owner` field

### **Asset Dependencies**
- **Lessons**: Must exist in the asset registry
- **Quizzes**: Must exist in the asset registry
- **Replits**: Must exist in the asset registry
- **Assignments**: Must exist in the asset registry

### **Change Tracking**
- **Change Log**: Automatically generated for version creation
- **User Tracking**: Records who created each version
- **Timestamp**: Includes creation timestamp

---

## 🚨 Troubleshooting

### Common Errors

#### 1. "Syllabus must have a 'days' property"
**Error:** `Syllabus must have a 'days' or 'modules' property`
**Solution:** Ensure JSON has a `days` array at the root level

#### 2. "Missing slug on lessons property"
**Error:** `Missing slug on lessons property on module {index}`
**Solution:** Ensure all assets have a `slug` field

#### 3. "Missing lesson with slug {slug}"
**Error:** `Missing lesson with slug {slug} on module {index}`
**Solution:** Ensure the referenced asset exists in the system

#### 4. "Empty teacher instructions"
**Warning:** `Empty teacher instructions on module {index}`
**Solution:** Add meaningful teacher instructions for each module

#### 5. "Syllabus with errors"
**Error:** `There are {count} errors in your syllabus`
**Solution:** Fix all validation errors before submitting

### Validation Tips

1. **Test First**: Use the test endpoint before creating versions
2. **Check Assets**: Ensure all referenced assets exist
3. **Validate Structure**: Follow the JSON structure exactly
4. **Review Instructions**: Add meaningful teacher instructions
5. **Check Slugs**: Ensure all slugs are valid strings

### Debug Steps

1. **Test Syllabus**: `POST /v1/admissions/syllabus/test`
2. **List Assets**: Check available assets in the registry
3. **Validate JSON**: Use JSON validators for structure
4. **Check Permissions**: Ensure you have `crud_syllabus` capability
5. **Review Logs**: Check server logs for detailed error messages

---

## 📞 Support

For additional help:
- Check API documentation: `/docs/`
- Review error messages for specific guidance
- Ensure all required fields are provided
- Verify permissions and academy context
- Test syllabus JSON before creating versions

---

## 🔄 Version Lifecycle

### **Version 1 (Marketing)**
- Automatically created when syllabus is created
- Used for marketing purposes only
- Cannot be assigned to cohorts
- Always has status "PUBLISHED"

### **Version 2+ (Functional)**
- Created manually via API
- Can be assigned to cohorts
- Must have status "PUBLISHED" for cohorts
- Supports "DRAFT" status for work in progress

### **Version Management**
- Versions are auto-incremented
- Previous versions are preserved
- Change logs track modifications
- Integrity checks validate content

---

*This guide covers the complete flow for creating syllabi with all dependencies. Follow the steps in order for successful syllabus creation and versioning.*
