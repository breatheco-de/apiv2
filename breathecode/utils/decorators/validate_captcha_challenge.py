import logging
import os

from rest_framework.views import APIView

from breathecode.services.google_cloud import Recaptcha
from breathecode.utils.exceptions import ProgrammingError
from capyc.rest_framework.exceptions import ValidationException

logger = logging.getLogger(__name__)
__all__ = ["validate_captcha_challenge"]


def validate_captcha_challenge(function):

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
            if token is None:
                raise ValidationException("Missing ReCaptcha Token", code=400)

            recaptcha = Recaptcha()
            recaptcha.create_assessment_v2(project_id=project_id, recaptcha_site_key=site_key, token=token)

            # TEMPORALILY DISABLING SCORE ANALYSIS
            # Google Recaptcha needs to work some time to learn about the site's traffic
            # It may be enabled in the future, though it is not recommended to just block the traffic based on punctuation
            # read more: https://cloud.google.com/recaptcha-enterprise/docs/interpret-assessment-website?authuser=1&hl=es&_gl=1*1yex6v*_ga*MzE4Mjc4NTMzLjE3MDAxNzgzMDU.*_ga_WH2QY8WWF5*MTcxNTk2NTkzOS41NC4xLjE3MTU5NjYyNDMuMC4wLjA.&_ga=2.84385883.-318278533.1700178305#interpret_scores

            # if (response.risk_analysis.score < 0.6):
            #     raise ValidationException('The action was denied because it was considered suspicious', code=429)

        except IndexError:
            raise ProgrammingError("Missing request information, use this decorator with DRF View")

        return function(*args, **kwargs)

    return wrapper
