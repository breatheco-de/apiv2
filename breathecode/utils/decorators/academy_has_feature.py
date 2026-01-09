"""
Decorator to validate academy feature flags.
Similar to capable_of but for academy_features validation.
"""

from functools import wraps

from asgiref.sync import sync_to_async
from capyc.rest_framework.exceptions import ValidationException
from rest_framework.views import APIView

from breathecode.admissions.models import Academy
from breathecode.admissions.utils.academy_features import has_feature_flag
from breathecode.utils.exceptions import ProgrammingError

__all__ = ["academy_has_feature", "aacademy_has_feature"]


def academy_has_feature(*required_features, require_white_labeled=False):
    """
    Decorator to validate that an academy has specific feature flags enabled.
    
    This decorator should be used in combination with @capable_of to ensure
    the user has the right permissions and the academy has the required features.
    
    Args:
        *required_features: One or more feature flag names (e.g., 'reseller', 'allow_events')
        require_white_labeled: If True, also validates that academy.white_labeled=True
        
    Usage:
        @capable_of('crud_course')
        @academy_has_feature('reseller', require_white_labeled=True)
        def post(self, request, academy_id=None):
            # This will only execute if:
            # 1. User has 'crud_course' capability
            # 2. Academy has 'reseller' feature enabled
            # 3. Academy is white labeled
            pass
            
    Raises:
        ValidationException: If academy doesn't have required features
        ProgrammingError: If used incorrectly
    """

    def decorator(function):

        @wraps(function)
        def wrapper(*args, **kwargs):
            if not required_features:
                raise ProgrammingError("At least one feature flag must be specified")

            # Extract academy_id from kwargs (should be set by capable_of)
            academy_id = kwargs.get("academy_id")
            if not academy_id:
                raise ProgrammingError(
                    "academy_id not found in kwargs. "
                    "Use @capable_of before @academy_has_feature to inject academy_id"
                )

            # Get academy instance
            academy = Academy.objects.filter(id=academy_id).first()
            if not academy:
                raise ValidationException(
                    "Academy not found",
                    slug="academy-not-found",
                    code=404,
                )

            # Validate white_labeled requirement
            if require_white_labeled and academy.white_labeled is False:
                raise ValidationException(
                    "This feature requires a white labeled academy",
                    slug="academy-not-white-labeled",
                    code=403,
                )

            # Validate each required feature
            for feature in required_features:
                if has_feature_flag(academy, feature, default=False) is False:
                    raise ValidationException(
                        f"Academy does not have the required feature: {feature}",
                        slug=f"academy-feature-{feature}-not-enabled",
                        code=403,
                    )

            # All validations passed, execute the function
            return function(*args, **kwargs)

        return wrapper

    return decorator


def aacademy_has_feature(*required_features, require_white_labeled=False):
    """
    Async version of academy_has_feature decorator.
    
    This decorator should be used with async views in combination with @acapable_of.
    
    Usage:
        @acapable_of('crud_course')
        @aacademy_has_feature('reseller', require_white_labeled=True)
        async def post(self, request, academy_id=None):
            pass
    """

    def decorator(function):

        @wraps(function)
        async def wrapper(*args, **kwargs):
            if not required_features:
                raise ProgrammingError("At least one feature flag must be specified")

            # Extract academy_id from kwargs (should be set by acapable_of)
            academy_id = kwargs.get("academy_id")
            if not academy_id:
                raise ProgrammingError(
                    "academy_id not found in kwargs. "
                    "Use @acapable_of before @aacademy_has_feature to inject academy_id"
                )

            # Get academy instance (async)
            academy = await sync_to_async(Academy.objects.filter(id=academy_id).first)()
            if not academy:
                raise ValidationException(
                    "Academy not found",
                    slug="academy-not-found",
                    code=404,
                )

            # Validate white_labeled requirement
            if require_white_labeled and academy.white_labeled is False:
                raise ValidationException(
                    "This feature requires a white labeled academy",
                    slug="academy-not-white-labeled",
                    code=403,
                )

            # Validate each required feature (async)
            for feature in required_features:
                feature_enabled = await sync_to_async(has_feature_flag)(academy, feature, default=False)
                if feature_enabled is False:
                    raise ValidationException(
                        f"Academy does not have the required feature: {feature}",
                        slug=f"academy-feature-{feature}-not-enabled",
                        code=403,
                    )

            # All validations passed, execute the function
            return await function(*args, **kwargs)

        return wrapper

    return decorator

