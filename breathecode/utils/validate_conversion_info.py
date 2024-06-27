from breathecode.utils.i18n import translation
from capyc.rest_framework.exceptions import PaymentException, ValidationException

__all__ = ['validate_conversion_info']


def validate_conversion_info(conversion_info, lang):
    if conversion_info is not None:
        if not isinstance(conversion_info, dict):
            raise ValidationException(translation(lang,
                                                  en='conversion_info must be a JSON object',
                                                  es='conversion_info debe ser un objeto de JSON',
                                                  slug='conversion-info-json-type'),
                                      code=400)

        expected_keys = [
            'utm_placement', 'utm_medium', 'utm_source', 'utm_term', 'utm_content', 'utm_campaign', 'conversion_url',
            'landing_url', 'user_agent', 'plan', 'location', 'translations', 'internal_cta_placement',
            'internal_cta_content', 'internal_cta_campaign'
        ]

        for key in conversion_info.keys():
            if key not in expected_keys:
                raise ValidationException(translation(lang,
                                                      en=f'Invalid key {key} was provided in the conversion_info',
                                                      es=f'Se agrego una clave inválida {key} en el conversion_info',
                                                      slug='conversion-info-invalid-key'),
                                          code=400)
