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
            financing_option={"how_many_months": 1, "monthly_price": 1},
            plan={"is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH", "status": "ACTIVE"},
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
        self.assertEqual(invoice.amount, 1)
        from breathecode.payments import tasks

        tasks.build_plan_financing.delay.assert_called_once_with(
            bag.id,
            invoice.id,
            is_free=False,
            cohorts=[model.cohort.slug],
        )

    @patch("breathecode.payments.tasks.build_plan_financing.delay", MagicMock())
    def test_joined_cohorts_passes_all_slugs_to_build(self):
        cohort_kw = {"available_as_saas": True}
        model = self.bc.database.create(
            user=1,
            academy=1,
            currency=1,
            cohort=(2, cohort_kw),
            cohort_set=1,
            cohort_set_cohort=[{"cohort_id": 1, "cohort_set_id": 1}, {"cohort_id": 2, "cohort_set_id": 1}],
            financing_option={"how_many_months": 1, "monthly_price": 1},
            plan={"is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH", "status": "ACTIVE"},
        )
        c0, c1 = model.cohort
        create_invited_plan_financing_for_user(
            user=model.user,
            plan=model.plan,
            academy=model.academy,
            cohort=c0,
            joined_cohorts=[c1],
            payment_method=None,
            author=None,
            lang="en",
        )
        from breathecode.payments import tasks

        bag = Bag.objects.filter(user=model.user, type="INVITED").first()
        invoice = Invoice.objects.filter(bag=bag).first()
        tasks.build_plan_financing.delay.assert_called_once_with(
            bag.id,
            invoice.id,
            is_free=False,
            cohorts=[c0.slug, c1.slug],
        )

    @patch("breathecode.payments.tasks.build_plan_financing.delay", MagicMock())
    def test_without_cohort_creates_financing_without_joined_slugs(self):
        """Staff can assign financing with no cohort; build_plan_financing gets no cohorts list."""
        model = self.bc.database.create(
            user=1,
            academy=1,
            currency=1,
            cohort={"available_as_saas": True},
            cohort_set=1,
            cohort_set_cohort=1,
            financing_option={"how_many_months": 1, "monthly_price": 1},
            plan={"is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH", "status": "ACTIVE"},
        )
        create_invited_plan_financing_for_user(
            user=model.user,
            plan=model.plan,
            academy=model.academy,
            cohort=None,
            payment_method=None,
            author=None,
            lang="en",
        )
        from breathecode.payments import tasks

        bag = Bag.objects.filter(user=model.user, type="INVITED").first()
        invoice = Invoice.objects.filter(bag=bag).first()
        tasks.build_plan_financing.delay.assert_called_once_with(bag.id, invoice.id, is_free=False)

    @patch("breathecode.payments.tasks.build_plan_financing.delay", MagicMock())
    def test_unique_payment_negotiated_amount_sets_invoice_without_initial_payment_kwarg(self):
        model = self.bc.database.create(
            user=1,
            academy=1,
            currency=1,
            cohort={"available_as_saas": True},
            cohort_set=1,
            cohort_set_cohort=1,
            financing_option={"how_many_months": 1, "monthly_price": 9500},
            plan={"is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH", "status": "ACTIVE"},
        )
        create_invited_plan_financing_for_user(
            user=model.user,
            plan=model.plan,
            academy=model.academy,
            cohort=model.cohort,
            payment_method=None,
            author=None,
            lang="en",
            unique_payment_negotiated_amount=8500,
            initial_payment_notes="One-payment negotiated by staff",
        )
        bag = Bag.objects.filter(user=model.user, type="INVITED").first()
        invoice = Invoice.objects.filter(bag=bag).first()
        self.assertEqual(invoice.amount, 8500)
        self.assertEqual(
            invoice.amount_breakdown["plans"][model.plan.slug]["type"],
            "UNIQUE_PAYMENT_NEGOTIATED",
        )
        from breathecode.payments import tasks

        kw = tasks.build_plan_financing.delay.call_args.kwargs
        self.assertEqual(kw.get("principal_amount"), 8500)
        self.assertEqual(kw.get("initial_payment_notes"), "Note made by user 1: One-payment negotiated by staff")
        self.assertNotIn("initial_payment_amount", kw)

    @patch("breathecode.payments.tasks.build_plan_financing.delay", MagicMock())
    def test_zero_initial_payment_schedules_build_with_initial_payment_kwarg(self):
        model = self.bc.database.create(
            user=1,
            academy=1,
            currency=1,
            cohort={"available_as_saas": True},
            cohort_set=1,
            cohort_set_cohort=1,
            financing_option={"how_many_months": 1, "monthly_price": 1200},
            plan={"is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH", "status": "ACTIVE"},
        )

        create_invited_plan_financing_for_user(
            user=model.user,
            plan=model.plan,
            academy=model.academy,
            cohort=model.cohort,
            payment_method=None,
            author=model.user,
            lang="en",
            initial_payment_amount=0,
            initial_payment_notes="Prework paid at course start",
            grace_period_duration=2,
            grace_period_duration_unit="WEEK",
        )

        bag = Bag.objects.filter(user=model.user, type="INVITED").first()
        invoice = Invoice.objects.filter(bag=bag).first()
        self.assertEqual(invoice.amount, 0)

        from breathecode.payments import tasks

        tasks.build_plan_financing.delay.assert_called_once_with(
            bag.id,
            invoice.id,
            is_free=False,
            conversion_info=None,
            cohorts=[model.cohort.slug],
            grace_period_duration=2,
            grace_period_duration_unit="WEEK",
            initial_payment_notes="Note made by user 1: Prework paid at course start",
            principal_amount=1200,
            initial_payment_amount=0,
        )

    @patch("breathecode.payments.tasks.build_plan_financing.delay", MagicMock())
    def test_unique_payment_negotiated_amount_requires_notes_for_one_payment(self):
        model = self.bc.database.create(
            user=1,
            academy=1,
            currency=1,
            cohort={"available_as_saas": True},
            cohort_set=1,
            cohort_set_cohort=1,
            financing_option={"how_many_months": 1, "monthly_price": 9500},
            plan={"is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH", "status": "ACTIVE"},
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
                unique_payment_negotiated_amount=8500,
            )
        self.assertEqual(getattr(cm.exception, "slug", None), "negotiated-amount-notes-required")

    def test_plan_cohort_mismatch_raises(self):
        """Raises when plan's cohort_set does not include the cohort."""
        model = self.bc.database.create(
            user=1,
            academy=1,
            currency=1,
            cohort={"available_as_saas": True},
            cohort_set=1,
            cohort_set_cohort=1,
            financing_option={"how_many_months": 1, "monthly_price": 1},
            plan={"is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH", "status": "ACTIVE"},
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
            financing_option={"how_many_months": 1, "monthly_price": 1},
            plan={"is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH", "status": "ACTIVE"},
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

    def test_plan_draft_status_raises(self):
        """Raises when plan status is DRAFT."""
        model = self.bc.database.create(
            user=1,
            academy=1,
            currency=1,
            cohort={"available_as_saas": True},
            cohort_set=1,
            cohort_set_cohort=1,
            financing_option={"how_many_months": 1, "monthly_price": 1},
            plan={"is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH", "status": "ACTIVE"},
        )
        from breathecode.payments.models import Plan

        model.plan.status = Plan.Status.DRAFT
        model.plan.save(update_fields=["status"])
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
        self.assertEqual(getattr(cm.exception, "slug", None), "plan-draft-not-assignable")

    def test_plan_without_default_installment_financing_option_raises(self):
        """Raises when plan has no financing_option for default how_many_installments=1."""
        model = self.bc.database.create(
            user=1,
            academy=1,
            currency=1,
            cohort={"available_as_saas": True},
            cohort_set=1,
            cohort_set_cohort=1,
            financing_option={"how_many_months": 6, "monthly_price": 100},
            plan={"is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH", "status": "ACTIVE"},
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
        self.assertEqual(getattr(cm.exception, "slug", None), "financing-option-not-found")
