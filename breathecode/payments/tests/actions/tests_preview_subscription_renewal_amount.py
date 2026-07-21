"""Tests for preview_subscription_renewal_amount."""

from datetime import timedelta

from django.utils import timezone

from breathecode.payments.actions import (
    get_amount_by_chosen_period,
    get_bag_from_subscription,
    get_discounted_price,
    preview_subscription_renewal_amount,
)
from breathecode.payments.models import Bag
from breathecode.payments.serializers import GetSubscriptionSerializer

from ..mixins import PaymentsTestCase


class PreviewSubscriptionRenewalAmountTestSuite(PaymentsTestCase):
    def test_returns_none_without_invoices(self):
        model = self.bc.database.create(
            subscription={
                "next_payment_at": timezone.now() + timedelta(days=30),
            },
            plan={
                "is_renewable": True,
                "price_per_month": 10.0,
                "price_per_year": 100.0,
                "trial_duration": 0,
            },
        )
        model.subscription.plans.add(model.plan)

        self.assertIsNone(preview_subscription_renewal_amount(model.subscription))

    def test_matches_renewal_pricing_and_does_not_persist_bags(self):
        plan = {
            "is_renewable": True,
            "time_of_life": 0,
            "time_of_life_unit": None,
            "price_per_month": 10.0,
            "price_per_quarter": 30.0,
            "price_per_half": 60.0,
            "price_per_year": 100.0,
            "trial_duration": 0,
        }
        bag = {
            "chosen_period": "YEAR",
            "amount_per_month": 10.0,
            "amount_per_quarter": 30.0,
            "amount_per_half": 60.0,
            "amount_per_year": 100.0,
        }
        model = self.bc.database.create(
            subscription={
                "pay_every": 1,
                "pay_every_unit": "YEAR",
                "next_payment_at": timezone.now() + timedelta(days=30),
            },
            invoice={"amount": 191.996, "status": "FULFILLED", "paid_at": timezone.now() - timedelta(days=365)},
            plan=plan,
            bag=bag,
        )
        model.subscription.plans.add(model.plan)
        model.subscription.invoices.add(model.invoice)
        model.invoice.bag = model.bag
        model.invoice.save()

        bags_before = Bag.objects.count()
        renewal_bags_before = Bag.objects.filter(status="RENEWAL").count()

        preview = preview_subscription_renewal_amount(model.subscription)

        self.assertEqual(Bag.objects.count(), bags_before)
        self.assertEqual(Bag.objects.filter(status="RENEWAL").count(), renewal_bags_before)

        bag = get_bag_from_subscription(model.subscription)
        expected = get_amount_by_chosen_period(bag, bag.chosen_period, "en")
        coupons = list(bag.coupons.all())
        if coupons:
            expected = get_discounted_price(expected, coupons)

        self.assertEqual(preview, float(expected))
        self.assertEqual(preview, 100.0)

    def test_serializer_exposes_next_renewal_amount_and_currency(self):
        plan = {
            "is_renewable": True,
            "time_of_life": 0,
            "time_of_life_unit": None,
            "price_per_month": 10.0,
            "price_per_quarter": 30.0,
            "price_per_half": 60.0,
            "price_per_year": 479.99,
            "trial_duration": 0,
        }
        bag = {
            "chosen_period": "YEAR",
            "amount_per_month": 10.0,
            "amount_per_quarter": 30.0,
            "amount_per_half": 60.0,
            "amount_per_year": 191.996,
        }
        model = self.bc.database.create(
            subscription={
                "pay_every": 1,
                "pay_every_unit": "YEAR",
                "next_payment_at": timezone.now() + timedelta(days=30),
            },
            invoice={"amount": 191.996, "status": "FULFILLED", "paid_at": timezone.now() - timedelta(days=30)},
            plan=plan,
            bag=bag,
        )
        model.subscription.plans.add(model.plan)
        model.subscription.invoices.add(model.invoice)
        model.invoice.bag = model.bag
        model.invoice.save()
        model.subscription.currency = model.invoice.currency
        model.subscription.save(update_fields=["currency"])

        bags_before = Bag.objects.count()
        data = GetSubscriptionSerializer(model.subscription).data

        self.assertEqual(data["next_renewal_amount"], 479.99)
        self.assertIsNotNone(data["currency"])
        self.assertEqual(data["currency"]["code"], model.invoice.currency.code)
        self.assertEqual(Bag.objects.count(), bags_before)

    def test_serializer_returns_null_next_renewal_amount_without_invoices(self):
        model = self.bc.database.create(
            subscription={
                "next_payment_at": timezone.now() + timedelta(days=30),
            },
            plan={
                "is_renewable": True,
                "price_per_month": 10.0,
                "trial_duration": 0,
            },
        )
        model.subscription.plans.add(model.plan)

        data = GetSubscriptionSerializer(model.subscription).data
        self.assertIsNone(data["next_renewal_amount"])
