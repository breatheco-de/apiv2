#!/usr/bin/env python
"""
Alert when a reseller academy doesn't have Stripe payment credentials configured
"""

# flake8: noqa: F821

from breathecode.payments.models import AcademyPaymentSettings
from breathecode.utils import ScriptNotification

if academy.status == "ACTIVE" and academy.reseller:
    payment_settings = AcademyPaymentSettings.objects.filter(academy__id=academy.id).first()

    missing_fields = []

    if payment_settings is None:
        missing_fields.append("AcademyPaymentSettings not configured")
    else:
        if not payment_settings.stripe_api_key or payment_settings.stripe_api_key.strip() == "":
            missing_fields.append("Stripe API Key")
        if not payment_settings.stripe_webhook_secret or payment_settings.stripe_webhook_secret.strip() == "":
            missing_fields.append("Stripe Webhook Secret")
        if not payment_settings.stripe_publishable_key or payment_settings.stripe_publishable_key.strip() == "":
            missing_fields.append("Stripe Publishable Key")

    if missing_fields:
        btn_url = f"https://github.com/breatheco-de/apiv2/blob/main/docs/payments/how-to-configure-stripe.md"

        missing_list = "\n".join([f"• {field}" for field in missing_fields])

        raise ScriptNotification(
            f"Academy {academy.name} is configured as a reseller but the following Stripe credentials or requirements are missing:\n\n{missing_list}",
            status="CRITICAL",
            title=f"Stripe credentials missing for {academy.name}",
            slug="reseller-missing-stripe-credentials",
            btn_url=btn_url,
            btn_label="How to configure Stripe for your academy",
        )

print(f"{academy.name} has complete Stripe credentials configured")
