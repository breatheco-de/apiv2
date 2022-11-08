from datetime import timedelta
import random
from unittest.mock import MagicMock, call, patch
from rest_framework.authtoken.models import Token

from django.urls import reverse_lazy
from rest_framework import status

from breathecode.payments import signals

from django.utils import timezone
from ..mixins import PaymentsTestCase

UTC_NOW = timezone.now()


def format_user_setting(data={}):
    return {
        'id': 1,
        'user_id': 1,
        'main_currency_id': None,
        'lang': 'en',
        **data,
    }


def price_serializer(price, data={}):
    return {
        'price': price.price,
        **data,
    }


def plan_serializer(plan, service_items, prices, data={}):
    return {
        'description': plan.description,
        'prices': [price_serializer(price) for price in prices],
        'renew_every': plan.renew_every,
        'renew_every_unit': plan.renew_every_unit,
        'services': [service_item_serializer(service) for service in service_items],
        'slug': plan.slug,
        'status': plan.status,
        'title': plan.title,
        'trial_duration': plan.trial_duration,
        'trial_duration_unit': plan.trial_duration_unit,
        **data,
    }


def service_item_serializer(service_item, data={}):
    return {
        'how_many': service_item.how_many,
        'unit_type': service_item.unit_type,
        **data,
    }


def get_serializer(bag, plans=[], service_items=[], prices=[], data={}):
    return {
        'amount': bag.amount,
        'expires_at': bag.expires_at,
        'is_recurrent': bag.is_recurrent,
        'plans': [plan_serializer(plan, service_items, prices) for plan in plans],
        'services': [service_item_serializer(service) for service in service_items],
        'status': bag.status,
        'token': bag.token,
        'type': bag.type,
        'was_delivered': bag.was_delivered,
        **data,
    }


class SignalTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 GET without auth
    """

    def test__without_auth(self):
        url = reverse_lazy('payments:pay')
        response = self.client.post(url)

        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [])

    """
    🔽🔽🔽 Get with zero Bag
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__without_bag(self):
        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:pay')
        response = self.client.post(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {'detail': 'not-found-or-without-checking', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({'lang': 'en'}),
        ])
