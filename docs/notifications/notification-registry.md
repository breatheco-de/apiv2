# Notification Registry

The Notification Registry is a centralized system for managing and previewing email, Slack, SMS, and other notification templates used throughout the BreatheCode platform.

## Overview

The notification system consists of:

1. **JSON Registry Files**: Individual JSON files in `breathecode/notify/registry/` that define each notification's metadata
2. **EmailManager**: A singleton class that loads and manages notification templates
3. **API Endpoints**: REST endpoints for listing, viewing, and previewing notifications (requires `read_notification` capability)
4. **Template Files**: Django templates in various app `templates/` directories

## Architecture

### Registry Structure

Each notification is defined in a separate JSON file located at:

```
breathecode/notify/registry/{slug}.json
```

The file name must match the `slug` field inside the JSON.

### JSON File Format

```json
{
    "slug": "pick_password",
    "name": "Pick Password",
    "description": "Sent when user requests a password reset",
    "category": "authentication",
    "channels": {
        "email": {
            "template_path": "pick_password",
            "default_subject": "Reset your password"
        },
        "slack": {
            "template_path": "pick_password",
            "default_subject": null
        }
    },
    "variables": [
        {
            "name": "LINK",
            "description": "URL to password reset page with token",
            "source": "Generated from API_URL + token",
            "example": "https://api.4geeks.com/v1/auth/password/reset?token=abc123",
            "required": true
        }
    ]
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `slug` | string | Unique identifier, must match filename (without .json) |
| `name` | string | Human-readable name |
| `description` | string | Detailed description of when this notification is sent |
| `category` | string | Category for grouping (authentication, academy, feedback, monitoring, general) |
| `channels` | object | Available channels and their configurations |
| `channels.{channel}.template_path` | string | Path to template files (without extension) |
| `channels.{channel}.default_subject` | string | Default subject line (email only) |
| `variables` | array | List of template variables |
| `variables[].name` | string | Variable name as used in template |
| `variables[].description` | string | Human-readable description |
| `variables[].source` | string | Where/how the variable is generated |
| `variables[].example` | string | Example value |
| `variables[].required` | boolean | Whether variable must be provided |

## Available Notifications

### Authentication Category

#### pick_password
- **Description**: Sent when user requests a password reset or needs to set their password
- **Channels**: email
- **Variables**: `LINK`, `subject`

#### verify_email
- **Description**: Email verification for new user accounts
- **Channels**: email
- **Variables**: `LINK`, `subject`

### Academy Category

#### academy_invite
- **Description**: Sent when a user is invited to join an academy
- **Channels**: email
- **Variables**: `user.first_name`, `LINK`, `invites`

#### welcome_academy
- **Description**: Welcome email sent to new academy members
- **Channels**: email
- **Variables**: `FIRST_NAME`, `LINK`, `subject`

### Feedback Category

#### nps_survey
- **Description**: Net Promoter Score survey request
- **Channels**: email, slack
- **Variables**: `SUBJECT`, `MESSAGE`, `LINK`, `BUTTON`

### Monitoring Category

#### diagnostic
- **Description**: System monitoring diagnostic reports
- **Channels**: email
- **Variables**: `subject`, `details`, `button`

### General Category

#### message
- **Description**: Generic notification template for custom messages
- **Channels**: email
- **Variables**: `SUBJECT`, `MESSAGE`, `BUTTON`, `LINK`, `BUTTON_TARGET`, `GO_BACK`, `URL_BACK`

## Variable Types

The system provides three types of variables:

### 1. Default Variables
Always available in all templates:

- `API_URL`: Base API URL from environment
- `COMPANY_NAME`: Company name from environment
- `COMPANY_CONTACT_URL`: Contact URL from environment
- `COMPANY_LEGAL_NAME`: Legal company name from environment
- `COMPANY_ADDRESS`: Company address from environment
- `style__success`: Success color (#99ccff)
- `style__danger`: Danger color (#ffcccc)
- `style__secondary`: Secondary color (#ededed)

### 2. Template-Specific Variables
Defined in each notification's JSON file, specific to that template.

### 3. Academy-Specific Variables
Automatically included when an academy context is provided:

- `COMPANY_INFO_EMAIL`: Academy feedback email
- `COMPANY_LEGAL_NAME`: Academy legal name or name
- `COMPANY_LOGO`: Academy logo URL
- `COMPANY_NAME`: Academy name

## API Endpoints

All endpoints require the `read_notification` capability (available to admin and country_manager roles).

### List All Notifications

```http
GET /v1/messaging/academy/template
```

**Query Parameters:**
- `category` (optional): Filter by category
- `search` (optional): Search in name/description
- `channel` (optional): Filter by channel availability

**Response:**
```json
{
    "templates": [
        {
            "slug": "pick_password",
            "name": "Pick Password",
            "description": "...",
            "category": "authentication",
            "channels": {...},
            "variables": [...]
        }
    ],
    "categories": ["authentication", "academy", "feedback"],
    "total": 7
}
```

### Get Notification Details

```http
GET /v1/messaging/academy/template/{slug}
```

**Response:**
```json
{
    "slug": "pick_password",
    "name": "Pick Password",
    "description": "...",
    "category": "authentication",
    "channels": {...},
    "variables": [...]
}
```

### Preview Notification Template

```http
GET /v1/messaging/academy/template/{slug}/preview
```

**Headers:**
- `Academy` (required): Academy ID from request headers (validated by capable_of decorator)

**Query Parameters:**
- `channels` (optional): Comma-separated list of channels to preview (e.g., "email,slack")

**Response:**
```json
{
    "slug": "pick_password",
    "name": "Pick Password",
    "description": "...",
    "category": "authentication",
    "channels": {
        "email": {
            "html": "{% extends \"base.html\" %}...",
            "text": "You are seen this email...",
            "subject": "Reset your password"
        }
    },
    "variables": {
        "default": {
            "API_URL": "https://api.4geeks.com",
            "COMPANY_NAME": "4Geeks"
        },
        "template_specific": {
            "LINK": {
                "description": "URL to password reset page",
                "source": "Generated from API_URL + token",
                "example": "https://api.4geeks.com/...",
                "required": true
            }
        },
        "academy_specific": {
            "COMPANY_LOGO": "https://..."
        }
    }
}
```

## Usage Examples

### Using curl

```bash
# List all notifications
curl -H "Authorization: Token YOUR_TOKEN" \
  https://api.4geeks.com/v1/messaging/academy/template

# Get specific notification
curl -H "Authorization: Token YOUR_TOKEN" \
  https://api.4geeks.com/v1/messaging/academy/template/pick_password

# Preview with academy branding (academy ID from header)
curl -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 1" \
  "https://api.4geeks.com/v1/messaging/academy/template/pick_password/preview"
```

### Using JavaScript/Axios

```javascript
// List all authentication notifications
const response = await axios.get(
  '/v1/messaging/academy/template',
  {
    params: { category: 'authentication' },
    headers: { Authorization: `Token ${token}` }
  }
);

// Preview notification (academy ID in header)
const preview = await axios.get(
  `/v1/messaging/academy/template/pick_password/preview`,
  {
    params: { channels: 'email' },
    headers: { 
      Authorization: `Token ${token}`,
      Academy: '1'
    }
  }
);

// Access template source
console.log(preview.data.channels.email.html);
console.log(preview.data.variables.template_specific);
```

## Adding New Notifications

### Step 1: Create Template Files

Create Django templates in the appropriate app's `templates/` directory:

```
breathecode/authenticate/templates/
  - my_notification.html
  - my_notification.txt
  - my_notification.slack (optional)
  - my_notification.sms (optional)
```

### Step 2: Create JSON Registry File

Create `breathecode/notify/registry/my_notification.json`:

```json
{
    "slug": "my_notification",
    "name": "My Notification",
    "description": "Description of when this is sent",
    "category": "authentication",
    "channels": {
        "email": {
            "template_path": "my_notification",
            "default_subject": "Subject Line"
        }
    },
    "variables": [
        {
            "name": "VARIABLE_NAME",
            "description": "What this variable contains",
            "source": "How it's generated",
            "example": "Example value",
            "required": true
        }
    ]
}
```

### Step 3: Verify Registration

The EmailManager automatically loads all JSON files on startup. Verify your notification appears:

```bash
curl -H "Authorization: Token YOUR_TOKEN" \
  https://api.4geeks.com/v1/messaging/academy/template | grep my_notification
```

## Best Practices

1. **Naming**: Use snake_case for slugs, matching the template file names
2. **Categories**: Use existing categories when possible (authentication, academy, feedback, monitoring, general)
3. **Documentation**: Provide clear descriptions and examples for all variables
4. **Template Paths**: Path should match the template location without extension
5. **Required Fields**: Mark variables as required only if the template breaks without them
6. **Examples**: Use realistic example values that help understand the variable's format

## Troubleshooting

### Notification Not Appearing

1. Check that the JSON file is in `breathecode/notify/registry/`
2. Verify the filename matches the `slug` field (e.g., `pick_password.json` for slug `pick_password`)
3. Validate the JSON syntax (use a JSON validator)
4. Check server logs for parsing errors

### Template Not Loading

1. Verify template files exist with correct names
2. Check the `template_path` in the JSON matches the template filename (without extension)
3. Ensure templates are in a valid templates directory

### Permission Denied

The API endpoints require the `read_notification` capability, which is only assigned to:
- `admin` role
- `country_manager` role

## Security

- All endpoints require authentication
- The `read_notification` capability is required
- Academy-specific variables only included when user has academy access
- Template source code is exposed intentionally for preview purposes
- No sensitive data should be in template defaults

## Related Documentation

- [Authentication System](../authenticate/README.md)
- [Notification Models](../models.md)
- [Email Actions](../actions.md)

