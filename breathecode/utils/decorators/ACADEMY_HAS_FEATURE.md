# Academy Has Feature Decorator

## Overview

The `@academy_has_feature` decorator validates that an academy has specific feature flags enabled before allowing access to an endpoint. It works similarly to `@capable_of` but for academy features instead of user capabilities.

## Purpose

- Enforce feature flag requirements at the view level
- Provide clear error messages when features are missing
- Support white label validation
- Work seamlessly with `@capable_of` decorator

## Usage

### Basic Usage

```python
from breathecode.utils.decorators import capable_of, academy_has_feature

class MyView(APIView):
    @capable_of('crud_course')
    @academy_has_feature('reseller')
    def post(self, request, academy_id=None):
        # This will only execute if:
        # 1. User has 'crud_course' capability (from @capable_of)
        # 2. Academy has 'reseller' feature enabled
        pass
```

### With White Label Requirement

```python
@capable_of('crud_course')
@academy_has_feature('reseller', require_white_labeled=True)
def post(self, request, academy_id=None):
    # This will only execute if:
    # 1. User has 'crud_course' capability
    # 2. Academy has 'reseller' feature enabled
    # 3. Academy is white labeled (academy.white_labeled=True)
    pass
```

### Multiple Features

```python
@capable_of('crud_event')
@academy_has_feature('allow_events', 'allow_other_academy_events')
def post(self, request, academy_id=None):
    # Academy must have BOTH features enabled
    pass
```

### Async Version

```python
from breathecode.utils.decorators import acapable_of, aacademy_has_feature

class MyAsyncView(APIView):
    @acapable_of('crud_course')
    @aacademy_has_feature('reseller', require_white_labeled=True)
    async def post(self, request, academy_id=None):
        # Async version for async views
        pass
```

## Parameters

### `@academy_has_feature(*required_features, require_white_labeled=False)`

- **`*required_features`** (required): One or more feature flag names to validate
  - Examples: `'reseller'`, `'allow_events'`, `'allow_mentoring'`
  - All specified features must be enabled (AND logic)
  
- **`require_white_labeled`** (optional, default=False): If True, also validates `academy.white_labeled=True`

## Error Responses

### Missing Feature

```json
{
  "detail": "Academy does not have the required feature: reseller",
  "slug": "academy-feature-reseller-not-enabled",
  "status_code": 403
}
```

### Not White Labeled (when required)

```json
{
  "detail": "This feature requires a white labeled academy",
  "slug": "academy-not-white-labeled",
  "status_code": 403
}
```

### Academy Not Found

```json
{
  "detail": "Academy not found",
  "slug": "academy-not-found",
  "status_code": 404
}
```

## Requirements

1. **Must be used AFTER `@capable_of`**: The decorator depends on `academy_id` being injected by `@capable_of`
2. **Feature must exist in `academy_features`**: The feature flag must be defined in `default_academy_features()`
3. **Academy must exist**: The academy_id must reference a valid academy

## How It Works

1. Extracts `academy_id` from kwargs (injected by `@capable_of`)
2. Fetches the academy from database
3. Validates white label requirement (if specified)
4. Checks each required feature using `has_feature_flag()` helper
5. Raises `ValidationException` if any validation fails
6. Executes the wrapped function if all validations pass

## Adding New Features

To add a new feature flag that can be validated:

1. Add it to `default_academy_features()` in `breathecode/admissions/models.py`:

```python
def default_academy_features():
    return {
        "features": {
            # ... existing features
            "my_new_feature": False,  # Add your feature here
        },
    }
```

2. Use it in your view:

```python
@capable_of('some_capability')
@academy_has_feature('my_new_feature')
def my_view(self, request, academy_id=None):
    pass
```

## Real-World Example

### Course Resale Feature

```python
class CourseResaleSettingsView(APIView):
    @capable_of("crud_course")
    @academy_has_feature("reseller", require_white_labeled=True)
    def post(self, request, course_slug=None, academy_id=None):
        """
        Create resale settings for a course.
        
        Requirements:
        - User must have 'crud_course' capability
        - Academy must have 'reseller' feature enabled
        - Academy must be white labeled
        """
        # Implementation here
        pass
```

## Best Practices

1. **Always use with `@capable_of`**: Don't use this decorator alone
2. **Order matters**: Place `@capable_of` before `@academy_has_feature`
3. **Feature naming**: Use descriptive feature names that match `academy_features` structure
4. **Error handling**: The decorator handles all validation errors automatically
5. **Documentation**: Document feature requirements in view docstrings

## Related Files

- Decorator: `breathecode/utils/decorators/academy_has_feature.py`
- Helper: `breathecode/admissions/utils/academy_features.py`
- Model: `breathecode/admissions/models.py` (Academy model and `default_academy_features()`)
- Tests: `breathecode/utils/decorators/tests/test_academy_has_feature.py`

## Comparison with `@capable_of`

| Feature | `@capable_of` | `@academy_has_feature` |
|---------|---------------|------------------------|
| Validates | User permissions (role capabilities) | Academy features |
| Injects | `academy_id` into kwargs | Nothing (uses existing `academy_id`) |
| Use case | User authorization | Feature availability |
| Can be used alone | ✅ Yes | ❌ No (requires `@capable_of`) |
| Order | First | Second |

## Migration from Manual Validation

### Before (manual validation in serializer/view):

```python
def post(self, request, academy_id=None):
    academy = Academy.objects.get(id=academy_id)
    
    if not academy.white_labeled:
        raise ValidationException("Not white labeled")
    
    if not has_feature_flag(academy, 'reseller'):
        raise ValidationException("No reseller feature")
    
    # ... rest of logic
```

### After (using decorator):

```python
@capable_of('crud_course')
@academy_has_feature('reseller', require_white_labeled=True)
def post(self, request, academy_id=None):
    # All validations handled by decorator
    # ... rest of logic
```

## Benefits

1. **DRY Principle**: Avoid repeating validation logic across views
2. **Consistency**: Standardized error messages and status codes
3. **Readability**: Clear declaration of feature requirements
4. **Maintainability**: Centralized validation logic
5. **Type Safety**: Decorator validates at runtime before view execution

