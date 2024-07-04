"""
Test /answer/:id
"""

import math
import random
from django.utils import timezone
from breathecode.provisioning.tasks import calculate_bill_amounts
import logging
from unittest.mock import patch, MagicMock, call
from breathecode.payments.services.stripe import Stripe
from breathecode.monitoring import signals as monitoring_signals
from breathecode.tests.mixins.legacy import LegacyAPITestCase

UTC_NOW = timezone.now()
STRIPE_ID = f"price_{random.randint(1000, 9999)}"


def apply_get_env(configuration={}):

    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


class TestMakeBills(LegacyAPITestCase):
    # Given: 1 StripeEvent
    # When: with no bills and event type isn't checkout.session.completed
    # Then: nothing happens

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_nothing(self, enable_signals):
        enable_signals()

        model = self.bc.database.create(stripe_event=1)
        db = self.bc.format.to_dict(model.stripe_event)
        monitoring_signals.stripe_webhook.send(instance=model.stripe_event, sender=model.stripe_event.__class__)

        self.assertEqual(
            self.bc.database.list_of("monitoring.StripeEvent"),
            [
                {
                    **db,
                    "status_texts": {},
                },
            ],
        )
        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningBill"), [])

    # Given: 1 StripeEvent
    # When: with no bills and event type is checkout.session.completed, bad context
    # Then: nothing happens

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_bad_context(self, enable_signals):
        enable_signals()

        stripe_event = {"type": "checkout.session.completed"}
        model = self.bc.database.create(stripe_event=stripe_event)
        db = self.bc.format.to_dict(model.stripe_event)
        monitoring_signals.stripe_webhook.send(instance=model.stripe_event, sender=model.stripe_event.__class__)

        self.assertEqual(
            self.bc.database.list_of("monitoring.StripeEvent"),
            [
                {
                    **db,
                    "status": "ERROR",
                    "status_texts": {
                        "provisioning.bill_was_paid": "Invalid context",
                    },
                },
            ],
        )
        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningBill"), [])

    # Given: 1 StripeEvent
    # When: with no bills and event type is checkout.session.completed
    # Then: nothing happens

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_no_bills(self, enable_signals):
        enable_signals()

        stripe_event = {
            "type": "checkout.session.completed",
            "data": {
                "payment_link": STRIPE_ID,
            },
        }
        model = self.bc.database.create(stripe_event=stripe_event)
        db = self.bc.format.to_dict(model.stripe_event)
        monitoring_signals.stripe_webhook.send(instance=model.stripe_event, sender=model.stripe_event.__class__)

        self.assertEqual(
            self.bc.database.list_of("monitoring.StripeEvent"),
            [
                {
                    **db,
                    "status_texts": {},
                    "status": "DONE",
                },
            ],
        )
        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningBill"), [])

    # Given: 1 StripeEvent, 2 ProvisioningBills
    # When: with bills and event type is checkout.session.completed
    # Then: nothing happens

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_not_related_bills(self, enable_signals):
        enable_signals()

        stripe_event = {
            "type": "checkout.session.completed",
            "data": {
                "payment_link": STRIPE_ID,
            },
        }
        model = self.bc.database.create(stripe_event=stripe_event, provisioning_bill=2)
        db = self.bc.format.to_dict(model.stripe_event)
        monitoring_signals.stripe_webhook.send(instance=model.stripe_event, sender=model.stripe_event.__class__)

        self.assertEqual(
            self.bc.database.list_of("monitoring.StripeEvent"),
            [
                {
                    **db,
                    "status_texts": {},
                    "status": "DONE",
                },
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            self.bc.format.to_dict(model.provisioning_bill),
        )

    # Given: 1 StripeEvent, 2 ProvisioningBills
    # When: with bills and event type is checkout.session.completed
    # Then: nothing happens

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_a_related_bill(self, enable_signals):
        enable_signals()

        stripe_event = {
            "type": "checkout.session.completed",
            "data": {
                "payment_link": STRIPE_ID,
            },
        }
        provisioning_bill = {"stripe_id": STRIPE_ID}
        model = self.bc.database.create(stripe_event=stripe_event, provisioning_bill=provisioning_bill)
        db = self.bc.format.to_dict(model.stripe_event)
        monitoring_signals.stripe_webhook.send(instance=model.stripe_event, sender=model.stripe_event.__class__)

        self.assertEqual(
            self.bc.database.list_of("monitoring.StripeEvent"),
            [
                {
                    **db,
                    "status": "DONE",
                    "status_texts": {},
                },
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                {
                    **self.bc.format.to_dict(model.provisioning_bill),
                    "status": "PAID",
                    "paid_at": model.stripe_event.created_at,
                },
            ],
        )
