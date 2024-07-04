import random
from unittest.mock import MagicMock, call, patch

import stripe
from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.utils.attr_dict import AttrDict

from ..mixins import PaymentsTestCase

UTC_NOW = timezone.now()


def format_user_setting(data={}):
    return {
        "id": 1,
        "user_id": 1,
        "main_currency_id": None,
        "lang": "en",
        **data,
    }


def format_invoice_item(data={}):
    return {
        "academy_id": 1,
        "amount": 0.0,
        "currency_id": 1,
        "bag_id": 1,
        "id": 1,
        "paid_at": UTC_NOW,
        "status": "FULFILLED",
        "stripe_id": None,
        "user_id": 1,
        "refund_stripe_id": None,
        "refunded_at": None,
        **data,
    }


def get_serializer(self, currency, user, data={}):
    return {
        "amount": 0,
        "currency": {
            "code": currency.code,
            "name": currency.name,
        },
        "paid_at": self.bc.datetime.to_iso_string(UTC_NOW),
        "status": "FULFILLED",
        "user": {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        },
        **data,
    }


def generate_amounts_by_time():
    return {
        "amount_per_month": random.random() * 100 + 1,
        "amount_per_quarter": random.random() * 100 + 1,
        "amount_per_half": random.random() * 100 + 1,
        "amount_per_year": random.random() * 100 + 1,
    }


def generate_three_amounts_by_time():
    l = random.shuffle(
        [
            0,
            random.random() * 100 + 1,
            random.random() * 100 + 1,
            random.random() * 100 + 1,
        ]
    )
    return {
        "amount_per_month": l[0],
        "amount_per_quarter": l[1],
        "amount_per_half": l[2],
        "amount_per_year": l[3],
    }


def which_amount_is_zero(data={}):
    for key in data:
        if key == "amount_per_quarter":
            return "MONTH", 1


CHOSEN_PERIOD = {
    "MONTH": "amount_per_month",
    "QUARTER": "amount_per_quarter",
    "HALF": "amount_per_half",
    "YEAR": "amount_per_year",
}


def get_amount_per_period(period, data):
    return data[CHOSEN_PERIOD[period]]


def invoice_mock():

    class FakeInvoice:
        id = 1
        amount = 100

    return FakeInvoice()


class SignalTestSuite(PaymentsTestCase):
    # When: no auth
    # Then: return 401
    def test__no_auth(self):
        url = reverse_lazy("payments:card")
        response = self.client.post(url)

        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [])
        self.assertEqual(self.bc.database.list_of("authenticate.UserSetting"), [])

    # When: no body
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("stripe.Token.create", MagicMock(return_value={"id": 1}))
    @patch("stripe.Customer.create", MagicMock(return_value={"id": 1}))
    @patch("stripe.Customer.modify", MagicMock(return_value={"id": 1}))
    def test__no_body(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:card")
        response = self.client.post(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {"detail": "missing-card-information", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserSetting"),
            [
                format_user_setting({"lang": "en"}),
            ],
        )

        self.bc.check.calls(stripe.Token.create.call_args_list, [])
        self.bc.check.calls(
            stripe.Customer.create.call_args_list,
            [
                call(email=model.user.email, name=f"{model.user.first_name} {model.user.last_name}"),
            ],
        )

        self.bc.check.calls(stripe.Customer.modify.call_args_list, [])

    # When: passing card
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("stripe.Token.create", MagicMock(return_value=AttrDict(id=1)))
    @patch("stripe.Customer.create", MagicMock(return_value=AttrDict(id=1)))
    @patch("stripe.Customer.modify", MagicMock(return_value=AttrDict(id=1)))
    def test__passing_card(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:card")
        data = {"card_number": "4242424242424242", "exp_month": "12", "exp_year": "2030", "cvc": "123"}
        response = self.client.post(url, data, format="json")
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {"status": "ok"}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserSetting"),
            [
                format_user_setting({"lang": "en"}),
            ],
        )

        data["number"] = data.pop("card_number")
        self.bc.check.calls(stripe.Token.create.call_args_list, [call(card=data)])
        self.bc.check.calls(
            stripe.Customer.create.call_args_list,
            [
                call(email=model.user.email, name=f"{model.user.first_name} {model.user.last_name}"),
            ],
        )

        self.bc.check.calls(stripe.Customer.modify.call_args_list, [call("1", source=1)])
