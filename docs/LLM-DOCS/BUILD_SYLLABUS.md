# Building with Syllabus and Assets

This guide documents the key endpoints for interacting with syllabi and assets in the BreatheCode API.

## Base URL

All endpoints are prefixed with `/v1/admissions` for syllabus operations and `/v1/registry` for asset operations.

---

## Syllabus Endpoints

### List/Get Syllabi

**Endpoint:** `GET /v1/admissions/syllabus`

**Description:** List all syllabi accessible to the user (public + owned by academies they have access to)

**Query Parameters:**
- `like`: Filter by name or slug (case-insensitive)

**Permission Required:** `read_syllabus`

**Response:** Array of syllabus objects

---

**Endpoint:** `GET /v1/admissions/syllabus/{syllabus_id}`

**Description:** Get a specific syllabus by ID

**Permission Required:** `read_syllabus`

**Response:** Single syllabus object

---

**Endpoint:** `GET /v1/admissions/syllabus/{syllabus_slug}`

**Description:** Get a specific syllabus by slug

**Permission Required:** `read_syllabus`

**Response:** Single syllabus object

---

**Endpoint:** `GET /v1/admissions/academy/{academy_id}/syllabus`

**Description:** List all syllabi for a specific academy

**Permission Required:** `read_syllabus`

**Response:** Array of syllabus objects

---

**Endpoint:** `GET /v1/admissions/academy/{academy_id}/syllabus/{syllabus_id}`

**Description:** Get a specific syllabus for an academy by ID

**Permission Required:** `read_syllabus`

**Response:** Single syllabus object

---

**Endpoint:** `GET /v1/admissions/academy/{academy_id}/syllabus/{syllabus_slug}`

**Description:** Get a specific syllabus for an academy by slug

**Permission Required:** `read_syllabus`

**Response:** Single syllabus object

---

**Endpoint:** `GET /v1/admissions/public/syllabus`

**Description:** Get public syllabi (no authentication required)

**Response:** Array of public syllabus objects

---

### Create Syllabus

**Endpoint:** `POST /v1/admissions/academy/{academy_id}/syllabus`

**Description:** Create a new syllabus for an academy

**Permission Required:** `crud_syllabus`

**Request Body:**
```json
{
  "slug": "web-development-fundamentals",
  "name": "Web Development Fundamentals",
  "description": "Learn the basics of web development",
  "private": false
}
```

**Required Fields:**
- `slug`: Unique identifier for the syllabus
- `name`: Display name of the syllabus

**Response:** Created syllabus object (HTTP 201)

---

### Update Syllabus

**Endpoint:** `PUT /v1/admissions/academy/{academy_id}/syllabus/{syllabus_id}`

**Description:** Update an existing syllabus by ID

**Permission Required:** `crud_syllabus`

**Request Body:**
```json
{
  "name": "Updated Syllabus Name",
  "description": "Updated description",
  "private": true
}
```

**Notes:**
- Cannot set `slug` or `name` to empty strings
- Only the academy owner can update the syllabus

**Response:** Updated syllabus object (HTTP 200)

---

**Endpoint:** `PUT /v1/admissions/academy/{academy_id}/syllabus/{syllabus_slug}`

**Description:** Update an existing syllabus by slug

**Permission Required:** `crud_syllabus`

**Response:** Updated syllabus object (HTTP 200)

---

## Syllabus Version Endpoints

### List/Get Syllabus Versions

**Endpoint:** `GET /v1/admissions/syllabus/{syllabus_id}/version`

**Description:** List all versions of a syllabus

**Permission Required:** `read_syllabus`

**Query Parameters:**
- `status`: Filter by status (comma-separated: `PUBLISHED`, `DRAFT`, etc.)

**Response:** Array of syllabus version objects

---

**Endpoint:** `GET /v1/admissions/syllabus/{syllabus_slug}/version`

**Description:** List all versions of a syllabus by slug

**Permission Required:** `read_syllabus`

**Response:** Array of syllabus version objects

---

**Endpoint:** `GET /v1/admissions/syllabus/{syllabus_id}/version/{version}`

**Description:** Get a specific version of a syllabus

**Permission Required:** `read_syllabus`

**Special Values:**
- `version=latest`: Gets the latest published version

**Response:** Single syllabus version object

---

**Endpoint:** `GET /v1/admissions/syllabus/{syllabus_slug}/version/{version}`

**Description:** Get a specific version of a syllabus by slug

**Permission Required:** `read_syllabus`

**Response:** Single syllabus version object

---

**Endpoint:** `GET /v1/admissions/academy/{academy_id}/syllabus/{syllabus_id}/version`

**Description:** List all versions for an academy's syllabus

**Permission Required:** `read_syllabus`

**Response:** Array of syllabus version objects

---

**Endpoint:** `GET /v1/admissions/academy/{academy_id}/syllabus/{syllabus_id}/version/{version}`

**Description:** Get a specific version of an academy's syllabus

**Permission Required:** `read_syllabus`

**Response:** Single syllabus version object

---

**Endpoint:** `GET /v1/admissions/syllabus/version`

**Description:** Get all syllabus versions across all syllabi

**Permission Required:** `read_syllabus`

**Response:** Array of all syllabus version objects

---

### Create Syllabus Version

**Endpoint:** `POST /v1/admissions/syllabus/{syllabus_id}/version`

**Description:** Create a new version of a syllabus

**Permission Required:** `crud_syllabus`

**Request Body:**
```json
{
  "json": {
    "days": [],
    "weeks": []
  },
  "status": "DRAFT",
  "integrity_check_at": null,
  "integrity_status": "PENDING"
}
```

**Response:** Created syllabus version object (HTTP 201)

---

**Endpoint:** `POST /v1/admissions/syllabus/{syllabus_slug}/version`

**Description:** Create a new version of a syllabus by slug

**Permission Required:** `crud_syllabus`

**Response:** Created syllabus version object (HTTP 201)

---

**Endpoint:** `POST /v1/admissions/academy/{academy_id}/syllabus/{syllabus_id}/version`

**Description:** Create a new version for an academy's syllabus

**Permission Required:** `crud_syllabus`

**Response:** Created syllabus version object (HTTP 201)

---

### Update Syllabus Version

**Endpoint:** `PUT /v1/admissions/syllabus/{syllabus_id}/version/{version}`

**Description:** Update a specific version of a syllabus

**Permission Required:** `crud_syllabus`

**Request Body:**
```json
{
  "json": {
    "days": [],
    "weeks": []
  },
  "status": "PUBLISHED"
}
```

**Notes:**
- Version must be numeric
- Only the academy owner can update

**Response:** Updated syllabus version object (HTTP 200)

---

**Endpoint:** `PUT /v1/admissions/syllabus/{syllabus_slug}/version/{version}`

**Description:** Update a specific version of a syllabus by slug

**Permission Required:** `crud_syllabus`

**Response:** Updated syllabus version object (HTTP 200)

---

**Endpoint:** `PUT /v1/admissions/academy/{academy_id}/syllabus/{syllabus_id}/version/{version}`

**Description:** Update a specific version for an academy's syllabus

**Permission Required:** `crud_syllabus`

**Response:** Updated syllabus version object (HTTP 200)

---

### Export/Preview Syllabus Version

**Endpoint:** `GET /v1/admissions/syllabus/{syllabus_id}/version/{version}.csv`

**Description:** Export a syllabus version as CSV

**Permission Required:** `read_syllabus`

**Response:** CSV file download

---

**Endpoint:** `GET /v1/admissions/syllabus/{syllabus_id}/version/{version}/preview`

**Description:** Preview a syllabus version in HTML format

**Permission Required:** `read_syllabus`

**Response:** HTML preview

---

### Admin Endpoints

**Endpoint:** `PUT /v1/admissions/admin/syllabus/asset/{asset_slug}`

**Description:** Replace an asset slug across all syllabus versions

**Permission Required:** Superuser

**Response:** Summary of changes made

---

## Asset Endpoints

### List/Get Public Assets

**Endpoint:** `GET /v1/registry/asset`

**Description:** List all public assets

**Query Parameters:**
- `academy`: Filter by academy ID(s) (comma-separated)
- `asset_type`: Filter by asset type (e.g., `LESSON`, `ARTICLE`, `EXERCISE`, `PROJECT`)
- `category`: Filter by category slug(s) (comma-separated)
- `exclude_category`: Exclude category slug(s) (comma-separated)
- `technologies`: Filter by technology slug(s) (comma-separated)
- `exclude_technologies`: Exclude technology slug(s) (comma-separated)
- `language`: Filter by language code
- `video`: Filter assets with video (`true`)
- `external`: Filter external assets (`true`, `false`, or `both`)
- `like`: Search by title, slug, or content
- `status`: Filter by status (default shows only `PUBLISHED`)
- `visibility`: Filter by visibility (default is `PUBLIC`)
- `need_translation`: Show assets needing translation (`true`)
- `authors_username`: Filter by author username(s) (comma-separated)
- `big`: Return extended asset information
- `expand`: Expand related objects (e.g., `technologies,category`)

**Response:** Array of public asset objects

---

**Endpoint:** `GET /v1/registry/asset/{asset_slug}`

**Description:** Get a specific public asset by slug

**Response:** Single asset object

---

### List/Get User's Assets

**Endpoint:** `GET /v1/registry/asset/me`

**Description:** List assets created or owned by the authenticated user

**Permission Required:** `learnpack_create_package`

**Query Parameters:** Same as public asset endpoint

**Response:** Array of user's asset objects

---

**Endpoint:** `GET /v1/registry/asset/me/{asset_slug}`

**Description:** Get a specific asset owned by the user

**Permission Required:** `learnpack_create_package`

**Response:** Single asset object

---

### List/Get Academy Assets

**Endpoint:** `GET /v1/registry/academy/asset`

**Description:** List all assets for an academy (includes public assets and academy-specific assets)

**Permission Required:** `read_asset`

**Query Parameters:**
- All query parameters from public asset endpoint, plus:
- `author`: Filter by author ID
- `owner`: Filter by owner ID
- `like`: Search by slug, title, readme_url, url, or alias slug
- `asset_type`: Filter by asset type
- `category`: Filter by category slug(s)
- `exclude_category`: Exclude category slug(s)
- `technologies`: Filter by technology slug(s)
- `exclude_technologies`: Exclude technology slug(s)
- `language`: Filter by language
- `status`: Filter by status
- `visibility`: Filter by visibility
- `test_status`: Filter by test status
- `sync_status`: Filter by sync status
- `published`: Filter by published status
- `slug`: Filter by exact slug(s) (comma-separated)
- `interactive`: Filter interactive assets

**Notes:**
- Content writers can only see assets they authored
- Returns assets belonging to the academy or public assets

**Response:** Array of academy asset objects

---

**Endpoint (v1):** `GET /v1/registry/academy/asset/{asset_slug_or_id}`

**Description:** Get a specific asset for an academy by slug or ID

**Permission Required:** `read_asset`

**Response:** Single academy asset object

---

**Endpoint (v2):** `GET /v2/registry/academy/asset/{asset_slug}`

**Description:** Get a specific asset for an academy (v2 with consumption tracking)

**Permission Required:** `read_asset`

**Consumption:** `read_lesson` (tracks asset consumption)

**Response:** Single academy asset object

---

### Create Asset

**Endpoint:** `POST /v1/registry/asset/me`

**Description:** Create a new asset for the authenticated user

**Permission Required:** `learnpack_create_package`

**Request Body:**
```json
{
  "slug": "intro-to-python",
  "title": "Introduction to Python",
  "asset_type": "LESSON",
  "category": 1,
  "lang": "en",
  "readme": "# Introduction to Python\n\nThis is the content...",
  "visibility": "PUBLIC",
  "status": "DRAFT",
  "technologies": [1, 2, 3]
}
```

**Required Fields:**
- `slug`: Unique identifier
- `title`: Display title
- `asset_type`: Type of asset
- `category`: Category ID

**Response:** Created asset object (HTTP 201)

---

**Endpoint:** `POST /v1/registry/academy/asset`

**Description:** Create a new asset for an academy

**Permission Required:** `crud_asset`

**Request Body:** Same as above, asset is automatically assigned to the academy

**Response:** Created asset object (HTTP 201)

---

### Update Asset

**Endpoint:** `PUT /v1/registry/asset/me/{asset_slug}`

**Description:** Update an existing asset owned by the user

**Permission Required:** `learnpack_create_package`

**Request Body:**
```json
{
  "title": "Updated Title",
  "readme": "# Updated content...",
  "status": "PUBLISHED"
}
```

**Notes:**
- Can update single asset or multiple assets (send array)
- User must be the author or owner of the asset

**Response:** Updated asset object (HTTP 200)

---

**Endpoint:** `PUT /v1/registry/academy/asset/{asset_slug_or_id}`

**Description:** Update an existing asset for an academy

**Permission Required:** `crud_asset`

**Request Body:** Same as above

**Notes:**
- Asset must belong to the academy or be public (and will be claimed by the academy)

**Response:** Updated asset object (HTTP 200)

---

### Asset Actions

**Endpoint:** `POST /v1/registry/academy/asset/action/{action_slug}`

**Description:** Perform bulk actions on multiple assets

**Permission Required:** `crud_asset`

**Available Actions:**
- `test`: Run automated tests on the assets
- `pull`: Pull latest changes from GitHub
- `push`: Push changes to GitHub (ARTICLE, LESSON, QUIZ only)
- `analyze_seo`: Analyze SEO performance
- `claim_asset`: Claim an unowned asset for the academy
- `create_repo`: Create a GitHub repository for the asset

**Request Body:**
```json
{
  "assets": ["intro-to-python", "python-loops", "python-functions"],
  "override_meta": false
}
```

**Response:** Array of successfully processed assets

---

**Endpoint:** `PUT /v1/registry/academy/asset/{asset_slug}/action/{action_slug}`

**Description:** Perform an action on a single asset

**Permission Required:** `crud_asset`

**Available Actions:** Same as above

**Request Body:**
```json
{
  "override_meta": false
}
```

**Response:** Updated asset object (HTTP 200)

---

### Asset Relations and Metadata

**Endpoint:** `GET /v1/registry/asset/{asset_id}/context`

**Description:** Get context information for an asset

**Response:** Context object with related assets and metadata

---

**Endpoint:** `GET /v1/registry/asset/{asset_slug}/supersedes`

**Description:** Get assets that are superseded by this asset

**Permission Required:** `read_asset`

**Response:** Array of superseded assets

---

**Endpoint:** `GET /v1/registry/asset/{asset_slug}/github/config`

**Description:** Get GitHub configuration for an asset

**Response:** GitHub config object

---

**Endpoint:** `GET /v1/registry/asset/{asset_slug}.{extension}`

**Description:** Get asset readme in specific format

**Extensions:** `md`, `json`, `html`

**Response:** Rendered content in requested format

---

**Endpoint:** `GET /v1/registry/asset/preview/{asset_slug}`

**Description:** Preview asset in HTML

**Response:** HTML preview

---

**Endpoint:** `GET /v1/registry/asset/thumbnail/{asset_slug}`

**Description:** Get or generate asset thumbnail

**Response:** Image URL or generated thumbnail

---

**Endpoint:** `PUT /v1/registry/academy/asset/{asset_slug}/thumbnail`

**Description:** Update asset thumbnail

**Permission Required:** `crud_asset`

**Response:** Updated thumbnail URL

---

### Asset Comments

**Endpoint:** `GET /v1/registry/academy/asset/comment`

**Description:** List all comments on academy assets

**Permission Required:** `read_asset`

**Query Parameters:**
- `asset`: Filter by asset slug
- `status`: Filter by comment status
- `author`: Filter by author ID

**Response:** Array of comment objects

---

**Endpoint:** `POST /v1/registry/academy/asset/comment`

**Description:** Create a new comment on an asset

**Permission Required:** `crud_asset`

**Request Body:**
```json
{
  "asset": 1,
  "text": "This needs improvement...",
  "status": "PENDING"
}
```

**Response:** Created comment object (HTTP 201)

---

**Endpoint:** `PUT /v1/registry/academy/asset/comment/{comment_id}`

**Description:** Update an existing comment

**Permission Required:** `crud_asset`

**Response:** Updated comment object (HTTP 200)

---

**Endpoint:** `DELETE /v1/registry/academy/asset/comment/{comment_id}`

**Description:** Delete a comment

**Permission Required:** `crud_asset`

**Response:** HTTP 204 (No Content)

---

### Asset Errors

**Endpoint:** `GET /v1/registry/academy/asset/error`

**Description:** List all errors for academy assets

**Permission Required:** `read_asset`

**Query Parameters:**
- `asset`: Filter by asset slug
- `status`: Filter by error status

**Response:** Array of error objects

---

**Endpoint:** `PUT /v1/registry/academy/asset/error`

**Description:** Update multiple errors (bulk operation)

**Permission Required:** `crud_asset_error`

**Response:** Array of updated error objects

---

**Endpoint:** `DELETE /v1/registry/academy/asset/error/{error_id}`

**Description:** Delete a specific error

**Permission Required:** `crud_asset_error`

**Response:** HTTP 204 (No Content)

---

**Endpoint:** `DELETE /v1/registry/academy/asset/error`

**Description:** Delete multiple errors (bulk operation)

**Permission Required:** `crud_asset_error`

**Query Parameters:** Use filter parameters like `id=1,2,3`

**Response:** HTTP 204 (No Content)

---

### Asset Aliases

**Endpoint:** `GET /v1/registry/academy/asset/alias`

**Description:** List all asset aliases for an academy

**Permission Required:** `read_asset`

**Response:** Array of alias objects

---

**Endpoint:** `GET /v1/registry/academy/asset/alias/{alias_slug}`

**Description:** Get a specific alias

**Permission Required:** `read_asset`

**Response:** Single alias object

---

**Endpoint:** `DELETE /v1/registry/academy/asset/alias/{alias_slug}`

**Description:** Delete an asset alias

**Permission Required:** `crud_asset`

**Notes:**
- Cannot delete an alias if it's the same as the asset's main slug (must rename asset first)

**Response:** HTTP 204 (No Content)

---

### SEO and Quality

**Endpoint:** `GET /v1/registry/academy/asset/{asset_slug}/seo_report`

**Description:** Get SEO analysis report for an asset

**Permission Required:** `read_asset`

**Response:** SEO report object

---

**Endpoint:** `GET /v1/registry/academy/asset/{asset_slug}/originality`

**Description:** Get originality/plagiarism check for an asset

**Permission Required:** `read_asset`

**Response:** Originality report object

---

### Asset Images

**Endpoint:** `GET /v1/registry/academy/asset/image`

**Description:** List all images used in academy assets

**Permission Required:** `read_asset`

**Query Parameters:**
- `slug`: Filter by asset slug(s)
- `download_status`: Filter by download status
- `original_url`: Filter by original URL

**Response:** Array of asset image objects

---

## Permission Requirements

### Syllabus Permissions
- `read_syllabus`: View syllabi and versions
- `crud_syllabus`: Create, update, and delete syllabi and versions

### Asset Permissions
- `read_asset`: View assets
- `crud_asset`: Create, update assets
- `crud_asset_error`: Manage asset errors
- `learnpack_create_package`: Create/update personal assets

## Common Patterns

### Filtering by Academy

Many endpoints support filtering by academy:

```
GET /v1/registry/asset?academy=1,2,3
```

This returns assets from academies 1, 2, and 3, plus public assets.

### Searching Assets

Use the `like` parameter for fuzzy search:

```
GET /v1/registry/academy/asset?like=python
```

This searches in slug, title, readme_url, url, and alias slugs.

### Pagination

Most list endpoints support pagination:

```
GET /v1/registry/academy/asset?limit=20&offset=40
```

### Expanding Relations

Use the `expand` parameter to include related objects:

```
GET /v1/registry/asset?expand=technologies,category,author
```

### Getting Latest Version

To get the latest published version of a syllabus:

```
GET /v1/admissions/syllabus/{syllabus_id}/version/latest
```

## Notes

- All endpoints require appropriate authentication unless explicitly marked as public
- Academy-scoped endpoints require the user to be a member of the academy
- Assets can be either academy-specific or public (shared across academies)
- Syllabi are owned by academies but can be marked as private or public
- Asset types include: `LESSON`, `ARTICLE`, `EXERCISE`, `PROJECT`, `QUIZ`, `VIDEO`, etc.
- Syllabus versions can have status: `DRAFT`, `PUBLISHED`, etc.

