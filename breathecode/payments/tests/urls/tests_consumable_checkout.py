import math
import random
from unittest.mock import MagicMock, call, patch

import pytest
import stripe
from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import breathecode.activity.tasks as activity_tasks
from breathecode.payments.actions import apply_pricing_ratio
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

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


def format_consumable_item(data={}):
    return {
        "cohort_set_id": None,
        "event_type_set_id": None,
        "how_many": -1,
        "id": 1,
        "mentorship_service_set_id": None,
        "service_item_id": 0,
        "unit_type": "UNIT",
        "user_id": 0,
        "valid_until": None,
        "sort_priority": 1,
        **data,
    }


def format_bag_item(data={}):
    return {
        "academy_id": 1,
        "amount_per_half": 0.0,
        "amount_per_month": 0.0,
        "amount_per_quarter": 0.0,
        "amount_per_year": 0.0,
        "chosen_period": "NO_SET",
        "currency_id": 1,
        "expires_at": None,
        "how_many_installments": 0,
        "id": 1,
        "is_recurrent": False,
        "status": "PAID",
        "token": None,
        "type": "CHARGE",
        "user_id": 1,
        "was_delivered": True,
        "country_code": None,
        "pricing_ratio_explanation": {"service_items": []},
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
        "externally_managed": False,
        "payment_method_id": None,
        "proof_id": None,
        **data,
    }


def get_serializer(currency, user, data={}):
    return {
        "amount": 0,
        "currency": {
            "code": currency.code,
            "name": currency.name,
        },
        "paid_at": UTC_NOW.isoformat().replace("+00:00", "Z"),
        "status": "FULFILLED",
        "user": {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        },
        **data,
    }


def get_discounted_price(academy_service, num_items, country_code=None, currency=None) -> float:
    if num_items > academy_service.max_items:
        raise ValueError("num_items cannot be greater than max_items")

    total_discount_ratio = 0
    current_discount_ratio = academy_service.discount_ratio
    discount_nerf = 0.1
    max_discount = 0.2

    for n in range(math.floor(num_items / academy_service.bundle_size)):
        if n == 0:
            continue

        total_discount_ratio += current_discount_ratio
        current_discount_ratio -= current_discount_ratio * discount_nerf

    if total_discount_ratio > max_discount:
        total_discount_ratio = max_discount

    exceptions = academy_service.pricing_ratio_exceptions.get(country_code, {})

    currency = currency or academy_service.currency

    ratio = None

    # Direct price override - Check this FIRST
    if exceptions.get("price") is not None:
        adjusted_price_per_unit = exceptions["price"]

    # Ratio override
    elif exceptions.get("ratio") is not None:
        ratio = exceptions["ratio"]
        adjusted_price_per_unit = academy_service.price_per_unit * ratio

    else:
        adjusted_price_per_unit = academy_service.price_per_unit

    pricing_ratio_explanation = {"service_items": []}
    if ratio:
        pricing_ratio_explanation["service_items"].append(
            {"service": academy_service.service.slug, "ratio": ratio, "country": country_code}
        )

    amount = adjusted_price_per_unit * num_items
    discount = amount * total_discount_ratio

    return amount - discount, currency, pricing_ratio_explanation


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setattr(activity_tasks.add_activity, "delay", MagicMock())
    yield


class SignalTestSuite(PaymentsTestCase):
    # When: no auth
    # Then: return 401
    def test__without_auth(self):
        url = reverse_lazy("payments:consumable_checkout")
        response = self.client.post(url)

        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [])
        self.assertEqual(self.bc.database.list_of("payments.Invoice"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(self.bc.database.list_of("authenticate.UserSetting"), [])
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    # Given: 1 User
    # When: is auth and no service in body
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__no_service(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:consumable_checkout")
        response = self.client.post(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {"detail": "service-is-required", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [])
        self.assertEqual(self.bc.database.list_of("payments.Invoice"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserSetting"),
            [
                format_user_setting({"lang": "en"}),
            ],
        )
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    # Given: 1 User
    # When: is auth and service that not found in body
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__service_not_found(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:consumable_checkout")
        data = {"service": 1}
        response = self.client.post(url, data, format="json")
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {"detail": "service-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [])
        self.assertEqual(self.bc.database.list_of("payments.Invoice"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserSetting"),
            [
                format_user_setting({"lang": "en"}),
            ],
        )
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    # Given: 1 User and 1 Service
    # When: is auth, with a service in body
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_service(self):
        model = self.bc.database.create(user=1, service=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:consumable_checkout")
        data = {"service": 1}
        response = self.client.post(url, data, format="json")
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {"detail": "how-many-is-required", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [])
        self.assertEqual(self.bc.database.list_of("payments.Invoice"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserSetting"),
            [
                format_user_setting({"lang": "en"}),
            ],
        )
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    # Given: 1 User and 1 Service
    # When: is auth, with a service and how_many in body
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__academy_is_required(self):
        model = self.bc.database.create(user=1, service=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:consumable_checkout")
        data = {"service": 1, "how_many": 1}
        response = self.client.post(url, data, format="json")
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {"detail": "academy-is-required", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [])
        self.assertEqual(self.bc.database.list_of("payments.Invoice"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserSetting"),
            [
                format_user_setting({"lang": "en"}),
            ],
        )
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    # Given: 1 User and 1 Service
    # When: is auth, with a service, how_many and academy in body, and academy not found
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__academy_not_found(self):
        model = self.bc.database.create(user=1, service=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:consumable_checkout")
        data = {"service": 1, "how_many": 1, "academy": 1}
        response = self.client.post(url, data, format="json")
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {"detail": "academy-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [])
        self.assertEqual(self.bc.database.list_of("payments.Invoice"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserSetting"),
            [
                format_user_setting({"lang": "en"}),
            ],
        )
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    # Given: 1 User, 1 Service and 1 Academy
    # When: is auth, with a service, how_many and academy in body, resource is required
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__resourse_is_required(self):
        model = self.bc.database.create(user=1, service=1, academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:consumable_checkout")
        data = {
            "service": 1,
            "how_many": 1,
            "academy": 1,
            "mentorship_service_set": 1,
            "event_type_set": 1,
        }
        response = self.client.post(url, data, format="json")
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {"detail": "mentorship-service-set-or-event-type-set-is-required", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [])
        self.assertEqual(self.bc.database.list_of("payments.Invoice"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserSetting"),
            [
                format_user_setting({"lang": "en"}),
            ],
        )
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    # Given: 1 User, 1 Service and 1 Academy
    # When: is auth, with a service, how_many, academy and event_type_set in body,
    # ----> service type is MENTORSHIP_SERVICE_SET
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__bad_service_type_for_event_type_set(self):
        service = {"type": "MENTORSHIP_SERVICE_SET"}
        model = self.bc.database.create(user=1, service=service, academy=1, event_type_set=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:consumable_checkout")
        data = {"service": 1, "how_many": 1, "academy": 1, "event_type_set": 1}
        response = self.client.post(url, data, format="json")
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {"detail": "bad-service-type-mentorship-service-set", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [])
        self.assertEqual(self.bc.database.list_of("payments.Invoice"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserSetting"),
            [
                format_user_setting({"lang": "en"}),
            ],
        )
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    # Given: 1 User, 1 Service and 1 Academy
    # When: is auth, with a service, how_many, academy and mentorship_service_set in body,
    # ----> service type is EVENT_TYPE_SET
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__bad_service_type_for_mentorship_service_set(self):
        service = {"type": "EVENT_TYPE_SET"}
        model = self.bc.database.create(user=1, service=service, academy=1, mentorship_service_set=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:consumable_checkout")
        data = {"service": 1, "how_many": 1, "academy": 1, "mentorship_service_set": 1}
        response = self.client.post(url, data, format="json")
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {"detail": "bad-service-type-event-type-set", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [])
        self.assertEqual(self.bc.database.list_of("payments.Invoice"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserSetting"),
            [
                format_user_setting({"lang": "en"}),
            ],
        )
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    # Given: 1 User, 1 Service and 1 Academy
    # When: is auth, with a service, how_many and academy in body,
    # ----> mentorship_service_set or event_type_set in body
    # ----> service type is COHORT
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__service_is_cohort(self):
        service = {"type": "COHORT_SET"}
        kwargs = {}

        if random.randint(0, 1) == 0:
            kwargs["mentorship_service_set"] = 1
        else:
            kwargs["event_type_set"] = 1

        model = self.bc.database.create(user=1, service=service, academy=1, **kwargs)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:consumable_checkout")
        data = {"service": 1, "how_many": 1, "academy": 1, "mentorship_service_set": 1}
        response = self.client.post(url, data, format="json")
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {"detail": "service-type-no-implemented", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [])
        self.assertEqual(self.bc.database.list_of("payments.Invoice"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserSetting"),
            [
                format_user_setting({"lang": "en"}),
            ],
        )
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    # Given: 1 User, 1 Service and 1 Academy
    # When: is auth, with a service, how_many and academy in body,
    # ----> mentorship_service_set and service type is MENTORSHIP_SERVICE_SET or
    # ----> event_type_set in body and service type is EVENT_TYPE_SET
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__academy_service_not_found(self):
        kwargs = {}

        if random.randint(0, 1) == 0:
            service = {"type": "MENTORSHIP_SERVICE_SET"}
            kwargs["mentorship_service_set"] = 1
        else:
            service = {"type": "EVENT_TYPE_SET"}
            kwargs["event_type_set"] = 1

        model = self.bc.database.create(user=1, service=service, academy=1, **kwargs)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:consumable_checkout")
        data = {"service": 1, "how_many": 1, "academy": 1, **kwargs}
        response = self.client.post(url, data, format="json")
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {"detail": "academy-service-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [])
        self.assertEqual(self.bc.database.list_of("payments.Invoice"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserSetting"),
            [
                format_user_setting({"lang": "en"}),
            ],
        )
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    # Given: 1 User, 1 Service, 1 Academy and 1 AcademyService
    # When: is auth, with a service, how_many and academy in body,
    # ----> mentorship_service_set and service type is MENTORSHIP_SERVICE_SET or
    # ----> event_type_set in body and service type is EVENT_TYPE_SET,
    # ----> over academy_service max_items
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("stripe.Charge.create", MagicMock(return_value={"id": 1}))
    @patch("stripe.Customer.create", MagicMock(return_value={"id": 1}))
    @patch("stripe.Refund.create", MagicMock(return_value={"id": 1}))
    def test__how_many_very_low(self):
        kwargs = {}

        how_many = 1

        if random.randint(0, 1) == 0:
            service = {"type": "MENTORSHIP_SERVICE_SET"}
            kwargs["mentorship_service_set"] = 1

        else:
            service = {"type": "EVENT_TYPE_SET"}
            kwargs["event_type_set"] = 1

        academy_service = {
            "price_per_unit": (0.5 + (random.random() / 2)) / how_many,
            "max_amount": 11,
            "bundle_size": 2,
        }
        # how_many  * 1
        # how_many / 2
        model = self.bc.database.create(user=1, service=service, academy=1, academy_service=academy_service, **kwargs)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:consumable_checkout")
        data = {"service": 1, "how_many": how_many, "academy": 1, **kwargs}
        response = self.client.post(url, data, format="json")
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {"detail": "the-amount-of-items-is-too-low", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [])
        self.assertEqual(self.bc.database.list_of("payments.Invoice"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserSetting"),
            [
                format_user_setting({"lang": "en"}),
            ],
        )

        self.assertEqual(stripe.Charge.create.call_args_list, [])
        self.assertEqual(stripe.Customer.create.call_args_list, [])
        self.assertEqual(stripe.Refund.create.call_args_list, [])
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    # Given: 1 User, 1 Service, 1 Academy and 1 AcademyService
    # When: is auth, with a service, how_many and academy in body,
    # ----> mentorship_service_set and service type is MENTORSHIP_SERVICE_SET or
    # ----> event_type_set in body and service type is EVENT_TYPE_SET,
    # ----> over academy_service max_items
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("stripe.Charge.create", MagicMock(return_value={"id": 1}))
    @patch("stripe.Customer.create", MagicMock(return_value={"id": 1}))
    @patch("stripe.Refund.create", MagicMock(return_value={"id": 1}))
    def test__how_many_very_hight(self):
        kwargs = {}

        how_many = random.randint(2, 10)

        if random.randint(0, 1) == 0:
            service = {"type": "MENTORSHIP_SERVICE_SET"}
            kwargs["mentorship_service_set"] = 1

        else:
            service = {"type": "EVENT_TYPE_SET"}
            kwargs["event_type_set"] = 1

        academy_service = {"price_per_unit": (0.5 + (random.random() / 2)) / how_many, "max_amount": 11}
        # how_many  * 1
        # how_many / 2
        model = self.bc.database.create(user=1, service=service, academy=1, academy_service=academy_service, **kwargs)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:consumable_checkout")
        data = {"service": 1, "how_many": how_many, "academy": 1, **kwargs}
        response = self.client.post(url, data, format="json")
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {"detail": "the-amount-of-items-is-too-high", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [])
        self.assertEqual(self.bc.database.list_of("payments.Invoice"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserSetting"),
            [
                format_user_setting({"lang": "en"}),
            ],
        )

        self.assertEqual(stripe.Charge.create.call_args_list, [])
        self.assertEqual(stripe.Customer.create.call_args_list, [])
        self.assertEqual(stripe.Refund.create.call_args_list, [])
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    # Given: 1 User, 1 Service, 1 Academy and 1 AcademyService
    # When: is auth, with a service, how_many and academy in body,
    # ----> mentorship_service_set and service type is MENTORSHIP_SERVICE_SET or
    # ----> event_type_set in body and service type is EVENT_TYPE_SET,
    # ----> academy_service price_per_unit is less than 0.50
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("stripe.Charge.create", MagicMock(return_value={"id": 1}))
    @patch("stripe.Customer.create", MagicMock(return_value={"id": 1}))
    @patch("stripe.Refund.create", MagicMock(return_value={"id": 1}))
    def test__value_too_low(self):
        kwargs = {}

        how_many = random.randint(1, 10)

        if random.randint(0, 1) == 0:
            service = {"type": "MENTORSHIP_SERVICE_SET"}
            kwargs["mentorship_service_set"] = 1

        else:
            service = {"type": "EVENT_TYPE_SET"}
            kwargs["event_type_set"] = 1

        academy_service = {"price_per_unit": random.random() / 2.01 / how_many, "max_items": how_many}
        model = self.bc.database.create(user=1, service=service, academy=1, academy_service=academy_service, **kwargs)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:consumable_checkout")
        data = {"service": 1, "how_many": how_many, "academy": 1, **kwargs}
        response = self.client.post(url, data, format="json")
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {"detail": "the-amount-is-too-low", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [])
        self.assertEqual(self.bc.database.list_of("payments.Invoice"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserSetting"),
            [
                format_user_setting({"lang": "en"}),
            ],
        )

        self.assertEqual(stripe.Charge.create.call_args_list, [])
        self.assertEqual(stripe.Customer.create.call_args_list, [])
        self.assertEqual(stripe.Refund.create.call_args_list, [])
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    # Given: 1 User, 1 Service, 1 Academy, 1 AcademyService and 1 MentorshipServiceSet
    # When: is auth, with a service, how_many, academy and mentorship_service_set in body,
    # ----> academy_service price_per_unit is greater than 0.50,
    # ----> calculated amount is over academy_service max_amount
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("stripe.Charge.create", MagicMock())
    @patch("stripe.Customer.create", MagicMock())
    @patch("stripe.Refund.create", MagicMock())
    def test__amount_to_hight(self):
        how_many = random.randint(3, 10)
        service = {"type": "MENTORSHIP_SERVICE_SET"}
        # Ensure price_per_unit is high enough
        price_per_unit = (random.random() + 0.50) * 10
        # Calculate total amount
        total_amount = price_per_unit * how_many
        # Set max_amount slightly lower than total to trigger error
        max_amount = total_amount - 1

        academy_service = {
            "price_per_unit": price_per_unit,
            "max_items": how_many + 1,  # Allow enough items
            "bundle_size": 1,  # Simplify bundle logic
            "max_amount": max_amount,  # Set max amount to trigger error
            "discount_ratio": 0,  # No discounts for simplicity
        }

        model = self.bc.database.create(
            user=1, service=service, academy=1, academy_service=academy_service, mentorship_service_set=1, currency=1
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:consumable_checkout")
        # Send the full how_many that causes the total amount to exceed max_amount
        data = {
            "service": 1,
            "how_many": how_many,
            "academy": 1,
            "mentorship_service_set": 1,
            "type": "charge",
            "token": "tok_visa",
        }
        response = self.client.post(url, data, format="json")

        json = response.json()
        # Expect the correct error detail
        expected = {"detail": "the-amount-is-too-high", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [])
        self.assertEqual(self.bc.database.list_of("payments.Invoice"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserSetting"),
            [
                format_user_setting({"lang": "en"}),
            ],
        )
        self.bc.check.calls(stripe.Charge.create.call_args_list, [])
        self.assertEqual(stripe.Customer.create.call_args_list, [])
        self.assertEqual(stripe.Refund.create.call_args_list, [])
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    # Given: 1 User, 1 Service, 1 Academy, 1 AcademyService and 1 MentorshipServiceSet
    # When: is auth, with a service, how_many, academy and mentorship_service_set in body,
    # ----> academy_service price_per_unit is greater than 0.50
    # Then: return 201
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("stripe.Charge.create", MagicMock(return_value={"id": 1}))
    @patch("stripe.Customer.create", MagicMock(return_value={"id": 1}))
    @patch("stripe.Refund.create", MagicMock(return_value={"id": 1}))
    def test__x_mentorship_service_set_bought(self):
        how_many = random.randint(3, 10)

        service = {"type": "MENTORSHIP_SERVICE_SET"}
        price_per_unit = random.random() * 100 / how_many
        academy_service = {
            "price_per_unit": price_per_unit,
            "max_items": how_many,
            "bundle_size": 2,
            "max_amount": price_per_unit * how_many,
            "discount_ratio": random.random() * 0.2,
        }

        model = self.bc.database.create(
            user=1, service=service, academy=1, academy_service=academy_service, mentorship_service_set=1
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:consumable_checkout")
        data = {"service": 1, "how_many": how_many, "academy": 1, "mentorship_service_set": 1}
        response = self.client.post(url, data, format="json")
        self.client.force_authenticate(model.user)

        json = response.json()

        amount, _, _ = get_discounted_price(model.academy_service, how_many)
        amount = math.ceil(amount)
        expected = get_serializer(
            model.currency,
            model.user,
            data={
                "amount": amount,
            },
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [format_bag_item()])
        self.assertEqual(
            self.bc.database.list_of("payments.Invoice"),
            [
                format_invoice_item(
                    {
                        "stripe_id": "1",
                        "amount": amount,
                    }
                ),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                format_consumable_item(
                    data={
                        "mentorship_service_set_id": 1,
                        "service_item_id": 1,
                        "user_id": 1,
                        "how_many": how_many,
                    }
                ),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserSetting"),
            [
                format_user_setting({"lang": "en"}),
            ],
        )

        self.bc.check.calls(
            stripe.Charge.create.call_args_list,
            [
                call(
                    customer="1",
                    amount=amount,
                    currency=model.currency.code.lower(),
                    description=f"Can join to {int(how_many)} mentorships",
                ),
            ],
        )
        self.assertEqual(
            stripe.Customer.create.call_args_list,
            [
                call(email=model.user.email, name=f"{model.user.first_name} {model.user.last_name}"),
            ],
        )
        self.assertEqual(stripe.Refund.create.call_args_list, [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
                call(1, "checkout_completed", related_type="payments.Invoice", related_id=1),
            ],
        )

    # Given: 1 User, 1 Service, 1 Academy, 1 AcademyService and 1 EventTypeSet
    # When: is auth, with a service, how_many, academy and event_type_set in body,
    # ----> academy_service price_per_unit is greater than 0.50
    # Then: return 201
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("stripe.Charge.create", MagicMock(return_value={"id": 1}))
    @patch("stripe.Customer.create", MagicMock(return_value={"id": 1}))
    @patch("stripe.Refund.create", MagicMock(return_value={"id": 1}))
    def test__x_event_type_set_bought(self):
        how_many = random.randint(3, 10)

        service = {"type": "EVENT_TYPE_SET"}
        price_per_unit = random.random() * 100 / how_many
        academy_service = {
            "price_per_unit": price_per_unit,
            "max_items": how_many,
            "bundle_size": 2,
            "max_amount": price_per_unit * how_many,
            "max_items": 11,
            "discount_ratio": random.random() * 0.2,
        }

        model = self.bc.database.create(
            user=1, service=service, academy=1, academy_service=academy_service, event_type_set=1
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:consumable_checkout")
        data = {"service": 1, "how_many": how_many, "academy": 1, "event_type_set": 1}
        response = self.client.post(url, data, format="json")
        self.client.force_authenticate(model.user)

        amount, _, _ = get_discounted_price(model.academy_service, how_many)
        amount = math.ceil(amount)

        json = response.json()
        expected = get_serializer(
            model.currency,
            model.user,
            data={
                "amount": amount,
            },
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [format_bag_item()])
        self.assertEqual(
            self.bc.database.list_of("payments.Invoice"),
            [
                format_invoice_item(
                    {
                        "stripe_id": "1",
                        "amount": amount,
                    }
                )
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                format_consumable_item(
                    data={
                        "event_type_set_id": 1,
                        "service_item_id": 1,
                        "user_id": 1,
                        "how_many": how_many,
                    }
                ),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserSetting"),
            [
                format_user_setting({"lang": "en"}),
            ],
        )

        self.bc.check.calls(
            stripe.Charge.create.call_args_list,
            [
                call(
                    customer="1",
                    amount=amount,
                    currency=model.currency.code.lower(),
                    description=f"Can join to {int(how_many)} events",
                ),
            ],
        )
        self.assertEqual(
            stripe.Customer.create.call_args_list,
            [
                call(email=model.user.email, name=f"{model.user.first_name} {model.user.last_name}"),
            ],
        )
        self.assertEqual(stripe.Refund.create.call_args_list, [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
                call(1, "checkout_completed", related_type="payments.Invoice", related_id=1),
            ],
        )


@pytest.mark.parametrize(
    "exception_details, country_code",
    [
        # Scenario 1: pricing_ratio exception only
        ({"ratio": 0.8}, "VE"),
        # Scenario 2: price exception only
        ({"price": 50.0}, "VE"),
        # Scenario 3: pricing_ratio and currency exception
        ({"ratio": 0.7, "currency": "EUR"}, "VE"),
        # Scenario 4: price and currency exception
        ({"price": 60.0, "currency": "EUR"}, "VE"),
        # Scenario 5: No exception, but country_code provided (should use base price)
        ({}, "US"),
        # Scenario 6: No country_code provided (baseline, uses base price)
        ({}, None),
    ],
)
def test_checkout_with_country_code_and_exceptions(
    db, bc: Breathecode, client: APIClient, exception_details, country_code, monkeypatch, set_datetime
):
    """
    Test the consumable checkout endpoint with country_code and various
    pricing_ratio_exceptions defined on the AcademyService.
    """

    set_datetime(UTC_NOW)
    utc_now = UTC_NOW

    # Patch stripe.Customer.create and stripe.Charge.create
    customer_create_calls = []
    charge_create_calls = []

    def fake_customer_create(**kwargs):
        customer_create_calls.append(kwargs)
        return {"id": "cus_mock"}

    def fake_charge_create(**kwargs):
        charge_create_calls.append(kwargs)
        return {"id": "ch_mock"}

    monkeypatch.setattr("stripe.Customer.create", fake_customer_create)
    monkeypatch.setattr("stripe.Charge.create", fake_charge_create)

    # Setup model with exception details
    academy_service = {
        "price_per_unit": 100.0,
        "bundle_size": 1,
        "max_items": 10,
        "max_amount": 1000.0,
        "discount_ratio": 0,  # Assuming no bundle discount for simplicity
        "pricing_ratio_exceptions": {country_code.lower(): exception_details} if country_code else {},
    }
    service = {"type": "VOID"}  # Use VOID type for consumable checkout
    currency_code = exception_details.get("currency", "USD")  # Default to USD if no override
    currency = {"code": currency_code, "name": f"{currency_code} Name"}
    model = bc.database.create(user=1, academy_service=academy_service, service=service, currency=currency, academy=1)

    client.force_authenticate(model.user)
    url = reverse_lazy("payments:consumable_checkout")
    data = {
        "service": model.service.id,
        "how_many": 5,
        "academy": model.academy.id,
        "type": "charge",
        "token": "tok_visa",
    }
    if country_code:
        data["country_code"] = country_code

    # Calculate expected price using the action
    base_price = model.academy_service.price_per_unit

    expected_price, final_currency, expected_explanation = get_discounted_price(
        model.academy_service, data["how_many"], country_code, model.currency
    )

    base_price = base_price * data["how_many"]
    final_currency_obj = final_currency or model.currency  # Use model currency if not overridden
    expected_price_ceil = math.ceil(expected_price)

    response = client.post(url, data, format="json")

    json = response.json()

    # expected_json = get_local_serializer(final_currency_obj, model.user, invoice)
    expected_json = get_serializer(
        final_currency,
        model.user,
        data={
            "amount": expected_price_ceil,
        },
    )

    assert json == expected_json
    assert response.status_code == status.HTTP_201_CREATED

    assert bc.database.list_of("payments.Bag") == [
        format_bag_item({"currency_id": final_currency_obj.id, "country_code": country_code})
    ]

    # Fetch invoice again as dict for easier comparison
    expected_invoice_data = {
        "id": 1,
        "academy_id": model.academy.id,
        "amount": expected_price_ceil,  # Use the ceiling value for invoice amount
        "currency_id": final_currency_obj.id,
        "bag_id": 1,
        "paid_at": utc_now,  # Use actual paid_at
        "status": "FULFILLED",
        "stripe_id": "ch_mock",
        "user_id": model.user.id,
        "refund_stripe_id": None,
        "refunded_at": None,
        "externally_managed": False,
        "payment_method_id": None,
        "proof_id": None,
    }
    assert bc.database.list_of("payments.Invoice") == [expected_invoice_data]

    # Verify Consumable creation
    expected_consumable = {
        "id": 1,
        "user_id": model.user.id,
        "service_item_id": 1,  # Use actual value from DB
        "unit_type": "UNIT",
        "how_many": data["how_many"],
        "valid_until": None,  # Check actual logic for valid_until
        "cohort_set_id": None,
        "event_type_set_id": None,
        "mentorship_service_set_id": None,
        "sort_priority": 1,  # Assuming default
    }
    assert bc.database.list_of("payments.Consumable") == [expected_consumable]

    # Verify stripe calls: find the call with the expected parameters
    assert charge_create_calls == [
        {
            "customer": "cus_mock",
            "amount": int(expected_price_ceil),  # Stripe expects amount in cents (integer)
            "currency": final_currency_obj.code.lower(),
            "description": "Can join to 5 events",  # Assuming default description for simplicity
        }
    ]

    # Verify activity call
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(model.user.id, "bag_created", related_type="payments.Bag", related_id=1),
            call(model.user.id, "checkout_completed", related_type="payments.Invoice", related_id=1),
        ],
    )
