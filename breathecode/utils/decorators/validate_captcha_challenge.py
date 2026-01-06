import logging
import os
from typing import Callable

from rest_framework.views import APIView

from breathecode.services.cloudflare import Turnstile
from breathecode.services.google_cloud import Recaptcha
from breathecode.utils.exceptions import ProgrammingError
from capyc.rest_framework.exceptions import ValidationException

logger = logging.getLogger(__name__)
__all__ = ["validate_captcha_challenge"]


def validate_captcha_challenge(vendor=None):
    """
    Decorator to validate CAPTCHA challenges from Google reCAPTCHA or Cloudflare Turnstile.

    Args:
        vendor: CAPTCHA vendor to use ("google" or "cloudflare"). Defaults to "google" for backward compatibility.

    Usage:
        # Default (Google - backward compatible)
        @validate_captcha_challenge
        def my_view(request):
            ...

        # Explicit Google
        @validate_captcha_challenge(vendor="google")
        def my_view(request):
            ...

        # Cloudflare Turnstile
        @validate_captcha_challenge(vendor="cloudflare")
        def my_view(request):
            ...
    """

    # Handle decorator called without parentheses: @validate_captcha_challenge
    # In this case, vendor will be the function itself (callable)
    if callable(vendor):
        # First argument is the function, so vendor defaults to "google"
        return _create_wrapper("google", vendor)

    # Handle decorator called with parentheses: @validate_captcha_challenge(vendor="cloudflare")
    def decorator(func: Callable):
        # Use provided vendor or default to "google"
        selected_vendor = vendor if vendor is not None else "google"
        return _create_wrapper(selected_vendor, func)

    return decorator


def _create_wrapper(vendor: str, function: Callable) -> Callable:
    """Create a wrapper function for the CAPTCHA validation decorator."""

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

            token = data.get("token")
            if token is None:
                raise ValidationException("Missing CAPTCHA token", code=400)

            # Validate based on selected vendor
            if vendor == "cloudflare":
                secret_key = os.getenv("CLOUDFLARE_TURNSTILE_SECRET_KEY", "")
                site_key = os.getenv("CLOUDFLARE_TURNSTILE_SITE_KEY", "")

                if not secret_key:
                    logger.warning("CLOUDFLARE_TURNSTILE_SECRET_KEY not configured")
                    raise ValidationException("Cloudflare Turnstile secret key is not configured", code=500)

                turnstile = Turnstile()
                turnstile.verify_token(secret_key=secret_key, token=token)

            elif vendor == "google":
                project_id = os.getenv("GOOGLE_PROJECT_ID", "")
                site_key = os.getenv("GOOGLE_CAPTCHA_KEY", "")

                recaptcha = Recaptcha()
                recaptcha.create_assessment_v2(project_id=project_id, recaptcha_site_key=site_key, token=token)

                # TEMPORALILY DISABLING SCORE ANALYSIS
                # Google Recaptcha needs to work some time to learn about the site's traffic
                # It may be enabled in the future, though it is not recommended to just block the traffic based on punctuation
                # read more: https://cloud.google.com/recaptcha-enterprise/docs/interpret-assessment-website?authuser=1&hl=es&_gl=1*1yex6v*_ga*MzE4Mjc4NTMzLjE3MDAxNzgzMDU.*_ga_WH2QY8WWF5*MTcxNTk2NTkzOS41NC4xLjE3MTU5NjYyNDMuMC4wLjA.&_ga=2.84385883.-318278533.1700178305#interpret_scores

                # if (response.risk_analysis.score < 0.6):
                #     raise ValidationException('The action was denied because it was considered suspicious', code=429)

            else:
                raise ProgrammingError(f"Unknown CAPTCHA vendor: {vendor}. Supported vendors: 'google', 'cloudflare'")

        except IndexError:
            raise ProgrammingError("Missing request information, use this decorator with DRF View")

        return function(*args, **kwargs)

    return wrapper
