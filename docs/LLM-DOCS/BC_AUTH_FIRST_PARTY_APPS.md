# BreatheCode Authentication for First-Party 4Geeks Apps

## Overview

This guide explains authentication for applications owned and operated by 4Geeks. First-party apps have direct access to BreatheCode's authentication APIs without complex OAuth app registration.

## Authentication Methods

### 1. Email & Password Login

**Endpoint:**
```
POST /v1/auth/login/
```

**Request:**
```json
{
  "email": "user@example.com",
  "password": "userpassword"
}
```

**Response (200 OK):**
```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "user_id": 123,
  "email": "user@example.com",
  "expires_at": null
}
```

**Error (401 Unauthorized):**
```json
{
  "detail": "Unable to log in with provided credentials.",
  "status_code": 401
}
```

### 2. GitHub Single Sign-On (SSO)

**Endpoint:**
```
GET /v1/auth/github?url=<base64-encoded-callback-url>
```

**Parameters:**
- `url` (required): Base64-encoded URL where user will be redirected after auth
- `scope` (optional): GitHub scopes (default: `user:email`)

**Example:**
```bash
# Your callback URL: https://your-app.com/auth/callback
# Base64 encode it: aHR0cHM6Ly95b3VyLWFwcC5jb20vYXV0aC9jYWxsYmFjaw==

GET /v1/auth/github?url=aHR0cHM6Ly95b3VyLWFwcC5jb20vYXV0aC9jYWxsYmFjaw==
```

**After Authentication:**

User is redirected to your callback URL with the token:
```
https://your-app.com/auth/callback?token=9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

### 3. Google Single Sign-On (SSO)

**Endpoint:**
```
GET /v1/auth/google?url=<base64-encoded-callback-url>
```

**Parameters:**
- `url` (required): Base64-encoded callback URL

**After Authentication:**

User is redirected to your callback with token:
```
https://your-app.com/auth/callback?token=9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

## Making Authenticated API Requests

### Standard Authentication Header

All authenticated API requests use the token in the `Authorization` header:

```bash
curl -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" \
  https://api.breatheco.de/v1/auth/user/me
```

**Header Format:**
```
Authorization: Token <user-token>
```

**Note:** Use `Token` (not `Bearer`)

### Academy Header (Required for Academy Endpoints)

**Endpoints with `/academy/` in the path require an additional Academy header:**

```bash
curl -H "Authorization: Token <token>" \
     -H "Academy: <academy-id-or-slug>" \
     https://api.breatheco.de/v1/auth/academy/settings
```

**Examples of Academy-Scoped Endpoints:**
- `/v1/auth/academy/settings` - Requires `Academy` header
- `/v1/auth/academy/member` - Requires `Academy` header
- `/v1/auth/academy/token/` - Requires `Academy` header
- `/v1/admissions/academy/cohort` - Requires `Academy` header
- `/v1/admissions/academy/student` - Requires `Academy` header

**Academy Header Format:**
```
Academy: 1
```
or
```
Academy: downtown-miami
```

**Complete Request Example:**
```bash
curl -X GET https://api.breatheco.de/v1/auth/academy/member \
  -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" \
  -H "Academy: downtown-miami"
```

**Error Without Academy Header (400 Bad Request):**
```json
{
  "detail": "Missing academy_id parameter expected for the endpoint url or 'Academy' property expected in the request header",
  "status_code": 400
}
```

## Key Endpoints

### Authentication

| Endpoint | Method | Headers Required | Description |
|----------|--------|------------------|-------------|
| `/v1/auth/login/` | POST | None | Email/password login |
| `/v1/auth/github` | GET | None | GitHub SSO redirect |
| `/v1/auth/google` | GET | None | Google SSO redirect |
| `/v1/auth/logout/` | POST | Token | Logout and invalidate token |
| `/v1/auth/token/<token>` | GET | None | Verify token validity |

### User Data

| Endpoint | Method | Headers Required | Description |
|----------|--------|------------------|-------------|
| `/v1/auth/user/me` | GET | Token | Get current user with roles & permissions |
| `/v1/auth/profile/me` | GET | Token | Get user profile |
| `/v1/auth/profile/me` | PUT | Token | Update user profile |

### Academy-Scoped (Require Academy Header)

| Endpoint | Method | Headers Required | Description |
|----------|--------|------------------|-------------|
| `/v1/auth/academy/settings` | GET | Token + Academy | Get academy auth settings |
| `/v1/auth/academy/member` | GET | Token + Academy | List academy members |
| `/v1/auth/academy/member/<id>` | GET | Token + Academy | Get specific member |
| `/v1/admissions/academy/cohort` | GET | Token + Academy | Get academy cohorts |
| `/v1/admissions/academy/student` | GET | Token + Academy | Get academy students |

### Public Endpoints (No Auth)

| Endpoint | Method | Auth Required | Description |
|----------|--------|---------------|-------------|
| `/v1/admissions/catalog/countries` | GET | ❌ | List countries |
| `/v1/admissions/catalog/cities` | GET | ❌ | List cities (filter: `?country=us`) |
| `/v1/admissions/catalog/timezones` | GET | ❌ | List timezones |
| `/v1/admissions/academy` | GET | ❌ | List all academies |

## Response Structures

### User Object (from `/v1/auth/user/me`)

**Request:**
```bash
GET /v1/auth/user/me
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

**Response (200 OK):**
```json
{
  "id": 123,
  "email": "aalejo@gmail.com",
  "username": "aalejo@gmail.com",
  "first_name": "Alejandro",
  "last_name": "Sanchez",
  "date_joined": "2022-10-12T20:42:55.827Z",
  
  "github": {
    "avatar_url": "https://avatars.githubusercontent.com/u/123456",
    "name": "Alejandro Sanchez",
    "username": "aalejosan"
  },
  
  "profile": {
    "avatar_url": "https://avatars.githubusercontent.com/u/123456"
  },
  
  "roles": [
    {
      "id": 1,
      "academy": {
        "id": 1,
        "slug": "downtown-miami",
        "name": "4Geeks Academy Miami"
      },
      "cohort": {
        "id": 5,
        "slug": "web-dev-2024",
        "name": "Web Development 2024"
      },
      "role": {
        "slug": "student",
        "name": "Student"
      },
      "created_at": "2022-10-12T21:59:33.999Z"
    }
  ],
  
  "permissions": [
    {
      "codename": "get_my_profile",
      "name": "Get my profile"
    },
    {
      "codename": "get_my_certificate",
      "name": "Get my certificate"
    }
  ],
  
  "settings": {
    "lang": "en",
    "main_currency": "usd"
  }
}
```

**Field Notes:**
- `github`: GitHub account info (null if not connected)
- `profile`: User profile (null if not created)
- `roles`: ProfileAcademy relationships (academies user belongs to)
- `permissions`: Permissions from Django groups
- `settings`: User preferences

### Profile Object (from `/v1/auth/profile/me`)

**Request:**
```bash
GET /v1/auth/profile/me
Authorization: Token <token>
```

**Response (200 OK):**
```json
{
  "user": {
    "id": 123,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  },
  "avatar_url": "https://avatars.githubusercontent.com/u/123456",
  "bio": "Full-stack developer passionate about education",
  "phone": "+1234567890",
  "show_tutorial": false,
  "twitter_username": "johndoe",
  "github_username": "johndoe",
  "portfolio_url": "https://johndoe.dev",
  "linkedin_url": "https://linkedin.com/in/johndoe",
  "blog": "https://blog.johndoe.com"
}
```

### Token Verification (from `/v1/auth/token/<token>`)

**Request:**
```bash
GET /v1/auth/token/9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

**Response (200 OK):**
```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "token_type": "login",
  "expires_at": null,
  "user": {
    "id": 123,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

## Request Examples

### Basic Authentication Request

```bash
curl -X GET https://api.breatheco.de/v1/auth/user/me \
  -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
```

### Academy-Scoped Request

```bash
curl -X GET https://api.breatheco.de/v1/auth/academy/member \
  -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" \
  -H "Academy: downtown-miami"
```

### Creating a Resource

```bash
curl -X POST https://api.breatheco.de/v1/admissions/academy/cohort \
  -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" \
  -H "Academy: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Cohort",
    "slug": "new-cohort-2024",
    "kickoff_date": "2024-01-15T09:00:00Z"
  }'
```

### Public Request (No Auth)

```bash
curl -X GET https://api.breatheco.de/v1/admissions/catalog/countries
```

## Token Types

| Type | Lifetime | Use Case |
|------|----------|----------|
| `login` | Permanent | Standard user login |
| `temporal` | 1 hour | Password reset, temporary access |
| `one_time` | Single use | Email verification, one-time operations |
| `permanent` | Never expires | Service accounts, integrations |

## Error Handling

### Common HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | OK | Request successful |
| 201 | Created | Resource created |
| 400 | Bad Request | Check request data or missing Academy header |
| 401 | Unauthorized | Token missing or invalid - user needs to login |
| 403 | Forbidden | User lacks permission for this operation |
| 404 | Not Found | Resource doesn't exist |
| 500 | Server Error | Try again later or contact support |

### Error Response Formats

**Simple Error:**
```json
{
  "detail": "Error message",
  "status_code": 401
}
```

**Validation Error:**
```json
{
  "detail": "Cannot remove user because they are whitelisted",
  "status_code": 400,
  "slug": "user-whitelisted"
}
```

**With Translation Support:**
```json
{
  "detail": "Missing academy_id parameter expected for the endpoint url or 'Academy' property expected in the request header",
  "status_code": 400,
  "slug": "missing-academy-header"
}
```

## Security Best Practices

### 1. Always Use HTTPS

```bash
# ✅ Correct
https://api.breatheco.de

# ❌ Never in production
http://api.breatheco.de
```

### 2. Secure Token Storage

- Use HttpOnly cookies for web apps (prevents XSS)
- Encrypt tokens in mobile app storage
- Never log tokens in console/files
- Never commit tokens to version control

### 3. Token Transmission

```bash
# ✅ Correct - In header
Authorization: Token abc123...

# ❌ Never in URL
https://api.breatheco.de/endpoint?token=abc123
```

### 4. Handle Expiration

When you receive a 401 response:
1. Clear stored token
2. Redirect user to login
3. Don't retry with same token

### 5. Validate on Every Request

Don't assume a token is valid - handle 401 responses gracefully.

## Complete Authentication Flow

### Step 1: User Initiates Login

Redirect to authentication endpoint:
- GitHub: `/v1/auth/github?url=<callback>`
- Google: `/v1/auth/google?url=<callback>`
- Email/Password: `POST /v1/auth/login/`

### Step 2: Receive Token

- **OAuth (GitHub/Google)**: Extract from callback URL query parameter
- **Email/Password**: Extract from response JSON

### Step 3: Store Token Securely

Store in your application's secure storage.

### Step 4: Make API Requests

Include token in Authorization header:
```
Authorization: Token <token>
```

For academy-scoped endpoints, also include:
```
Academy: <academy-id-or-slug>
```

### Step 5: Fetch User Data

```bash
GET /v1/auth/user/me
Authorization: Token <token>
```

Use the response to:
- Display user information
- Check user roles and permissions
- Determine which academies they belong to

### Step 6: Handle Logout

```bash
POST /v1/auth/logout/
Authorization: Token <token>
```

Clear stored token from your application.

## Common Integration Patterns

### Pattern 1: Check User Permissions

```bash
# Get user with permissions
GET /v1/auth/user/me
Authorization: Token <token>

# Check if user has specific permission
# In response, look for permission in permissions array:
{
  "permissions": [
    {"codename": "crud_cohort", "name": "Create, update or delete cohort info"}
  ]
}
```

### Pattern 2: Find User's Academies

```bash
# Get user data
GET /v1/auth/user/me
Authorization: Token <token>

# User's academies are in the roles array:
{
  "roles": [
    {
      "academy": {
        "id": 1,
        "slug": "downtown-miami",
        "name": "4Geeks Academy Miami"
      },
      "role": {"slug": "admin"}
    }
  ]
}
```

### Pattern 3: Academy-Scoped Operations

```bash
# Step 1: Get user's academies from /v1/auth/user/me
# Step 2: Choose an academy
# Step 3: Make academy-scoped request

GET /v1/admissions/academy/cohort
Authorization: Token <token>
Academy: downtown-miami
```

## Token Types Explained

### `login` Token (Default)
- Created during email/password or OAuth login
- Permanent (doesn't expire)
- Used for normal user sessions
- Can be invalidated via logout

### `temporal` Token
- Short-lived (1 hour)
- Used for password reset links
- Automatically expires
- Can't be used for general API access

### `one_time` Token
- Single use only
- Deleted after first use
- Used for email verification, secure operations
- Can't be reused

### `permanent` Token
- Never expires
- Used for service accounts, academy tokens
- Requires special permission to create
- Should be carefully managed

## Troubleshooting

### Issue: 401 Unauthorized

**Possible Causes:**
- Token not provided in header
- Token expired or invalid
- Token format incorrect (should be `Token abc...` not `Bearer abc...`)

**Solution:**
```bash
# Check token format
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b

# Verify token is valid
GET /v1/auth/token/<your-token>
```

### Issue: 400 Bad Request on Academy Endpoints

**Cause:**
Missing Academy header on endpoint that requires it.

**Solution:**
```bash
# Add Academy header
-H "Academy: <academy-id-or-slug>"
```

**How to know if endpoint needs Academy header:**
- URL contains `/academy/` → Requires Academy header
- Error message mentions "Missing academy_id" → Requires Academy header

### Issue: 403 Forbidden

**Cause:**
User lacks the required permission for this operation.

**Solution:**
1. Check user's permissions: `GET /v1/auth/user/me`
2. Verify user has correct role in the academy
3. Contact academy admin to grant permission

### Issue: CORS Errors

**Cause:**
Your domain not whitelisted in BreatheCode CORS settings.

**Solution:**
Contact platform team to add your domain to CORS whitelist.

## Testing

### Manual API Testing

```bash
# 1. Login
curl -X POST https://api.breatheco.de/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Response: {"token":"abc123...","user_id":1,"email":"test@example.com"}

# 2. Get user info
curl https://api.breatheco.de/v1/auth/user/me \
  -H "Authorization: Token abc123..."

# 3. Academy-scoped request
curl https://api.breatheco.de/v1/auth/academy/member \
  -H "Authorization: Token abc123..." \
  -H "Academy: 1"

# 4. Logout
curl -X POST https://api.breatheco.de/v1/auth/logout/ \
  -H "Authorization: Token abc123..."
```

### Verify Token is Working

```bash
# Method 1: Get user info
curl https://api.breatheco.de/v1/auth/user/me \
  -H "Authorization: Token <your-token>"
# Should return user object

# Method 2: Verify token directly
curl https://api.breatheco.de/v1/auth/token/<your-token>
# Should return token info
```

## Quick Start Checklist

For a new first-party 4Geeks app:

- [ ] Choose authentication method (GitHub/Google SSO recommended)
- [ ] Implement login redirect with base64-encoded callback
- [ ] Handle OAuth callback to extract token
- [ ] Store token securely
- [ ] Add `Authorization: Token <token>` header to all API requests
- [ ] Add `Academy: <id-or-slug>` header for academy-scoped endpoints
- [ ] Fetch user data from `/v1/auth/user/me`
- [ ] Handle 401 errors (redirect to login)
- [ ] Handle 400 errors on academy endpoints (add Academy header)
- [ ] Implement logout
- [ ] Test with real user accounts

## Environment Configuration

```bash
# Production
BREATHECODE_API_URL=https://api.breatheco.de

# Staging
BREATHECODE_API_URL=https://api-staging.breatheco.de

# Local Development
BREATHECODE_API_URL=http://localhost:8000
```

## Additional Resources

- **API Documentation**: https://api.breatheco.de/swagger/
- **GraphQL Playground**: https://api.breatheco.de/graphql
- **OpenAPI Spec**: https://api.breatheco.de/openapi.json
- **Linked Services** (for third-party apps): https://breatheco-de.github.io/linked-services-django-plugin/

---

**Summary:** First-party 4Geeks apps use simple token-based authentication. Get a token via email/password or OAuth (GitHub/Google), include it in the `Authorization` header, and add the `Academy` header for academy-scoped endpoints. No app registration needed!
