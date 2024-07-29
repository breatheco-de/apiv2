import math
import random
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

import pytest
from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status

import breathecode.activity.tasks as activity_tasks

from ..mixins import PaymentsTestCase

UTC_NOW = timezone.now()


def academy_serializer(academy):
    return {
        "id": academy.id,
        "name": academy.name,
        "slug": academy.slug,
    }


def currency_serializer(currency):
    return {
        "code": currency.code,
        "name": currency.name,
    }


def user_serializer(user):
    return {
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }


def invoice_serializer(self, invoice, currency, user):
    return {
        "amount": invoice.amount,
        "currency": currency_serializer(currency),
        "paid_at": self.bc.datetime.to_iso_string(invoice.paid_at),
        "status": invoice.status,
        "user": user_serializer(user),
    }


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


def plan_serializer(self, plan, service, groups=[], permissions=[], service_items=[]):
    return {
        "financing_options": [],
        "service_items": [
            service_item_serializer(self, service_item, service, groups, permissions) for service_item in service_items
        ],
        "slug": plan.slug,
        "status": plan.status,
        "time_of_life": plan.time_of_life,
        "time_of_life_unit": plan.time_of_life_unit,
        "trial_duration": plan.trial_duration,
        "trial_duration_unit": plan.trial_duration_unit,
        "has_available_cohorts": bool(plan.cohort_set),
    }


def get_mentorship_service_serializer(mentorship_service, academy):
    return {
        "academy": {
            "id": academy.id,
            "name": academy.name,
            "slug": academy.slug,
        },
        "id": mentorship_service.id,
    }


def get_mentorship_service_set_serializer(mentorship_service_set, academy, mentorship_services=[]):
    return {
        "academy": {
            "id": academy.id,
            "name": academy.name,
            "slug": academy.slug,
        },
        "id": mentorship_service_set.id,
        "mentorship_services": [
            get_mentorship_service_serializer(mentorship_service, academy) for mentorship_service in mentorship_services
        ],
        "slug": mentorship_service_set.slug,
        "academy_services": [],
    }


def get_event_type_serializer(event_type, academy):
    return {
        "academy": {
            "id": academy.id,
            "name": academy.name,
            "slug": academy.slug,
        },
        "id": event_type.id,
    }


def get_event_type_set_serializer(event_type_set, academy, event_types=[]):
    return {
        "academy": {
            "id": academy.id,
            "name": academy.name,
            "slug": academy.slug,
        },
        "id": event_type_set.id,
        "event_types": [get_event_type_serializer(event_type, academy) for event_type in event_types],
        "slug": event_type_set.slug,
        "academy_services": [],
    }


def get_academy_serializer(academy):
    return {
        "id": academy.id,
        "slug": academy.slug,
        "name": academy.name,
    }


def get_cohort_serializer(cohort):
    return {
        "id": cohort.id,
        "slug": cohort.slug,
        "name": cohort.name,
    }


def get_cohort_set_serializer(cohort_set, academy, cohorts=[]):
    return {
        "academy": get_academy_serializer(academy),
        "cohorts": [get_cohort_serializer(cohort) for cohort in cohorts],
        "id": cohort_set.id,
        "slug": cohort_set.slug,
    }


def get_plan_financing_serializer(
    self,
    plan_financing,
    academy,
    currency,
    user,
    service,
    mentorship_service_set=None,
    event_type_set=None,
    cohort_set=None,
    invoices=[],
    financing_options=[],
    plans=[],
    groups=[],
    permissions=[],
    service_items=[],
    mentorship_services=[],
    event_types=[],
    cohorts=[],
):

    if cohort_set:
        cohort_set = get_cohort_set_serializer(cohort_set, academy, cohorts=cohorts)

    if mentorship_service_set:
        mentorship_service_set = get_mentorship_service_set_serializer(
            mentorship_service_set, academy, mentorship_services=mentorship_services
        )

    if event_type_set:
        event_type_set = get_event_type_set_serializer(event_type_set, academy, event_types=event_types)

    return {
        "id": plan_financing.id,
        "academy": academy_serializer(academy),
        "invoices": [invoice_serializer(self, invoice, currency, user) for invoice in invoices],
        "valid_until": self.bc.datetime.to_iso_string(plan_financing.valid_until),
        "next_payment_at": self.bc.datetime.to_iso_string(plan_financing.next_payment_at),
        "plan_expires_at": self.bc.datetime.to_iso_string(plan_financing.plan_expires_at),
        "plans": [plan_serializer(self, plan, service, groups, permissions, service_items) for plan in plans],
        "selected_mentorship_service_set": mentorship_service_set,
        "selected_event_type_set": event_type_set,
        "selected_cohort_set": cohort_set,
        "status": plan_financing.status,
        "monthly_price": plan_financing.monthly_price,
        "status_message": plan_financing.status_message,
        "user": user_serializer(user),
    }


def get_subscription_serializer(
    self,
    subscription,
    academy,
    currency,
    user,
    service,
    mentorship_service_set=None,
    event_type_set=None,
    cohort_set=None,
    invoices=[],
    financing_options=[],
    plans=[],
    groups=[],
    permissions=[],
    service_items=[],
    mentorship_services=[],
    event_types=[],
    cohorts=[],
):
    valid_until = self.bc.datetime.to_iso_string(subscription.valid_until) if subscription.valid_until else None

    if cohort_set:
        cohort_set = get_cohort_set_serializer(cohort_set, academy, cohorts=cohorts)

    if mentorship_service_set:
        mentorship_service_set = get_mentorship_service_set_serializer(
            mentorship_service_set, academy, mentorship_services=mentorship_services
        )

    if event_type_set:
        event_type_set = get_event_type_set_serializer(event_type_set, academy, event_types=event_types)

    return {
        "id": subscription.id,
        "academy": academy_serializer(academy),
        "invoices": [invoice_serializer(self, invoice, currency, user) for invoice in invoices],
        "paid_at": self.bc.datetime.to_iso_string(subscription.paid_at),
        "valid_until": valid_until,
        "plans": [plan_serializer(self, plan, service, groups, permissions, service_items) for plan in plans],
        "status": subscription.status,
        "status_message": subscription.status_message,
        "is_refundable": subscription.is_refundable,
        "next_payment_at": self.bc.datetime.to_iso_string(subscription.next_payment_at),
        "pay_every": subscription.pay_every,
        "pay_every_unit": subscription.pay_every_unit,
        "selected_mentorship_service_set": mentorship_service_set,
        "selected_event_type_set": event_type_set,
        "selected_cohort_set": cohort_set,
        "user": user_serializer(user),
        "service_items": [
            service_item_serializer(self, service_item, service, groups, permissions) for service_item in service_items
        ],
    }


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setattr(activity_tasks.add_activity, "delay", MagicMock())
    yield


class SignalTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 GET without auth
    """

    def test__without_auth(self):
        url = reverse_lazy("payments:me_subscription")
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    """
    🔽🔽🔽 Get without items
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__without_items(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription")
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {"plan_financings": [], "subscriptions": []}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_many_items(self):
        subscriptions = [
            {
                "valid_until": x,
            }
            for x in [None, UTC_NOW + timedelta(days=1)]
        ]
        plan_financing = {
            "valid_until": UTC_NOW + timedelta(days=1),
            "plan_expires_at": UTC_NOW + timedelta(days=1),
            "monthly_price": random.random() * 99.99 + 0.01,
        }

        plan_service_items = [{"service_item_id": x, "plan_id": 1} for x in range(1, 3)]
        plan_service_items += [{"service_item_id": x, "plan_id": 2} for x in range(1, 3)]
        subscription_service_items = [{"service_item_id": x, "subscription_id": 1} for x in range(1, 3)]
        subscription_service_items += [{"service_item_id": x, "subscription_id": 2} for x in range(1, 3)]
        plan = {"is_renewable": False}
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=(2, plan),
            service_item=2,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription")
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "plan_financings": [
                get_plan_financing_serializer(
                    self,
                    model.plan_financing[1],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
                get_plan_financing_serializer(
                    self,
                    model.plan_financing[0],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
            ],
            "subscriptions": [
                get_subscription_serializer(
                    self,
                    model.subscription[1],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
                get_subscription_serializer(
                    self,
                    model.subscription[0],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by subscription
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_subscription(self):
        subscriptions = [
            {
                "valid_until": x,
            }
            for x in [None, UTC_NOW + timedelta(days=1)]
        ]
        plan_financing = {
            "valid_until": UTC_NOW + timedelta(days=1),
            "plan_expires_at": UTC_NOW + timedelta(days=1),
            "monthly_price": random.random() * 99.99 + 0.01,
        }
        plan_service_items = [{"service_item_id": x, "plan_id": 1} for x in range(1, 3)]
        plan_service_items += [{"service_item_id": x, "plan_id": 2} for x in range(1, 3)]
        subscription_service_items = [{"service_item_id": x, "subscription_id": 1} for x in range(1, 3)]
        subscription_service_items += [{"service_item_id": x, "subscription_id": 2} for x in range(1, 3)]
        plan = {"is_renewable": False}
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=(2, plan),
            service_item=2,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription") + f"?subscription={model.subscription[0].id}"
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "plan_financings": [],
            "subscriptions": [
                get_subscription_serializer(
                    self,
                    model.subscription[0],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by plan financing
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_plan_financing(self):
        subscriptions = [
            {
                "valid_until": x,
            }
            for x in [None, UTC_NOW + timedelta(days=1)]
        ]
        plan_financing = {
            "valid_until": UTC_NOW + timedelta(days=1),
            "plan_expires_at": UTC_NOW + timedelta(days=1),
            "monthly_price": random.random() * 99.99 + 0.01,
        }
        plan_service_items = [{"service_item_id": x, "plan_id": 1} for x in range(1, 3)]
        plan_service_items += [{"service_item_id": x, "plan_id": 2} for x in range(1, 3)]
        subscription_service_items = [{"service_item_id": x, "subscription_id": 1} for x in range(1, 3)]
        subscription_service_items += [{"service_item_id": x, "subscription_id": 2} for x in range(1, 3)]
        plan = {"is_renewable": False}
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=(2, plan),
            service_item=2,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription") + f"?plan-financing={model.plan_financing[0].id}"
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "plan_financings": [
                get_plan_financing_serializer(
                    self,
                    model.plan_financing[0],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
            ],
            "subscriptions": [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by subscription and plan financing
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_subscription_and_plan_financing(self):
        subscriptions = [
            {
                "valid_until": x,
            }
            for x in [None, UTC_NOW + timedelta(days=1)]
        ]
        plan_financing = {
            "valid_until": UTC_NOW + timedelta(days=1),
            "plan_expires_at": UTC_NOW + timedelta(days=1),
            "monthly_price": random.random() * 99.99 + 0.01,
        }
        plan_service_items = [{"service_item_id": x, "plan_id": 1} for x in range(1, 3)]
        plan_service_items += [{"service_item_id": x, "plan_id": 2} for x in range(1, 3)]
        subscription_service_items = [{"service_item_id": x, "subscription_id": 1} for x in range(1, 3)]
        subscription_service_items += [{"service_item_id": x, "subscription_id": 2} for x in range(1, 3)]
        plan = {"is_renewable": False}
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=(2, plan),
            service_item=2,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription") + (
            f"?subscription={model.subscription[0].id}&" f"plan-financing={model.plan_financing[0].id}"
        )
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "plan_financings": [
                get_plan_financing_serializer(
                    self,
                    model.plan_financing[0],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
            ],
            "subscriptions": [
                get_subscription_serializer(
                    self,
                    model.subscription[0],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, with wrong statuses
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_many_items__with_wrong_statuses(self):
        wrong_statuses = ["PAYMENT_ISSUE", "DEPRECATED", "CANCELLED"]
        subscriptions = [
            {
                "valid_until": x,
                "status": random.choice(wrong_statuses),
            }
            for x in [None, UTC_NOW + timedelta(days=1)]
        ]
        plan_financing = {
            "valid_until": UTC_NOW + timedelta(days=1),
            "plan_expires_at": UTC_NOW + timedelta(days=1),
            "status": random.choice(wrong_statuses),
            "monthly_price": random.random() * 99.99 + 0.01,
        }
        plan_service_items = [{"service_item_id": x, "plan_id": 1} for x in range(1, 3)]
        plan_service_items += [{"service_item_id": x, "plan_id": 2} for x in range(1, 3)]
        subscription_service_items = [{"service_item_id": x, "subscription_id": 1} for x in range(1, 3)]
        subscription_service_items += [{"service_item_id": x, "subscription_id": 2} for x in range(1, 3)]
        plan = {"is_renewable": False}
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=(2, plan),
            service_item=2,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription")
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "plan_financings": [],
            "subscriptions": [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by status
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_statuses(self):
        statuses = ["FREE_TRIAL", "ACTIVE", "PAYMENT_ISSUE", "DEPRECATED", "CANCELLED", "ERROR"]
        chosen_statuses = [random.choice(statuses) for _ in range(2)]
        subscriptions = [
            {
                "valid_until": x,
                "status": random.choice(chosen_statuses),
            }
            for x in [None, UTC_NOW + timedelta(days=1)]
        ]
        plan_financing = {
            "valid_until": UTC_NOW + timedelta(days=1),
            "plan_expires_at": UTC_NOW + timedelta(days=1),
            "status": random.choice(chosen_statuses),
            "monthly_price": random.random() * 99.99 + 0.01,
        }
        plan_service_items = [{"service_item_id": x, "plan_id": 1} for x in range(1, 3)]
        plan_service_items += [{"service_item_id": x, "plan_id": 2} for x in range(1, 3)]
        subscription_service_items = [{"service_item_id": x, "subscription_id": 1} for x in range(1, 3)]
        subscription_service_items += [{"service_item_id": x, "subscription_id": 2} for x in range(1, 3)]
        plan = {"is_renewable": False}
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=(2, plan),
            service_item=2,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription") + (f"?status={chosen_statuses[0]}," f"{chosen_statuses[1]}")
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "plan_financings": [
                get_plan_financing_serializer(
                    self,
                    model.plan_financing[1],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
                get_plan_financing_serializer(
                    self,
                    model.plan_financing[0],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
            ],
            "subscriptions": [
                get_subscription_serializer(
                    self,
                    model.subscription[1],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
                get_subscription_serializer(
                    self,
                    model.subscription[0],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by wrong invoice
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_wrong_invoice(self):
        statuses = ["FREE_TRIAL", "ACTIVE", "PAYMENT_ISSUE", "DEPRECATED", "CANCELLED", "ERROR"]
        chosen_statuses = [random.choice(statuses) for _ in range(2)]
        subscriptions = [
            {
                "valid_until": x,
                "status": random.choice(chosen_statuses),
            }
            for x in [None, UTC_NOW + timedelta(days=1)]
        ]
        plan_financing = {
            "valid_until": UTC_NOW + timedelta(days=1),
            "plan_expires_at": UTC_NOW + timedelta(days=1),
            "status": random.choice(chosen_statuses),
            "monthly_price": random.random() * 99.99 + 0.01,
        }
        plan_service_items = [{"service_item_id": x, "plan_id": 1} for x in range(1, 3)]
        plan_service_items += [{"service_item_id": x, "plan_id": 2} for x in range(1, 3)]
        subscription_service_items = [{"service_item_id": x, "subscription_id": 1} for x in range(1, 3)]
        subscription_service_items += [{"service_item_id": x, "subscription_id": 2} for x in range(1, 3)]
        plan = {"is_renewable": False}
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=(2, plan),
            service_item=2,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription") + (f"?invoice=3,4")
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "plan_financings": [],
            "subscriptions": [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by good invoice
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_good_invoice(self):
        subscriptions = [
            {
                "valid_until": x,
            }
            for x in [None, UTC_NOW + timedelta(days=1)]
        ]
        plan_financing = {
            "valid_until": UTC_NOW + timedelta(days=1),
            "plan_expires_at": UTC_NOW + timedelta(days=1),
            "monthly_price": random.random() * 99.99 + 0.01,
        }
        plan_service_items = [{"service_item_id": x, "plan_id": 1} for x in range(1, 3)]
        plan_service_items += [{"service_item_id": x, "plan_id": 2} for x in range(1, 3)]
        subscription_service_items = [{"service_item_id": x, "subscription_id": 1} for x in range(1, 3)]
        subscription_service_items += [{"service_item_id": x, "subscription_id": 2} for x in range(1, 3)]
        plan = {"is_renewable": False}
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=(2, plan),
            service_item=2,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription") + "?invoice=1,2"
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "plan_financings": [
                get_plan_financing_serializer(
                    self,
                    model.plan_financing[1],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
                get_plan_financing_serializer(
                    self,
                    model.plan_financing[0],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
            ],
            "subscriptions": [
                get_subscription_serializer(
                    self,
                    model.subscription[1],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
                get_subscription_serializer(
                    self,
                    model.subscription[0],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by wrong service
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_wrong_service(self):
        statuses = ["FREE_TRIAL", "ACTIVE", "PAYMENT_ISSUE", "DEPRECATED", "CANCELLED", "ERROR"]
        chosen_statuses = [random.choice(statuses) for _ in range(2)]
        subscriptions = [
            {
                "valid_until": x,
                "status": random.choice(chosen_statuses),
            }
            for x in [None, UTC_NOW + timedelta(days=1)]
        ]
        plan_financing = {
            "valid_until": UTC_NOW + timedelta(days=1),
            "plan_expires_at": UTC_NOW + timedelta(days=1),
            "status": random.choice(chosen_statuses),
            "monthly_price": random.random() * 99.99 + 0.01,
        }
        plan_service_items = [{"service_item_id": x, "plan_id": 1} for x in range(1, 3)]
        plan_service_items += [{"service_item_id": x, "plan_id": 2} for x in range(1, 3)]
        subscription_service_items = [{"service_item_id": x, "subscription_id": 1} for x in range(1, 3)]
        subscription_service_items += [{"service_item_id": x, "subscription_id": 2} for x in range(1, 3)]
        plan = {"is_renewable": False}
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=(2, plan),
            service_item=2,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription") + (
            f'?invoice={random.choice([3, "gangsters-i"])},' f'{random.choice([4, "gangsters-ii"])}'
        )
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "plan_financings": [],
            "subscriptions": [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by good service
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_good_service(self):
        subscriptions = [
            {
                "valid_until": x,
            }
            for x in [None, UTC_NOW + timedelta(days=1)]
        ]
        plan_financing = {
            "valid_until": UTC_NOW + timedelta(days=1),
            "plan_expires_at": UTC_NOW + timedelta(days=1),
            "monthly_price": random.random() * 99.99 + 0.01,
        }
        plan_service_items = [{"service_item_id": x, "plan_id": 1} for x in range(1, 3)]
        plan_service_items += [{"service_item_id": x, "plan_id": 2} for x in range(1, 3)]
        subscription_service_items = [{"service_item_id": x, "subscription_id": 1} for x in range(1, 3)]
        subscription_service_items += [{"service_item_id": x, "subscription_id": 2} for x in range(1, 3)]
        plan = {"is_renewable": False}
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=(2, plan),
            service_item=2,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription") + (
            f"?service={random.choice([model.service.id, model.service.slug])},"
            f"{random.choice([model.service.id, model.service.slug])}"
        )
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "plan_financings": [
                get_plan_financing_serializer(
                    self,
                    model.plan_financing[1],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
                get_plan_financing_serializer(
                    self,
                    model.plan_financing[0],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
            ],
            "subscriptions": [
                get_subscription_serializer(
                    self,
                    model.subscription[1],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
                get_subscription_serializer(
                    self,
                    model.subscription[0],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by wrong plan
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_wrong_plan(self):
        statuses = ["FREE_TRIAL", "ACTIVE", "PAYMENT_ISSUE", "DEPRECATED", "CANCELLED", "ERROR"]
        chosen_statuses = [random.choice(statuses) for _ in range(2)]
        subscriptions = [
            {
                "valid_until": x,
                "status": random.choice(chosen_statuses),
            }
            for x in [None, UTC_NOW + timedelta(days=1)]
        ]
        plan_financing = {
            "valid_until": UTC_NOW + timedelta(days=1),
            "status": random.choice(chosen_statuses),
            "plan_expires_at": UTC_NOW + timedelta(days=1),
            "monthly_price": random.random() * 99.99 + 0.01,
        }
        plan_service_items = [{"service_item_id": x, "plan_id": 1} for x in range(1, 3)]
        plan_service_items += [{"service_item_id": x, "plan_id": 2} for x in range(1, 3)]
        subscription_service_items = [{"service_item_id": x, "subscription_id": 1} for x in range(1, 3)]
        subscription_service_items += [{"service_item_id": x, "subscription_id": 2} for x in range(1, 3)]
        plan = {"is_renewable": False}
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=(2, plan),
            service_item=2,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription") + (
            f'?plan={random.choice([3, "gangsters-i"])},' f'{random.choice([4, "gangsters-ii"])}'
        )
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "plan_financings": [],
            "subscriptions": [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by good plan
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_good_plan(self):
        subscriptions = [
            {
                "valid_until": x,
            }
            for x in [None, UTC_NOW + timedelta(days=1)]
        ]
        plan_financing = {
            "valid_until": UTC_NOW + timedelta(days=1),
            "plan_expires_at": UTC_NOW + timedelta(days=1),
            "monthly_price": random.random() * 99.99 + 0.01,
        }
        plan_service_items = [{"service_item_id": x, "plan_id": 1} for x in range(1, 3)]
        plan_service_items += [{"service_item_id": x, "plan_id": 2} for x in range(1, 3)]
        subscription_service_items = [{"service_item_id": x, "subscription_id": 1} for x in range(1, 3)]
        subscription_service_items += [{"service_item_id": x, "subscription_id": 2} for x in range(1, 3)]
        plan = {"is_renewable": False}
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=(2, plan),
            service_item=2,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription") + (
            f"?plan={random.choice([model.plan[0].id, model.plan[0].slug])},"
            f"{random.choice([model.plan[1].id, model.plan[1].slug])}"
        )
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "plan_financings": [
                get_plan_financing_serializer(
                    self,
                    model.plan_financing[1],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
                get_plan_financing_serializer(
                    self,
                    model.plan_financing[0],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
            ],
            "subscriptions": [
                get_subscription_serializer(
                    self,
                    model.subscription[1],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
                get_subscription_serializer(
                    self,
                    model.subscription[0],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by wrong cohort
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_wrong_cohort(self):
        subscriptions = [
            {
                "valid_until": x,
                "selected_cohort_set_id": None,
            }
            for x in [None, UTC_NOW + timedelta(days=1)]
        ]
        plan_financings = [
            {
                "valid_until": UTC_NOW + timedelta(days=1),
                "plan_expires_at": UTC_NOW + timedelta(days=1),
                "monthly_price": random.random() * 99.99 + 0.01,
                "selected_cohort_set_id": None,
            }
            for _ in range(1, 3)
        ]
        plan_service_items = [{"service_item_id": x, "plan_id": 1} for x in range(1, 3)]
        plan_service_items += [{"service_item_id": x, "plan_id": 2} for x in range(1, 3)]
        subscription_service_items = [{"service_item_id": x, "subscription_id": 1} for x in range(1, 3)]
        subscription_service_items += [{"service_item_id": x, "subscription_id": 2} for x in range(1, 3)]
        plan = {"is_renewable": False}
        academy = {"available_as_saas": True}
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=plan_financings,
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=(2, plan),
            service_item=2,
            cohort_set=2,
            academy=academy,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription") + (
            f'?cohort-set-selected={random.choice([1, "slug1"])},' f'{random.choice([2, "slug2"])}'
        )
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "plan_financings": [],
            "subscriptions": [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by good cohort
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_good_cohort(self):
        subscriptions = [
            {
                "valid_until": x,
                "selected_cohort_set_id": y,
            }
            for x, y in [(None, 1), (UTC_NOW + timedelta(days=1), 2)]
        ]
        plan_financings = [
            {
                "valid_until": UTC_NOW + timedelta(days=1),
                "plan_expires_at": UTC_NOW + timedelta(days=1),
                "monthly_price": random.random() * 99.99 + 0.01,
                "selected_cohort_set_id": x,
            }
            for x in range(1, 3)
        ]
        plan_service_items = [{"service_item_id": x, "plan_id": 1} for x in range(1, 3)]
        plan_service_items += [{"service_item_id": x, "plan_id": 2} for x in range(1, 3)]
        subscription_service_items = [{"service_item_id": x, "subscription_id": 1} for x in range(1, 3)]
        subscription_service_items += [{"service_item_id": x, "subscription_id": 2} for x in range(1, 3)]
        plan = {"is_renewable": False}
        cohort_set_cohorts = [{"cohort_id": 1, "cohort_set_id": x} for x in range(1, 3)]
        cohort = {"available_as_saas": True}
        academy = {"available_as_saas": True}
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=plan_financings,
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=(2, plan),
            service_item=2,
            cohort=cohort,
            cohort_set=2,
            cohort_set_cohort=cohort_set_cohorts,
            academy=academy,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription") + (
            f"?cohort-set-selected={random.choice([model.cohort_set[0].id, model.cohort_set[0].slug])},"
            f"{random.choice([model.cohort_set[1].id, model.cohort_set[1].slug])}"
        )
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "plan_financings": [
                get_plan_financing_serializer(
                    self,
                    model.plan_financing[1],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    cohort_set=model.cohort_set[1],
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    cohorts=[model.cohort],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
                get_plan_financing_serializer(
                    self,
                    model.plan_financing[0],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    cohort_set=model.cohort_set[0],
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    cohorts=[model.cohort],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
            ],
            "subscriptions": [
                get_subscription_serializer(
                    self,
                    model.subscription[1],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    cohort_set=model.cohort_set[1],
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    cohorts=[model.cohort],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
                get_subscription_serializer(
                    self,
                    model.subscription[0],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    cohort_set=model.cohort_set[0],
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    cohorts=[model.cohort],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by wrong MentorshipServiceSet
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_wrong_mentorship_service_set(self):
        subscriptions = [
            {
                "valid_until": x,
                "selected_mentorship_service_set_id": None,
            }
            for x in [None, UTC_NOW + timedelta(days=1)]
        ]
        plan_financings = [
            {
                "valid_until": UTC_NOW + timedelta(days=1),
                "plan_expires_at": UTC_NOW + timedelta(days=1),
                "monthly_price": random.random() * 99.99 + 0.01,
                "selected_mentorship_service_set_id": None,
            }
            for _ in range(1, 3)
        ]
        plan_service_items = [{"service_item_id": x, "plan_id": 1} for x in range(1, 3)]
        plan_service_items += [{"service_item_id": x, "plan_id": 2} for x in range(1, 3)]
        subscription_service_items = [{"service_item_id": x, "subscription_id": 1} for x in range(1, 3)]
        subscription_service_items += [{"service_item_id": x, "subscription_id": 2} for x in range(1, 3)]
        plan = {"is_renewable": False}
        academy = {"available_as_saas": True}
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=plan_financings,
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=(2, plan),
            service_item=2,
            cohort_set=2,
            academy=academy,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription") + (
            f'?cohort-set-selected={random.choice([3, "slug1"])},' f'{random.choice([4, "slug2"])}'
        )
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "plan_financings": [],
            "subscriptions": [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by good MentorshipServiceSet
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_good_mentorship_service_set(self):
        subscriptions = [
            {
                "valid_until": x,
                "selected_mentorship_service_set_id": y,
                "selected_event_type_set_id": None,
            }
            for x, y in [(None, 1), (UTC_NOW + timedelta(days=1), 2)]
        ]
        plan_financings = [
            {
                "valid_until": UTC_NOW + timedelta(days=1),
                "plan_expires_at": UTC_NOW + timedelta(days=1),
                "monthly_price": random.random() * 99.99 + 0.01,
                "selected_mentorship_service_set_id": x,
                "selected_event_type_set_id": None,
            }
            for x in range(1, 3)
        ]
        plan_service_items = [{"service_item_id": x, "plan_id": 1} for x in range(1, 3)]
        plan_service_items += [{"service_item_id": x, "plan_id": 2} for x in range(1, 3)]
        subscription_service_items = [{"service_item_id": x, "subscription_id": 1} for x in range(1, 3)]
        subscription_service_items += [{"service_item_id": x, "subscription_id": 2} for x in range(1, 3)]
        plan = {"is_renewable": False}
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=plan_financings,
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=(2, plan),
            service_item=2,
            mentorship_service_set=2,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription") + (
            "?mentorship-service-set-selected="
            f"{random.choice([model.mentorship_service_set[0].id,model.mentorship_service_set[0].slug])},"
            f"{random.choice([model.mentorship_service_set[1].id, model.mentorship_service_set[1].slug])}"
        )
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "plan_financings": [
                get_plan_financing_serializer(
                    self,
                    model.plan_financing[1],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    mentorship_service_set=model.mentorship_service_set[1],
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
                get_plan_financing_serializer(
                    self,
                    model.plan_financing[0],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    mentorship_service_set=model.mentorship_service_set[0],
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
            ],
            "subscriptions": [
                get_subscription_serializer(
                    self,
                    model.subscription[1],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    mentorship_service_set=model.mentorship_service_set[1],
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
                get_subscription_serializer(
                    self,
                    model.subscription[0],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    mentorship_service_set=model.mentorship_service_set[0],
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by wrong EventTypeSet
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_wrong_event_type_set(self):
        subscriptions = [
            {
                "valid_until": x,
                "selected_event_type_set_id": None,
            }
            for x in [None, UTC_NOW + timedelta(days=1)]
        ]
        plan_financings = [
            {
                "valid_until": UTC_NOW + timedelta(days=1),
                "plan_expires_at": UTC_NOW + timedelta(days=1),
                "monthly_price": random.random() * 99.99 + 0.01,
                "selected_event_type_set_id": None,
            }
            for _ in range(1, 3)
        ]
        plan_service_items = [{"service_item_id": x, "plan_id": 1} for x in range(1, 3)]
        plan_service_items += [{"service_item_id": x, "plan_id": 2} for x in range(1, 3)]
        subscription_service_items = [{"service_item_id": x, "subscription_id": 1} for x in range(1, 3)]
        subscription_service_items += [{"service_item_id": x, "subscription_id": 2} for x in range(1, 3)]
        plan = {"is_renewable": False}
        academy = {"available_as_saas": True}
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=plan_financings,
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=(2, plan),
            service_item=2,
            cohort_set=2,
            academy=academy,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription") + (
            f'?event-type-set-selected={random.choice([1, "slug1"])},' f'{random.choice([2, "slug2"])}'
        )
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "plan_financings": [],
            "subscriptions": [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by good MentorshipServiceSet
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_good_event_type_set(self):
        subscriptions = [
            {
                "valid_until": x,
                "selected_event_type_set_id": y,
            }
            for x, y in [(None, 1), (UTC_NOW + timedelta(days=1), 2)]
        ]
        plan_financings = [
            {
                "valid_until": UTC_NOW + timedelta(days=1),
                "plan_expires_at": UTC_NOW + timedelta(days=1),
                "monthly_price": random.random() * 99.99 + 0.01,
                "selected_event_type_set_id": x,
            }
            for x in range(1, 3)
        ]
        plan_service_items = [{"service_item_id": x, "plan_id": 1} for x in range(1, 3)]
        plan_service_items += [{"service_item_id": x, "plan_id": 2} for x in range(1, 3)]
        subscription_service_items = [{"service_item_id": x, "subscription_id": 1} for x in range(1, 3)]
        subscription_service_items += [{"service_item_id": x, "subscription_id": 2} for x in range(1, 3)]
        plan = {"is_renewable": False}
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=plan_financings,
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=(2, plan),
            service_item=2,
            event_type_set=2,
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription") + (
            "?event-type-set-selected="
            f"{random.choice([model.event_type_set[0].id,model.event_type_set[0].slug])},"
            f"{random.choice([model.event_type_set[1].id, model.event_type_set[1].slug])}"
        )
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            "plan_financings": [
                get_plan_financing_serializer(
                    self,
                    model.plan_financing[1],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    event_type_set=model.event_type_set[1],
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
                get_plan_financing_serializer(
                    self,
                    model.plan_financing[0],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    event_type_set=model.event_type_set[0],
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
            ],
            "subscriptions": [
                get_subscription_serializer(
                    self,
                    model.subscription[1],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    event_type_set=model.event_type_set[1],
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
                get_subscription_serializer(
                    self,
                    model.subscription[0],
                    model.academy,
                    model.currency,
                    model.user,
                    model.service,
                    event_type_set=model.event_type_set[0],
                    invoices=[model.invoice[0], model.invoice[1]],
                    financing_options=[],
                    plans=[model.plan[0], model.plan[1]],
                    service_items=[model.service_item[0], model.service_item[1]],
                ),
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )
