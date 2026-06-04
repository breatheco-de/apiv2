from unittest.mock import MagicMock, call, patch

from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status

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


class V2CardGetTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 GET without auth
    """

    def test__get__no_auth(self):
        url = reverse_lazy("v2:payments:card")
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    """
    🔽🔽🔽 GET without academy_id
    """

    def test__get__without_academy_id(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("v2:payments:card")
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "academy-required", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    """
    🔽🔽🔽 GET with academy_id, no payment method
    """

    @patch("breathecode.payments.services.stripe.Stripe.get_payment_method_info", MagicMock(return_value=None))
    def test__get__with_academy__no_payment_method(self):
        model = self.bc.database.create(user=1, academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("v2:payments:card") + "?academy=1"
        response = self.client.get(url)

        json = response.json()
        expected = {"has_payment_method": False}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserSetting"),
            [
                format_user_setting({"lang": "en"}),
            ],
        )

    """
    🔽🔽🔽 GET with academy_id, has payment method
    """

    @patch(
        "breathecode.payments.services.stripe.Stripe.get_payment_method_info",
        MagicMock(
            return_value={
                "has_payment_method": True,
                "card_last4": "4242",
                "card_brand": "Visa",
                "card_exp_month": 12,
                "card_exp_year": 2025,
            }
        ),
    )
    def test__get__with_academy__has_payment_method(self):
        model = self.bc.database.create(user=1, academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("v2:payments:card") + "?academy=1"
        response = self.client.get(url)

        json = response.json()
        expected = {
            "has_payment_method": True,
            "card_last4": "4242",
            "card_brand": "Visa",
            "card_exp_month": 12,
            "card_exp_year": 2025,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class V2CardPostTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 POST without auth
    """

    def test__post__no_auth(self):
        url = reverse_lazy("v2:payments:card")
        response = self.client.post(url)

        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    """
    🔽🔽🔽 POST without token
    """

    def test__post__without_token(self):
        model = self.bc.database.create(user=1, academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("v2:payments:card")
        response = self.client.post(url, {"academy": 1}, format="json")

        json = response.json()
        expected = {"detail": "missing-token", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    """
    🔽🔽🔽 POST with token, successful
    """

    @patch(
        "breathecode.payments.services.stripe.Stripe.add_payment_method",
        MagicMock(return_value=(None, {"last4": "4242", "brand": "Visa"})),
    )
    @patch("breathecode.payments.services.stripe.Stripe.add_contact", MagicMock())
    def test__post__with_token__success(self):
        model = self.bc.database.create(user=1, academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("v2:payments:card")
        data = {"token": "tok_visa", "academy": 1}
        response = self.client.post(url, data, format="json")

        json = response.json()
        expected = {"status": "ok", "details": {"last4": "4242", "brand": "Visa"}}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserSetting"),
            [
                format_user_setting({"lang": "en"}),
            ],
        )
