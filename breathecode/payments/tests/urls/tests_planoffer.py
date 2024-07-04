from datetime import timedelta
import math
import random
from unittest.mock import MagicMock, call, patch
from rest_framework.authtoken.models import Token

from django.urls import reverse_lazy
from rest_framework import status

from breathecode.payments import signals

from django.utils import timezone
from ..mixins import PaymentsTestCase

UTC_NOW = timezone.now()


def permission_serializer(permission):
    return {
        "codename": permission.codename,
        "name": permission.name,
    }


def group_serializer(group, permissions=[]):
    return {
        "name": group.name,
        "permissions": [permission_serializer(permission) for permission in permissions],
    }


def service_serializer(service, groups=[], permissions=[]):
    return {
        "private": service.private,
        "slug": service.slug,
        "title": service.title,
        "icon_url": service.icon_url,
        "groups": [group_serializer(group, permissions) for group in groups],
    }


def service_item_serializer(self, service_item, service, groups=[], permissions=[]):
    return {
        "how_many": service_item.how_many,
        "unit_type": service_item.unit_type,
        "sort_priority": service_item.sort_priority,
        "service": service_serializer(service, groups, permissions),
    }


def currency_serializer(currency):
    return {
        "code": currency.code,
        "name": currency.name,
    }


def plan_serializer(self, plan, service, currency, groups=[], permissions=[], service_items=[]):
    return {
        "financing_options": [],
        "service_items": [
            service_item_serializer(self, service_item, service, groups, permissions) for service_item in service_items
        ],
        "currency": currency_serializer(currency),
        "slug": plan.slug,
        "status": plan.status,
        "time_of_life": plan.time_of_life,
        "time_of_life_unit": plan.time_of_life_unit,
        "trial_duration": plan.trial_duration,
        "trial_duration_unit": plan.trial_duration_unit,
        "has_waiting_list": plan.has_waiting_list,
        "is_renewable": plan.is_renewable,
        "owner": plan.owner,
        "price_per_half": plan.price_per_half,
        "price_per_month": plan.price_per_month,
        "price_per_quarter": plan.price_per_quarter,
        "price_per_year": plan.price_per_year,
        "has_available_cohorts": bool(plan.cohort_set),
    }


def plan_offer_transaction_serializer(plan_offer_transaction):
    return {
        "lang": plan_offer_transaction.lang,
        "title": plan_offer_transaction.title,
        "description": plan_offer_transaction.description,
        "short_description": plan_offer_transaction.short_description,
    }


def get_serializer(
    self,
    plan_offer,
    plan1,
    plan2,
    service,
    currency,
    plan_offer_translation=None,
    groups=[],
    permissions=[],
    service_items=[],
):

    if plan_offer_translation:
        plan_offer_translation = plan_offer_transaction_serializer(plan_offer_translation)

    return {
        "details": plan_offer_translation,
        "original_plan": plan_serializer(self, plan1, service, currency, groups, permissions, service_items),
        "suggested_plan": plan_serializer(self, plan2, service, currency, groups, permissions, service_items),
        "show_modal": plan_offer.show_modal,
        "expires_at": self.bc.datetime.to_iso_string(plan_offer.expires_at) if plan_offer.expires_at else None,
    }


class SignalTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 GET without auth
    """

    def test__without_auth__without_service_items(self):
        url = reverse_lazy("payments:planoffer")
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.PlanOffer"), [])

    def test__without_auth__with_plan_offer__expires_at_eq_none(self):
        plan_service_items = [{"service_item_id": n, "plan_id": 1} for n in range(1, 3)]
        plan_service_items += [{"service_item_id": n, "plan_id": 2} for n in range(1, 3)]

        plan_offer = {
            "original_plan_id": 1,
            "suggested_plan_id": 2,
            "show_modal": bool(random.getrandbits(1)),
            "expires_at": None,
        }

        plan = {"is_renewable": False}

        model = self.bc.database.create(
            plan=(2, plan),
            service=1,
            service_item=2,
            plan_offer=plan_offer,
            plan_service_item=plan_service_items,
            group=2,
            permission=1,
        )

        url = reverse_lazy("payments:planoffer")
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                self,
                model.plan_offer,
                model.plan[0],
                model.plan[1],
                model.service,
                model.currency,
                groups=model.group,
                permissions=[model.permission],
                service_items=model.service_item,
            )
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.PlanOffer"),
            [
                self.bc.format.to_dict(model.plan_offer),
            ],
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__without_auth__with_plan_offer__expires_at_in_the_future(self):
        plan_service_items = [{"service_item_id": n, "plan_id": 1} for n in range(1, 3)]
        plan_service_items += [{"service_item_id": n, "plan_id": 2} for n in range(1, 3)]

        plan_offer = {
            "original_plan_id": 1,
            "suggested_plan_id": 2,
            "show_modal": bool(random.getrandbits(1)),
            "expires_at": UTC_NOW + timedelta(seconds=random.randint(1, 60)),
        }

        plan = {"is_renewable": False}

        model = self.bc.database.create(
            plan=(2, plan),
            service=1,
            service_item=2,
            plan_offer=plan_offer,
            plan_service_item=plan_service_items,
            group=2,
            permission=1,
        )

        url = reverse_lazy("payments:planoffer")
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                self,
                model.plan_offer,
                model.plan[0],
                model.plan[1],
                model.service,
                model.currency,
                groups=model.group,
                permissions=[model.permission],
                service_items=model.service_item,
            )
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.PlanOffer"),
            [
                self.bc.format.to_dict(model.plan_offer),
            ],
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__without_auth__with_plan_offer__expires_at_in_the_past(self):
        plan_service_items = [{"service_item_id": n, "plan_id": 1} for n in range(1, 3)]
        plan_service_items += [{"service_item_id": n, "plan_id": 2} for n in range(1, 3)]

        plan_offer = {
            "original_plan_id": 1,
            "suggested_plan_id": 2,
            "show_modal": bool(random.getrandbits(1)),
            "expires_at": UTC_NOW - timedelta(seconds=random.randint(1, 60)),
        }

        plan = {"is_renewable": False}

        model = self.bc.database.create(
            plan=(2, plan),
            service=1,
            service_item=2,
            plan_offer=plan_offer,
            plan_service_item=plan_service_items,
            group=2,
            permission=1,
        )

        url = reverse_lazy("payments:planoffer")
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.PlanOffer"),
            [
                self.bc.format.to_dict(model.plan_offer),
            ],
        )

    def test__without_auth__with_plan_offer_transaction(self):
        plan_service_items = [{"service_item_id": n, "plan_id": 1} for n in range(1, 3)]
        plan_service_items += [{"service_item_id": n, "plan_id": 2} for n in range(1, 3)]

        plan_offers = [
            {"original_plan_id": 1, "suggested_plan_id": 2, "show_modal": bool(random.getrandbits(1))},
            {"original_plan_id": 2, "suggested_plan_id": 1, "show_modal": bool(random.getrandbits(1))},
        ]

        plan_offer_translation = [
            {
                "lang": "en",
                "offer_id": n,
            }
            for n in range(1, 3)
        ]

        plan = {"is_renewable": False}

        model = self.bc.database.create(
            plan=(4, plan),
            service=1,
            service_item=2,
            plan_offer=plan_offers,
            plan_service_item=plan_service_items,
            group=2,
            permission=1,
            plan_offer_translation=plan_offer_translation,
        )

        url = reverse_lazy("payments:planoffer")
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                self,
                model.plan_offer[1],
                model.plan[1],
                model.plan[0],
                model.service,
                model.currency,
                plan_offer_translation=model.plan_offer_translation[1],
                groups=model.group,
                permissions=[model.permission],
                service_items=model.service_item,
            ),
            get_serializer(
                self,
                model.plan_offer[0],
                model.plan[0],
                model.plan[1],
                model.service,
                model.currency,
                plan_offer_translation=model.plan_offer_translation[0],
                groups=model.group,
                permissions=[model.permission],
                service_items=model.service_item,
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.PlanOffer"),
            self.bc.format.to_dict(model.plan_offer),
        )

    def test__without_auth__filter_by_original_plan(self):
        plan_service_items = [{"service_item_id": n, "plan_id": 1} for n in range(1, 3)]
        plan_service_items += [{"service_item_id": n, "plan_id": 2} for n in range(1, 3)]

        plan_offers = [
            {"original_plan_id": 1, "suggested_plan_id": 2, "show_modal": bool(random.getrandbits(1))},
            {"original_plan_id": 2, "suggested_plan_id": 1, "show_modal": bool(random.getrandbits(1))},
        ]

        plan_offer_translation = [
            {
                "lang": "en",
                "offer_id": n,
            }
            for n in range(1, 3)
        ]

        plan = {"is_renewable": False}

        model = self.bc.database.create(
            plan=(4, plan),
            service=1,
            service_item=2,
            plan_offer=plan_offers,
            plan_service_item=plan_service_items,
            group=2,
            permission=1,
            plan_offer_translation=plan_offer_translation,
        )

        url = (
            reverse_lazy("payments:planoffer")
            + f"?original_plan={random.choice([model.plan[0].id, model.plan[0].slug])}"
        )
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                self,
                model.plan_offer[0],
                model.plan[0],
                model.plan[1],
                model.service,
                model.currency,
                plan_offer_translation=model.plan_offer_translation[0],
                groups=model.group,
                permissions=[model.permission],
                service_items=model.service_item,
            )
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.PlanOffer"),
            self.bc.format.to_dict(model.plan_offer),
        )

    def test__without_auth__filter_by_suggested_plan(self):
        plan_service_items = [{"service_item_id": n, "plan_id": 1} for n in range(1, 3)]
        plan_service_items += [{"service_item_id": n, "plan_id": 2} for n in range(1, 3)]

        plan_offers = [
            {"original_plan_id": 1, "suggested_plan_id": 2, "show_modal": bool(random.getrandbits(1))},
            {"original_plan_id": 2, "suggested_plan_id": 1, "show_modal": bool(random.getrandbits(1))},
        ]

        plan_offer_translation = [
            {
                "lang": "en",
                "offer_id": n,
            }
            for n in range(1, 3)
        ]

        plan = {"is_renewable": False}

        model = self.bc.database.create(
            plan=(4, plan),
            service=1,
            service_item=2,
            plan_offer=plan_offers,
            plan_service_item=plan_service_items,
            group=2,
            permission=1,
            plan_offer_translation=plan_offer_translation,
        )

        url = (
            reverse_lazy("payments:planoffer")
            + f"?suggested_plan={random.choice([model.plan[1].id, model.plan[1].slug])}"
        )
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                self,
                model.plan_offer[0],
                model.plan[0],
                model.plan[1],
                model.service,
                model.currency,
                plan_offer_translation=model.plan_offer_translation[0],
                groups=model.group,
                permissions=[model.permission],
                service_items=model.service_item,
            )
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.PlanOffer"),
            self.bc.format.to_dict(model.plan_offer),
        )
