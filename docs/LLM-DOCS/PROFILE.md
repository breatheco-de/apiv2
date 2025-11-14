# Academy Profile Management API Endpoints

This guide covers the REST endpoints you need to read and update academy profile data (name, location, branding assets, and other metadata). The endpoints live under `/v1/admissions` unless otherwise noted and reuse the `Academy` serializers from the admissions app.

## Authentication & Required Headers

- All `/academy/me` endpoints require an authenticated user plus the `Academy` header set to the target academy ID.
- Capabilities enforced by `@capable_of`:
  - `read_my_academy` for `GET /academy/me`
  - `crud_my_academy` for `PUT /academy/me`
- Public endpoints are explicitly marked; everything else expects a JWT in `Authorization: Bearer <token>`.

## Core Retrieval Endpoints

### 1. Get My Academy Profile
**Endpoint:** `GET /v1/admissions/academy/me`  
**Capability:** `read_my_academy`  
**Purpose:** Return a detailed profile for the academy selected via the `Academy` header.  
**Response highlights (from `GetBigAcademySerializer`):**
- Identity: `id`, `slug`, `name`, `owner`
- Location: `country`, `city`, `street_address`, `latitude`, `longitude`, `timezone`
- Branding: `logo_url`, `icon_url`, `white_labeled`, `white_label_url`, `white_label_features`
- Marketing & contact: `marketing_email`, `marketing_phone`, social handles, `website_url`
- Integrations: `active_campaign_slug`, `available_as_saas`

### 2. Get Academy Profile by ID (Public)
**Endpoint:** `GET /v1/admissions/academy/{academy_id}`  
**Auth:** Public (`AllowAny`)  
**Purpose:** Read-only access to the same `GetBigAcademySerializer` payload for public or cross-academy scenarios. Returns `404` with `slug="academy-not-found"` when the academy does not exist.

### 3. List Academies (Public)
**Endpoint:** `GET /v1/admissions/academy`  
**Auth:** Public  
**Query parameters:**
- `status=ACTIVE,INACTIVE,DELETED` – filter by status (case-insensitive list)
- `academy_id=1,2,3` – restrict to specific IDs
**Response:** Array of academies serialized with `AcademySerializer` (compact subset: `id`, `slug`, `name`, `country`, `city`, `logo_url`, `is_hidden_on_prework`).

## Profile Updates

### 4. Update My Academy Profile
**Endpoint:** `PUT /v1/admissions/academy/me`  
**Capability:** `crud_my_academy`  
**Behavior:** Partially update the academy represented by the `Academy` header. The serializer only accepts a curated set of fields; unknown fields are ignored.

#### Editable Fields
- `name`
- `street_address`
- `country` (expects ISO country code present in admissions catalog)
- `city` (numeric city ID)
- `logo_url`
- `icon_url`
- `is_hidden_on_prework`

#### Validation Notes
- `slug` is read-only; passing it in the payload is ignored and will raise a validation error if forced through.
- `logo_url` and `icon_url` are validated with `breathecode.utils.url_validator.test_url`; invalid URLs trigger `ValidationException` with slugs `invalid-logo-url` or `invalid-icon-url`.
- `country` must exist in `admissions.Country`; `city` must exist in `admissions.City`. Both are coerced to integers/strings by the serializer.
- Other profile attributes returned by `GET /academy/me` (marketing emails, social handles, etc.) are currently read-only through this endpoint.

#### Example Request
```json
{
  "name": "4Geeks Academy Madrid",
  "street_address": "Calle de Example 123",
  "country": "ES",
  "city": 57,
  "logo_url": "https://assets.4geeks.com/madrid/logo.png",
  "icon_url": "https://assets.4geeks.com/madrid/icon.png",
  "is_hidden_on_prework": false
}
```

#### Example Response (200)
```json
{
  "id": 12,
  "slug": "madrid",
  "name": "4Geeks Academy Madrid",
  "street_address": "Calle de Example 123",
  "country": {
    "code": "ES",
    "name": "Spain",
    "flag": "🇪🇸"
  },
  "city": {
    "id": 57,
    "name": "Madrid"
  },
  "logo_url": "https://assets.4geeks.com/madrid/logo.png",
  "icon_url": "https://assets.4geeks.com/madrid/icon.png",
  "is_hidden_on_prework": false
}
```

### 5. Create a New Academy
**Endpoint:** `POST /v1/admissions/academy`  
**Permission:** Django permission `manage_organizations` (checked via `@has_permission`).  
**Purpose:** Provision new academies; automatically sets the request user as owner and triggers the `academy_saved` signal that creates the initial `ProfileAcademy` admin record.  
**Required fields:** `slug`, `name`, `logo_url`, `street_address`, `city`, `country`. Additional metadata (contacts, social handles, coordinates, ActiveCampaign slug, etc.) can be provided on creation even though they are read-only on update.

## Supporting Catalog Endpoints

Use the admissions catalogs to drive valid dropdowns when updating profile data:

- `GET /v1/admissions/catalog/countries` – returns `code`, `name`, `flag`.
- `GET /v1/admissions/catalog/cities` – returns `id`, `name`, `country`; filter by `?country=US` (country code) to scope the list.
- `GET /v1/admissions/catalog/timezones` – helpful when displaying time zone options alongside the profile payload (although `timezone` is not currently writable through `PUT /academy/me`).

## Error Handling

- All protected endpoints raise `ValidationException` with translated messages (`slug` provided) for invalid input.
- Missing or non-numeric `Academy` headers trigger `ValidationException` `slug="invalid-academy-id"`.
- Lack of capability results in `403 PermissionDenied` with a message indicating the missing capability.
- Not-found resources return `404` with semantic slugs (e.g., `academy-not-found`).

## Typical Workflow

1. `GET /v1/admissions/academy/me` – load the current profile.  
2. `GET /v1/admissions/catalog/countries` and `GET /v1/admissions/catalog/cities?country={code}` – build valid location options.  
3. `PUT /v1/admissions/academy/me` – submit changes for allowed fields.  
4. `GET /v1/admissions/academy/me` – confirm the persisted profile and review read-only attributes.  
5. (Optional) `GET /v1/admissions/academy/{academy_id}` – verify the public-facing representation for external consumers.

