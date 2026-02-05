"""
Unit tests for create_invited_plan_financing_for_user action.
"""

from unittest.mock import MagicMock, patch

from capyc.rest_framework.exceptions import ValidationException

from breathecode.payments.actions import create_invited_plan_financing_for_user
from breathecode.payments.models import Bag, Invoice

from ..mixins import PaymentsTestCase


class CreateInvitedPlanFinancingForUserTestSuite(PaymentsTestCase):
    """Tests for create_invited_plan_financing_for_user."""

    @patch("breathecode.payments.tasks.build_plan_financing.delay", MagicMock())
    def test_creates_bag_and_invoice_and_schedules_task(self):
        """Creates Bag, Invoice, and calls build_plan_financing.delay."""
        model = self.bc.database.create(
            user=1,
            academy=1,
            currency=1,
            cohort={"available_as_saas": True},
            cohort_set=1,
            cohort_set_cohort=1,
            financing_option={"how_many_months": 1, "monthly_price": 0},
            plan=1,
        )
        create_invited_plan_financing_for_user(
            user=model.user,
            plan=model.plan,
            academy=model.academy,
            cohort=model.cohort,
            payment_method=None,
            author=None,
            lang="en",
        )
        bags = Bag.objects.filter(user=model.user, type="INVITED")
        self.assertEqual(bags.count(), 1)
        bag = bags.first()
        self.assertEqual(bag.status, "PAID")
        self.assertEqual(bag.how_many_installments, 1)
        self.assertIn(model.plan, bag.plans.all())
        invoices = Invoice.objects.filter(bag=bag)
        self.assertEqual(invoices.count(), 1)
        invoice = invoices.first()
        self.assertEqual(invoice.status, "FULFILLED")
        self.assertEqual(invoice.amount, 0)
        from breathecode.payments import tasks

        tasks.build_plan_financing.delay.assert_called_once_with(bag.id, invoice.id, is_free=True)

    def test_plan_cohort_mismatch_raises(self):
        """Raises when plan's cohort_set does not include the cohort."""
        model = self.bc.database.create(
            user=1,
            academy=1,
            currency=1,
            cohort=1,
            cohort_set=1,
            cohort_set_cohort=1,
            financing_option={"how_many_months": 1, "monthly_price": 0},
            plan=1,
        )
        cohort2 = self.bc.database.create(cohort=1, academy=model.academy).cohort
        with self.assertRaises(ValidationException) as cm:
            create_invited_plan_financing_for_user(
                user=model.user,
                plan=model.plan,
                academy=model.academy,
                cohort=cohort2,
                payment_method=None,
                author=None,
                lang="en",
            )
        self.assertEqual(getattr(cm.exception, "slug", None), "plan-cohort-mismatch")

    def test_academy_without_main_currency_raises(self):
        """Raises when academy has no main_currency."""
        model = self.bc.database.create(
            user=1,
            academy=1,
            currency=1,
            cohort={"available_as_saas": True},
            cohort_set=1,
            cohort_set_cohort=1,
            financing_option={"how_many_months": 1, "monthly_price": 0},
            plan=1,
        )
        model.academy.main_currency = None
        model.academy.save(update_fields=["main_currency_id"])
        with self.assertRaises(ValidationException) as cm:
            create_invited_plan_financing_for_user(
                user=model.user,
                plan=model.plan,
                academy=model.academy,
                cohort=model.cohort,
                payment_method=None,
                author=None,
                lang="en",
            )
        self.assertEqual(getattr(cm.exception, "slug", None), "academy-main-currency-required")

    def test_plan_without_one_month_financing_option_raises(self):
        """Raises when plan has no financing_option with how_many_months=1."""
        model = self.bc.database.create(
            user=1,
            academy=1,
            currency=1,
            cohort={"available_as_saas": True},
            cohort_set=1,
            cohort_set_cohort=1,
            financing_option={"how_many_months": 6, "monthly_price": 100},
            plan=1,
        )
        with self.assertRaises(ValidationException) as cm:
            create_invited_plan_financing_for_user(
                user=model.user,
                plan=model.plan,
                academy=model.academy,
                cohort=model.cohort,
                payment_method=None,
                author=None,
                lang="en",
            )
        self.assertEqual(getattr(cm.exception, "slug", None), "plan-without-one-month-financing-option")
