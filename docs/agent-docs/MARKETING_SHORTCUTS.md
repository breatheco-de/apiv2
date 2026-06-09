# Marketing Short Links API

The Marketing Short Links API allows you to create, manage, and track short URLs for marketing campaigns. Short links automatically append UTM parameters to destination URLs and track click statistics.

## Overview

Short links are accessible via `/s/<slug>` and redirect to destination URLs with UTM parameters automatically appended. The system tracks click counts, validates destination URLs, and monitors link health.

## Model Structure

Each ShortLink has the following key properties:

- `slug`: Unique identifier for the short link (auto-generated if not provided)
- `destination`: The full URL to redirect to
- `hits`: Number of clicks (automatically incremented)
- `active`: Whether the link is active (inactive links won't redirect)
- `private`: If true, only visible to the owning academy
- `destination_status`: Health status (ACTIVE, ERROR, NOT_FOUND)
- `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term`, `utm_placement`, `utm_plan`: UTM tracking parameters
- `academy`: The academy that owns this link
- `author`: The user who created the link
- `lastclick_at`: Timestamp of the last click
- `event`: Event reference in format `"<id:slug>"` (e.g., `"<3434:event_slug>"`) - Optional, for event promotions
- `course`: Course reference in format `"<id:slug>"` (e.g., `"<123:course_slug>"`) - Optional, for course promotions
- `downloadable`: Downloadable content reference in format `"<id:slug>"` (e.g., `"<567:downloadable_slug>"`) - Optional, for content downloads
- `plan`: Plan reference in format `"<id:slug>"` (e.g., `"<789:plan_slug>"`) - Optional, for subscription plan promotions
- `referrer_user`: User ID of the referrer (for affiliate tracking) - Optional ForeignKey to User
- `purpose`: Internal description of what this link is used for - Optional TextField (max 500 chars)
- `notes`: Internal notes about this short link - Optional TextField (max 1000 chars)

## API Endpoints

All endpoints require authentication and are under `/v1/marketing/academy/`.

### List Short Links

**GET** `/v1/marketing/academy/short`

Lists all short links accessible to the authenticated academy.

**Required Capability:** `read_shortlink`

**Query Parameters:**
- `private=true`: Filter to show only private links
- `like=<search_term>`: Search by slug (case-insensitive)
- `sort=<field>`: Sort by field (default: `-created_at`)
- Standard pagination parameters

**Response:**
```json
[
    {
        "id": 1,
        "slug": "L1",
        "destination": "https://example.com/landing",
        "hits": 42,
        "private": true,
        "destination_status": "ACTIVE",
        "destination_status_text": null,
        "lastclick_at": "2025-01-15T10:30:00Z",
        "active": true,
        "utm_content": null,
        "utm_medium": "social",
        "utm_campaign": "summer-2025",
        "utm_source": "facebook",
        "utm_placement": null,
        "utm_term": null,
        "utm_plan": null,
        "event": null,
        "course": null,
        "downloadable": null,
        "plan": null,
        "referrer_user": null,
        "purpose": null,
        "notes": null
    }
]
```

**Access Rules:**
- Shows links from your academy
- Shows public links (where `private=false`) from other academies
- Private links from other academies are hidden

### Get Single Short Link

**GET** `/v1/marketing/academy/short/<slug>`

Get a specific short link by slug.

**Required Capability:** `read_shortlink`

**Response:** Same structure as list endpoint (single object)

**Error:** Returns 404 if link not found or if it's private and belongs to another academy

### Create Short Link

**POST** `/v1/marketing/academy/short`

Create a new short link.

**Required Capability:** `crud_shortlink`

**Request Body:**
```json
{
    "slug": "summer-promo",  // Optional: auto-generated if not provided
    "destination": "https://example.com/landing",
    "active": true,
    "private": true,
    "utm_source": "facebook",
    "utm_medium": "social",
    "utm_campaign": "summer-2025",
    "utm_content": "ad-123",
    "utm_term": "coding-bootcamp",
    "utm_placement": "feed",
    "utm_plan": "upfront",
    "event": "<3434:summer-workshop-2025>",  // Optional: Event reference in format "<id:slug>"
    "course": "<123:full-stack-bootcamp>",  // Optional: Course reference in format "<id:slug>"
    "downloadable": "<567:course-guide>",  // Optional: Downloadable reference in format "<id:slug>"
    "plan": "<789:4geeks-plus-subscription>",  // Optional: Plan reference in format "<id:slug>"
    "referrer_user": 42,  // Optional: User ID of the referrer
    "purpose": "Promote summer bootcamp enrollment",  // Optional: Internal description
    "notes": "Used in email campaign sent to previous students"  // Optional: Internal notes
}
```

**Response:** 201 Created with the created short link object

**Auto-Generated Slug:**
- If no slug provided, generates format: `L<base-encoded-id>`
- Example: `L1`, `L2`, `L3`, etc.
- Uses base encoding for compact representation

**Validation:**
- Slug must match pattern: `^[-\w]+$` (letters, numbers, hyphens, underscores only)
- Slug must be unique
- Destination URL must return HTTP status 200-299 (validated via HTTP request)
- Academy must exist

**Error Responses:**
- `invalid-slug-format`: Slug contains invalid characters
- `shortlink-already-exists`: Slug is already taken
- `academy-not-found`: Academy ID is invalid
- 400 with validation errors if destination URL is invalid

### Update Short Link

**PUT** `/v1/marketing/academy/short/<short_slug>`

Update an existing short link.

**Required Capability:** `crud_shortlink`

**Request Body:** Same structure as POST (all fields optional except those being changed)

**Response:** 200 OK with updated short link object

**Important Restrictions:**
- **Can only update links created less than 1 day ago**
- Cannot change `destination` or `slug` if link is older than 1 day
- For older links, create a new link instead

**Error Responses:**
- `short-not-found`: Short link doesn't exist or doesn't belong to your academy
- `update-days-ago`: Link is older than 1 day and cannot be modified
- Same validation errors as POST

### Delete Short Link

**DELETE** `/v1/marketing/academy/short?id=<id>`

Delete one or more short links.

**Required Capability:** `crud_shortlink`

**Query Parameters:**
- `id=<id>`: ID of link to delete (required)
- Multiple IDs can be specified for bulk delete

**Response:** 204 No Content

**Important Restrictions:**
- **Can only delete links created less than 1 day ago**
- For older links, they remain in the system for historical tracking

**Error Responses:**
- `update-days-ago`: One or more links are older than 1 day
- 400 if no `id` parameter provided

## Short Link Redirection

When a user accesses a short link via `/s/<slug>`, the system:

1. Looks up the short link by slug
2. Checks if it's active (returns 404 if inactive)
3. Asynchronously increments the click counter via Celery task
4. Merges UTM parameters from the ShortLink model with any existing parameters in the destination URL
5. Redirects to the final URL with all UTM parameters

**Redirection Behavior:**
- Destination URL's existing query parameters are preserved
- ShortLink UTM parameters are merged in (can override destination params if same key)
- Final redirect includes all merged parameters
- HTTP 302 redirect is used

**Example:**

If you have a ShortLink:
- `destination`: `https://example.com/landing?ref=partner`
- `utm_source`: `facebook`
- `utm_campaign`: `summer-2025`
- `utm_medium`: `social`

Accessing `/s/L1` redirects to:
```
https://example.com/landing?ref=partner&utm_source=facebook&utm_campaign=summer-2025&utm_medium=social
```

## Click Tracking

When a short link is accessed:

1. The `hits` counter is incremented (asynchronously via Celery)
2. `lastclick_at` timestamp is updated
3. Destination URL is validated (HTTP request to check status)
4. `destination_status` is updated:
   - `ACTIVE`: URL returns 200-299 status
   - `ERROR`: URL returns error status code
   - `NOT_FOUND`: URL not accessible

The click tracking happens asynchronously, so the redirect is not delayed by the tracking operation.

## URL Validation

When creating or updating a short link, the destination URL is validated:

- HTTP GET request is made to the destination URL
- Must return status code 200-299 to be valid
- If invalid, creation/update fails with validation error

The validation also runs after each click to monitor link health.

## UTM Parameters

Short links support all standard UTM parameters for campaign tracking:

- `utm_source`: Traffic source (e.g., "facebook", "google", "twitter")
- `utm_medium`: Marketing medium (e.g., "social", "email", "paid", "organic")
- `utm_campaign`: Campaign identifier (e.g., "summer-2025", campaign ID)
- `utm_content`: Ad/content identifier (e.g., ad group ID, ad ID)
- `utm_term`: Keyword (used for CPC campaigns)
- `utm_placement`: Placement identifier (e.g., "feed", "sidebar")
- `utm_plan`: Payment plan type (e.g., "upfront", "isa", "scholarship", "financing")

All UTM parameters are optional. When provided, they are automatically appended to the destination URL during redirection.

## Privacy and Access Control

**Private Links (`private=true`):**
- Only visible to users from the same academy
- Not shown in listings from other academies
- Can only be accessed/edited by academy members

**Public Links (`private=false`):**
- Visible in listings from all academies
- Can be accessed by anyone with the URL
- Still require proper permissions to edit/delete

**Access Control:**
- `read_shortlink`: Required to view short links
- `crud_shortlink`: Required to create, update, or delete short links
- Links are always scoped to an academy
- Users can only manage links from their academy

## Best Practices

1. **Use Descriptive Slugs**: When creating links, use meaningful slugs like `summer-promo-2025` instead of relying on auto-generated slugs
2. **Set UTM Parameters**: Always set UTM parameters for proper campaign tracking in analytics tools
3. **Monitor Destination Status**: Check `destination_status` regularly to ensure links are working
4. **Use Private Links for Internal Campaigns**: Mark links as private if they're academy-specific
5. **Update Restrictions**: Remember that links older than 1 day cannot be updated - create new links instead
6. **Validate Destinations**: Ensure destination URLs are accessible and return valid HTTP status codes

## Error Handling

Common error scenarios:

- **Link Not Found**: 404 when accessing `/s/<slug>` if link doesn't exist or is inactive
- **Duplicate Slug**: Validation error when creating a link with an existing slug
- **Invalid Destination**: Validation error when destination URL returns non-2xx status
- **Update After 1 Day**: Error when trying to update/delete links older than 1 day
- **Permission Denied**: 403 if user lacks required capabilities
- **Academy Mismatch**: Cannot access private links from other academies

## Monitoring

The system includes automated monitoring for short links:

- Destination URLs are checked after each click
- `destination_status` tracks whether URLs are accessible
- Monitoring scripts can alert on links with ERROR or NOT_FOUND status
- Historical click data (`hits`, `lastclick_at`) available for analytics

## Example Workflows

### Creating a Campaign Link

```bash
POST /v1/marketing/academy/short
{
    "slug": "summer-bootcamp-2025",
    "destination": "https://4geeksacademy.com/coding-bootcamps",
    "utm_source": "facebook",
    "utm_medium": "paid",
    "utm_campaign": "summer-2025",
    "utm_content": "ad-set-123",
    "utm_term": "coding-bootcamp",
    "private": false,
    "active": true,
    "course": "<123:full-stack-bootcamp>",
    "plan": "<789:4geeks-plus-subscription>",
    "purpose": "Summer 2025 enrollment campaign",
    "notes": "Facebook ad campaign targeting 25-35 age group"
}
```

### Listing Campaign Links

```bash
GET /v1/marketing/academy/short?sort=-hits&private=false
```

Returns links sorted by most clicks first, showing only public links.

### Tracking Performance

After links are used, check their performance:

```bash
GET /v1/marketing/academy/short
```

Review the `hits` and `lastclick_at` fields to see click statistics, and `destination_status` to ensure links are still working.

