# Academy Feature Flags - Configuration

## Overview

The `academy_features` field in the `Academy` model allows configuring custom features for all academies, such as hiding widgets, customizing navigation, and controlling feature availability. Feature flags are available for all academies to provide flexible configuration options.

## Architecture

### Automatic Default Merging

The system automatically merges saved configurations with current defaults. This ensures:
- **Backward Compatibility**: When new feature flags are added, existing academies automatically get them with default values
- **Custom Values Preserved**: Academy-specific customizations are never overwritten
- **No Manual Updates Required**: The API always returns the latest structure

### How It Works

1. **Default Function** (`default_academy_features()`): Defines the baseline structure with default values
2. **Model Method** (`get_academy_features()`): Merges saved data with current defaults using deep merge
3. **Serializer**: Uses the merge method to always return complete feature structure
4. **Management Command**: Available for batch updates when needed

## Feature Structure

```python
{
    "features": {
        "allow_events": True,  # Allow events
        "allow_mentoring": True,  # Allow mentoring
        "allow_feedback_widget": True,  # Allow feedback widget
        "allow_community_widget": True,  # Allow community widget
        "allow_referral_program": True,  # Allow referral program
        "allow_other_academy_events": True,  # Allow other academy events
        "allow_other_academy_courses": True  # Allow other academy courses on dashboard
    },
    "navigation": {
        "custom_links": [],  # Additional links added to academy navbar
        "show_marketing_navigation": False  # Show marketing navigation (url to 4geeks programs) - Only for white label academies
    }
}
```

## Adding New Features

When you need to add a new feature flag:

### 1. Update the Default Function

Edit `breathecode/admissions/models.py`:

```python
def default_academy_features():
    return {
        "navigation": {
            "show_marketing_navigation": False,
            "custom_links": [],
            "show_new_feature": True,  # ← Add your new feature
        },
        "features": {
            # ... existing features
        }
    }
```

### 2. (Optional) Update Existing Academies

If you want to persist the new defaults to the database:

```bash
# Preview changes
python manage.py normalize_academy_features --dry-run

# Apply changes
python manage.py normalize_academy_features
```

> **Note**: This step is optional! The API will automatically return merged values even without running the command. Only run it if you want to persist the new structure in the database.

### 3. No Serializer Changes Needed

The serializer automatically uses `get_academy_features()`, so it will return the merged structure.

## API Usage

### GET Academy

```bash
GET /v1/admissions/academy/{academy_id}
```

**Response** (always includes all current features):
```json
{
  "id": 1,
  "slug": "my-academy",
  "name": "My Academy",
  // ... other fields
  "academy_features": {
    "features": {
      "allow_events": true,
      "allow_mentoring": true,
      "allow_feedback_widget": true,
      "allow_community_widget": true,
      "allow_referral_program": true,
      "allow_other_academy_events": true,
      "allow_other_academy_courses": true
    },
    "navigation": {
      "custom_links": [],
      "show_marketing_navigation": false
    }
  }
}
```

### Update Academy Features

To update feature flags, use the Academy update endpoint with the fields you want to change:

```bash
PUT /v1/admissions/academy/{academy_id}
```

```json
{
  "academy_features": {
    "features": {
      "allow_events": false
    },
    "navigation": {
      "custom_links": [
        {
          "url": "/custom-page",
          "label": "Custom Link"
        }
      ],
      "show_marketing_navigation": false
    }
  }
}
```

## Management Command

### `normalize_academy_features`

Updates all academies with the latest default structure.

**Usage:**
```bash
# Dry run (preview changes)
python manage.py normalize_academy_features --dry-run

# Apply changes
python manage.py normalize_academy_features
```

**When to use:**
- After adding new feature flags to ensure database consistency
- Before major releases to normalize all academies
- When debugging feature flag issues

**When NOT to use:**
- Not required for normal operation (API handles merging automatically)
- Don't run frequently (creates unnecessary database writes)

## Testing

Tests are located in `breathecode/admissions/tests/models/test_academy_white_label_features.py`

Run tests:
```bash
pytest breathecode/admissions/tests/models/test_academy_white_label_features.py -v
```

## Key Benefits

✅ **Automatic Updates**: New features are automatically available to all academies
✅ **Backward Compatible**: Old academies work seamlessly with new feature structure
✅ **Custom Preservation**: Academy-specific settings are never lost
✅ **No Downtime**: Changes don't require migrations or service restarts
✅ **Type Safe**: Python dictionaries ensure structure consistency

## Best Practices

1. **Feature Naming**: Use clear, descriptive names with `allow_*` or `show_*` prefix
2. **Default Values**: Choose safe defaults (typically `False` for new features)
3. **Documentation**: Update this file when adding new features
4. **Testing**: Add tests for new features in the test suite
5. **Communication**: Notify frontend team about new feature flags available

## Backend Integration

Backend code can check feature flags using the helper functions:

```python
from breathecode.admissions.utils.academy_features import has_feature_flag, get_feature_flag
from breathecode.admissions.models import Academy

# Get academy instance
academy = Academy.objects.get(id=1)

# Check boolean feature flag
if has_feature_flag(academy, 'allow_events'):
    # Show events widget
    show_events_widget()

# Check feature flag with default value
if has_feature_flag(academy, 'allow_events', default=True):
    # Show events

# Get non-boolean feature flag (like custom_links)
custom_links = get_feature_flag(academy, 'custom_links', default=[])

# Works with None academy (returns default)
if has_feature_flag(None, 'allow_events', default=True):
    # Use default value when academy is None
```

### Helper Functions

- **`has_feature_flag(academy, feature_key, default=True)`**: Returns boolean value of a feature flag
- **`get_feature_flag(academy, feature_key, default=None)`**: Returns the actual value of a feature flag (useful for non-boolean flags)

## Frontend Integration

Frontend can check feature availability:

```javascript
const academy = await getAcademy(academyId);
const features = academy.academy_features;

// Check if feature is enabled
if (features.features.allow_referral_program) {
  // Show referral program widget
}

// Check navigation settings
if (features.navigation.show_marketing_navigation) {
  // Show marketing navigation
}

// Render custom links
features.navigation.custom_links.forEach(link => {
  // Render link in navbar
});
```

## Troubleshooting

### Problem: Old academy missing new feature flags

**Solution**: The API automatically merges defaults. No action needed. If you want to persist to database, run:
```bash
python manage.py normalize_academy_features
```

### Problem: Custom values being overwritten

**Solution**: Check that your update payload includes all custom values you want to keep. The system uses deep merge, so partial updates should work, but full object replacement will reset unspecified keys to defaults.

### Problem: Feature flag not appearing in API response

**Solution**:
1. Verify the feature is added to `default_academy_features()`
2. Check that the serializer uses `get_academy_features()` method
3. Restart the Django server to reload model definitions

## Related Files

- Model: `breathecode/admissions/models.py` (Academy model, line ~29 and ~173)
- Serializer: `breathecode/admissions/serializers.py` (GetBigAcademySerializer, line ~215)
- Management Command: `breathecode/admissions/management/commands/normalize_academy_features.py`
- Backend Helper: `breathecode/admissions/utils/academy_features.py` (has_feature_flag, get_feature_flag)
- Tests: `breathecode/admissions/tests/models/test_academy_white_label_features.py`

