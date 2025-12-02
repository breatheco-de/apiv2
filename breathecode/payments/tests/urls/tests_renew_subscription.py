from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.payments.models import AcademyPaymentSettings, Bag, Invoice, Subscription
from breathecode.payments.tests.mixins import PaymentsTestCase

UTC_NOW = timezone.now()


def format_user_setting(data={}):
    return {
        "id": 1,
        "user_id": 1,
        "main_currency_id": None,
        "lang": "en",
        **data,
    }


class RenewSubscriptionViewTestSuite(PaymentsTestCase):
    def test__post__no_auth(self):
        url = reverse_lazy("payments:renew_subscription")
        response = self.client.post(url)

        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test__post__without_payment_method(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:renew_subscription")
        response = self.client.post(url, {"subscription": 1}, format="json")

        json = response.json()
        expected = {"detail": "payment-method-required", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test__post__without_subscription(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:renew_subscription")
        response = self.client.post(url, {"payment_method": "stripe"}, format="json")

        json = response.json()
        expected = {"detail": "subscription-required", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test__post__subscription_not_found(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:renew_subscription")
        response = self.client.post(url, {"payment_method": "stripe", "subscription": 999}, format="json")

        json = response.json()
        expected = {"detail": "subscription-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test__post__subscription_cancelled(self):
        subscription = {"status": "CANCELLED"}
        model = self.bc.database.create(user=1, subscription=subscription)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:renew_subscription")
        response = self.client.post(url, {"payment_method": "stripe", "subscription": 1}, format="json")

        json = response.json()
        expected = {"detail": "subscription-not-renewable", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test__post__plan_discontinued(self):
        plan = {
            "status": "DISCONTINUED",
            "is_renewable": False,
            "time_of_life": 30,
            "time_of_life_unit": "DAY",
            "trial_duration": 0,
        }
        subscription = {"status": "ACTIVE"}
        model = self.bc.database.create(user=1, subscription=subscription, plan=plan)
        model.subscription.plans.add(model.plan)

        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:renew_subscription")
        response = self.client.post(url, {"payment_method": "stripe", "subscription": 1}, format="json")

        json = response.json()
        expected = {"detail": "plan-discontinued", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test__post__subscription_expired(self):
        subscription = {"status": "ACTIVE", "valid_until": UTC_NOW - timedelta(days=1)}
        model = self.bc.database.create(user=1, subscription=subscription)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:renew_subscription")
        response = self.client.post(url, {"payment_method": "stripe", "subscription": 1}, format="json")

        json = response.json()
        expected = {"detail": "subscription-expired-permanently", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test__post__no_early_renewal_allowed(self):
        plan = {
            "status": "ACTIVE",
            "is_renewable": False,
            "time_of_life": 30,
            "time_of_life_unit": "DAY",
            "trial_duration": 0,
        }
        # Set next_payment_at in the future
        subscription = {"status": "ACTIVE", "next_payment_at": UTC_NOW + timedelta(days=5)}
        model = self.bc.database.create(user=1, academy=1, subscription=subscription, plan=plan)
        model.subscription.plans.add(model.plan)

        # Create payment settings manually
        AcademyPaymentSettings.objects.create(academy=model.academy, early_renewal_window_days=1)

        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:renew_subscription")
        response = self.client.post(url, {"payment_method": "stripe", "subscription": 1}, format="json")

        json = response.json()
        expected = {"detail": "too-early-to-renew", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test__post__already_renewed(self):
        plan = {
            "status": "ACTIVE",
            "is_renewable": False,
            "time_of_life": 30,
            "time_of_life_unit": "DAY",
            "trial_duration": 0,
        }
        subscription = {"status": "ACTIVE", "next_payment_at": UTC_NOW + timedelta(days=5)}
        model = self.bc.database.create(user=1, academy=1, subscription=subscription, plan=plan, currency=1)
        model.subscription.plans.add(model.plan)

        # Create payment settings manually
        AcademyPaymentSettings.objects.create(academy=model.academy, early_renewal_window_days=7)

        # Create a recent payment in the renewal window
        bag = Bag.objects.create(
            user=model.user,
            academy=model.academy,
            currency=model.currency,
            status="PAID",
            was_delivered=False,
        )
        invoice = Invoice.objects.create(
            user=model.user,
            academy=model.academy,
            currency=model.currency,
            amount=100.0,
            status="FULFILLED",
            paid_at=UTC_NOW - timedelta(days=2),
            bag=bag,
        )
        model.subscription.invoices.add(invoice)

        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:renew_subscription")
        response = self.client.post(url, {"payment_method": "stripe", "subscription": 1}, format="json")

        json = response.json()
        expected = {"detail": "already-renewed", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("breathecode.payments.actions.get_bag_from_subscription")
    @patch("breathecode.payments.actions.get_amount_by_chosen_period")
    @patch("breathecode.payments.services.stripe.Stripe.pay")
    def test__post__error_paying_with_stripe(self, mock_stripe_pay, mock_get_amount, mock_get_bag):
        plan = {
            "status": "ACTIVE",
            "price_per_month": 100.0,
            "is_renewable": True,
            "time_of_life": 0,
            "time_of_life_unit": None,
            "trial_duration": 0,
        }
        subscription = {"status": "ACTIVE", "next_payment_at": UTC_NOW + timedelta(days=5)}
        model = self.bc.database.create(user=1, academy=1, subscription=subscription, plan=plan, currency=1)
        model.subscription.plans.add(model.plan)

        # Create payment settings manually
        AcademyPaymentSettings.objects.create(academy=model.academy, early_renewal_window_days=7)

        # Mock bag
        bag = Bag.objects.create(
            user=model.user,
            academy=model.academy,
            currency=model.currency,
            status="RENEWAL",
            chosen_period="MONTH",
        )
        mock_get_bag.return_value = bag
        mock_get_amount.return_value = 100.0

        # Mock Stripe to raise exception
        mock_stripe_pay.side_effect = Exception("Stripe API error")

        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:renew_subscription")
        response = self.client.post(url, {"payment_method": "stripe", "subscription": 1}, format="json")

        json = response.json()
        expected = {"detail": "error-paying-with-stripe", "status_code": 500}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @patch("breathecode.payments.actions.get_bag_from_subscription")
    @patch("breathecode.payments.actions.get_amount_by_chosen_period")
    @patch("breathecode.payments.services.coinbase.CoinbaseCommerce.create_charge")
    def test__post__successful_coinbase_renewal(self, mock_coinbase_charge, mock_get_amount, mock_get_bag):
        plan = {
            "status": "ACTIVE",
            "price_per_month": 100.0,
            "is_renewable": True,
            "time_of_life": 0,
            "time_of_life_unit": None,
            "trial_duration": 0,
        }
        subscription = {"status": "ACTIVE", "next_payment_at": UTC_NOW + timedelta(days=5)}
        model = self.bc.database.create(user=1, academy=1, subscription=subscription, plan=plan, currency=1)
        model.subscription.plans.add(model.plan)

        # Create payment settings manually
        AcademyPaymentSettings.objects.create(academy=model.academy, early_renewal_window_days=7)

        # Mock bag
        bag = Bag.objects.create(
            user=model.user,
            academy=model.academy,
            currency=model.currency,
            status="RENEWAL",
            chosen_period="MONTH",
            amount_per_month=100.0,
        )
        bag.plans.add(model.plan)
        mock_get_bag.return_value = bag
        mock_get_amount.return_value = 100.0

        # Mock Coinbase charge
        mock_coinbase_charge.return_value = {
            "id": "CHARGE123",
            "hosted_url": "https://commerce.coinbase.com/charges/CHARGE123",
        }

        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:renew_subscription")
        response = self.client.post(
            url,
            {"payment_method": "coinbase", "subscription": 1, "return_url": "https://example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json = response.json()
        self.assertEqual(json["charge_id"], "CHARGE123")
        self.assertEqual(json["hosted_url"], "https://commerce.coinbase.com/charges/CHARGE123")

        # Verify subscription was marked as externally_managed
        model.subscription.refresh_from_db()
        self.assertTrue(model.subscription.externally_managed)

        # Verify Coinbase charge was created with correct metadata
        mock_coinbase_charge.assert_called_once()
        call_kwargs = mock_coinbase_charge.call_args[1]
        self.assertEqual(call_kwargs["bag"], bag)
        self.assertEqual(call_kwargs["amount"], 100.0)
        self.assertEqual(call_kwargs["metadata"]["subscription_id"], model.subscription.id)
        self.assertEqual(call_kwargs["metadata"]["is_recurrent"], True)
        self.assertEqual(call_kwargs["return_url"], "https://example.com")
