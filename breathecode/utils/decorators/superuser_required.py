from functools import wraps
from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException

def superuser_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        # Support both APIView methods and function-based views
        request = args[1] if hasattr(args[0], "__class__") else args[0]
        lang = getattr(request.user, 'lang', 'en')
        if not getattr(request.user, 'is_superuser', False):
            raise ValidationException(
                translation(
                    lang,
                    en="Only superusers can perform this action.",
                    es="Solo los superusuarios pueden realizar esta acción.",
                    slug="not-superuser"
                ),
                code=403
            )
        return function(*args, **kwargs)
    return wrapper 