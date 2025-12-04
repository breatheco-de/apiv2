# Notification Registry System

## Overview

The Notification Registry is a centralized system for managing notification templates in BreatheCode. It provides a JSON-based configuration system that documents notification templates across multiple channels (email, Slack, SMS) and makes them discoverable through API endpoints.

### Purpose

- **Centralized Documentation**: All notification templates are documented in one place with their variables, channels, and usage
- **Template Discovery**: Frontend can query available notification templates and their requirements
- **Template Preview**: Staff can preview notification templates with variables before sending
- **Validation**: Ensures notification templates are properly configured before use
- **Multi-Channel Support**: Single registry entry can define templates for email, Slack, and SMS

## How It Works

### Registry Structure

The notification registry consists of JSON files stored in `breathecode/notify/registry/`. Each file represents one notification template and must follow a specific schema.

**Key Principles:**
1. **One file per template**: Each notification gets its own JSON file
2. **Filename matches slug**: File `message.json` must have `"slug": "message"`
3. **Auto-discovery**: Files are automatically loaded at startup
4. **Multi-channel**: One template can support multiple delivery channels

### Loading Process

When the application starts:

1. `EmailManager` scans `breathecode/notify/registry/` directory
2. Loads all `.json` files
3. Validates slug matches filename
4. Caches templates in memory for fast access
5. Logs any parsing errors or validation issues

### Template Categories

Templates are organized by category for easier discovery:

- `authentication` - User verification and password reset
- `academy` - Academy invitations and management
- `general` - Generic messages and notifications
- `feedback` - Surveys and NPS requests
- `monitoring` - System diagnostics and alerts

## Registry JSON Schema

Each notification template must follow this JSON structure:

```json
{
  "slug": "template_slug",
  "name": "Human Readable Name",
  "description": "Detailed description of when and why this notification is sent",
  "category": "authentication|academy|general|feedback|monitoring",
  "channels": {
    "email": {
      "template_path": "template_file_name",
      "default_subject": "Default email subject"
    },
    "slack": {
      "template_path": "template_file_name",
      "default_subject": null
    },
    "sms": {
      "template_path": "template_file_name"
    }
  },
  "variables": [
    {
      "name": "VARIABLE_NAME",
      "description": "What this variable represents",
      "source": "How/where this variable is generated",
      "example": "Example value",
      "required": true
    }
  ]
}
```

### Field Descriptions

#### Root Level

- **slug** (string, required): Unique identifier for the template. Must match filename without `.json`
- **name** (string, required): Human-readable name displayed in UI
- **description** (string, required): Explains when and why this notification is sent
- **category** (string, required): Organizational category for filtering

#### Channels Object

Each channel entry defines how the notification is delivered through that medium.

**Email Channel:**
```json
"email": {
  "template_path": "message",
  "default_subject": "Message from {academy_name}"
}
```
- `template_path`: Name of template files (looks for `message.html` and `message.txt`)
- `default_subject`: Default subject line, supports variable interpolation

**Slack Channel:**
```json
"slack": {
  "template_path": "nps_survey",
  "default_subject": null
}
```
- `template_path`: Name of template file (looks for `nps_survey.slack`)
- `default_subject`: Usually null for Slack

**SMS Channel:**
```json
"sms": {
  "template_path": "verification_code"
}
```
- `template_path`: Name of template file (looks for `verification_code.sms`)

#### Variables Array

Documents all variables that can/must be passed to the template:

```json
{
  "name": "SUBJECT",
  "description": "Message subject/title",
  "source": "Passed in data dict",
  "example": "Important Update",
  "required": true
}
```

- **name** (string): Variable name as used in template (usually UPPERCASE)
- **description** (string): What this variable represents
- **source** (string): How/where this variable is generated in code
- **example** (string): Example value for testing/documentation
- **required** (boolean): Whether this variable must be provided

### Built-in Variables

All templates automatically have access to these default variables:

- `API_URL` - Base API URL from environment
- `COMPANY_NAME` - Company name from environment
- `COMPANY_CONTACT_URL` - Contact URL from environment
- `COMPANY_LEGAL_NAME` - Legal company name from environment
- `COMPANY_ADDRESS` - Company address from environment
- `style__success` - Success color `#99ccff`
- `style__danger` - Danger color `#ffcccc`
- `style__secondary` - Secondary color `#ededed`

When an academy is provided, these are also available:

- `COMPANY_INFO_EMAIL` - Academy feedback email
- `COMPANY_LEGAL_NAME` - Academy legal name or name
- `COMPANY_LOGO` - Academy logo URL
- `COMPANY_NAME` - Academy name

## API Endpoints

All notification registry endpoints require authentication and the `read_notification` capability.

### 1. List All Templates

**Endpoint:** `GET /v1/notify/academy/template`

**Description:** Returns all registered notification templates with optional filtering.

**Headers:**
```
Authorization: Token <user_token>
Academy: <academy_id>
```

**Query Parameters:**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `category` | string | Filter by category | `?category=authentication` |
| `channel` | string | Filter by channel availability | `?channel=email` |
| `search` | string | Search in name/description | `?search=verify` |

**Example Request:**
```bash
GET /v1/notify/academy/template?category=authentication&channel=email
Authorization: Token abc123
Academy: 4
```

**Response Schema:**
```json
{
  "templates": [
    {
      "slug": "verify_email",
      "name": "Verify Email",
      "description": "Email verification for new user accounts...",
      "category": "authentication",
      "channels": {
        "email": {
          "template_path": "verify_email",
          "default_subject": "Verify your email address"
        }
      },
      "variables": [...]
    }
  ],
  "categories": ["authentication", "academy", "general", "feedback"],
  "total": 1
}
```

**Status Codes:**
- `200 OK` - Templates retrieved successfully
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - User lacks `read_notification` capability

### 2. Get Template Details

**Endpoint:** `GET /v1/notify/academy/template/<slug>`

**Description:** Returns complete configuration for a specific notification template.

**Headers:**
```
Authorization: Token <user_token>
Academy: <academy_id>
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `slug` | string | Template slug identifier |

**Example Request:**
```bash
GET /v1/notify/academy/template/verify_email
Authorization: Token abc123
Academy: 4
```

**Response Schema:**
```json
{
  "slug": "verify_email",
  "name": "Verify Email",
  "description": "Email verification for new user accounts to confirm email ownership",
  "category": "authentication",
  "channels": {
    "email": {
      "template_path": "verify_email",
      "default_subject": "Verify your email address"
    }
  },
  "variables": [
    {
      "name": "LINK",
      "description": "Email verification URL with token",
      "source": "Generated from API_URL + verification token",
      "example": "https://api.4geeks.com/v1/auth/email/verify?token=xyz789abc",
      "required": true
    },
    {
      "name": "subject",
      "description": "Email subject line",
      "source": "Passed in data dict or uses default",
      "example": "Verify your email address",
      "required": true
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Template found and returned
- `404 Not Found` - Template slug does not exist
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - User lacks `read_notification` capability

**Error Response:**
```json
{
  "detail": "Notification template 'invalid_slug' not found",
  "slug": "notification-not-found",
  "status_code": 404
}
```

### 3. Preview Template

**Endpoint:** `GET /v1/notify/academy/template/<slug>/preview`

**Description:** Returns both raw template source code and fully rendered HTML/text with schema-driven placeholders. The rendered version includes complete template structure (including parent templates like `base.html`) with variables shown as `{VARIABLE_NAME}` placeholders, making it easy for frontend to display the complete email layout while still seeing where each variable will be inserted.

**Headers:**
```
Authorization: Token <user_token>
Academy: <academy_id>
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `slug` | string | Template slug identifier |

**Query Parameters:**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `channels` | string | Comma-separated list of channels to preview | `?channels=email,slack` |

**Example Request:**
```bash
GET /v1/notify/academy/template/message/preview?channels=email
Authorization: Token abc123
Academy: 4
```

**Response Schema:**
```json
{
  "slug": "message",
  "name": "Generic Message",
  "description": "Generic notification template for sending custom messages...",
  "category": "general",
  "channels": {
    "email": {
      "html_source": "{% extends \"base.html\" %}\n{% block content %}...",
      "html_rendered": "<!DOCTYPE html>\n<html>...\n{MESSAGE}\n...</html>",
      "text_source": "{{ MESSAGE }}\n\n{{ BUTTON }}: {{ LINK }}",
      "text_rendered": "{MESSAGE}\n\n{BUTTON}: {LINK}",
      "subject": "Message from {academy_name}"
    }
  },
  "variables": {
    "default": {
      "API_URL": "https://api.4geeks.com",
      "COMPANY_NAME": "4Geeks",
      "COMPANY_CONTACT_URL": "https://4geeks.com/contact",
      "style__success": "#99ccff",
      "style__danger": "#ffcccc"
    },
    "template_specific": {
      "SUBJECT": {
        "description": "Message subject/title",
        "source": "Passed in data dict",
        "example": "Important Update",
        "required": true
      },
      "MESSAGE": {
        "description": "Main message content (supports HTML)",
        "source": "Passed in data dict",
        "example": "Your cohort schedule has been updated.",
        "required": true
      }
    },
    "academy_specific": {
      "COMPANY_NAME": "Miami Academy",
      "COMPANY_LOGO": "https://...",
      "COMPANY_INFO_EMAIL": "info@miami.4geeks.com"
    }
  },
  "preview_context": {
    "SUBJECT": "{SUBJECT}",
    "MESSAGE": "{MESSAGE}",
    "BUTTON": "{BUTTON}",
    "LINK": "{LINK}"
  }
}
```

**Channel-Specific Responses:**

**Email Channel:**
```json
"email": {
  "html_source": "{% extends \"base.html\" %}...",
  "html_rendered": "<!DOCTYPE html>...<h1>{SUBJECT}</h1>...",
  "text_source": "{{ MESSAGE }}...",
  "text_rendered": "{MESSAGE}...",
  "subject": "Default subject"
}
```
- `html_source`: Raw child template code (Django template syntax)
- `html_rendered`: Complete HTML including parent templates with `{VARIABLE}` placeholders
- `text_source`: Raw text template code
- `text_rendered`: Complete text with `{VARIABLE}` placeholders

**Slack Channel:**
```json
"slack": {
  "source": "{\n  \"blocks\": [...]\n}",
  "rendered": "{\"text\": \"{SUBJECT}\"}",
  "format": "json"
}
```

**SMS Channel:**
```json
"sms": {
  "source": "{{ MESSAGE }}",
  "rendered": "{MESSAGE}"
}
```

**Status Codes:**
- `200 OK` - Preview generated successfully
- `404 Not Found` - Template slug does not exist
- `500 Internal Server Error` - Error rendering template
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - User lacks `read_notification` capability

**Error Response:**
```json
{
  "detail": "Error generating preview: Template not found",
  "slug": "preview-error",
  "status_code": 500
}
```

## Example Templates

### Example 1: Simple Email Notification

**File:** `breathecode/notify/registry/welcome_academy.json`

```json
{
  "slug": "welcome_academy",
  "name": "Welcome to Academy",
  "description": "Sent when a user is successfully added to an academy",
  "category": "academy",
  "channels": {
    "email": {
      "template_path": "welcome_academy",
      "default_subject": "Welcome to {academy_name}"
    }
  },
  "variables": [
    {
      "name": "user",
      "description": "Serialized user object with first_name, last_name, email",
      "source": "UserSmallSerializer(user).data",
      "example": "{\"first_name\": \"John\"}",
      "required": true
    },
    {
      "name": "LINK",
      "description": "URL to academy dashboard",
      "source": "Generated from academy dashboard URL",
      "example": "https://app.4geeks.com/academy/dashboard",
      "required": true
    }
  ]
}
```

### Example 2: Multi-Channel Notification

**File:** `breathecode/notify/registry/nps_survey.json`

```json
{
  "slug": "nps_survey",
  "name": "NPS Survey",
  "description": "Net Promoter Score survey request sent to users for feedback",
  "category": "feedback",
  "channels": {
    "email": {
      "template_path": "nps_survey",
      "default_subject": "How was your experience?"
    },
    "slack": {
      "template_path": "nps_survey",
      "default_subject": null
    }
  },
  "variables": [
    {
      "name": "SUBJECT",
      "description": "Survey subject/question",
      "source": "Passed in data dict",
      "example": "How was your experience with this cohort?",
      "required": true
    },
    {
      "name": "LINK",
      "description": "URL to the survey form",
      "source": "Generated survey response URL with token",
      "example": "https://app.4geeks.com/feedback/survey?token=survey123",
      "required": true
    },
    {
      "name": "BUTTON",
      "description": "Button text for call-to-action",
      "source": "Passed in data dict or uses default",
      "example": "Take Survey",
      "required": false
    }
  ]
}
```

### Example 3: Complex Variables

**File:** `breathecode/notify/registry/academy_invite.json`

```json
{
  "slug": "academy_invite",
  "name": "Academy Invitation",
  "description": "Sent when a user is invited to join an academy",
  "category": "academy",
  "channels": {
    "email": {
      "template_path": "academy_invite",
      "default_subject": "You've been invited to join an academy"
    }
  },
  "variables": [
    {
      "name": "user",
      "description": "Serialized user object",
      "source": "UserSmallSerializer(user).data",
      "example": "{\"first_name\": \"John\", \"last_name\": \"Doe\"}",
      "required": true
    },
    {
      "name": "LINK",
      "description": "Base URL for accepting/rejecting invitations",
      "source": "Generated invitation management URL",
      "example": "https://app.4geeks.com/invite/manage",
      "required": true
    },
    {
      "name": "invites",
      "description": "List of academy invitation objects",
      "source": "ProfileAcademy invitation records",
      "example": "[{academy: {name: 'Miami'}, role: 'STUDENT', id: 123}]",
      "required": true
    }
  ]
}
```

## Frontend Integration

### Discovering Available Templates

Use the list endpoint to discover what notification templates are available:

```javascript
// Fetch all authentication-related templates
const response = await fetch('/v1/notify/academy/template?category=authentication', {
  headers: {
    'Authorization': 'Token abc123',
    'Academy': '4'
  }
});

const data = await response.json();
// data.templates - array of available templates
// data.categories - list of all categories
// data.total - count of matching templates
```

### Getting Template Requirements

Before sending a notification, fetch template details to know what variables are required:

```javascript
const response = await fetch('/v1/notify/academy/template/verify_email', {
  headers: {
    'Authorization': 'Token abc123',
    'Academy': '4'
  }
});

const template = await response.json();

// Extract required variables
const requiredVars = template.variables
  .filter(v => v.required)
  .map(v => v.name);

console.log('Required variables:', requiredVars);
// ['LINK', 'subject']
```

### Previewing Templates

Preview templates to see both raw source and rendered HTML with placeholders:

```javascript
const response = await fetch(
  '/v1/notify/academy/template/message/preview?channels=email',
  {
    headers: {
      'Authorization': 'Token abc123',
      'Academy': '4'
    }
  }
);

const preview = await response.json();

// Display fully rendered HTML (includes base template with {VARIABLE} placeholders)
document.getElementById('preview').innerHTML = preview.channels.email.html_rendered;
// Shows: <html>...<h1>{SUBJECT}</h1><div>{MESSAGE}</div>...</html>

// Or show raw source code (child template only)
document.getElementById('source').textContent = preview.channels.email.html_source;
// Shows: {% extends "base.html" %}{% block content %}...

// Parse variables from rendered HTML if needed
const variableMatches = preview.channels.email.html_rendered.match(/{(\w+)}/g);
console.log('Variables in template:', variableMatches);
// Output: ['{SUBJECT}', '{MESSAGE}', '{BUTTON}', '{LINK}']

// Get variable documentation
console.log(preview.variables.template_specific);

// See what placeholder values were used
console.log(preview.preview_context);
```

### Building Template Selection UI

Example React component:

```javascript
function TemplateSelector({ category, onSelect }) {
  const [templates, setTemplates] = useState([]);
  
  useEffect(() => {
    fetch(`/v1/notify/academy/template?category=${category}`, {
      headers: {
        'Authorization': `Token ${token}`,
        'Academy': academyId
      }
    })
    .then(r => r.json())
    .then(data => setTemplates(data.templates));
  }, [category]);
  
  return (
    <select onChange={(e) => onSelect(e.target.value)}>
      {templates.map(t => (
        <option key={t.slug} value={t.slug}>
          {t.name} - {t.description}
        </option>
      ))}
    </select>
  );
}
```

## Schema-Driven Placeholder Generation

The preview endpoint intelligently generates placeholders based on the variable definitions in the registry JSON files. This ensures that complex object and array structures are properly represented.

### How It Works

The system uses multiple strategies to determine the correct placeholder structure:

#### 1. JSON Example Parsing

If the variable has a valid JSON example, it's parsed and converted to placeholders:

**Registry Definition:**
```json
{
  "name": "user",
  "example": "{\"first_name\": \"John\", \"last_name\": \"Doe\", \"email\": \"john@example.com\"}"
}
```

**Generated Placeholder:**
```json
{
  "first_name": "{user.first_name}",
  "last_name": "{user.last_name}",
  "email": "{user.email}"
}
```

**Rendered Output:**
```html
Hi {user.first_name}, welcome!
```

#### 2. Array Structure Inference

For arrays, the system parses the example to extract object properties:

**Registry Definition:**
```json
{
  "name": "invites",
  "example": "[{academy: {name: 'Miami Academy'}, role: 'STUDENT', id: 123}]"
}
```

**Generated Placeholder:**
```json
[
  {
    "academy": {"name": "{invites[0].academy.name}"},
    "role": "{invites[0].role}",
    "id": "{invites[0].id}"
  }
]
```

**Rendered Output:**
```html
{% for invite in invites %}
  <p>{invites[0].academy.name}</p>
  <small>Role: {invites[0].role}</small>
{% endfor %}
```

#### 3. Description Analysis

If no JSON example exists, the system analyzes the description for property hints:

**Registry Definition:**
```json
{
  "name": "user",
  "description": "Serialized user object (template accesses user.first_name)"
}
```

Extracts `first_name` and generates `{user.first_name}` placeholder.

#### 4. Serializer Detection

Recognizes common serializer patterns in the source field:

**Registry Definition:**
```json
{
  "name": "user",
  "source": "UserSmallSerializer(user).data"
}
```

Generates standard user object structure:
```json
{
  "id": "{user.id}",
  "first_name": "{user.first_name}",
  "last_name": "{user.last_name}",
  "email": "{user.email}"
}
```

#### 5. Simple String Fallback

For simple variables without structure, uses direct placeholder:

**Registry Definition:**
```json
{
  "name": "SUBJECT",
  "example": "Important Update"
}
```

**Generated Placeholder:**
```
"{SUBJECT}"
```

### Benefits

- ✅ **Automatic Structure Detection**: No manual placeholder configuration needed
- ✅ **Complete HTML Preview**: Includes parent templates (like `base.html`)
- ✅ **Frontend-Friendly Format**: Easy to parse `{VARIABLE}` format
- ✅ **Type Safety**: Complex objects maintain their structure
- ✅ **Self-Documenting**: Placeholders show exact variable access patterns

## Common Use Cases

### 1. Template Discovery Dashboard

Build a UI that shows all available notification templates organized by category:

```
GET /v1/notify/academy/template
→ Display templates grouped by category
→ Show channel availability icons (📧 email, 💬 slack, 📱 sms)
```

### 2. Template Testing Interface

Allow staff to preview and test notification templates:

```
GET /v1/notify/academy/template/<slug>/preview
→ Show raw template source
→ Display variable requirements
→ Provide form to input test values
```

### 3. Dynamic Form Generation

Build forms dynamically based on template requirements:

```javascript
// 1. Fetch template details
GET /v1/notify/academy/template/message

// 2. Extract variables
const fields = template.variables.filter(v => v.required);

// 3. Generate form fields
fields.forEach(field => {
  createFormField(field.name, field.description, field.example);
});
```

### 4. Notification Documentation

Generate human-readable documentation of all notifications:

```
GET /v1/notify/academy/template
→ For each template, display:
  - Name and description
  - Supported channels
  - Required and optional variables
  - Example values
```

## Best Practices

### For Backend Developers

1. **Always Register New Templates**: Before sending a notification, create its registry JSON file
2. **Match Slug to Filename**: `message.json` must have `"slug": "message"`
3. **Document All Variables**: Include description, source, and example for each variable
4. **Use Descriptive Categories**: Choose appropriate category for easier discovery
5. **Provide Examples**: Include realistic example values for testing

### For Frontend Developers

1. **Check Template Availability**: Query templates before building notification UI
2. **Validate Required Variables**: Ensure all required variables are provided
3. **Handle Missing Templates**: Gracefully handle 404 responses
4. **Cache Template Lists**: Templates don't change frequently, cache the list
5. **Show Variable Documentation**: Display examples and descriptions to users

### For Creating New Templates

**Step 1:** Create JSON registry file

```bash
touch breathecode/notify/registry/my_notification.json
```

**Step 2:** Define template configuration

```json
{
  "slug": "my_notification",
  "name": "My Notification",
  "description": "Detailed description of when this is sent",
  "category": "general",
  "channels": {
    "email": {
      "template_path": "my_notification",
      "default_subject": "Notification Subject"
    }
  },
  "variables": [
    {
      "name": "VARIABLE_NAME",
      "description": "What it represents",
      "source": "Where it comes from",
      "example": "Example value",
      "required": true
    }
  ]
}
```

**Step 3:** Create template files

```bash
touch breathecode/notify/templates/my_notification.html
touch breathecode/notify/templates/my_notification.txt
```

**Step 4:** Restart server to load new template

```bash
# Registry is loaded at startup
```

## Troubleshooting

### Template Not Found

**Error:** `"Notification template 'xyz' not found"`

**Solutions:**
1. Verify JSON file exists: `breathecode/notify/registry/xyz.json`
2. Check slug matches filename: `"slug": "xyz"` in JSON
3. Restart server to reload registry
4. Check logs for parsing errors

### Template Validation Fails

**Error:** `"Slug mismatch in xyz.json: expected abc.json"`

**Solution:** Update slug in JSON to match filename:
```json
{
  "slug": "xyz",  // Must match filename xyz.json
  ...
}
```

### Missing Variables

**Error:** Template renders with empty/missing values

**Solution:** Check template registry for required variables:
```bash
GET /v1/notify/academy/template/template_name
# Review variables array for required: true
```

### Preview Returns Error

**Error:** `"Error generating preview: Template not found"`

**Solutions:**
1. Verify template files exist in `breathecode/notify/templates/`
2. Check `template_path` in registry matches file name
3. Ensure channel configuration is correct

## Academy Notification Settings

### Overview

Academy Notification Settings allow each academy to customize notification templates without code changes. Academies can override variables globally or per-template, with support for variable interpolation.

### Purpose

- **Per-Academy Customization**: Each academy has full control over notification content
- **No Code Changes Required**: Customize through API or Django Admin
- **Variable Override Priority**: Academy settings override code defaults
- **Variable Interpolation**: Reuse variables within other variables

### Model Structure

Each academy can have one `AcademyNotifySettings` instance with the following fields:

#### Fields

- **template_variables** (JSONField): Variable overrides for notification templates
  - Format: `{"template.SLUG.VARIABLE": "value", "global.VARIABLE": "value"}`
  - Supports interpolation with `{{variable}}` syntax

- **disabled_templates** (JSONField): List of template slugs to disable
  - Format: `["template_slug1", "template_slug2"]`
  - Disabled templates won't send (silently skipped)

**Variable Override Priority:**
1. Academy template-specific override (highest)
2. Academy global override
3. Code context from `send_email_message` call
4. System defaults (lowest)

### API Endpoints

#### Get Academy Settings

**Endpoint:** `GET /v1/notify/academy/settings`

**Permission:** Requires `read_notification` capability

**Headers:**
```
Authorization: Token <user_token>
Academy: <academy_id>
```

**Response (no settings):**
```json
{
  "template_variables": {},
  "disabled_templates": [],
  "academy": 4
}
```

**Response (with settings):**
```json
{
  "academy": 4,
  "template_variables": {
    "template.welcome_academy.subject": "¡Bienvenido!",
    "global.COMPANY_NAME": "Miami Academy"
  },
  "disabled_templates": ["nps_survey"],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-02T00:00:00Z"
}
```

#### Update Academy Settings

**Endpoint:** `PUT /v1/notify/academy/settings`

**Permission:** Requires `crud_notification` capability

**Headers:**
```
Authorization: Token <user_token>
Academy: <academy_id>
Content-Type: application/json
```

**Request Body:**
```json
{
  "template_variables": {
    "template.welcome_academy.subject": "Welcome to our school!",
    "global.COMPANY_NAME": "Custom Academy Name"
  },
  "disabled_templates": ["nps_survey"]
}
```

**Response:**
```json
{
  "academy": 4,
  "template_variables": {
    "template.welcome_academy.subject": "Welcome to our school!",
    "global.COMPANY_NAME": "Custom Academy Name"
  },
  "disabled_templates": ["nps_survey"],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-02T10:30:00Z"
}
```

**Validation Errors:**

Invalid template in template_variables:
```json
{
  "template_variables": [
    "Template 'invalid_slug' not found in notification registry"
  ]
}
```

Invalid template in disabled_templates:
```json
{
  "disabled_templates": [
    "Disabled template 'invalid_slug' not found in notification registry"
  ]
}
```

Multiple errors:
```json
{
  "template_variables": [
    "disabled_templates must be a list; Template 'bad_slug' not found in notification registry"
  ]
}
```

### Variable Interpolation

Variables can reference other variables using `{{variable_name}}` syntax:

**Example:**
```json
{
  "template.welcome_academy.subject": "{{global.greeting}} to {{global.COMPANY_NAME}}!",
  "global.greeting": "Welcome",
  "global.COMPANY_NAME": "Miami Academy"
}
```

**Result:**
```
subject = "Welcome to Miami Academy!"
```

**Interpolation Rules:**
- Uses double braces: `{{global.VAR}}` or `{{template.slug.VAR}}`
- Supports nested references (up to 5 levels)
- Protects against circular references
- Resolves at template rendering time

### Disabling Templates

Academies can completely disable specific notification templates:

```json
{
  "disabled_templates": ["nps_survey", "welcome_academy"]
}
```

**Behavior:**
- Calls to `send_email_message()` with disabled templates return `True` without sending
- Logged as INFO: "Template 'nps_survey' is disabled for academy 4"
- Silently skips sending (no error raised)
- Code execution continues normally

**Use Cases:**
- Disable NPS surveys for trial accounts
- Turn off welcome emails for partner academies
- Disable marketing notifications for specific regions
- Prevent duplicate notifications from external systems

**Validation:**
- Template slugs must exist in notification registry
- Invalid slugs will cause validation error on save
- Empty list `[]` means all templates are enabled

### Usage Examples

#### Example 1: Override Subject for Specific Template

```json
{
  "template_variables": {
    "template.welcome_academy.subject": "¡Bienvenido a nuestra academia!"
  }
}
```

When `send_email_message("welcome_academy", ...)` is called, the subject will use the academy's custom value instead of the code default.

#### Example 2: Global Company Name

```json
{
  "global.COMPANY_NAME": "Academia de Programación Miami"
}
```

All templates will use this company name unless overridden by template-specific values.

#### Example 3: Complex Composition

```json
{
  "template.welcome_academy.subject": "{{global.welcome_message}}",
  "template.welcome_academy.MESSAGE": "We're excited to have you at {{global.COMPANY_NAME}}",
  "global.welcome_message": "Welcome to {{global.COMPANY_NAME}}!",
  "global.COMPANY_NAME": "Miami Coding Academy"
}
```

**Resolves to:**
- `subject`: "Welcome to Miami Coding Academy!"
- `MESSAGE`: "We're excited to have you at Miami Coding Academy"
- `COMPANY_NAME`: "Miami Coding Academy"

### Code Integration

The integration happens automatically in `send_email_message`:

```python
from breathecode.notify import actions as notify_actions

notify_actions.send_email_message(
    "welcome_academy",
    "student@example.com",
    {
        "subject": "Default welcome subject",  # Overridden if academy has template.welcome_academy.subject
        "FIRST_NAME": "John",  # Not overridden (code takes precedence for specific values)
    },
    academy=academy,
)
```

**Override Behavior:**
1. Code provides default values in `data` dict
2. Academy settings are retrieved if available
3. Academy overrides are applied with `.update(overrides)`
4. Academy values override code defaults
5. Template is rendered with final merged data

### Django Admin

Settings can be managed through Django Admin:

1. Navigate to **Notify → Academy Notification Settings**
2. Select academy
3. Edit `template_variables` JSON field
4. Format must be valid JSON with proper key format
5. Validation runs on save

**Admin Interface:**
- List view shows academy and updated_at
- Search by academy name or slug
- Read-only created_at and updated_at fields
- Collapsible metadata section

### Validation

Strict validation ensures data integrity:

**Validated:**
- Template slugs must exist in notification registry
- Variable names must exist in template's variable list
- Global variables are always allowed
- Key format must be `template.SLUG.VAR` or `global.VAR`

**Validation Errors:**
- Invalid template slug: "Template 'xyz' not found in notification registry"
- Invalid variable: "Variable 'XYZ' not found in template 'abc'. Available variables: ..."
- Invalid format: "Invalid key format: 'xyz'. Must start with 'template.' or 'global.'"

### Best Practices

1. **Use Global Variables**: For values used across multiple templates
2. **Template-Specific Only When Needed**: Override per-template only when different from global
3. **Interpolation for Consistency**: Compose complex values from simpler ones
4. **Test Before Production**: Use preview endpoint to verify templates render correctly
5. **Document Custom Variables**: Keep track of what each academy customizes
6. **Validate Early**: Use PUT endpoint to validate settings before deploying

### Frontend Integration

```javascript
// Get current academy settings
const response = await fetch('/v1/notify/academy/settings', {
  headers: {
    'Authorization': 'Token abc123',
    'Academy': '4'
  }
});
const settings = await response.json();

console.log('Disabled templates:', settings.disabled_templates);
console.log('Variable overrides:', settings.template_variables);

// Update academy settings
const updateResponse = await fetch('/v1/notify/academy/settings', {
  method: 'PUT',
  headers: {
    'Authorization': 'Token abc123',
    'Academy': '4',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    template_variables: {
      'template.welcome_academy.subject': 'Custom Welcome!',
      'global.COMPANY_NAME': 'My Academy'
    },
    disabled_templates: ['nps_survey']
  })
});

if (!updateResponse.ok) {
  const errors = await updateResponse.json();
  console.error('Validation errors:', errors);
}
```

#### Building a Template Toggle UI

```javascript
function TemplateManager({ academyId }) {
  const [settings, setSettings] = useState({});
  const [templates, setTemplates] = useState([]);

  // Fetch available templates
  useEffect(() => {
    fetch('/v1/notify/academy/template', { headers })
      .then(r => r.json())
      .then(data => setTemplates(data.templates));
  }, []);

  // Fetch current settings
  useEffect(() => {
    fetch('/v1/notify/academy/settings', { headers })
      .then(r => r.json())
      .then(data => setSettings(data));
  }, []);

  const toggleTemplate = async (slug) => {
    const isDisabled = settings.disabled_templates?.includes(slug);
    const newDisabled = isDisabled
      ? settings.disabled_templates.filter(s => s !== slug)
      : [...(settings.disabled_templates || []), slug];

    await fetch('/v1/notify/academy/settings', {
      method: 'PUT',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...settings,
        disabled_templates: newDisabled
      })
    });
    
    setSettings(prev => ({ ...prev, disabled_templates: newDisabled }));
  };

  return (
    <div>
      {templates.map(t => (
        <div key={t.slug}>
          <input
            type="checkbox"
            checked={!settings.disabled_templates?.includes(t.slug)}
            onChange={() => toggleTemplate(t.slug)}
          />
          {t.name} - {t.description}
        </div>
      ))}
    </div>
  );
}
```

### Common Patterns

#### Pattern 1: Multilingual Templates

```json
{
  "template_variables": {
    "template.welcome_academy.subject": "¡Bienvenido!",
    "template.verify_email.subject": "Verifica tu correo",
    "global.COMPANY_NAME": "Academia Miami"
  }
}
```

#### Pattern 2: White-Label Branding

```json
{
  "template_variables": {
    "global.COMPANY_NAME": "Partner Academy Inc.",
    "global.COMPANY_CONTACT_URL": "https://partner.example.com/contact",
    "template.welcome_academy.MESSAGE": "Welcome to our partnership program!"
  }
}
```

#### Pattern 3: Custom CTAs

```json
{
  "template_variables": {
    "template.welcome_academy.BUTTON": "Comenzar Ahora",
    "template.verify_email.BUTTON": "Verificar Mi Correo"
  }
}
```

#### Pattern 4: Disable Marketing Notifications

```json
{
  "disabled_templates": ["nps_survey", "feedback_request"],
  "template_variables": {
    "global.COMPANY_NAME": "Corporate Training Division"
  }
}
```

**Use Case:** Corporate training academies that don't want to send marketing/survey emails but still want to customize branding.

### Troubleshooting

**Issue:** Settings not applying

**Solutions:**
- Verify academy has notify_settings relationship
- Check variable names match exactly (case-sensitive)
- Ensure academy is passed to `send_email_message`
- Check logs for override application errors

**Issue:** Disabled template still sending

**Solutions:**
- Check template slug is exactly in `disabled_templates` list
- Verify academy object is passed to `send_email_message`
- Check logs for "Template 'X' is disabled for academy Y" message
- Ensure settings relationship exists (not None)

**Issue:** Validation fails unexpectedly

**Solutions:**
- Verify template slug exists in registry
- Check variable name exists in template's variables array
- Use exact key format: `template.slug.VARIABLE` or `global.VARIABLE`
- Check for typos in slug or variable names

**Issue:** Interpolation not working

**Solutions:**
- Use double braces: `{{variable}}`
- Reference format: `{{global.VAR}}` or `{{template.slug.VAR}}`
- Check for circular references (max depth is 5)
- Verify referenced variables exist in template_variables

## Related Documentation

- [Email Notifications](./notifications.md) - How to send notifications
- [Template Development](./template_development.md) - Creating notification templates
- [Webhook System](./webhooks.md) - Notification delivery webhooks

