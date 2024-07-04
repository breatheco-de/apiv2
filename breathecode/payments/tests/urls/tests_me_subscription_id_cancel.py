import math
import random
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token

from breathecode.payments import signals

from ..mixins import PaymentsTestCase

UTC_NOW = timezone.now()


def academy_serializer(academy):
    return {
        "id": academy.id,
        "name": academy.name,
        "slug": academy.slug,
    }


def user_serializer(user):
    return {
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }


def get_serializer(self, subscription, academy, user, data={}):
    return {
        "academy": academy_serializer(academy),
        "id": subscription.id,
        "invoices": [],
        "is_refundable": subscription.is_refundable,
        "next_payment_at": self.bc.datetime.to_iso_string(subscription.next_payment_at),
        "paid_at": self.bc.datetime.to_iso_string(subscription.paid_at),
        "pay_every": subscription.pay_every,
        "pay_every_unit": subscription.pay_every_unit,
        "plans": [],
        "selected_cohort_set": subscription.selected_cohort_set,
        "selected_event_type_set": subscription.selected_event_type_set,
        "selected_mentorship_service_set": subscription.selected_mentorship_service_set,
        "service_items": [],
        "status": subscription.status,
        "status_message": subscription.status_message,
        "user": user_serializer(user),
        "valid_until": self.bc.datetime.to_iso_string(subscription.valid_until) if subscription.valid_until else None,
        **data,
    }


class SignalTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 GET without auth
    """

    def test__without_auth(self):
        url = reverse_lazy("payments:me_subscription_id_cancel", kwargs={"subscription_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bc.database.list_of("payments.Subscription"), [])

    def test__put__not_found(self):
        model = self.bc.database.create(
            user=1,
        )

        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription_id_cancel", kwargs={"subscription_id": 1})
        response = self.client.put(url)

        json = response.json()
        expected = {"detail": "not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of("payments.Subscription"), [])

    def test__put__cancelled_these_statuses(self):
        statuses = ["FREE_TRIAL", "ACTIVE", "PAYMENT_ISSUE", "ERROR"]
        for s in statuses:
            subscription = {"status": s}
            model = self.bc.database.create(user=1, subscription=subscription)

            self.client.force_authenticate(model.user)

            url = reverse_lazy("payments:me_subscription_id_cancel", kwargs={"subscription_id": model.subscription.id})
            response = self.client.put(url)

            json = response.json()
            expected = get_serializer(self, model.subscription, model.academy, model.user, data={"status": "CANCELLED"})

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("payments.Subscription"),
                [
                    {
                        **self.bc.format.to_dict(model.subscription),
                        "status": "CANCELLED",
                    },
                ],
            )

            # teardown
            self.bc.database.delete("payments.Subscription")

    def test__put__cancelled_twice(self):
        subscription = {"status": "CANCELLED"}
        model = self.bc.database.create(user=1, subscription=subscription)

        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription_id_cancel", kwargs={"subscription_id": model.subscription.id})
        response = self.client.put(url)

        json = response.json()
        expected = {"detail": "already-cancelled", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.bc.database.list_of("payments.Subscription"),
            [
                {
                    **self.bc.format.to_dict(model.subscription),
                    "status": "CANCELLED",
                },
            ],
        )

    def test__put__cancelled_over_deprecated(self):
        subscription = {"status": "DEPRECATED"}
        model = self.bc.database.create(user=1, subscription=subscription)

        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:me_subscription_id_cancel", kwargs={"subscription_id": model.subscription.id})
        response = self.client.put(url)

        json = response.json()
        expected = {"detail": "deprecated", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.bc.database.list_of("payments.Subscription"),
            [
                {
                    **self.bc.format.to_dict(model.subscription),
                    "status": "DEPRECATED",
                },
            ],
        )
