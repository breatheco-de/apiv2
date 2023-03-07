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
        'codename': permission.codename,
        'name': permission.name,
    }


def group_serializer(group, permissions=[]):
    return {
        'name': group.name,
        'permissions': [permission_serializer(permission) for permission in permissions],
    }


def service_serializer(service, groups=[], permissions=[]):
    return {
        'price_per_unit': service.price_per_unit,
        'private': service.private,
        'slug': service.slug,
        'groups': [group_serializer(group, permissions) for group in groups],
    }


def service_item_serializer(self, service_item, service, groups=[], permissions=[]):
    return {
        'how_many': service_item.how_many,
        'unit_type': service_item.unit_type,
        'service': service_serializer(service, groups, permissions),
    }


def currency_serializer(currency):
    return {
        'code': currency.code,
        'name': currency.name,
    }


def plan_serializer(self, plan, service, currency, groups=[], permissions=[], service_items=[]):
    return {
        'financing_options': [],
        'service_items': [
            service_item_serializer(self, service_item, service, groups, permissions)
            for service_item in service_items
        ],
        'currency':
        currency_serializer(currency),
        'slug':
        plan.slug,
        'status':
        plan.status,
        'time_of_life':
        plan.time_of_life,
        'time_of_life_unit':
        plan.time_of_life_unit,
        'trial_duration':
        plan.trial_duration,
        'trial_duration_unit':
        plan.trial_duration_unit,
        'is_renewable':
        plan.is_renewable,
        'owner':
        plan.owner,
        'price_per_half':
        plan.price_per_half,
        'price_per_month':
        plan.price_per_month,
        'price_per_quarter':
        plan.price_per_quarter,
        'price_per_year':
        plan.price_per_year,
    }


def plan_offer_transaction_serializer(plan_offer_transaction):
    return {
        'lang': plan_offer_transaction.lang,
        'title': plan_offer_transaction.title,
        'description': plan_offer_transaction.description,
        'short_description': plan_offer_transaction.short_description,
    }


def get_serializer(self,
                   plan_offer,
                   plan1,
                   plan2,
                   service,
                   currency,
                   plan_offer_translation=None,
                   groups=[],
                   permissions=[],
                   service_items=[]):

    if plan_offer_translation:
        plan_offer_translation = plan_offer_transaction_serializer(plan_offer_translation)

    return {
        'details': plan_offer_translation,
        'original_plan': plan_serializer(self, plan1, service, currency, groups, permissions, service_items),
        'suggested_plan': plan_serializer(self, plan2, service, currency, groups, permissions, service_items),
        'show_modal': plan_offer.show_modal,
        'expires_at':
        self.bc.datetime.to_iso_string(plan_offer.expires_at) if plan_offer.expires_at else None,
    }


class SignalTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 GET without auth
    """

    def test__without_auth__without_service_items(self):
        url = reverse_lazy('payments:me_subscription_id_cancel', kwargs={'subscription_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bc.database.list_of('payments.Subscription'), [])

    def test__put__without_auth__with_plan_offer(self):
        model = self.bc.database.create(user=1, )

        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_subscription_id_cancel', kwargs={'subscription_id': 1})
        response = self.client.put(url)

        json = response.json()
        expected = {}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('payments.Subscription'), [
            self.bc.format.to_dict(model.plan_offer),
        ])
