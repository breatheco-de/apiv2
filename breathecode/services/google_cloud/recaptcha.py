import logging

from google.cloud import recaptchaenterprise_v1
from google.cloud.recaptchaenterprise_v1 import Assessment

from capyc.rest_framework.exceptions import ValidationException

from .credentials import resolve_credentials

logger = logging.getLogger(__name__)

__all__ = ["Recaptcha"]


class Recaptcha:
    """Google Cloud Recaptcha v3"""

    def __init__(self):
        resolve_credentials()

    def create_assessment(
        self, project_id: str, recaptcha_site_key: str, token: str, recaptcha_action: str
    ) -> Assessment:
        """Create an assessment to analyze the risk of a UI action.
        Args:
            project_id: GCloud Project ID
            recaptcha_site_key: Site key obtained by registering a domain/app to use recaptcha services.
            token: The token obtained from the client on passing the recaptchaSiteKey.
            recaptcha_action: Action name corresponding to the token.
        """
        client = recaptchaenterprise_v1.RecaptchaEnterpriseServiceClient()

        # Set the properties of the event to be tracked.
        event = recaptchaenterprise_v1.Event()
        event.site_key = recaptcha_site_key
        event.token = token

        assessment = recaptchaenterprise_v1.Assessment()
        assessment.event = event

        project_name = f"projects/{project_id}"

        # Build the assessment request.
        request = recaptchaenterprise_v1.CreateAssessmentRequest()
        request.assessment = assessment
        request.parent = project_name

        response = client.create_assessment(request)

        # Check if the token is valid.
        if not response.token_properties.valid:
            logger.error(
                "The CreateAssessment call failed because the token was "
                + "invalid for for the following reasons: "
                + str(response.token_properties.invalid_reason)
            )
            raise ValidationException(
                f"Invalid token for the following reasons: {str(response.token_properties.invalid_reason)}", code=400
            )

        # Check if the expected action was executed.
        if response.token_properties.action != recaptcha_action:
            logger.error(
                "The action attribute in your reCAPTCHA tag does" + "not match the action you are expecting to score"
            )
            raise ValidationException(
                "The action attribute in your reCAPTCHA tag does not match the action you are expecting to score",
                code=400,
            )
        else:
            # Get the risk score and the reason(s)
            # For more information on interpreting the assessment,
            # see: https://cloud.google.com/recaptcha-enterprise/docs/interpret-assessment
            for reason in response.risk_analysis.reasons:
                logger.info(reason)
            logger.info("The reCAPTCHA score for this token is: " + str(response.risk_analysis.score))
            # Get the assessment name (id). Use this to annotate the assessment.
            assessment_name = client.parse_assessment_path(response.name).get("assessment")
            logger.info(f"Assessment name: {assessment_name}")
            return response

    def create_assessment_v2(self, project_id: str, recaptcha_site_key: str, token: str) -> Assessment:
        """Create an assessment to analyze the risk of a UI action.
        Args:
            project_id: GCloud Project ID
            recaptcha_site_key: Site key obtained by registering a domain/app to use recaptcha services.
            token: The token obtained from the client on passing the recaptchaSiteKey.
        """
        client = recaptchaenterprise_v1.RecaptchaEnterpriseServiceClient()

        # Set the properties of the event to be tracked.
        event = recaptchaenterprise_v1.Event()
        event.site_key = recaptcha_site_key
        event.token = token

        assessment = recaptchaenterprise_v1.Assessment()
        assessment.event = event

        project_name = f"projects/{project_id}"

        # Build the assessment request.
        request = recaptchaenterprise_v1.CreateAssessmentRequest()
        request.assessment = assessment
        request.parent = project_name

        response = client.create_assessment(request)

        # Check if the token is valid.
        if not response.token_properties.valid:
            from breathecode.utils.validation_exception import ValidationException

            logger.error(
                "The CreateAssessment call failed because the token was "
                + "invalid for for the following reasons: "
                + str(response.token_properties.invalid_reason)
            )
            raise ValidationException(
                f"Invalid token for the following reasons: {str(response.token_properties.invalid_reason)}", code=400
            )

        # Get the risk score and the reason(s)
        # For more information on interpreting the assessment,
        # see: https://cloud.google.com/recaptcha-enterprise/docs/interpret-assessment
        for reason in response.risk_analysis.reasons:
            logger.info(reason)
        logger.info("The reCAPTCHA score for this token is: " + str(response.risk_analysis.score))
        # Get the assessment name (id). Use this to annotate the assessment.
        assessment_name = client.parse_assessment_path(response.name).get("assessment")
        logger.info(f"Assessment name: {assessment_name}")
        return response
