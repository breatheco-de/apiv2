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
        url = reverse_lazy('payments:checking')
        response = self.client.put(url)

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

        url = reverse_lazy('payments:checking')
        response = self.client.put(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {'detail': 'not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({'lang': 'en'}),
        ])

    """
    🔽🔽🔽 Get with one Bag, type is BAG
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__with_bag__type_bag(self):
        bag = {
            'status': 'CHECKING',
            'type': 'BAG',
        }

        cases = [{}, {'type': 'BAG'}]
        for case in cases:
            model = self.bc.database.create(user=1, bag=bag)
            self.bc.request.authenticate(model.user)

            url = reverse_lazy('payments:checking')

            token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
            with patch('rest_framework.authtoken.models.Token.generate_key', MagicMock(return_value=token)):
                response = self.client.put(url, data=case, format='json')

            json = response.json()
            expected = get_serializer(
                model.bag,
                data={
                    'amount': 0.0,
                    'expires_at': self.bc.datetime.to_iso_string(UTC_NOW + timedelta(minutes=10)),
                    'token': token,
                },
            )

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            self.assertEqual(self.bc.database.list_of('payments.Bag'), [
                {
                    **self.bc.format.to_dict(model.bag),
                    'amount': 0.0,
                    'expires_at': UTC_NOW + timedelta(minutes=10),
                    'token': token,
                },
            ])
            self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
                format_user_setting({
                    'lang': 'en',
                    'id': model.user.id,
                    'user_id': model.user.id,
                }),
            ])

            # teardown
            self.bc.database.delete('payments.Bag', model.bag.id)
            self.bc.database.delete('authenticate.UserSetting', model.bag.id)

    """
    🔽🔽🔽 Get with one Bag, type is PREVIEW, passing nothing
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__with_bag__type_bag__passing_nothing(self):
        bag = {
            'status': 'CHECKING',
            'type': 'PREVIEW',
        }

        model = self.bc.database.create(user=1, bag=bag)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:checking')
        response = self.client.put(url)

        json = response.json()
        expected = {'detail': 'not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [self.bc.format.to_dict(model.bag)])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({
                'lang': 'en',
                'id': model.user.id,
                'user_id': model.user.id,
            }),
        ])

    """
    🔽🔽🔽 Get with one Bag, type is PREVIEW, passing type preview
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__with_bag__type_bag__passing_type_preview(self):
        bag = {
            'status': 'CHECKING',
            'type': 'PREVIEW',
        }

        model = self.bc.database.create(user=1, bag=bag)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:checking')
        data = {'type': 'PREVIEW'}

        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('rest_framework.authtoken.models.Token.generate_key', MagicMock(return_value=token)):
            response = self.client.put(url, data, format='json')

        json = response.json()

        expected = get_serializer(
            model.bag,
            data={
                'amount': 0.0,
                'expires_at': self.bc.datetime.to_iso_string(UTC_NOW + timedelta(minutes=10)),
                'token': token,
            },
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [
            {
                **self.bc.format.to_dict(model.bag),
                'amount': 0.0,
                'expires_at': UTC_NOW + timedelta(minutes=10),
                'token': token,
            },
        ])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({
                'lang': 'en',
                'id': model.user.id,
                'user_id': model.user.id,
            }),
        ])

    """
    🔽🔽🔽 Get with one Bag, type is PREVIEW, passing type preview and many ServiceItem and Plan that not found
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__with_bag__type_bag__passing_type_preview__items_not_found(self):
        bag = {
            'status': 'CHECKING',
            'type': 'PREVIEW',
        }

        model = self.bc.database.create(user=1, bag=bag)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:checking')
        data = {'type': 'PREVIEW', 'plans': [1], 'services': [1]}

        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('rest_framework.authtoken.models.Token.generate_key', MagicMock(return_value=token)):
            response = self.client.put(url, data, format='json')

        json = response.json()

        expected = {'detail': 'some-items-not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [self.bc.format.to_dict(model.bag)])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({
                'lang': 'en',
                'id': model.user.id,
                'user_id': model.user.id,
            }),
        ])

    """
    🔽🔽🔽 Get with one Bag, type is PREVIEW, passing type preview and many ServiceItem and Plan found,
    without the Currency
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__with_bag__type_bag__passing_type_preview__items_found__without_the_currency(self):
        bag = {
            'status': 'CHECKING',
            'type': 'PREVIEW',
        }

        model = self.bc.database.create(user=1, bag=bag, service_item=1, plan=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:checking')
        data = {'type': 'PREVIEW', 'plans': [1], 'services': [1]}

        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('rest_framework.authtoken.models.Token.generate_key', MagicMock(return_value=token)):
            response = self.client.put(url, data, format='json')

        json = response.json()

        expected = get_serializer(
            model.bag,
            # [model.plan],
            # [model.service_item],
            data={
                'amount': 0.0,
                'expires_at': self.bc.datetime.to_iso_string(UTC_NOW + timedelta(minutes=10)),
                'token': token,
            },
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [
            {
                **self.bc.format.to_dict(model.bag),
                'amount': 0.0,
                'expires_at': UTC_NOW + timedelta(minutes=10),
                'token': token,
            },
        ])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({
                'lang': 'en',
                'id': model.user.id,
                'user_id': model.user.id,
            }),
        ])
        self.bc.check.queryset_with_pks(model.bag.services.all(), [])
        self.bc.check.queryset_with_pks(model.bag.plans.all(), [])

    """
    🔽🔽🔽 Get with one Bag, type is PREVIEW, passing type preview and many ServiceItem and Plan found,
    with the correct Currency and Price
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__with_bag__type_bag__passing_type_preview__items_found__with_the_correct_currency(self):
        bag = {
            'status': 'CHECKING',
            'type': 'PREVIEW',
            'plans': [],
            'services': [],
        }

        currency = {'code': 'USD', 'name': 'United States dollar'}
        price = {'price': random.random() * 100}

        model = self.bc.database.create(user=1,
                                        bag=bag,
                                        service_item=1,
                                        plan=1,
                                        price=price,
                                        currency=currency)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:checking')
        data = {'type': 'PREVIEW', 'plans': [1], 'services': [1]}

        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('rest_framework.authtoken.models.Token.generate_key', MagicMock(return_value=token)):
            response = self.client.put(url, data, format='json')

        json = response.json()

        expected = get_serializer(
            model.bag,
            [model.plan],
            [model.service_item],
            [model.price],
            data={
                'amount': model.price.price * 2,
                'expires_at': self.bc.datetime.to_iso_string(UTC_NOW + timedelta(minutes=10)),
                'token': token,
            },
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [
            {
                **self.bc.format.to_dict(model.bag),
                'amount': model.price.price * 2,
                'expires_at': UTC_NOW + timedelta(minutes=10),
                'token': token,
            },
        ])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({
                'lang': 'en',
                'id': model.user.id,
                'user_id': model.user.id,
            }),
        ])
        self.bc.check.queryset_with_pks(model.bag.services.all(), [1])
        self.bc.check.queryset_with_pks(model.bag.plans.all(), [1])
