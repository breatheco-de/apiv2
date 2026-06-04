from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException

__all__ = ["validate_conversion_info"]


def validate_conversion_info(conversion_info, lang):
    if conversion_info is not None:
        if not isinstance(conversion_info, dict):
            raise ValidationException(
                translation(
                    lang,
                    en="conversion_info must be a JSON object",
                    es="conversion_info debe ser un objeto de JSON",
                    slug="conversion-info-json-type",
                ),
                code=400,
            )

        expected_keys = [
            "utm_placement",
            "utm_referrer",
            "utm_medium",
            "utm_source",
            "utm_term",
            "utm_content",
            "utm_campaign",
            "conversion_url",
            "landing_url",
            "user_agent",
            "plan",
            "coupon",
            "ref",
            "location",
            "translations",
            "internal_cta_placement",
            "internal_cta_content",
            "internal_cta_campaign",
            "sale",
        ]

        expected_sale_keys = [
            "is_offline_sale",
            "contract_id",
            "deal_expected_value",
            "deal_final_price",
            "deal_currency",
            "deal_discount",
            "how_did_you_hear_about_us",
            "deal_owner_name",
            "deal_owner_id",
            "how_many_installments",
            "installment_value",
            "grace_period_months",
            "plan_id",
            "payment_method_id",
        ]

        for key in conversion_info.keys():
            if key not in expected_keys:
                raise ValidationException(
                    translation(
                        lang,
                        en=f"Invalid key {key} was provided in the conversion_info",
                        es=f"Se agrego una clave inválida {key} en el conversion_info",
                        slug="conversion-info-invalid-key",
                    ),
                    code=400,
                )

        sale = conversion_info.get("sale", None)
        if sale is not None:
            if not isinstance(sale, dict):
                raise ValidationException(
                    translation(
                        lang,
                        en="sale must be a JSON object inside conversion_info",
                        es="sale debe ser un objeto JSON dentro de conversion_info",
                        slug="conversion-info-sale-json-type",
                    ),
                    code=400,
                )

            for sale_key in sale.keys():
                if sale_key not in expected_sale_keys:
                    raise ValidationException(
                        translation(
                            lang,
                            en=f"Invalid key {sale_key} was provided in conversion_info.sale",
                            es=f"Se agrego una clave inválida {sale_key} en conversion_info.sale",
                            slug="conversion-info-sale-invalid-key",
                        ),
                        code=400,
                    )
