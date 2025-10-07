import math
import random
from typing import Callable, Literal, TypedDict
from unittest.mock import MagicMock, call, patch

import pytest
from aiohttp_retry import Any
from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.tests.mixins.legacy import LegacyAPITestCase

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
        "academy_id": None,
        "amount": 0.0,
        "amount_refunded": 0.0,
        "bag_id": None,
        "currency_id": 1,
        "externally_managed": False,
        "id": 1,
        "paid_at": UTC_NOW,
        "payment_method_id": None,
        "proof_id": None,
        "refund_stripe_id": None,
        "refunded_at": None,
        "status": "FULFILLED",
        "stripe_id": None,
        "subscription_billing_team_id": None,
        "subscription_seat_id": None,
        "user_id": 1,
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


def serialize_consumable(consumable, data={}):
    return {
        "how_many": consumable.how_many,
        "id": consumable.id,
        "unit_type": consumable.unit_type,
        "valid_until": consumable.valid_until,
        "subscription_seat": consumable.subscription_seat.id if consumable.subscription_seat else None,
        "subscription_billing_team": (
            consumable.subscription_billing_team.id if consumable.subscription_billing_team else None
        ),
        "user": consumable.user.id if consumable.user else None,
        "plan_financing": consumable.plan_financing.id if consumable.plan_financing else None,
        "subscription": consumable.subscription.id if consumable.subscription else None,
        **data,
    }


class GenericConsumableMockArg(TypedDict, total=False):
    resource: Literal["cohort_set", "event_type_set", "mentorship_service_set"]
    id: int


class ConsumableMockArg(GenericConsumableMockArg):
    service: int
    how_many: int


def get_virtual_consumables_mock(
    *consumables: ConsumableMockArg,
) -> Callable[[], list[dict[str, Any]]]:

    # the wrapper avoid raising an error during the setup
    def wrapper():
        from breathecode.payments.utils import consumable, service_item

        nonlocal consumables

        result = []
        for x in consumables:
            kwargs = {
                "service_item": service_item(service=x["service"], unit_type="unit", how_many=x["how_many"]),
            }
            if "resource" in x and "id" in x:
                kwargs[x["resource"]] = x["id"]

            result.append(consumable(**kwargs))

        return result

    return wrapper


class TestSignal(LegacyAPITestCase):
    """
    🔽🔽🔽 GET without auth
    """

    def test__without_auth(self):
        url = reverse_lazy("payments:me_service_consumable")
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])

    """
    🔽🔽🔽 Get with zero Consumable
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__without_consumables(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable")
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])

    """
    🔽🔽🔽 Get with one Consumable, how_many = 0
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__one_consumable__how_many_is_zero(self):
        model = self.bc.database.create_v2(user=1, consumable=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable")
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                self.bc.format.to_dict(model.consumable),
            ],
        )

    """
    🔽🔽🔽 Get with nine Consumable and three Cohort, random how_many
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__random_how_many__related_to_three_cohorts__without_cohorts_in_querystring(self):
        consumables = [{"how_many": random.randint(1, 30), "cohort_set_id": math.floor(n / 3) + 1} for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        academy = {"available_as_saas": True}

        model = self.bc.database.create(user=1, consumable=consumables, cohort_set=3, academy=academy)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable")
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [
                {
                    "balance": {"unit": how_many_belong_to1},
                    "id": model.cohort_set[0].id,
                    "slug": model.cohort_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.cohort_set[1].id,
                    "slug": model.cohort_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.cohort_set[2].id,
                    "slug": model.cohort_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__random_how_many__related_to_three_cohorts__with_wrong_cohorts_in_querystring(self):
        consumables = [{"how_many": random.randint(1, 30), "cohort_set_id": math.floor(n / 3) + 1} for n in range(9)]

        academy = {"available_as_saas": True}

        model = self.bc.database.create(user=1, consumable=consumables, cohort_set=3, academy=academy)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?cohort_set=4,5,6"
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__random_how_many__related_to_three_cohorts__with_cohorts_in_querystring(self):
        consumables = [{"how_many": random.randint(1, 30), "cohort_set_id": math.floor(n / 3) + 1} for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        academy = {"available_as_saas": True}

        model = self.bc.database.create(user=1, consumable=consumables, cohort_set=3, academy=academy)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?cohort_set=1,2,3"
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [
                {
                    "balance": {"unit": how_many_belong_to1},
                    "id": model.cohort_set[0].id,
                    "slug": model.cohort_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.cohort_set[1].id,
                    "slug": model.cohort_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.cohort_set[2].id,
                    "slug": model.cohort_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    """
    🔽🔽🔽 Get with nine Consumable and three MentorshipService, random how_many
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_mentorship_services__without_cohorts_in_querystring(self):
        consumables = [
            {"how_many": random.randint(1, 30), "mentorship_service_set_id": math.floor(n / 3) + 1} for n in range(9)
        ]

        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        model = self.bc.database.create(user=1, consumable=consumables, mentorship_service_set=3)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable")
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "mentorship_service_sets": [
                {
                    "balance": {
                        "unit": how_many_belong_to1,
                    },
                    "id": model.mentorship_service_set[0].id,
                    "slug": model.mentorship_service_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.mentorship_service_set[1].id,
                    "slug": model.mentorship_service_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.mentorship_service_set[2].id,
                    "slug": model.mentorship_service_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            "cohort_sets": [],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_mentorship_services__with_wrong_cohorts_in_querystring(self):
        consumables = [
            {"how_many": random.randint(1, 30), "mentorship_service_set_id": math.floor(n / 3) + 1} for n in range(9)
        ]

        model = self.bc.database.create(user=1, consumable=consumables, mentorship_service_set=3)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?mentorship_service_set=4,5,6"
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "cohort_sets": [],
            "mentorship_service_sets": [],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_mentorship_services__with_cohorts_in_querystring(self):
        consumables = [
            {"how_many": random.randint(1, 30), "mentorship_service_set_id": math.floor(n / 3) + 1} for n in range(9)
        ]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        model = self.bc.database.create(user=1, consumable=consumables, mentorship_service_set=3)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?mentorship_service_set=1,2,3"
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "cohort_sets": [],
            "mentorship_service_sets": [
                {
                    "balance": {
                        "unit": how_many_belong_to1,
                    },
                    "id": model.mentorship_service_set[0].id,
                    "slug": model.mentorship_service_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.mentorship_service_set[1].id,
                    "slug": model.mentorship_service_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.mentorship_service_set[2].id,
                    "slug": model.mentorship_service_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    """
    🔽🔽🔽 Get with nine Consumable and three EventType, random how_many
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_event_types__without_cohorts_in_querystring(self):
        consumables = [
            {"how_many": random.randint(1, 30), "event_type_set_id": math.floor(n / 3) + 1} for n in range(9)
        ]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        event_type_sets = [{"event_type_id": x} for x in range(1, 4)]

        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            event_type_set=event_type_sets,
            event_type=[
                {"icon_url": "https://www.google.com"},
                {"icon_url": "https://www.google.com"},
                {"icon_url": "https://www.google.com"},
            ],
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable")
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [],
            "event_type_sets": [
                {
                    "balance": {
                        "unit": how_many_belong_to1,
                    },
                    "id": model.event_type_set[0].id,
                    "slug": model.event_type_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.event_type_set[1].id,
                    "slug": model.event_type_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.event_type_set[2].id,
                    "slug": model.event_type_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_event_types__with_wrong_cohorts_in_querystring(self):
        consumables = [
            {"how_many": random.randint(1, 30), "event_type_set_id": math.floor(n / 3) + 1} for n in range(9)
        ]

        event_type_sets = [{"event_type_id": x} for x in range(1, 4)]
        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            event_type_set=event_type_sets,
            event_type=[
                {"icon_url": "https://www.google.com"},
                {"icon_url": "https://www.google.com"},
                {"icon_url": "https://www.google.com"},
            ],
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?event_type_set=4,5,6"
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "cohort_sets": [],
            "event_type_sets": [],
            "mentorship_service_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_event_types__with_cohorts_in_querystring(self):
        consumables = [
            {"how_many": random.randint(1, 30), "event_type_set_id": math.floor(n / 3) + 1} for n in range(9)
        ]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        event_type_sets = [{"event_type_id": x} for x in range(1, 4)]
        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            event_type_set=event_type_sets,
            event_type=[
                {"icon_url": "https://www.google.com"},
                {"icon_url": "https://www.google.com"},
                {"icon_url": "https://www.google.com"},
            ],
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?event_type_set=1,2,3"
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "cohort_sets": [],
            "event_type_sets": [
                {
                    "balance": {
                        "unit": how_many_belong_to1,
                    },
                    "id": model.event_type_set[0].id,
                    "slug": model.event_type_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.event_type_set[1].id,
                    "slug": model.event_type_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.event_type_set[2].id,
                    "slug": model.event_type_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            "mentorship_service_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    # ???
    """
    🔽🔽🔽 Get with nine Consumable and three Cohort, random how_many
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__random_how_many__related_to_three_cohorts__without_cohort_slugs_in_querystring(self):
        consumables = [{"how_many": random.randint(1, 30), "cohort_set_id": math.floor(n / 3) + 1} for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        academy = {"available_as_saas": True}

        model = self.bc.database.create(user=1, consumable=consumables, cohort_set=3, academy=academy)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable")
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [
                {
                    "balance": {
                        "unit": how_many_belong_to1,
                    },
                    "id": model.cohort_set[0].id,
                    "slug": model.cohort_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.cohort_set[1].id,
                    "slug": model.cohort_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.cohort_set[2].id,
                    "slug": model.cohort_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__random_how_many__related_to_three_cohorts__with_wrong_cohort_slugs_in_querystring(self):
        consumables = [{"how_many": random.randint(1, 30), "cohort_set_id": math.floor(n / 3) + 1} for n in range(9)]

        academy = {"available_as_saas": True}

        model = self.bc.database.create(user=1, consumable=consumables, cohort_set=3, academy=academy)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + f"?cohort_set_slug=blabla1,blabla2,blabla3"
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__random_how_many__related_to_three_cohorts__with_cohort_slugs_in_querystring(self):
        consumables = [{"how_many": random.randint(1, 30), "cohort_set_id": math.floor(n / 3) + 1} for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        academy = {"available_as_saas": True}

        model = self.bc.database.create(user=1, consumable=consumables, cohort_set=3, academy=academy)
        self.client.force_authenticate(model.user)

        url = (
            reverse_lazy("payments:me_service_consumable")
            + f'?cohort_set_slug={",".join([x.slug for x in model.cohort_set])}'
        )
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [
                {
                    "balance": {
                        "unit": how_many_belong_to1,
                    },
                    "id": model.cohort_set[0].id,
                    "slug": model.cohort_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.cohort_set[1].id,
                    "slug": model.cohort_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.cohort_set[2].id,
                    "slug": model.cohort_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    """
    🔽🔽🔽 Get with nine Consumable and three MentorshipService, random how_many
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_mentorship_services__without_cohort_slugs_in_querystring(self):
        consumables = [
            {"how_many": random.randint(1, 30), "mentorship_service_set_id": math.floor(n / 3) + 1} for n in range(9)
        ]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        model = self.bc.database.create(user=1, consumable=consumables, mentorship_service_set=3)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable")
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "mentorship_service_sets": [
                {
                    "balance": {
                        "unit": how_many_belong_to1,
                    },
                    "id": model.mentorship_service_set[0].id,
                    "slug": model.mentorship_service_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.mentorship_service_set[1].id,
                    "slug": model.mentorship_service_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.mentorship_service_set[2].id,
                    "slug": model.mentorship_service_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            "cohort_sets": [],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_mentorship_services__with_wrong_cohort_slugs_in_querystring(self):
        consumables = [
            {"how_many": random.randint(1, 30), "mentorship_service_set_id": math.floor(n / 3) + 1} for n in range(9)
        ]

        model = self.bc.database.create(user=1, consumable=consumables, mentorship_service_set=3)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + f"?mentorship_service_set_slug=blabla1,blabla2,blabla3"
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "cohort_sets": [],
            "mentorship_service_sets": [],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_mentorship_services__with_cohort_slugs_in_querystring(self):
        consumables = [
            {"how_many": random.randint(1, 30), "mentorship_service_set_id": math.floor(n / 3) + 1} for n in range(9)
        ]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        model = self.bc.database.create(user=1, consumable=consumables, mentorship_service_set=3)
        self.client.force_authenticate(model.user)

        url = (
            reverse_lazy("payments:me_service_consumable")
            + f'?mentorship_service_set_slug={",".join([x.slug for x in model.mentorship_service_set])}'
        )
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "cohort_sets": [],
            "mentorship_service_sets": [
                {
                    "balance": {
                        "unit": how_many_belong_to1,
                    },
                    "id": model.mentorship_service_set[0].id,
                    "slug": model.mentorship_service_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.mentorship_service_set[1].id,
                    "slug": model.mentorship_service_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.mentorship_service_set[2].id,
                    "slug": model.mentorship_service_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    """
    🔽🔽🔽 Get with nine Consumable and three EventType, random how_many
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_event_types__without_cohort_slugs_in_querystring(self):
        consumables = [
            {"how_many": random.randint(1, 30), "event_type_set_id": math.floor(n / 3) + 1} for n in range(9)
        ]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        event_type_sets = [{"event_type_id": x} for x in range(1, 4)]
        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            event_type_set=event_type_sets,
            event_type=[
                {"icon_url": "https://www.google.com"},
                {"icon_url": "https://www.google.com"},
                {"icon_url": "https://www.google.com"},
            ],
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable")
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [],
            "event_type_sets": [
                {
                    "balance": {
                        "unit": how_many_belong_to1,
                    },
                    "id": model.event_type_set[0].id,
                    "slug": model.event_type_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.event_type_set[1].id,
                    "slug": model.event_type_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.event_type_set[2].id,
                    "slug": model.event_type_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_event_types__with_wrong_cohort_slugs_in_querystring(self):
        consumables = [
            {"how_many": random.randint(1, 30), "event_type_set_id": math.floor(n / 3) + 1} for n in range(9)
        ]

        event_type_sets = [{"event_type_id": x} for x in range(1, 4)]
        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            event_type_set=event_type_sets,
            event_type=[
                {"icon_url": "https://www.google.com"},
                {"icon_url": "https://www.google.com"},
                {"icon_url": "https://www.google.com"},
            ],
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + f"?event_type_set_slug=blabla1,blabla2,blabla3"
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "cohort_sets": [],
            "event_type_sets": [],
            "mentorship_service_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_event_types__with_cohort_slugs_in_querystring(self):
        consumables = [
            {"how_many": random.randint(1, 30), "event_type_set_id": math.floor(n / 3) + 1} for n in range(9)
        ]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        event_type_sets = [{"event_type_id": x} for x in range(1, 4)]
        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            event_type_set=event_type_sets,
            event_type=[
                {"icon_url": "https://www.google.com"},
                {"icon_url": "https://www.google.com"},
                {"icon_url": "https://www.google.com"},
            ],
        )
        self.client.force_authenticate(model.user)

        url = (
            reverse_lazy("payments:me_service_consumable")
            + f'?event_type_set_slug={",".join([x.slug for x in model.event_type_set])}'
        )
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "cohort_sets": [],
            "event_type_sets": [
                {
                    "balance": {
                        "unit": how_many_belong_to1,
                    },
                    "id": model.event_type_set[0].id,
                    "slug": model.event_type_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.event_type_set[1].id,
                    "slug": model.event_type_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.event_type_set[2].id,
                    "slug": model.event_type_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            "mentorship_service_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    """
    🔽🔽🔽 Get with nine Consumable and three Services, random how_many
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_services__without_cohort_slugs_in_querystring(self):
        consumables = [{"how_many": random.randint(1, 30), "service_item_id": math.floor(n / 3) + 1} for n in range(9)]
        service_items = [{"service_id": n + 1} for n in range(3)]

        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            service=(3, {"type": "VOID"}),
            service_item=service_items,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable")
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        serialized_consumables = [serialize_consumable(model.consumable[n]) for n in range(9)]
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [],
            "event_type_sets": [],
            "voids": [
                {
                    "balance": {
                        "unit": how_many_belong_to1,
                    },
                    "id": model.service[0].id,
                    "slug": model.service[0].slug,
                    "items": serialized_consumables[:3],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.service[1].id,
                    "slug": model.service[1].slug,
                    "items": serialized_consumables[3:6],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.service[2].id,
                    "slug": model.service[2].slug,
                    "items": serialized_consumables[6:9],
                },
            ],
        }

        assert json == expected
        assert response.status_code == status.HTTP_200_OK
        assert self.bc.database.list_of("payments.Consumable") == self.bc.format.to_dict(model.consumable)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_services__with_wrong_cohort_slugs_in_querystring(self):
        consumables = [{"how_many": random.randint(1, 30), "service_item_id": math.floor(n / 3) + 1} for n in range(9)]
        service_items = [{"service_id": n + 1} for n in range(3)]

        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            service=(3, {"type": "VOID"}),
            service_item=service_items,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + f"?service_slug=blabla1,blabla2,blabla3"
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "cohort_sets": [],
            "event_type_sets": [],
            "mentorship_service_sets": [],
            "voids": [],
        }

        assert json == expected
        assert response.status_code == status.HTTP_200_OK
        assert self.bc.database.list_of("payments.Consumable") == self.bc.format.to_dict(model.consumable)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_services__with_cohort_slugs_in_querystring(self):
        consumables = [{"how_many": random.randint(1, 30), "service_item_id": math.floor(n / 3) + 1} for n in range(9)]
        service_items = [{"service_id": n + 1} for n in range(3)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            service=(3, {"type": "VOID"}),
            service_item=service_items,
        )
        self.client.force_authenticate(model.user)

        url = (
            reverse_lazy("payments:me_service_consumable")
            + f'?service_slug={",".join([x.slug for x in model.service])}'
        )
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        serialized_consumables = [serialize_consumable(model.consumable[n]) for n in range(9)]
        expected = {
            "cohort_sets": [],
            "event_type_sets": [],
            "mentorship_service_sets": [],
            "voids": [
                {
                    "balance": {
                        "unit": how_many_belong_to1,
                    },
                    "id": model.service[0].id,
                    "slug": model.service[0].slug,
                    "items": serialized_consumables[:3],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.service[1].id,
                    "slug": model.service[1].slug,
                    "items": serialized_consumables[3:6],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.service[2].id,
                    "slug": model.service[2].slug,
                    "items": serialized_consumables[6:9],
                },
            ],
        }

        assert json == expected
        assert response.status_code == status.HTTP_200_OK
        assert self.bc.database.list_of("payments.Consumable") == self.bc.format.to_dict(model.consumable)

    """
    🔽🔽🔽 Virtual Consumables, append to the real balance
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__append_to_same_balance___cohort_set__with_three_virtual_consumables(self, monkeypatch):
        from breathecode.payments.utils import reset_cache

        reset_cache()

        rand1 = random.randint(1, 9)
        rand2 = random.randint(1, 9)
        rand3 = random.randint(1, 9)

        monkeypatch.setattr(
            "breathecode.payments.data.get_virtual_consumables",
            get_virtual_consumables_mock(
                *[{"resource": "cohort_set", "id": 1, "service": 2 + n, "how_many": rand1 * (1 + n)} for n in range(3)],
                *[{"resource": "cohort_set", "id": 2, "service": 5 + n, "how_many": rand2 * (1 + n)} for n in range(3)],
                *[{"resource": "cohort_set", "id": 3, "service": 8 + n, "how_many": rand3 * (1 + n)} for n in range(3)],
            ),
        )
        consumables = [{"how_many": random.randint(1, 30), "cohort_set_id": math.floor(n / 3) + 1} for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1]) + sum([rand1 * (1 + n) for n in range(3)])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2]) + sum([rand2 * (1 + n) for n in range(3)])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3]) + sum([rand3 * (1 + n) for n in range(3)])

        academy = {"available_as_saas": False}

        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            cohort_set=3,
            cohort_set_cohort=[{"cohort_set_id": 1 + n} for n in range(3)],
            academy=academy,
            service=(10, {"type": "COHORT_SET"}),
            cohort={"available_as_saas": True},
            cohort_user=1,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?virtual=true"
        with patch(
            "breathecode.admissions.actions.is_no_saas_student_up_to_date_in_any_cohort", return_value=True
        ) as mock:
            response = self.client.get(url)
            mock.call_args_list == [call(model.user, default=False)]

        json = response.json()
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [
                {
                    "balance": {"unit": how_many_belong_to1},
                    "id": model.cohort_set[0].id,
                    "slug": model.cohort_set[0].slug,
                    "items": [
                        *[serialize_consumable(model.consumable[n]) for n in range(9)],
                        *[
                            {
                                "how_many": rand1 * (1 + n),
                                "id": None,
                                "unit_type": "UNIT",
                                "valid_until": None,
                                "plan_financing": None,
                                "subscription": None,
                                "subscription_seat": None,
                                "subscription_billing_team": None,
                                "user": model.user.id,
                            }
                            for n in range(3)
                        ],
                    ],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.cohort_set[1].id,
                    "slug": model.cohort_set[1].slug,
                    "items": [
                        *[serialize_consumable(model.consumable[n]) for n in range(9)],
                        *[
                            {
                                "how_many": rand2 * (1 + n),
                                "id": None,
                                "unit_type": "UNIT",
                                "valid_until": None,
                                "plan_financing": None,
                                "subscription": None,
                                "subscription_seat": None,
                                "subscription_billing_team": None,
                                "user": model.user.id,
                            }
                            for n in range(3)
                        ],
                    ],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.cohort_set[2].id,
                    "slug": model.cohort_set[2].slug,
                    "items": [
                        *[serialize_consumable(model.consumable[n]) for n in range(9)],
                        *[
                            {
                                "how_many": rand3 * (1 + n),
                                "id": None,
                                "unit_type": "UNIT",
                                "valid_until": None,
                                "plan_financing": None,
                                "subscription": None,
                                "subscription_seat": None,
                                "subscription_billing_team": None,
                                "user": model.user.id,
                            }
                            for n in range(3)
                        ],
                    ],
                },
            ],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__append_to_same_balance___cohort_set__with_three_virtual_consumables__as_saas(self, monkeypatch):
        from breathecode.payments.utils import reset_cache

        reset_cache()

        rand1 = random.randint(1, 9)
        rand2 = random.randint(1, 9)
        rand3 = random.randint(1, 9)

        monkeypatch.setattr(
            "breathecode.payments.data.get_virtual_consumables",
            get_virtual_consumables_mock(
                *[{"resource": "cohort_set", "id": 1, "service": 2 + n, "how_many": rand1 * (1 + n)} for n in range(3)],
                *[{"resource": "cohort_set", "id": 2, "service": 5 + n, "how_many": rand2 * (1 + n)} for n in range(3)],
                *[{"resource": "cohort_set", "id": 3, "service": 8 + n, "how_many": rand3 * (1 + n)} for n in range(3)],
            ),
        )
        consumables = [{"how_many": random.randint(1, 30), "cohort_set_id": math.floor(n / 3) + 1} for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        academy = {"available_as_saas": True}

        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            cohort_set=3,
            cohort_set_cohort=[{"cohort_set_id": 1 + n} for n in range(3)],
            academy=academy,
            service=(10, {"type": "COHORT_SET"}),
            cohort={"available_as_saas": True},
            cohort_user=1,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?virtual=true"
        with patch(
            "breathecode.admissions.actions.is_no_saas_student_up_to_date_in_any_cohort", return_value=False
        ) as mock:
            response = self.client.get(url)
            mock.call_args_list == [call(model.user, default=False)]

        json = response.json()
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [
                {
                    "balance": {"unit": how_many_belong_to1},
                    "id": model.cohort_set[0].id,
                    "slug": model.cohort_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.cohort_set[1].id,
                    "slug": model.cohort_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.cohort_set[2].id,
                    "slug": model.cohort_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__append_to_same_balance___mentorship_service_set__with_three_virtual_consumables(self, monkeypatch):
        from breathecode.payments.utils import reset_cache

        reset_cache()

        rand1 = random.randint(1, 9)
        rand2 = random.randint(1, 9)
        rand3 = random.randint(1, 9)

        monkeypatch.setattr(
            "breathecode.payments.data.get_virtual_consumables",
            get_virtual_consumables_mock(
                *[
                    {"resource": "mentorship_service_set", "id": 1, "service": 2 + n, "how_many": rand1 * (1 + n)}
                    for n in range(3)
                ],
                *[
                    {"resource": "mentorship_service_set", "id": 2, "service": 5 + n, "how_many": rand2 * (1 + n)}
                    for n in range(3)
                ],
                *[
                    {"resource": "mentorship_service_set", "id": 3, "service": 8 + n, "how_many": rand3 * (1 + n)}
                    for n in range(3)
                ],
            ),
        )
        consumables = [
            {"how_many": random.randint(1, 30), "mentorship_service_set_id": math.floor(n / 3) + 1} for n in range(9)
        ]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1]) + sum([rand1 * (1 + n) for n in range(3)])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2]) + sum([rand2 * (1 + n) for n in range(3)])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3]) + sum([rand3 * (1 + n) for n in range(3)])

        academy = {"available_as_saas": False}

        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            mentorship_service_set=3,
            profile_academy=1,
            academy=academy,
            service=(10, {"type": "MENTORSHIP_SERVICE_SET"}),
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?virtual=true"
        with patch(
            "breathecode.admissions.actions.is_no_saas_student_up_to_date_in_any_cohort", return_value=True
        ) as mock:
            response = self.client.get(url)
            mock.call_args_list == [call(model.user, default=False)]

        json = response.json()
        expected = {
            "mentorship_service_sets": [
                {
                    "balance": {"unit": how_many_belong_to1},
                    "id": model.mentorship_service_set[0].id,
                    "slug": model.mentorship_service_set[0].slug,
                    "items": [
                        *[serialize_consumable(model.consumable[n]) for n in range(9)],
                        *[
                            {
                                "id": None,
                                "how_many": rand1 * (1 + n),
                                "unit_type": "UNIT",
                                "valid_until": None,
                                "plan_financing": None,
                                "subscription": None,
                                "subscription_seat": None,
                                "subscription_billing_team": None,
                                "user": model.user.id,
                            }
                            for n in range(3)
                        ],
                    ],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.mentorship_service_set[1].id,
                    "slug": model.mentorship_service_set[1].slug,
                    "items": [
                        *[serialize_consumable(model.consumable[n]) for n in range(9)],
                        *[
                            {
                                "id": None,
                                "how_many": rand2 * (1 + n),
                                "unit_type": "UNIT",
                                "valid_until": None,
                                "plan_financing": None,
                                "subscription": None,
                                "subscription_seat": None,
                                "subscription_billing_team": None,
                                "user": model.user.id,
                            }
                            for n in range(3)
                        ],
                    ],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.mentorship_service_set[2].id,
                    "slug": model.mentorship_service_set[2].slug,
                    "items": [
                        *[serialize_consumable(model.consumable[n]) for n in range(9)],
                        *[
                            {
                                "id": None,
                                "how_many": rand3 * (1 + n),
                                "unit_type": "UNIT",
                                "valid_until": None,
                                "plan_financing": None,
                                "subscription": None,
                                "subscription_seat": None,
                                "subscription_billing_team": None,
                                "user": model.user.id,
                            }
                            for n in range(3)
                        ],
                    ],
                },
            ],
            "cohort_sets": [],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__append_to_same_balance___mentorship_service_set__with_three_virtual_consumables__as_saas(
        self, monkeypatch
    ):
        from breathecode.payments.utils import reset_cache

        reset_cache()

        rand1 = random.randint(1, 9)
        rand2 = random.randint(1, 9)
        rand3 = random.randint(1, 9)

        monkeypatch.setattr(
            "breathecode.payments.data.get_virtual_consumables",
            get_virtual_consumables_mock(
                *[
                    {"resource": "mentorship_service_set", "id": 1, "service": 2 + n, "how_many": rand1 * (1 + n)}
                    for n in range(3)
                ],
                *[
                    {"resource": "mentorship_service_set", "id": 2, "service": 5 + n, "how_many": rand2 * (1 + n)}
                    for n in range(3)
                ],
                *[
                    {"resource": "mentorship_service_set", "id": 3, "service": 8 + n, "how_many": rand3 * (1 + n)}
                    for n in range(3)
                ],
            ),
        )
        consumables = [
            {"how_many": random.randint(1, 30), "mentorship_service_set_id": math.floor(n / 3) + 1} for n in range(9)
        ]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        academy = {"available_as_saas": True}

        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            mentorship_service_set=3,
            profile_academy=1,
            academy=academy,
            service=(10, {"type": "MENTORSHIP_SERVICE_SET"}),
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?virtual=true"
        with patch(
            "breathecode.admissions.actions.is_no_saas_student_up_to_date_in_any_cohort", return_value=False
        ) as mock:
            response = self.client.get(url)
            mock.call_args_list == [call(model.user, default=False)]

        json = response.json()
        expected = {
            "mentorship_service_sets": [
                {
                    "balance": {"unit": how_many_belong_to1},
                    "id": model.mentorship_service_set[0].id,
                    "slug": model.mentorship_service_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.mentorship_service_set[1].id,
                    "slug": model.mentorship_service_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.mentorship_service_set[2].id,
                    "slug": model.mentorship_service_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            "cohort_sets": [],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__append_to_same_balance___event_type_set__with_three_virtual_consumables(self, monkeypatch):
        from breathecode.payments.utils import reset_cache

        reset_cache()

        rand1 = random.randint(1, 9)
        rand2 = random.randint(1, 9)
        rand3 = random.randint(1, 9)

        monkeypatch.setattr(
            "breathecode.payments.data.get_virtual_consumables",
            get_virtual_consumables_mock(
                *[
                    {"resource": "event_type_set", "id": 1, "service": 2 + n, "how_many": rand1 * (1 + n)}
                    for n in range(3)
                ],
                *[
                    {"resource": "event_type_set", "id": 2, "service": 5 + n, "how_many": rand2 * (1 + n)}
                    for n in range(3)
                ],
                *[
                    {"resource": "event_type_set", "id": 3, "service": 8 + n, "how_many": rand3 * (1 + n)}
                    for n in range(3)
                ],
            ),
        )
        consumables = [
            {"how_many": random.randint(1, 30), "event_type_set_id": math.floor(n / 3) + 1} for n in range(9)
        ]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1]) + sum([rand1 * (1 + n) for n in range(3)])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2]) + sum([rand2 * (1 + n) for n in range(3)])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3]) + sum([rand3 * (1 + n) for n in range(3)])

        academy = {"available_as_saas": False}

        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            event_type_set=3,
            profile_academy=1,
            academy=academy,
            service=(10, {"type": "EVENT_TYPE_SET"}),
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?virtual=true"
        with patch(
            "breathecode.admissions.actions.is_no_saas_student_up_to_date_in_any_cohort", return_value=True
        ) as mock:
            response = self.client.get(url)
            mock.call_args_list == [call(model.user, default=False)]

        json = response.json()
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [],
            "event_type_sets": [
                {
                    "balance": {"unit": how_many_belong_to1},
                    "id": model.event_type_set[0].id,
                    "slug": model.event_type_set[0].slug,
                    "items": [
                        *[serialize_consumable(model.consumable[n]) for n in range(9)],
                        *[
                            {
                                "id": None,
                                "how_many": rand1 * (1 + n),
                                "unit_type": "UNIT",
                                "valid_until": None,
                                "plan_financing": None,
                                "subscription": None,
                                "subscription_seat": None,
                                "subscription_billing_team": None,
                                "user": model.user.id,
                            }
                            for n in range(3)
                        ],
                    ],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.event_type_set[1].id,
                    "slug": model.event_type_set[1].slug,
                    "items": [
                        *[serialize_consumable(model.consumable[n]) for n in range(9)],
                        *[
                            {
                                "id": None,
                                "how_many": rand2 * (1 + n),
                                "unit_type": "UNIT",
                                "valid_until": None,
                                "plan_financing": None,
                                "subscription": None,
                                "subscription_seat": None,
                                "subscription_billing_team": None,
                                "user": model.user.id,
                            }
                            for n in range(3)
                        ],
                    ],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.event_type_set[2].id,
                    "slug": model.event_type_set[2].slug,
                    "items": [
                        *[serialize_consumable(model.consumable[n]) for n in range(9)],
                        *[
                            {
                                "id": None,
                                "how_many": rand3 * (1 + n),
                                "unit_type": "UNIT",
                                "valid_until": None,
                                "plan_financing": None,
                                "subscription": None,
                                "subscription_seat": None,
                                "subscription_billing_team": None,
                                "user": model.user.id,
                            }
                            for n in range(3)
                        ],
                    ],
                },
            ],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__append_to_same_balance___event_type_set__with_three_virtual_consumables__as_saas(self, monkeypatch):
        from breathecode.payments.utils import reset_cache

        reset_cache()

        rand1 = random.randint(1, 9)
        rand2 = random.randint(1, 9)
        rand3 = random.randint(1, 9)

        monkeypatch.setattr(
            "breathecode.payments.data.get_virtual_consumables",
            get_virtual_consumables_mock(
                *[
                    {"resource": "event_type_set", "id": 1, "service": 2 + n, "how_many": rand1 * (1 + n)}
                    for n in range(3)
                ],
                *[
                    {"resource": "event_type_set", "id": 2, "service": 5 + n, "how_many": rand2 * (1 + n)}
                    for n in range(3)
                ],
                *[
                    {"resource": "event_type_set", "id": 3, "service": 8 + n, "how_many": rand3 * (1 + n)}
                    for n in range(3)
                ],
            ),
        )
        consumables = [
            {"how_many": random.randint(1, 30), "event_type_set_id": math.floor(n / 3) + 1} for n in range(9)
        ]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        academy = {"available_as_saas": True}

        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            event_type_set=3,
            profile_academy=1,
            academy=academy,
            service=(10, {"type": "EVENT_TYPE_SET"}),
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?virtual=true"
        with patch(
            "breathecode.admissions.actions.is_no_saas_student_up_to_date_in_any_cohort", return_value=False
        ) as mock:
            response = self.client.get(url)
            mock.call_args_list == [call(model.user, default=False)]

        json = response.json()
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [],
            "event_type_sets": [
                {
                    "balance": {"unit": how_many_belong_to1},
                    "id": model.event_type_set[0].id,
                    "slug": model.event_type_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.event_type_set[1].id,
                    "slug": model.event_type_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.event_type_set[2].id,
                    "slug": model.event_type_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__append_to_same_balance___service__with_three_virtual_consumables(self, monkeypatch):
        from breathecode.payments.utils import reset_cache

        reset_cache()

        rand1 = random.randint(1, 9)
        rand2 = random.randint(1, 9)
        rand3 = random.randint(1, 9)

        monkeypatch.setattr(
            "breathecode.payments.data.get_virtual_consumables",
            get_virtual_consumables_mock(
                *[{"service": 1, "how_many": rand1 * (1 + n)} for n in range(3)],
                *[{"service": 2, "how_many": rand2 * (1 + n)} for n in range(3)],
                *[{"service": 3, "how_many": rand3 * (1 + n)} for n in range(3)],
            ),
        )

        consumables = [{"how_many": random.randint(1, 30), "service_item_id": math.floor(n / 3) + 1} for n in range(9)]
        service_items = [{"service_id": n + 1} for n in range(3)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1]) + sum([rand1 * (1 + n) for n in range(3)])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2]) + sum([rand2 * (1 + n) for n in range(3)])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3]) + sum([rand3 * (1 + n) for n in range(3)])

        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            service_item=service_items,
            service=[{"type": "VOID"} for _ in range(3)],
        )

        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?virtual=true"
        with patch(
            "breathecode.admissions.actions.is_no_saas_student_up_to_date_in_any_cohort", return_value=True
        ) as mock:
            response = self.client.get(url)
            mock.call_args_list == [call(model.user, default=False)]

        json = response.json()
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [],
            "event_type_sets": [],
            "voids": [
                {
                    "balance": {"unit": how_many_belong_to1},
                    "id": model.service[0].id,
                    "slug": model.service[0].slug,
                    "items": [
                        *[serialize_consumable(consumable) for consumable in model.consumable[:3]],
                        *[
                            {
                                "id": None,
                                "how_many": rand1 * (1 + n),
                                "unit_type": "UNIT",
                                "valid_until": None,
                                "plan_financing": None,
                                "subscription": None,
                                "subscription_seat": None,
                                "subscription_billing_team": None,
                                "user": model.user.id,
                            }
                            for n in range(3)
                        ],
                    ],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.service[1].id,
                    "slug": model.service[1].slug,
                    "items": [
                        *[serialize_consumable(consumable) for consumable in model.consumable[3:6]],
                        *[
                            {
                                "id": None,
                                "how_many": rand2 * (1 + n),
                                "unit_type": "UNIT",
                                "valid_until": None,
                                "plan_financing": None,
                                "subscription": None,
                                "subscription_seat": None,
                                "subscription_billing_team": None,
                                "user": model.user.id,
                            }
                            for n in range(3)
                        ],
                    ],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.service[2].id,
                    "slug": model.service[2].slug,
                    "items": [
                        *[serialize_consumable(consumable) for consumable in model.consumable[6:]],
                        *[
                            {
                                "id": None,
                                "how_many": rand3 * (1 + n),
                                "unit_type": "UNIT",
                                "valid_until": None,
                                "plan_financing": None,
                                "subscription": None,
                                "subscription_seat": None,
                                "subscription_billing_team": None,
                                "user": model.user.id,
                            }
                            for n in range(3)
                        ],
                    ],
                },
            ],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__append_to_same_balance___service__with_three_virtual_consumables__as_saas(self, monkeypatch):
        from breathecode.payments.utils import reset_cache

        reset_cache()

        rand1 = random.randint(1, 9)
        rand2 = random.randint(1, 9)
        rand3 = random.randint(1, 9)

        monkeypatch.setattr(
            "breathecode.payments.data.get_virtual_consumables",
            get_virtual_consumables_mock(
                *[{"service": 1, "how_many": rand1 * (1 + n)} for n in range(3)],
                *[{"service": 2, "how_many": rand2 * (1 + n)} for n in range(3)],
                *[{"service": 3, "how_many": rand3 * (1 + n)} for n in range(3)],
            ),
        )

        consumables = [{"how_many": random.randint(1, 30), "service_item_id": math.floor(n / 3) + 1} for n in range(9)]
        service_items = [{"service_id": n + 1} for n in range(3)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            service_item=service_items,
            service=[{"type": "VOID"} for _ in range(3)],
        )

        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?virtual=true"
        with patch(
            "breathecode.admissions.actions.is_no_saas_student_up_to_date_in_any_cohort", return_value=False
        ) as mock:
            response = self.client.get(url)
            mock.call_args_list == [call(model.user, default=False)]

        json = response.json()
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [],
            "event_type_sets": [],
            "voids": [
                {
                    "balance": {"unit": how_many_belong_to1},
                    "id": model.service[0].id,
                    "slug": model.service[0].slug,
                    "items": [serialize_consumable(consumable) for consumable in model.consumable[:3]],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.service[1].id,
                    "slug": model.service[1].slug,
                    "items": [serialize_consumable(consumable) for consumable in model.consumable[3:6]],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.service[2].id,
                    "slug": model.service[2].slug,
                    "items": [serialize_consumable(consumable) for consumable in model.consumable[6:]],
                },
            ],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    """
    🔽🔽🔽 Virtual Consumables, append to a new balance
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__append_to_new_balance___cohort_set__with_three_virtual_consumables(self, monkeypatch):
        from breathecode.payments.utils import reset_cache

        reset_cache()

        rand1 = random.randint(1, 9)
        rand2 = random.randint(1, 9)
        rand3 = random.randint(1, 9)

        monkeypatch.setattr(
            "breathecode.payments.data.get_virtual_consumables",
            get_virtual_consumables_mock(
                *[{"resource": "cohort_set", "id": 4, "service": 2 + n, "how_many": rand1 * (1 + n)} for n in range(3)],
                *[{"resource": "cohort_set", "id": 5, "service": 5 + n, "how_many": rand2 * (1 + n)} for n in range(3)],
                *[{"resource": "cohort_set", "id": 6, "service": 8 + n, "how_many": rand3 * (1 + n)} for n in range(3)],
            ),
        )
        consumables = [{"how_many": random.randint(1, 30), "cohort_set_id": math.floor(n / 3) + 1} for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        academy = {"available_as_saas": False}

        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            cohort_set=6,
            cohort_set_cohort=[{"cohort_set_id": 4 + n} for n in range(3)],
            academy=academy,
            service=(10, {"type": "COHORT_SET"}),
            cohort={"available_as_saas": True},
            cohort_user=1,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?virtual=true"
        with patch(
            "breathecode.admissions.actions.is_no_saas_student_up_to_date_in_any_cohort", return_value=True
        ) as mock:
            response = self.client.get(url)
            mock.call_args_list == [call(model.user, default=False)]

        json = response.json()
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [
                {
                    "balance": {"unit": how_many_belong_to1},
                    "id": model.cohort_set[0].id,
                    "slug": model.cohort_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.cohort_set[1].id,
                    "slug": model.cohort_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.cohort_set[2].id,
                    "slug": model.cohort_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                #
                {
                    "balance": {
                        "unit": sum([rand1 * (1 + n) for n in range(3)]),
                    },
                    "id": model.cohort_set[3].id,
                    "slug": model.cohort_set[3].slug,
                    "items": [
                        {
                            "how_many": rand1 * (1 + n),
                            "id": None,
                            "unit_type": "UNIT",
                            "valid_until": None,
                            "plan_financing": None,
                            "subscription": None,
                            "subscription_seat": None,
                            "subscription_billing_team": None,
                            "user": model.user.id,
                        }
                        for n in range(3)
                    ],
                },
                {
                    "balance": {
                        "unit": sum([rand2 * (1 + n) for n in range(3)]),
                    },
                    "id": model.cohort_set[4].id,
                    "slug": model.cohort_set[4].slug,
                    "items": [
                        {
                            "how_many": rand2 * (1 + n),
                            "id": None,
                            "unit_type": "UNIT",
                            "valid_until": None,
                            "plan_financing": None,
                            "subscription": None,
                            "subscription_seat": None,
                            "subscription_billing_team": None,
                            "user": model.user.id,
                        }
                        for n in range(3)
                    ],
                },
                {
                    "balance": {
                        "unit": sum([rand3 * (1 + n) for n in range(3)]),
                    },
                    "id": model.cohort_set[5].id,
                    "slug": model.cohort_set[5].slug,
                    "items": [
                        {
                            "how_many": rand3 * (1 + n),
                            "id": None,
                            "unit_type": "UNIT",
                            "valid_until": None,
                            "plan_financing": None,
                            "subscription": None,
                            "subscription_seat": None,
                            "subscription_billing_team": None,
                            "user": model.user.id,
                        }
                        for n in range(3)
                    ],
                },
            ],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__append_to_new_balance___cohort_set__with_three_virtual_consumables__as_saas(self, monkeypatch):
        from breathecode.payments.utils import reset_cache

        reset_cache()

        rand1 = random.randint(1, 9)
        rand2 = random.randint(1, 9)
        rand3 = random.randint(1, 9)

        monkeypatch.setattr(
            "breathecode.payments.data.get_virtual_consumables",
            get_virtual_consumables_mock(
                *[{"resource": "cohort_set", "id": 4, "service": 2 + n, "how_many": rand1 * (1 + n)} for n in range(3)],
                *[{"resource": "cohort_set", "id": 5, "service": 5 + n, "how_many": rand2 * (1 + n)} for n in range(3)],
                *[{"resource": "cohort_set", "id": 6, "service": 8 + n, "how_many": rand3 * (1 + n)} for n in range(3)],
            ),
        )
        consumables = [{"how_many": random.randint(1, 30), "cohort_set_id": math.floor(n / 3) + 1} for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        academy = {"available_as_saas": True}

        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            cohort_set=6,
            cohort_set_cohort=[{"cohort_set_id": 4 + n} for n in range(3)],
            academy=academy,
            service=(10, {"type": "COHORT_SET"}),
            cohort={"available_as_saas": True},
            cohort_user=1,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?virtual=true"
        with patch(
            "breathecode.admissions.actions.is_no_saas_student_up_to_date_in_any_cohort", return_value=False
        ) as mock:
            response = self.client.get(url)
            mock.call_args_list == [call(model.user, default=False)]

        json = response.json()
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [
                {
                    "balance": {"unit": how_many_belong_to1},
                    "id": model.cohort_set[0].id,
                    "slug": model.cohort_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.cohort_set[1].id,
                    "slug": model.cohort_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.cohort_set[2].id,
                    "slug": model.cohort_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__append_to_new_balance___event_type_set__with_three_virtual_consumables(self, monkeypatch):
        from breathecode.payments.utils import reset_cache

        reset_cache()

        rand1 = random.randint(1, 9)
        rand2 = random.randint(1, 9)
        rand3 = random.randint(1, 9)

        monkeypatch.setattr(
            "breathecode.payments.data.get_virtual_consumables",
            get_virtual_consumables_mock(
                *[
                    {"resource": "event_type_set", "id": 4, "service": 2 + n, "how_many": rand1 * (1 + n)}
                    for n in range(3)
                ],
                *[
                    {"resource": "event_type_set", "id": 5, "service": 5 + n, "how_many": rand2 * (1 + n)}
                    for n in range(3)
                ],
                *[
                    {"resource": "event_type_set", "id": 6, "service": 8 + n, "how_many": rand3 * (1 + n)}
                    for n in range(3)
                ],
            ),
        )
        consumables = [
            {"how_many": random.randint(1, 30), "event_type_set_id": math.floor(n / 3) + 1} for n in range(9)
        ]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        academy = {"available_as_saas": False}

        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            event_type_set=6,
            academy=academy,
            service=(10, {"type": "EVENT_TYPE_SET"}),
            profile_academy=1,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?virtual=true"
        with patch(
            "breathecode.admissions.actions.is_no_saas_student_up_to_date_in_any_cohort", return_value=True
        ) as mock:
            response = self.client.get(url)
            mock.call_args_list == [call(model.user, default=False)]

        json = response.json()
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [],
            "event_type_sets": [
                {
                    "balance": {"unit": how_many_belong_to1},
                    "id": model.event_type_set[0].id,
                    "slug": model.event_type_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.event_type_set[1].id,
                    "slug": model.event_type_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.event_type_set[2].id,
                    "slug": model.event_type_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                #
                {
                    "balance": {
                        "unit": sum([rand1 * (1 + n) for n in range(3)]),
                    },
                    "id": model.event_type_set[3].id,
                    "slug": model.event_type_set[3].slug,
                    "items": [
                        {
                            "how_many": rand1 * (1 + n),
                            "id": None,
                            "unit_type": "UNIT",
                            "valid_until": None,
                            "plan_financing": None,
                            "subscription": None,
                            "subscription_seat": None,
                            "subscription_billing_team": None,
                            "user": model.user.id,
                        }
                        for n in range(3)
                    ],
                },
                {
                    "balance": {
                        "unit": sum([rand2 * (1 + n) for n in range(3)]),
                    },
                    "id": model.event_type_set[4].id,
                    "slug": model.event_type_set[4].slug,
                    "items": [
                        {
                            "how_many": rand2 * (1 + n),
                            "id": None,
                            "unit_type": "UNIT",
                            "valid_until": None,
                            "plan_financing": None,
                            "subscription": None,
                            "subscription_seat": None,
                            "subscription_billing_team": None,
                            "user": model.user.id,
                        }
                        for n in range(3)
                    ],
                },
                {
                    "balance": {
                        "unit": sum([rand3 * (1 + n) for n in range(3)]),
                    },
                    "id": model.event_type_set[5].id,
                    "slug": model.event_type_set[5].slug,
                    "items": [
                        {
                            "how_many": rand3 * (1 + n),
                            "id": None,
                            "unit_type": "UNIT",
                            "valid_until": None,
                            "plan_financing": None,
                            "subscription": None,
                            "subscription_seat": None,
                            "subscription_billing_team": None,
                            "user": model.user.id,
                        }
                        for n in range(3)
                    ],
                },
            ],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__append_to_new_balance___event_type_set__with_three_virtual_consumables__as_saas(self, monkeypatch):
        from breathecode.payments.utils import reset_cache

        reset_cache()

        rand1 = random.randint(1, 9)
        rand2 = random.randint(1, 9)
        rand3 = random.randint(1, 9)

        monkeypatch.setattr(
            "breathecode.payments.data.get_virtual_consumables",
            get_virtual_consumables_mock(
                *[
                    {"resource": "event_type_set", "id": 4, "service": 2 + n, "how_many": rand1 * (1 + n)}
                    for n in range(3)
                ],
                *[
                    {"resource": "event_type_set", "id": 5, "service": 5 + n, "how_many": rand2 * (1 + n)}
                    for n in range(3)
                ],
                *[
                    {"resource": "event_type_set", "id": 6, "service": 8 + n, "how_many": rand3 * (1 + n)}
                    for n in range(3)
                ],
            ),
        )
        consumables = [
            {"how_many": random.randint(1, 30), "event_type_set_id": math.floor(n / 3) + 1} for n in range(9)
        ]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        academy = {"available_as_saas": True}

        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            event_type_set=6,
            academy=academy,
            service=(10, {"type": "EVENT_TYPE_SET"}),
            profile_academy=1,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?virtual=true"
        with patch(
            "breathecode.admissions.actions.is_no_saas_student_up_to_date_in_any_cohort", return_value=False
        ) as mock:
            response = self.client.get(url)
            mock.call_args_list == [call(model.user, default=False)]

        json = response.json()
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [],
            "event_type_sets": [
                {
                    "balance": {"unit": how_many_belong_to1},
                    "id": model.event_type_set[0].id,
                    "slug": model.event_type_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.event_type_set[1].id,
                    "slug": model.event_type_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.event_type_set[2].id,
                    "slug": model.event_type_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__append_to_new_balance___mentorship_service_set__with_three_virtual_consumables(self, monkeypatch):
        from breathecode.payments.utils import reset_cache

        reset_cache()

        rand1 = random.randint(1, 9)
        rand2 = random.randint(1, 9)
        rand3 = random.randint(1, 9)

        monkeypatch.setattr(
            "breathecode.payments.data.get_virtual_consumables",
            get_virtual_consumables_mock(
                *[
                    {"resource": "mentorship_service_set", "id": 4, "service": 2 + n, "how_many": rand1 * (1 + n)}
                    for n in range(3)
                ],
                *[
                    {"resource": "mentorship_service_set", "id": 5, "service": 5 + n, "how_many": rand2 * (1 + n)}
                    for n in range(3)
                ],
                *[
                    {"resource": "mentorship_service_set", "id": 6, "service": 8 + n, "how_many": rand3 * (1 + n)}
                    for n in range(3)
                ],
            ),
        )
        consumables = [
            {"how_many": random.randint(1, 30), "mentorship_service_set_id": math.floor(n / 3) + 1} for n in range(9)
        ]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        academy = {"available_as_saas": False}

        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            mentorship_service_set=6,
            academy=academy,
            service=(10, {"type": "MENTORSHIP_SERVICE_SET"}),
            profile_academy=1,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?virtual=true"
        with patch(
            "breathecode.admissions.actions.is_no_saas_student_up_to_date_in_any_cohort", return_value=True
        ) as mock:
            response = self.client.get(url)
            mock.call_args_list == [call(model.user, default=False)]

        json = response.json()
        expected = {
            "mentorship_service_sets": [
                {
                    "balance": {"unit": how_many_belong_to1},
                    "id": model.mentorship_service_set[0].id,
                    "slug": model.mentorship_service_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.mentorship_service_set[1].id,
                    "slug": model.mentorship_service_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.mentorship_service_set[2].id,
                    "slug": model.mentorship_service_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                #
                {
                    "balance": {
                        "unit": sum([rand1 * (1 + n) for n in range(3)]),
                    },
                    "id": model.mentorship_service_set[3].id,
                    "slug": model.mentorship_service_set[3].slug,
                    "items": [
                        {
                            "how_many": rand1 * (1 + n),
                            "id": None,
                            "unit_type": "UNIT",
                            "valid_until": None,
                            "plan_financing": None,
                            "subscription": None,
                            "subscription_seat": None,
                            "subscription_billing_team": None,
                            "user": model.user.id,
                        }
                        for n in range(3)
                    ],
                },
                {
                    "balance": {
                        "unit": sum([rand2 * (1 + n) for n in range(3)]),
                    },
                    "id": model.mentorship_service_set[4].id,
                    "slug": model.mentorship_service_set[4].slug,
                    "items": [
                        {
                            "how_many": rand2 * (1 + n),
                            "id": None,
                            "unit_type": "UNIT",
                            "valid_until": None,
                            "plan_financing": None,
                            "subscription": None,
                            "subscription_seat": None,
                            "subscription_billing_team": None,
                            "user": model.user.id,
                        }
                        for n in range(3)
                    ],
                },
                {
                    "balance": {
                        "unit": sum([rand3 * (1 + n) for n in range(3)]),
                    },
                    "id": model.mentorship_service_set[5].id,
                    "slug": model.mentorship_service_set[5].slug,
                    "items": [
                        {
                            "how_many": rand3 * (1 + n),
                            "id": None,
                            "unit_type": "UNIT",
                            "valid_until": None,
                            "plan_financing": None,
                            "subscription": None,
                            "subscription_seat": None,
                            "subscription_billing_team": None,
                            "user": model.user.id,
                        }
                        for n in range(3)
                    ],
                },
            ],
            "cohort_sets": [],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__append_to_new_balance___mentorship_service_set__with_three_virtual_consumables__as_saas(
        self, monkeypatch
    ):
        from breathecode.payments.utils import reset_cache

        reset_cache()

        rand1 = random.randint(1, 9)
        rand2 = random.randint(1, 9)
        rand3 = random.randint(1, 9)

        monkeypatch.setattr(
            "breathecode.payments.data.get_virtual_consumables",
            get_virtual_consumables_mock(
                *[
                    {"resource": "mentorship_service_set", "id": 4, "service": 2 + n, "how_many": rand1 * (1 + n)}
                    for n in range(3)
                ],
                *[
                    {"resource": "mentorship_service_set", "id": 5, "service": 5 + n, "how_many": rand2 * (1 + n)}
                    for n in range(3)
                ],
                *[
                    {"resource": "mentorship_service_set", "id": 6, "service": 8 + n, "how_many": rand3 * (1 + n)}
                    for n in range(3)
                ],
            ),
        )
        consumables = [
            {"how_many": random.randint(1, 30), "mentorship_service_set_id": math.floor(n / 3) + 1} for n in range(9)
        ]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        academy = {"available_as_saas": True}

        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            mentorship_service_set=6,
            academy=academy,
            service=(10, {"type": "MENTORSHIP_SERVICE_SET"}),
            profile_academy=1,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?virtual=true"
        with patch(
            "breathecode.admissions.actions.is_no_saas_student_up_to_date_in_any_cohort", return_value=False
        ) as mock:
            response = self.client.get(url)
            mock.call_args_list == [call(model.user, default=False)]

        json = response.json()
        expected = {
            "mentorship_service_sets": [
                {
                    "balance": {"unit": how_many_belong_to1},
                    "id": model.mentorship_service_set[0].id,
                    "slug": model.mentorship_service_set[0].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.mentorship_service_set[1].id,
                    "slug": model.mentorship_service_set[1].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.mentorship_service_set[2].id,
                    "slug": model.mentorship_service_set[2].slug,
                    "items": [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            "cohort_sets": [],
            "event_type_sets": [],
            "voids": [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__append_to_new_balance___service__with_three_virtual_consumables(self, monkeypatch):
        from breathecode.payments.utils import reset_cache

        reset_cache()

        rand1 = random.randint(1, 9)
        rand2 = random.randint(1, 9)
        rand3 = random.randint(1, 9)

        monkeypatch.setattr(
            "breathecode.payments.data.get_virtual_consumables",
            get_virtual_consumables_mock(
                *[{"service": 4, "how_many": rand1 * (1 + n)} for n in range(3)],
                *[{"service": 5, "how_many": rand2 * (1 + n)} for n in range(3)],
                *[{"service": 6, "how_many": rand3 * (1 + n)} for n in range(3)],
            ),
        )

        consumables = [{"how_many": random.randint(1, 30), "service_item_id": math.floor(n / 3) + 1} for n in range(9)]
        service_items = [{"service_id": n + 1} for n in range(3)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        academy = {"available_as_saas": False}

        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            service_item=service_items,
            academy=academy,
            service=(6, {"type": "VOID"}),
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?virtual=true"
        with patch(
            "breathecode.admissions.actions.is_no_saas_student_up_to_date_in_any_cohort", return_value=True
        ) as mock:
            response = self.client.get(url)
            mock.call_args_list == [call(model.user, default=False)]

        json = response.json()
        consumables = [serialize_consumable(model.consumable[n]) for n in range(9)]
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [],
            "event_type_sets": [],
            "voids": [
                {
                    "balance": {"unit": how_many_belong_to1},
                    "id": model.service[0].id,
                    "slug": model.service[0].slug,
                    "items": consumables[:3],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.service[1].id,
                    "slug": model.service[1].slug,
                    "items": consumables[3:6],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.service[2].id,
                    "slug": model.service[2].slug,
                    "items": consumables[6:9],
                },
                #
                {
                    "balance": {
                        "unit": sum([rand1 * (1 + n) for n in range(3)]),
                    },
                    "id": model.service[3].id,
                    "slug": model.service[3].slug,
                    "items": [
                        {
                            "how_many": rand1 * (1 + n),
                            "id": None,
                            "unit_type": "UNIT",
                            "valid_until": None,
                            "plan_financing": None,
                            "subscription": None,
                            "subscription_seat": None,
                            "subscription_billing_team": None,
                            "user": model.user.id,
                        }
                        for n in range(3)
                    ],
                },
                {
                    "balance": {
                        "unit": sum([rand2 * (1 + n) for n in range(3)]),
                    },
                    "id": model.service[4].id,
                    "slug": model.service[4].slug,
                    "items": [
                        {
                            "how_many": rand2 * (1 + n),
                            "id": None,
                            "unit_type": "UNIT",
                            "valid_until": None,
                            "plan_financing": None,
                            "subscription": None,
                            "subscription_seat": None,
                            "subscription_billing_team": None,
                            "user": model.user.id,
                        }
                        for n in range(3)
                    ],
                },
                {
                    "balance": {
                        "unit": sum([rand3 * (1 + n) for n in range(3)]),
                    },
                    "id": model.service[5].id,
                    "slug": model.service[5].slug,
                    "items": [
                        {
                            "how_many": rand3 * (1 + n),
                            "id": None,
                            "unit_type": "UNIT",
                            "valid_until": None,
                            "plan_financing": None,
                            "subscription": None,
                            "subscription_seat": None,
                            "subscription_billing_team": None,
                            "user": model.user.id,
                        }
                        for n in range(3)
                    ],
                },
            ],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__append_to_new_balance___service__with_three_virtual_consumables__as_saas(self, monkeypatch):
        from breathecode.payments.utils import reset_cache

        reset_cache()

        rand1 = random.randint(1, 9)
        rand2 = random.randint(1, 9)
        rand3 = random.randint(1, 9)

        monkeypatch.setattr(
            "breathecode.payments.data.get_virtual_consumables",
            get_virtual_consumables_mock(
                *[{"service": 4, "how_many": rand1 * (1 + n)} for n in range(3)],
                *[{"service": 5, "how_many": rand2 * (1 + n)} for n in range(3)],
                *[{"service": 6, "how_many": rand3 * (1 + n)} for n in range(3)],
            ),
        )

        consumables = [{"how_many": random.randint(1, 30), "service_item_id": math.floor(n / 3) + 1} for n in range(9)]
        service_items = [{"service_id": n + 1} for n in range(3)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x["how_many"] for x in belong_to1])
        how_many_belong_to2 = sum([x["how_many"] for x in belong_to2])
        how_many_belong_to3 = sum([x["how_many"] for x in belong_to3])

        academy = {"available_as_saas": False}

        model = self.bc.database.create(
            user=1,
            consumable=consumables,
            service_item=service_items,
            academy=academy,
            service=(6, {"type": "VOID"}),
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_service_consumable") + "?virtual=true"
        with patch(
            "breathecode.admissions.actions.is_no_saas_student_up_to_date_in_any_cohort", return_value=False
        ) as mock:
            response = self.client.get(url)
            mock.call_args_list == [call(model.user, default=False)]

        json = response.json()
        consumables = [serialize_consumable(model.consumable[n]) for n in range(9)]
        expected = {
            "mentorship_service_sets": [],
            "cohort_sets": [],
            "event_type_sets": [],
            "voids": [
                {
                    "balance": {"unit": how_many_belong_to1},
                    "id": model.service[0].id,
                    "slug": model.service[0].slug,
                    "items": consumables[:3],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to2,
                    },
                    "id": model.service[1].id,
                    "slug": model.service[1].slug,
                    "items": consumables[3:6],
                },
                {
                    "balance": {
                        "unit": how_many_belong_to3,
                    },
                    "id": model.service[2].id,
                    "slug": model.service[2].slug,
                    "items": consumables[6:9],
                },
            ],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            self.bc.format.to_dict(model.consumable),
        )
