# Authentication API - Complete Guide

This document provides a comprehensive guide for frontend applications to implement authentication flows with the BreatheCode API.

## Table of Contents

1. [Overview](#overview)
2. [Authentication Methods](#authentication-methods)
3. [Token Management](#token-management)
4. [Authentication Flows](#authentication-flows)
5. [OAuth Integration](#oauth-integration)
6. [Security Best Practices](#security-best-practices)
7. [Error Handling](#error-handling)

---

## Overview

BreatheCode API supports multiple authentication methods:

- **Email/Password Login** - Traditional username/password authentication
- **OAuth2.0** - GitHub, Google, Facebook, Slack integration
- **Token-based Authentication** - Using JWT-like tokens with expiration
- **Invite-based Signup** - User invitation and registration flow
- **Password Reset** - Secure password recovery

All authenticated requests require a token in the `Authorization` header:

```http
Authorization: Token {your-token-here}
```

### Base URL

```
Production: https://breathecode.herokuapp.com
Development: http://localhost:8000
```

---

## Authentication Methods

### 1. Token Types

BreatheCode uses different token types for different purposes:

| Token Type | Purpose | Lifetime | Use Case |
|------------|---------|----------|----------|
| `login` | Standard authentication | Configurable (default: 30 days) | Regular user sessions |
| `temporal` | Temporary access | Short-lived (hours) | One-time operations |
| `permanent` | Long-term access | No expiration | Service accounts, integrations |

---

## Token Management

### Get Token Information

**Endpoint:** `GET /v1/auth/token/{token}`

**Purpose:** Validate and get information about a token.

**Parameters:**
- `token` - The token string to validate

**Response:**
```json
{
  "key": "abc123...",
  "token_type": "login",
  "expires_at": "2024-12-31T23:59:59Z",
  "user": {
    "id": 123,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

---

### Create Temporal Token

**Endpoint:** `POST /v1/auth/token/me`

**Purpose:** Generate a temporary token from an existing valid token.

**Headers:**
```http
Authorization: Token {your-login-token}
```

**Request Body:**
```json
{
  "token_type": "temporal"
}
```

**Response:**
```json
{
  "token": "temp_abc123...",
  "expires_at": "2024-02-20T18:00:00Z"
}
```

**Use Cases:**
- One-time password reset links
- Temporary access for external services
- Time-limited operations

---

## Authentication Flows

### Flow 1: Email/Password Login

#### Step 1: Login

**Endpoint:** `POST /v1/auth/login/`

**Purpose:** Authenticate user with email and password.

**Headers:**
```http
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Success Response (200 OK):**
```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "user_id": 123,
  "email": "user@example.com",
  "expires_at": "2024-03-20T10:30:00Z"
}
```

**Error Responses:**

**403 Forbidden - Invalid Credentials:**
```json
{
  "detail": "Unable to log in with provided credentials.",
  "status_code": 403
}
```

**403 Forbidden - Email Not Validated:**
```json
{
  "detail": "You need to validate your email first",
  "slug": "email-not-validated",
  "status_code": 403,
  "data": [
    {
      "id": 456,
      "email": "user@example.com",
      "status": "ACCEPTED",
      "is_email_validated": false,
      "token": "invite_token_abc123"
    }
  ]
}
```

#### Step 2: Store Token

Store the token securely in your frontend:

```javascript
// React example
localStorage.setItem('authToken', response.token);
localStorage.setItem('userId', response.user_id);
localStorage.setItem('tokenExpiry', response.expires_at);

// Or use secure cookie
document.cookie = `authToken=${response.token}; secure; httpOnly; sameSite=strict`;
```

#### Step 3: Use Token in Requests

Include token in all authenticated requests:

```javascript
// JavaScript/Fetch example
fetch('https://breathecode.herokuapp.com/v1/auth/user/me', {
  headers: {
    'Authorization': `Token ${authToken}`,
    'Content-Type': 'application/json'
  }
})
.then(response => response.json())
.then(data => console.log(data));
```

```python
# Python example
import requests

headers = {
    'Authorization': f'Token {auth_token}',
    'Content-Type': 'application/json'
}

response = requests.get(
    'https://breathecode.herokuapp.com/v1/auth/user/me',
    headers=headers
)
```

#### Step 4: Get User Information

**Endpoint:** `GET /v1/auth/user/me`

**Headers:**
```http
Authorization: Token {your-token}
```

**Response:**
```json
{
  "id": 123,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "github": {
    "username": "johndoe",
    "avatar_url": "https://avatars.githubusercontent.com/u/123?v=4"
  },
  "profile": {
    "avatar_url": "https://example.com/avatar.jpg",
    "bio": "Full-stack developer",
    "phone": "+1234567890"
  }
}
```

---

### Flow 2: User Signup via Invite

The invite flow is the primary way users join BreatheCode. Users receive an invitation email and complete their registration.

#### Step 1: User Receives Invite

Invitation is sent by academy staff with a unique token. The email contains a link like:

```
https://your-app.com/register?token=invite_abc123xyz
```

#### Step 2: Validate Invite Token

**Endpoint:** `GET /v1/auth/token/{invite_token}`

**Purpose:** Verify the invite token is valid.

**Response:**
```json
{
  "key": "invite_abc123xyz",
  "token_type": "temporal",
  "expires_at": "2024-12-31T23:59:59Z",
  "user": {
    "id": 456,
    "email": "newuser@example.com",
    "first_name": "Jane",
    "last_name": "Smith"
  }
}
```

#### Step 3: Accept Invite & Set Password

**Endpoint:** `PUT /v1/auth/user/me/invite/{new_status}`

**Purpose:** Accept invite and set password.

**Parameters:**
- `new_status` - Should be `accepted`

**Query Parameters:**
- `token={invite_token}` - The invitation token

**Request Body:**
```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "password": "securePassword123",
  "repeat_password": "securePassword123"
}
```

**Success Response (200 OK):**
```json
{
  "id": 456,
  "email": "newuser@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

#### Step 4: Login Automatically

After accepting invite, the response includes a login token. Store it and redirect to dashboard:

```javascript
// React example
const handleAcceptInvite = async (inviteToken, formData) => {
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/auth/user/me/invite/accepted?token=${inviteToken}`,
    {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        first_name: formData.firstName,
        last_name: formData.lastName,
        password: formData.password,
        repeat_password: formData.confirmPassword
      })
    }
  );

  if (response.ok) {
    const data = await response.json();
    // Store token
    localStorage.setItem('authToken', data.token);
    localStorage.setItem('userId', data.id);
    // Redirect to dashboard
    window.location.href = '/dashboard';
  }
};
```

---

### Flow 3: Password Reset

#### Step 1: Request Password Reset

**Endpoint:** `POST /v1/auth/password/reset`

**Purpose:** Request a password reset link.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Success Response (200 OK):**
```json
{
  "details": "If that email exists, you will receive a password reset link"
}
```

> **Note:** Always returns success even if email doesn't exist (security measure to prevent email enumeration).

#### Step 2: User Receives Email

User receives an email with a password reset link:

```
https://your-app.com/password/reset?token=reset_abc123xyz
```

#### Step 3: Validate Reset Token

**Endpoint:** `GET /v1/auth/token/{reset_token}`

**Purpose:** Verify reset token is valid.

```javascript
const validateResetToken = async (token) => {
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/auth/token/${token}`
  );
  
  if (response.ok) {
    const data = await response.json();
    return data; // Token is valid
  } else {
    throw new Error('Invalid or expired token');
  }
};
```

#### Step 4: Set New Password

**Endpoint:** `POST /v1/auth/password/{token}`

**Purpose:** Set new password using reset token.

**Request Body:**
```json
{
  "password": "newSecurePassword123",
  "repeat_password": "newSecurePassword123"
}
```

**Success Response (200 OK):**
```json
{
  "details": "Password updated successfully"
}
```

#### Step 5: Redirect to Login

After successful password reset, redirect user to login page:

```javascript
const handlePasswordReset = async (token, formData) => {
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/auth/password/${token}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        password: formData.password,
        repeat_password: formData.confirmPassword
      })
    }
  );

  if (response.ok) {
    // Redirect to login
    window.location.href = '/login?reset=success';
  }
};
```

---

### Flow 4: Logout

**Endpoint:** `POST /v1/auth/logout/`

**Purpose:** Invalidate current token.

**Headers:**
```http
Authorization: Token {your-token}
```

**Success Response (200 OK):**
```json
{
  "details": "Successfully logged out"
}
```

**Frontend Implementation:**
```javascript
const handleLogout = async () => {
  const token = localStorage.getItem('authToken');
  
  await fetch('https://breathecode.herokuapp.com/v1/auth/logout/', {
    method: 'POST',
    headers: {
      'Authorization': `Token ${token}`
    }
  });
  
  // Clear local storage
  localStorage.removeItem('authToken');
  localStorage.removeItem('userId');
  localStorage.removeItem('tokenExpiry');
  
  // Redirect to login
  window.location.href = '/login';
};
```

---

## OAuth Integration

### Flow 5: GitHub OAuth

BreatheCode supports GitHub OAuth for seamless authentication.

#### Step 1: Initiate GitHub OAuth

**Endpoint:** `GET /v1/auth/github/`

**Purpose:** Redirect user to GitHub authorization page.

**Query Parameters:**
- `url` - Base64 encoded callback URL (where to redirect after auth)
- `scope` - Optional, default: `user:email`

**Example:**
```javascript
const initiateGitHubLogin = () => {
  const callbackUrl = 'https://your-app.com/auth/callback';
  const encodedUrl = btoa(callbackUrl);
  
  window.location.href = `https://breathecode.herokuapp.com/v1/auth/github/?url=${encodedUrl}`;
};
```

#### Step 2: GitHub Callback

After user authorizes on GitHub, they're redirected to:

```
GET /v1/auth/github/callback?code={github_code}&url={your_callback_url}
```

BreatheCode processes the GitHub code and redirects to your app with token:

```
https://your-app.com/auth/callback?token={breathecode_token}
```

#### Step 3: Extract Token

```javascript
// React example
useEffect(() => {
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get('token');
  
  if (token) {
    // Validate and store token
    validateToken(token).then(data => {
      localStorage.setItem('authToken', token);
      localStorage.setItem('userId', data.user.id);
      window.location.href = '/dashboard';
    });
  }
}, []);
```

#### Complete GitHub Flow Example

```javascript
// GitHub OAuth Flow
class GitHubAuth {
  static async login() {
    const callbackUrl = window.location.origin + '/auth/callback';
    const encodedUrl = btoa(callbackUrl);
    window.location.href = `https://breathecode.herokuapp.com/v1/auth/github/?url=${encodedUrl}`;
  }

  static async handleCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    const error = urlParams.get('error');

    if (error) {
      console.error('GitHub auth error:', error);
      return { success: false, error };
    }

    if (token) {
      // Validate token
      const response = await fetch(
        `https://breathecode.herokuapp.com/v1/auth/token/${token}`
      );
      
      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('authToken', token);
        localStorage.setItem('userId', data.user.id);
        return { success: true, user: data.user };
      }
    }

    return { success: false, error: 'No token received' };
  }
}
```

---

### Flow 6: Google OAuth

Similar to GitHub, but uses Google OAuth 2.0.

#### Step 1: Initiate Google OAuth

**Endpoint:** `GET /v1/auth/google`

**Query Parameters:**
- `url` - Base64 encoded callback URL

**Example:**
```javascript
const initiateGoogleLogin = () => {
  const callbackUrl = 'https://your-app.com/auth/google/callback';
  const encodedUrl = btoa(callbackUrl);
  
  window.location.href = `https://breathecode.herokuapp.com/v1/auth/google?url=${encodedUrl}`;
};
```

#### Step 2: Google Callback

**Endpoint:** `GET /v1/auth/google/callback`

Works the same as GitHub callback - redirects to your URL with token parameter.

---

### Flow 7: Slack OAuth

#### Initiate Slack OAuth

**Endpoint:** `GET /v1/auth/slack/`

**Query Parameters:**
- `url` - Callback URL
- `user` - Optional, user token for linking accounts

**Callback:** `GET /v1/auth/slack/callback`

---

### Flow 8: Facebook OAuth

#### Initiate Facebook OAuth

**Endpoint:** `GET /v1/auth/facebook/`

**Query Parameters:**
- `url` - Callback URL

**Callback:** `GET /v1/auth/facebook/callback`

---

## Security Best Practices

### 1. Token Storage

**Best Practices:**

```javascript
// ✅ Good: Store in httpOnly cookie (most secure)
// Set on server-side
response.cookie('authToken', token, {
  httpOnly: true,
  secure: true,
  sameSite: 'strict',
  maxAge: 30 * 24 * 60 * 60 * 1000 // 30 days
});

// ⚠️ Acceptable: Store in localStorage (convenient but less secure)
localStorage.setItem('authToken', token);

// ❌ Bad: Store in regular cookie (vulnerable to XSS)
document.cookie = `authToken=${token}`;
```

### 2. Token Validation

Always validate token before using:

```javascript
const isTokenValid = async (token) => {
  try {
    const response = await fetch(
      `https://breathecode.herokuapp.com/v1/auth/token/${token}`
    );
    
    if (response.ok) {
      const data = await response.json();
      // Check expiration
      const expiresAt = new Date(data.expires_at);
      return expiresAt > new Date();
    }
    return false;
  } catch (error) {
    return false;
  }
};
```

### 3. Token Expiration Handling

Implement automatic token refresh or re-login:

```javascript
const makeAuthenticatedRequest = async (url, options = {}) => {
  const token = localStorage.getItem('authToken');
  const expiry = localStorage.getItem('tokenExpiry');
  
  // Check if token is expired
  if (new Date(expiry) <= new Date()) {
    // Token expired, redirect to login
    window.location.href = '/login?expired=true';
    return;
  }
  
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Token ${token}`
    }
  });
  
  if (response.status === 401) {
    // Token invalid, redirect to login
    localStorage.removeItem('authToken');
    window.location.href = '/login';
    return;
  }
  
  return response;
};
```

### 4. Secure Password Requirements

Enforce strong passwords on frontend:

```javascript
const validatePassword = (password) => {
  const requirements = {
    minLength: password.length >= 8,
    hasUpperCase: /[A-Z]/.test(password),
    hasLowerCase: /[a-z]/.test(password),
    hasNumber: /\d/.test(password),
    hasSpecialChar: /[!@#$%^&*(),.?":{}|<>]/.test(password)
  };
  
  return {
    isValid: Object.values(requirements).every(req => req),
    requirements
  };
};
```

### 5. HTTPS Only

**Always use HTTPS in production:**

```javascript
// Enforce HTTPS
if (location.protocol !== 'https:' && process.env.NODE_ENV === 'production') {
  location.replace(`https:${location.href.substring(location.protocol.length)}`);
}
```

### 6. CSRF Protection

For academy-scoped endpoints, include academy header:

```javascript
const makeAcademyRequest = async (url, academyId, options = {}) => {
  const token = localStorage.getItem('authToken');
  
  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Token ${token}`,
      'Academy': academyId
    }
  });
};
```

---

## Error Handling

### Common Error Codes

| Status Code | Error | Description | Action |
|-------------|-------|-------------|--------|
| 400 | Bad Request | Invalid request format | Check request payload |
| 401 | Unauthorized | Missing or invalid token | Redirect to login |
| 403 | Forbidden | Valid token but no permission | Show access denied message |
| 404 | Not Found | Resource doesn't exist | Check URL/endpoint |
| 429 | Too Many Requests | Rate limit exceeded | Implement backoff retry |
| 500 | Server Error | Internal server error | Show error message, retry |

### Error Response Format

```json
{
  "detail": "Error message",
  "slug": "error-identifier",
  "status_code": 403,
  "data": {} // Optional additional data
}
```

### Comprehensive Error Handler

```javascript
class AuthError extends Error {
  constructor(message, code, slug, data) {
    super(message);
    this.code = code;
    this.slug = slug;
    this.data = data;
  }
}

const handleAuthError = async (response) => {
  const data = await response.json().catch(() => ({}));
  
  switch (response.status) {
    case 400:
      throw new AuthError(
        data.detail || 'Invalid request',
        400,
        data.slug
      );
    
    case 401:
      // Unauthorized - token invalid or expired
      localStorage.removeItem('authToken');
      window.location.href = '/login?expired=true';
      throw new AuthError('Session expired', 401, 'token-expired');
    
    case 403:
      if (data.slug === 'email-not-validated') {
        // Special case: email not validated
        return {
          needsEmailValidation: true,
          invites: data.data
        };
      }
      throw new AuthError(
        data.detail || 'Access forbidden',
        403,
        data.slug
      );
    
    case 429:
      throw new AuthError(
        'Too many requests. Please try again later.',
        429,
        'rate-limit'
      );
    
    case 500:
      throw new AuthError(
        'Server error. Please try again.',
        500,
        'server-error'
      );
    
    default:
      throw new AuthError(
        data.detail || 'Unknown error',
        response.status,
        data.slug
      );
  }
};

// Usage
try {
  const response = await fetch('/v1/auth/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  
  if (!response.ok) {
    await handleAuthError(response);
  }
  
  const data = await response.json();
  // Success handling
} catch (error) {
  if (error instanceof AuthError) {
    // Handle specific auth errors
    console.error(`Auth error [${error.slug}]:`, error.message);
  }
}
```

---

## Complete Frontend Implementation Examples

### React Authentication Context

```javascript
import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('authToken'));

  useEffect(() => {
    if (token) {
      validateAndLoadUser(token);
    } else {
      setLoading(false);
    }
  }, [token]);

  const validateAndLoadUser = async (authToken) => {
    try {
      const response = await fetch(
        'https://breathecode.herokuapp.com/v1/auth/user/me',
        {
          headers: {
            'Authorization': `Token ${authToken}`
          }
        }
      );

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        // Invalid token
        localStorage.removeItem('authToken');
        setToken(null);
      }
    } catch (error) {
      console.error('Error validating token:', error);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    const response = await fetch(
      'https://breathecode.herokuapp.com/v1/auth/login/',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }

    const data = await response.json();
    localStorage.setItem('authToken', data.token);
    localStorage.setItem('tokenExpiry', data.expires_at);
    setToken(data.token);
    
    return data;
  };

  const logout = async () => {
    if (token) {
      await fetch('https://breathecode.herokuapp.com/v1/auth/logout/', {
        method: 'POST',
        headers: {
          'Authorization': `Token ${token}`
        }
      });
    }

    localStorage.removeItem('authToken');
    localStorage.removeItem('tokenExpiry');
    setToken(null);
    setUser(null);
  };

  const acceptInvite = async (inviteToken, formData) => {
    const response = await fetch(
      `https://breathecode.herokuapp.com/v1/auth/user/me/invite/accepted?token=${inviteToken}`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Invite acceptance failed');
    }

    const data = await response.json();
    localStorage.setItem('authToken', data.token);
    setToken(data.token);
    
    return data;
  };

  const requestPasswordReset = async (email) => {
    const response = await fetch(
      'https://breathecode.herokuapp.com/v1/auth/password/reset',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email })
      }
    );

    return response.ok;
  };

  const resetPassword = async (token, password, repeatPassword) => {
    const response = await fetch(
      `https://breathecode.herokuapp.com/v1/auth/password/${token}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          password,
          repeat_password: repeatPassword
        })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Password reset failed');
    }

    return true;
  };

  const value = {
    user,
    token,
    loading,
    login,
    logout,
    acceptInvite,
    requestPasswordReset,
    resetPassword
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
```

### Protected Route Component

```javascript
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';

export const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!user) {
    // Redirect to login, but save the location they were trying to access
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
};
```

---

## API Reference Summary

### Authentication Endpoints

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/v1/auth/login/` | POST | Login with email/password | No |
| `/v1/auth/logout/` | POST | Logout and invalidate token | Yes |
| `/v1/auth/user/me` | GET | Get current user info | Yes |
| `/v1/auth/user/me` | PUT | Update user info | Yes |
| `/v1/auth/token/{token}` | GET | Get token information | No |
| `/v1/auth/token/me` | POST | Create temporal token | Yes |
| `/v1/auth/password/reset` | POST | Request password reset | No |
| `/v1/auth/password/{token}` | POST | Set new password | No |
| `/v1/auth/user/me/invite/accepted` | PUT | Accept invite & register | No |
| `/v1/auth/github/` | GET | Initiate GitHub OAuth | No |
| `/v1/auth/github/callback` | GET | GitHub OAuth callback | No |
| `/v1/auth/google` | GET | Initiate Google OAuth | No |
| `/v1/auth/google/callback` | GET | Google OAuth callback | No |
| `/v1/auth/slack/` | GET | Initiate Slack OAuth | No |
| `/v1/auth/slack/callback` | GET | Slack OAuth callback | No |
| `/v1/auth/facebook/` | GET | Initiate Facebook OAuth | No |
| `/v1/auth/facebook/callback` | GET | Facebook OAuth callback | No |

---

## Testing Authentication Flows

### Manual Testing Checklist

- [ ] Login with valid credentials
- [ ] Login with invalid credentials
- [ ] Login with unvalidated email
- [ ] Logout
- [ ] Access protected endpoint with valid token
- [ ] Access protected endpoint with expired token
- [ ] Access protected endpoint with invalid token
- [ ] Request password reset
- [ ] Complete password reset flow
- [ ] Accept invite with valid token
- [ ] Accept invite with expired token
- [ ] GitHub OAuth flow
- [ ] Google OAuth flow
- [ ] Token expiration handling
- [ ] Multiple concurrent sessions

---

## Related Documentation

- [BC_AUTH_FIRST_PARTY_APPS.md](./BC_AUTH_FIRST_PARTY_APPS.md) - First-party app authentication
- [BC_STAFF_INVITES.md](./BC_STAFF_INVITES.md) - Staff invitation system
- [STUDENT_REPORT.md](./STUDENT_REPORT.md) - Student data and permissions

---

## Support

For questions or issues with authentication:
- Check token expiration and format
- Verify HTTPS is used in production
- Review error messages and status codes
- Contact development team for API issues

**Last Updated:** October 2024

