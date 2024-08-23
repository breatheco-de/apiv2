import math
import random
from unittest.mock import MagicMock, call, patch

import pytest
import stripe
from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status

import breathecode.activity.tasks as activity_tasks

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


def get_discounted_price(academy_service, num_items) -> float:
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

    amount = academy_service.price_per_unit * num_items
    discount = amount * total_discount_ratio

    return amount - discount


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
        data = {"service": 1, "how_many": 1, "academy": 1}
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
    def test__how_many_too_hight(self):
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
    # ----> over academy_service max_amount
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("stripe.Charge.create", MagicMock(return_value={"id": 1}))
    @patch("stripe.Customer.create", MagicMock(return_value={"id": 1}))
    @patch("stripe.Refund.create", MagicMock(return_value={"id": 1}))
    def test__amount_to_hight(self):
        how_many = random.randint(1, 10)

        service = {"type": "MENTORSHIP_SERVICE_SET"}
        price_per_unit = (random.random() + 0.50) * 100 / how_many
        academy_service = {"price_per_unit": price_per_unit, "max_items": how_many, "bundle_size": 2}

        model = self.bc.database.create(
            user=1, service=service, academy=1, academy_service=academy_service, mentorship_service_set=1
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:consumable_checkout")
        data = {"service": 1, "how_many": how_many / 2, "academy": 1, "mentorship_service_set": 1}
        response = self.client.post(url, data, format="json")
        self.client.force_authenticate(model.user)

        json = response.json()
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
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("stripe.Charge.create", MagicMock(return_value={"id": 1}))
    @patch("stripe.Customer.create", MagicMock(return_value={"id": 1}))
    @patch("stripe.Refund.create", MagicMock(return_value={"id": 1}))
    def test__x_mentorship_service_set_bought(self):
        how_many = random.randint(1, 10)

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

        amount = get_discounted_price(model.academy_service, how_many)
        amount = math.ceil(amount)
        expected = get_serializer(
            self,
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
            ],
        )

    # Given: 1 User, 1 Service, 1 Academy, 1 AcademyService and 1 EventTypeSet
    # When: is auth, with a service, how_many, academy and event_type_set in body,
    # ----> academy_service price_per_unit is greater than 0.50
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("stripe.Charge.create", MagicMock(return_value={"id": 1}))
    @patch("stripe.Customer.create", MagicMock(return_value={"id": 1}))
    @patch("stripe.Refund.create", MagicMock(return_value={"id": 1}))
    def test__x_event_type_set_bought(self):
        how_many = random.randint(1, 10)

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

        amount = get_discounted_price(model.academy_service, how_many)
        amount = math.ceil(amount)

        json = response.json()
        expected = get_serializer(
            self,
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
            ],
        )
