import logging
import os

from rest_framework.views import APIView

from breathecode.services.google_cloud import Recaptcha
from breathecode.utils.exceptions import ProgrammingError
from capyc.rest_framework.exceptions import ValidationException

logger = logging.getLogger(__name__)
__all__ = ["validate_captcha"]


def validate_captcha(function):

    def wrapper(*args, **kwargs):
        try:
            if hasattr(args[0], "__class__") and isinstance(args[0], APIView):
                data = args[1].data.copy()

            elif hasattr(args[0], "user") and hasattr(args[0].user, "has_perm"):
                data = args[0].data.copy()

            # websocket support
            elif hasattr(args[0], "ws_request"):
                data = args[0].data.copy()

            else:
                raise IndexError()

            apply_captcha = os.getenv("APPLY_CAPTCHA", "FALSE").lower()

            if not apply_captcha or apply_captcha == "false":
                return function(*args, **kwargs)

            project_id = os.getenv("GOOGLE_PROJECT_ID", "")
            site_key = os.getenv("GOOGLE_CAPTCHA_KEY", "")

            token = data["token"] if "token" in data else None

            recaptcha_action = data["action"] if "action" in data else None

            recaptcha = Recaptcha()
            response = recaptcha.create_assessment(
                project_id=project_id, recaptcha_site_key=site_key, token=token, recaptcha_action=recaptcha_action
            )

            if response.risk_analysis.score < 0.8:
                raise ValidationException("The action was denied because it was considered suspicious", code=429)

        except IndexError:
            raise ProgrammingError("Missing request information, use this decorator with DRF View")

        return function(*args, **kwargs)

    return wrapper
