# White Label Features - Academy Configuration

## Overview

The `white_label_features` field in the `Academy` model allows configuring custom features for white label academies, such as hiding widgets, customizing navigation, and controlling feature availability.

## Architecture

### Automatic Default Merging

The system automatically merges saved configurations with current defaults. This ensures:
- **Backward Compatibility**: When new feature flags are added, existing academies automatically get them with default values
- **Custom Values Preserved**: Academy-specific customizations are never overwritten
- **No Manual Updates Required**: The API always returns the latest structure

### How It Works

1. **Default Function** (`default_white_label_features()`): Defines the baseline structure with default values
2. **Model Method** (`get_white_label_features()`): Merges saved data with current defaults using deep merge
3. **Serializer**: Uses the merge method to always return complete feature structure
4. **Management Command**: Available for batch updates when needed

## Feature Structure

```python
{
    "navigation": {
        "show_marketing_navigation": False,  # Show marketing navigation (url to 4geeks programs)
        "custom_links": []  # Additional links added to white label academy navbar
    },
    "features": {
        "allow_referral_program": False,  # Allow referral program
        "allow_events": True,  # Allow events
        "allow_mentoring": False,  # Allow mentoring
        "allow_feedback_widget": False,  # Allow feedback widget
        "allow_community_widget": False,  # Allow community widget
        "allow_other_academy_courses": False,  # Allow other academy courses on dashboard
        "allow_other_academy_events": False  # Allow other academy events
    }
}
```

## Adding New Features

When you need to add a new feature flag:

### 1. Update the Default Function

Edit `breathecode/admissions/models.py`:

```python
def default_white_label_features():
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
python manage.py normalize_white_label_features --dry-run

# Apply changes
python manage.py normalize_white_label_features
```

> **Note**: This step is optional! The API will automatically return merged values even without running the command. Only run it if you want to persist the new structure in the database.

### 3. No Serializer Changes Needed

The serializer automatically uses `get_white_label_features()`, so it will return the merged structure.

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
  "white_label_features": {
    "navigation": {
      "show_marketing_navigation": false,
      "custom_links": []
    },
    "features": {
      "allow_referral_program": false,
      "allow_events": true,
      "allow_mentoring": false,
      "allow_feedback_widget": false,
      "allow_community_widget": false,
      "allow_other_academy_courses": false,
      "allow_other_academy_events": false
    }
  }
}
```

### Update Academy Features

To update white label features, use the Academy update endpoint with the fields you want to change:

```bash
PUT /v1/admissions/academy/{academy_id}
```

```json
{
  "white_label_features": {
    "navigation": {
      "show_marketing_navigation": true,
      "custom_links": [
        {
          "url": "/custom-page",
          "label": "Custom Link"
        }
      ]
    },
    "features": {
      "allow_events": false
    }
  }
}
```

## Management Command

### `normalize_white_label_features`

Updates all academies with the latest default structure.

**Usage:**
```bash
# Dry run (preview changes)
python manage.py normalize_white_label_features --dry-run

# Apply changes
python manage.py normalize_white_label_features
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

## Frontend Integration

Frontend can check feature availability:

```javascript
const academy = await getAcademy(academyId);
const features = academy.white_label_features;

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
python manage.py normalize_white_label_features
```

### Problem: Custom values being overwritten

**Solution**: Check that your update payload includes all custom values you want to keep. The system uses deep merge, so partial updates should work, but full object replacement will reset unspecified keys to defaults.

### Problem: Feature flag not appearing in API response

**Solution**:
1. Verify the feature is added to `default_white_label_features()`
2. Check that the serializer uses `get_white_label_features()` method
3. Restart the Django server to reload model definitions

## Related Files

- Model: `breathecode/admissions/models.py` (Academy model, line ~29 and ~173)
- Serializer: `breathecode/admissions/serializers.py` (GetBigAcademySerializer, line ~215)
- Management Command: `breathecode/admissions/management/commands/normalize_white_label_features.py`
- Tests: `breathecode/admissions/tests/models/test_academy_white_label_features.py`
