import random
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status
from breathecode.payments import actions

from breathecode.payments.tests.mixins.payments_test_case import PaymentsTestCase

UTC_NOW = timezone.now()


def format_user_setting(data={}):
    return {
        'id': 1,
        'user_id': 1,
        'main_currency_id': None,
        'lang': 'en',
        **data,
    }


def financing_option_serializer(financing_option, currency, data={}):
    return {
        'currency': {
            'code': currency.code,
            'name': currency.name,
        },
        'how_many_months': financing_option.how_many_months,
        'monthly_price': financing_option.monthly_price,
    }


def plan_serializer(plan, service_items, service, cohorts=[], financing_options=[], currency=None, data={}):
    return {
        'service_items':
        [service_item_serializer(service_item, service, cohorts) for service_item in service_items],
        'financing_options':
        [financing_option_serializer(financing_option, currency) for financing_option in financing_options],
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
        'has_available_cohorts':
        plan.available_cohorts.exists(),
        **data,
    }


def service_serializer(service, cohorts=[], data={}):
    return {
        'groups': [],
        'price_per_unit': service.price_per_unit,
        'private': service.private,
        'slug': service.slug,
        **data,
    }


def service_item_serializer(service_item, service, cohorts=[], data={}):
    return {
        'how_many': service_item.how_many,
        'unit_type': service_item.unit_type,
        'service': service_serializer(service, cohorts),
        **data,
    }


def get_serializer(bag,
                   plans=[],
                   plan_service_items=[],
                   service_items=[],
                   service=None,
                   cohorts=[],
                   financing_options=[],
                   currency=None,
                   data={}):
    return {
        'amount_per_month':
        bag.amount_per_month,
        'amount_per_quarter':
        bag.amount_per_quarter,
        'amount_per_half':
        bag.amount_per_half,
        'amount_per_year':
        bag.amount_per_year,
        'expires_at':
        bag.expires_at,
        'is_recurrent':
        bag.is_recurrent,
        'plans': [
            plan_serializer(plan, plan_service_items, service, cohorts, financing_options, currency)
            for plan in plans
        ],
        'service_items':
        [service_item_serializer(service_item, service, cohorts) for service_item in service_items],
        'status':
        bag.status,
        'token':
        bag.token,
        'type':
        bag.type,
        'was_delivered':
        bag.was_delivered,
        **data,
    }


class SignalTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 GET without auth
    """

    @patch('breathecode.payments.actions.check_dependencies_in_bag', MagicMock())
    def test__without_auth(self):
        url = reverse_lazy('payments:checking')
        response = self.client.put(url)

        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [])
        self.assertEqual(actions.check_dependencies_in_bag.call_args_list, [])

    """
    🔽🔽🔽 Get with zero Bag
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.actions.check_dependencies_in_bag', MagicMock())
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
        self.assertEqual(actions.check_dependencies_in_bag.call_args_list, [])

    """
    🔽🔽🔽 Get with one Bag, type is BAG
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.actions.check_dependencies_in_bag', MagicMock())
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
                    'amount_per_month': 0.0,
                    'amount_per_quarter': 0.0,
                    'amount_per_half': 0.0,
                    'amount_per_year': 0.0,
                    'expires_at': self.bc.datetime.to_iso_string(UTC_NOW + timedelta(minutes=60)),
                    'token': token,
                },
            )

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            self.assertEqual(self.bc.database.list_of('payments.Bag'), [
                {
                    **self.bc.format.to_dict(model.bag),
                    'amount_per_month': 0.0,
                    'amount_per_quarter': 0.0,
                    'amount_per_half': 0.0,
                    'amount_per_year': 0.0,
                    'expires_at': UTC_NOW + timedelta(minutes=60),
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
            self.assertEqual(actions.check_dependencies_in_bag.call_args_list, [])

    """
    🔽🔽🔽 Get with one Bag, type is PREVIEW, passing nothing
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.actions.check_dependencies_in_bag', MagicMock())
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
        self.assertEqual(actions.check_dependencies_in_bag.call_args_list, [])

    """
    🔽🔽🔽 Get with one Bag, type is PREVIEW, passing type preview
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.actions.check_dependencies_in_bag', MagicMock())
    def test__with_bag__type_bag__passing_type_preview(self):
        bag = {
            'status': 'CHECKING',
            'type': 'PREVIEW',
        }

        model = self.bc.database.create(user=1, bag=bag, academy=1, currency=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:checking')
        data = {'academy': 1, 'type': 'PREVIEW'}

        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('rest_framework.authtoken.models.Token.generate_key', MagicMock(return_value=token)):
            response = self.client.put(url, data, format='json')

        json = response.json()

        expected = get_serializer(
            model.bag,
            data={
                'amount_per_month': 0.0,
                'amount_per_quarter': 0.0,
                'amount_per_half': 0.0,
                'amount_per_year': 0.0,
                'expires_at': self.bc.datetime.to_iso_string(UTC_NOW + timedelta(minutes=60)),
                'token': token,
            },
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [
            {
                **self.bc.format.to_dict(model.bag),
                'amount_per_month': 0.0,
                'amount_per_quarter': 0.0,
                'amount_per_half': 0.0,
                'amount_per_year': 0.0,
                'expires_at': UTC_NOW + timedelta(minutes=60),
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
        self.assertEqual(actions.check_dependencies_in_bag.call_args_list, [call(model.bag, 'en')])

    """
    🔽🔽🔽 Get with one Bag, type is PREVIEW, passing type preview and many ServiceItem and Plan that not found
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.actions.check_dependencies_in_bag', MagicMock())
    def test__with_bag__type_bag__passing_type_preview__service_item_not_is_object(self):
        bag = {
            'status': 'CHECKING',
            'type': 'PREVIEW',
        }

        model = self.bc.database.create(user=1, bag=bag, academy=1, currency=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:checking')
        data = {'academy': 1, 'type': 'PREVIEW', 'plans': [1], 'service_items': [1]}

        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('rest_framework.authtoken.models.Token.generate_key', MagicMock(return_value=token)):
            response = self.client.put(url, data, format='json')

        json = response.json()

        expected = {'detail': 'service-item-not-object', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [self.bc.format.to_dict(model.bag)])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({
                'lang': 'en',
                'id': model.user.id,
                'user_id': model.user.id,
            }),
        ])
        self.assertEqual(actions.check_dependencies_in_bag.call_args_list, [])

    """
    🔽🔽🔽 Get with one Bag, type is PREVIEW, passing type preview and many ServiceItem and Plan that not found
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.actions.check_dependencies_in_bag', MagicMock())
    def test__with_bag__type_bag__passing_type_preview__service_item_object_malformed(self):
        bag = {
            'status': 'CHECKING',
            'type': 'PREVIEW',
        }

        model = self.bc.database.create(user=1, bag=bag, academy=1, currency=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:checking')
        data = {'academy': 1, 'type': 'PREVIEW', 'plans': [1], 'service_items': [{}]}

        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('rest_framework.authtoken.models.Token.generate_key', MagicMock(return_value=token)):
            response = self.client.put(url, data, format='json')

        json = response.json()

        expected = {'detail': 'service-item-malformed', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [self.bc.format.to_dict(model.bag)])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({
                'lang': 'en',
                'id': model.user.id,
                'user_id': model.user.id,
            }),
        ])
        self.assertEqual(actions.check_dependencies_in_bag.call_args_list, [])

    """
    🔽🔽🔽 Get with one Bag, type is PREVIEW, passing type preview and many ServiceItem and Plan that not found
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.actions.check_dependencies_in_bag', MagicMock())
    def test__with_bag__type_bag__passing_type_preview__items_not_found(self):
        bag = {
            'status': 'CHECKING',
            'type': 'PREVIEW',
        }

        model = self.bc.database.create(user=1, bag=bag, academy=1, currency=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:checking')
        data = {
            'academy': 1,
            'type': 'PREVIEW',
            'plans': [1],
            'service_items': [{
                'how_many': 1,
                'service': 1
            }]
        }

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
        self.assertEqual(actions.check_dependencies_in_bag.call_args_list, [])

    """
    🔽🔽🔽 Get with one Bag, type is PREVIEW, passing type preview and many ServiceItem and Plan found,
    without the Currency
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.actions.check_dependencies_in_bag', MagicMock())
    def test__with_bag__type_bag__passing_type_preview__items_found__academy_without_the_currency(self):
        bag = {
            'status': 'CHECKING',
            'type': 'PREVIEW',
            'plans': [],
            'service_items': [],
        }

        academy = {'main_currency': None}

        model = self.bc.database.create(user=1, bag=bag, service_item=1, plan=1, academy=academy)
        self.bc.request.authenticate(model.user)

        self.bc.check.queryset_with_pks(model.bag.service_items.all(), [])
        self.bc.check.queryset_with_pks(model.bag.plans.all(), [])

        url = reverse_lazy('payments:checking')
        data = {
            'academy': 1,
            'type': 'PREVIEW',
            'plans': [1],
            'service_items': [{
                'how_many': 1,
                'service': 1
            }]
        }

        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('rest_framework.authtoken.models.Token.generate_key', MagicMock(return_value=token)):
            response = self.client.put(url, data, format='json')

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
        self.bc.check.queryset_with_pks(model.bag.service_items.all(), [])
        self.bc.check.queryset_with_pks(model.bag.plans.all(), [])
        self.assertEqual(actions.check_dependencies_in_bag.call_args_list, [])

    """
    🔽🔽🔽 Get with one Bag, type is PREVIEW, passing type preview and many ServiceItem and Plan found,
    with the correct Currency and Price
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.actions.check_dependencies_in_bag', MagicMock())
    def test__with_bag__type_bag__passing_type_preview__items_found__with_the_correct_currency__with_service_item(
            self):
        bag = {
            'status': 'CHECKING',
            'type': 'PREVIEW',
            'plans': [],
            'service_items': [],
        }

        currency = {'code': 'USD', 'name': 'United States dollar'}

        plan = {
            'price_per_month': random.random() * 100,
            'price_per_quarter': random.random() * 100,
            'price_per_half': random.random() * 100,
            'price_per_year': random.random() * 100,
        }

        service = {
            'price_per_unit': random.random() * 100,
        }

        how_many1 = random.randint(1, 5)
        how_many2 = random.choice([x for x in range(1, 6) if x != how_many1])
        service_item = {'how_many': how_many1}

        model = self.bc.database.create(user=1,
                                        bag=bag,
                                        academy=1,
                                        cohort=1,
                                        service_item=service_item,
                                        service=service,
                                        plan=plan,
                                        plan_service_item=1,
                                        currency=currency)
        self.bc.request.authenticate(model.user)

        service_item = self.bc.database.get('payments.ServiceItem', 1, dict=False)
        service_item.how_many = how_many2

        url = reverse_lazy('payments:checking')
        data = {
            'academy': 1,
            'type': 'PREVIEW',
            'plans': [1],
            'cohort': 1,
            'service_items': [{
                'how_many': how_many2,
                'service': 1
            }]
        }

        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('rest_framework.authtoken.models.Token.generate_key', MagicMock(return_value=token)):
            response = self.client.put(url, data, format='json')

        json = response.json()
        expected = {'detail': 'one-plan-and-many-services', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [
            {
                **self.bc.format.to_dict(model.bag),
            },
        ])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({
                'lang': 'en',
                'id': model.user.id,
                'user_id': model.user.id,
            }),
        ])
        self.bc.check.queryset_with_pks(model.bag.service_items.all(), [])
        self.bc.check.queryset_with_pks(model.bag.plans.all(), [])
        self.assertEqual(actions.check_dependencies_in_bag.call_args_list, [])

    # """
    # 🔽🔽🔽 Get with one Bag, type is PREVIEW, passing type preview and many ServiceItem and Plan found,
    # with the correct Currency and Price
    # """

    # @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    # def test__with_bag__type_bag__passing_type_preview__items_found__with_the_correct_currency__without_service_item(
    #         self):
    #     bag = {
    #         'status': 'CHECKING',
    #         'type': 'PREVIEW',
    #         'plans': [],
    #         'service_items': [],
    #     }

    #     currency = {'code': 'USD', 'name': 'United States dollar'}

    #     plan = {
    #         'price_per_month': random.random() * 100,
    #         'price_per_quarter': random.random() * 100,
    #         'price_per_half': random.random() * 100,
    #         'price_per_year': random.random() * 100,
    #     }

    #     service = {
    #         'price_per_unit': random.random() * 100,
    #     }

    #     how_many1 = random.randint(1, 5)
    #     how_many2 = random.choice([x for x in range(1, 6) if x != how_many1])
    #     service_item = {'how_many': how_many1}
    #     plan_service_item = {'cohorts': []}

    #     model = self.bc.database.create(user=1,
    #                                     bag=bag,
    #                                     academy=1,
    #                                     cohort=1,
    #                                     service_item=service_item,
    #                                     service=service,
    #                                     plan=plan,
    #                                     plan_service_item=plan_service_item,
    #                                     currency=currency)
    #     self.bc.request.authenticate(model.user)

    #     service_item = self.bc.database.get('payments.ServiceItem', 1, dict=False)
    #     service_item.how_many = how_many2

    #     url = reverse_lazy('payments:checking')
    #     data = {
    #         'academy': 1,
    #         'type': 'PREVIEW',
    #         'plans': [1],
    #     }

    #     token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
    #     with patch('rest_framework.authtoken.models.Token.generate_key', MagicMock(return_value=token)):
    #         response = self.client.put(url, data, format='json')

    #     json = response.json()

    #     price_per_month = model.plan.price_per_month
    #     price_per_quarter = model.plan.price_per_quarter
    #     price_per_half = model.plan.price_per_half
    #     price_per_year = model.plan.price_per_year
    #     expected = get_serializer(
    #         model.bag,
    #         [model.plan],
    #         [model.service_item],
    #         [],
    #         model.service,
    #         [model.cohort],
    #         data={
    #             'amount_per_month': price_per_month,
    #             'amount_per_quarter': price_per_quarter,
    #             'amount_per_half': price_per_half,
    #             'amount_per_year': price_per_year,
    #             'expires_at': self.bc.datetime.to_iso_string(UTC_NOW + timedelta(minutes=60)),
    #             'token': token,
    #         },
    #     )

    #     self.assertEqual(json, expected)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)

    #     self.assertEqual(self.bc.database.list_of('payments.Bag'), [
    #         {
    #             **self.bc.format.to_dict(model.bag),
    #             'amount_per_month': price_per_month,
    #             'amount_per_quarter': price_per_quarter,
    #             'amount_per_half': price_per_half,
    #             'amount_per_year': price_per_year,
    #             'expires_at': UTC_NOW + timedelta(minutes=60),
    #             'token': token,
    #         },
    #     ])
    #     self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
    #         format_user_setting({
    #             'lang': 'en',
    #             'id': model.user.id,
    #             'user_id': model.user.id,
    #         }),
    #     ])
    #     self.bc.check.queryset_with_pks(model.bag.service_items.all(), [])
    #     self.bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    #     self.assertEqual(actions.check_dependencies_in_bag.call_args_list, [])
    """
    🔽🔽🔽 Get with one Bag, type is PREVIEW, passing type preview and many ServiceItem and Plan found,
    with the correct Currency and Price
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.actions.check_dependencies_in_bag', MagicMock())
    def test__with_bag__type_bag__passing_type_preview__items_found__with_the_correct_currency__without_service_item(
            self):
        bag = {
            'status': 'CHECKING',
            'type': 'PREVIEW',
            'plans': [],
            'service_items': [],
        }

        currency = {'code': 'USD', 'name': 'United States dollar'}

        plan = {
            'price_per_month': random.random() * 100,
            'price_per_quarter': random.random() * 100,
            'price_per_half': random.random() * 100,
            'price_per_year': random.random() * 100,
            'is_renewable': False,
            'time_of_life': 0,
            'time_of_life_unit': None,
            'trial_duration': 0,
        }

        service = {
            'price_per_unit': random.random() * 100,
        }

        how_many1 = random.randint(1, 5)
        how_many2 = random.choice([x for x in range(1, 6) if x != how_many1])
        service_item = {'how_many': how_many1}

        model = self.bc.database.create(user=1,
                                        bag=bag,
                                        academy=1,
                                        cohort=1,
                                        service_item=service_item,
                                        service=service,
                                        plan=plan,
                                        plan_service_item=1,
                                        financing_option=1,
                                        currency=currency)
        self.bc.request.authenticate(model.user)

        service_item = self.bc.database.get('payments.ServiceItem', 1, dict=False)
        service_item.how_many = how_many2

        url = reverse_lazy('payments:checking')
        data = {
            'academy': 1,
            'type': 'PREVIEW',
            'plans': [1],
            'cohort': 1,
        }

        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('rest_framework.authtoken.models.Token.generate_key', MagicMock(return_value=token)):
            response = self.client.put(url, data, format='json')

        json = response.json()

        price_per_month = model.plan.price_per_month
        price_per_quarter = model.plan.price_per_quarter
        price_per_half = model.plan.price_per_half
        price_per_year = model.plan.price_per_year
        expected = get_serializer(
            model.bag,
            [model.plan],
            [model.service_item],
            [],
            model.service,
            [model.cohort],
            [model.financing_option],
            model.currency,
            data={
                'amount_per_month': price_per_month,
                'amount_per_quarter': price_per_quarter,
                'amount_per_half': price_per_half,
                'amount_per_year': price_per_year,
                'expires_at': self.bc.datetime.to_iso_string(UTC_NOW + timedelta(minutes=60)),
                'token': token,
            },
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [
            {
                **self.bc.format.to_dict(model.bag),
                'amount_per_month': price_per_month,
                'amount_per_quarter': price_per_quarter,
                'amount_per_half': price_per_half,
                'amount_per_year': price_per_year,
                'expires_at': UTC_NOW + timedelta(minutes=60),
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
        self.bc.check.queryset_with_pks(model.bag.service_items.all(), [])
        self.bc.check.queryset_with_pks(model.bag.plans.all(), [1])
        self.assertEqual(actions.check_dependencies_in_bag.call_args_list, [call(model.bag, 'en')])

    """
    🔽🔽🔽 Get with one Bag, type is PREVIEW, passing type preview and many ServiceItem and Plan found,
    with the correct Currency and Price, Plan with trial_duration
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.actions.check_dependencies_in_bag', MagicMock())
    def test__with_bag__type_bag__passing_type_preview__items_found__taking_free_trial(self):
        bag = {
            'status': 'CHECKING',
            'type': 'PREVIEW',
            'plans': [],
            'service_items': [],
        }

        currency = {'code': 'USD', 'name': 'United States dollar'}

        plan = {
            'price_per_month': random.random() * 100,
            'price_per_quarter': random.random() * 100,
            'price_per_half': random.random() * 100,
            'price_per_year': random.random() * 100,
            'is_renewable': False,
            'time_of_life': 0,
            'time_of_life_unit': None,
            'trial_duration': random.randint(1, 10),
        }

        service = {
            'price_per_unit': random.random() * 100,
        }

        how_many1 = random.randint(1, 5)
        how_many2 = random.choice([x for x in range(1, 6) if x != how_many1])
        service_item = {'how_many': how_many1}

        model = self.bc.database.create(user=1,
                                        bag=bag,
                                        academy=1,
                                        cohort=1,
                                        service_item=service_item,
                                        service=service,
                                        plan=plan,
                                        plan_service_item=1,
                                        financing_option=1,
                                        currency=currency)
        self.bc.request.authenticate(model.user)

        service_item = self.bc.database.get('payments.ServiceItem', 1, dict=False)
        service_item.how_many = how_many2

        url = reverse_lazy('payments:checking')
        data = {
            'academy': 1,
            'type': 'PREVIEW',
            'plans': [1],
            'cohort': 1,
        }

        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('rest_framework.authtoken.models.Token.generate_key', MagicMock(return_value=token)):
            response = self.client.put(url, data, format='json')

        json = response.json()

        price_per_month = model.plan.price_per_month
        price_per_quarter = model.plan.price_per_quarter
        price_per_half = model.plan.price_per_half
        price_per_year = model.plan.price_per_year
        expected = get_serializer(
            model.bag,
            [model.plan],
            [model.service_item],
            [],
            model.service,
            [model.cohort],
            [model.financing_option],
            model.currency,
            data={
                'amount_per_month': 0,
                'amount_per_quarter': 0,
                'amount_per_half': 0,
                'amount_per_year': 0,
                'expires_at': self.bc.datetime.to_iso_string(UTC_NOW + timedelta(minutes=60)),
                'token': token,
            },
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [
            {
                **self.bc.format.to_dict(model.bag),
                'amount_per_month': 0,
                'amount_per_quarter': 0,
                'amount_per_half': 0,
                'amount_per_year': 0,
                'expires_at': UTC_NOW + timedelta(minutes=60),
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
        self.bc.check.queryset_with_pks(model.bag.service_items.all(), [])
        self.bc.check.queryset_with_pks(model.bag.plans.all(), [1])
        self.assertEqual(actions.check_dependencies_in_bag.call_args_list, [call(model.bag, 'en')])

    """
    🔽🔽🔽 Get with one Bag, type is PREVIEW, passing type preview and many ServiceItem and Plan found,
    with the correct Currency and Price, Plan with trial_duration and Subscription
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.actions.check_dependencies_in_bag', MagicMock())
    def test__with_bag__type_bag__passing_type_preview__items_found__free_trial_already_taken(self):
        bag = {
            'status': 'CHECKING',
            'type': 'PREVIEW',
            'plans': [],
            'service_items': [],
        }

        currency = {'code': 'USD', 'name': 'United States dollar'}

        plan = {
            'price_per_month': random.random() * 100,
            'price_per_quarter': random.random() * 100,
            'price_per_half': random.random() * 100,
            'price_per_year': random.random() * 100,
            'is_renewable': False,
            'time_of_life': 0,
            'time_of_life_unit': None,
            'trial_duration': random.randint(1, 10),
        }

        service = {
            'price_per_unit': random.random() * 100,
        }

        how_many1 = random.randint(1, 5)
        how_many2 = random.choice([x for x in range(1, 6) if x != how_many1])
        service_item = {'how_many': how_many1}
        subscription = {'valid_until': UTC_NOW - timedelta(seconds=1)}

        model = self.bc.database.create(user=1,
                                        bag=bag,
                                        academy=1,
                                        subscription=subscription,
                                        cohort=1,
                                        service_item=service_item,
                                        service=service,
                                        plan=plan,
                                        plan_service_item=1,
                                        financing_option=1,
                                        currency=currency)
        self.bc.request.authenticate(model.user)

        service_item = self.bc.database.get('payments.ServiceItem', 1, dict=False)
        service_item.how_many = how_many2

        url = reverse_lazy('payments:checking')
        data = {
            'academy': 1,
            'type': 'PREVIEW',
            'plans': [1],
            'cohort': 1,
        }

        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('rest_framework.authtoken.models.Token.generate_key', MagicMock(return_value=token)):
            response = self.client.put(url, data, format='json')

        json = response.json()

        price_per_month = model.plan.price_per_month
        price_per_quarter = model.plan.price_per_quarter
        price_per_half = model.plan.price_per_half
        price_per_year = model.plan.price_per_year
        expected = get_serializer(
            model.bag,
            [model.plan],
            [model.service_item],
            [],
            model.service,
            [model.cohort],
            [model.financing_option],
            model.currency,
            data={
                'amount_per_month': price_per_month,
                'amount_per_quarter': price_per_quarter,
                'amount_per_half': price_per_half,
                'amount_per_year': price_per_year,
                'expires_at': self.bc.datetime.to_iso_string(UTC_NOW + timedelta(minutes=60)),
                'token': token,
            },
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [
            {
                **self.bc.format.to_dict(model.bag),
                'amount_per_month': price_per_month,
                'amount_per_quarter': price_per_quarter,
                'amount_per_half': price_per_half,
                'amount_per_year': price_per_year,
                'expires_at': UTC_NOW + timedelta(minutes=60),
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
        self.bc.check.queryset_with_pks(model.bag.service_items.all(), [])
        self.bc.check.queryset_with_pks(model.bag.plans.all(), [1])
        self.assertEqual(actions.check_dependencies_in_bag.call_args_list, [call(model.bag, 'en')])

    """
    🔽🔽🔽 Get with one Bag, type is PREVIEW, passing type preview and many ServiceItem and Plan found,
    with the correct Currency and Price, Plan with trial_duration and price et 0 and Subscription
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.actions.check_dependencies_in_bag', MagicMock())
    def test__with_bag__type_bag__passing_type_preview__items_found__free_trial_already_taken__amount_is_0(
            self):
        bag = {
            'status': 'CHECKING',
            'type': 'PREVIEW',
            'plans': [],
            'service_items': [],
        }

        currency = {'code': 'USD', 'name': 'United States dollar'}

        plan = {
            'price_per_month': 0,
            'price_per_quarter': 0,
            'price_per_half': 0,
            'price_per_year': 0,
            'is_renewable': False,
            'time_of_life': 0,
            'time_of_life_unit': None,
            'trial_duration': random.randint(1, 10),
        }

        service = {
            'price_per_unit': random.random() * 100,
        }

        how_many1 = random.randint(1, 5)
        how_many2 = random.choice([x for x in range(1, 6) if x != how_many1])
        service_item = {'how_many': how_many1}
        subscription = {'valid_until': UTC_NOW - timedelta(seconds=1)}

        model = self.bc.database.create(user=1,
                                        bag=bag,
                                        academy=1,
                                        subscription=subscription,
                                        cohort=1,
                                        service_item=service_item,
                                        service=service,
                                        plan=plan,
                                        plan_service_item=1,
                                        financing_option=1,
                                        currency=currency)
        self.bc.request.authenticate(model.user)

        service_item = self.bc.database.get('payments.ServiceItem', 1, dict=False)
        service_item.how_many = how_many2

        url = reverse_lazy('payments:checking')
        data = {
            'academy': 1,
            'type': 'PREVIEW',
            'plans': [1],
            'cohort': 1,
        }

        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('rest_framework.authtoken.models.Token.generate_key', MagicMock(return_value=token)):
            response = self.client.put(url, data, format='json')

        json = response.json()

        expected = {'detail': 'free-trial-already-bought', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [
            {
                **self.bc.format.to_dict(model.bag),
            },
        ])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({
                'lang': 'en',
                'id': model.user.id,
                'user_id': model.user.id,
            }),
        ])
        self.bc.check.queryset_with_pks(model.bag.service_items.all(), [])
        self.bc.check.queryset_with_pks(model.bag.plans.all(), [])
        self.assertEqual(actions.check_dependencies_in_bag.call_args_list, [])

    """
    🔽🔽🔽 Get with one Bag, type is PREVIEW, passing type preview and many ServiceItem and Plan found,
    with the correct Currency and Price, Plan with trial_duration and price et 0 and PlanFinancing
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.actions.check_dependencies_in_bag', MagicMock())
    def test__with_bag__type_bag__passing_type_preview__items_found__plan_already_financed(self):
        bag = {
            'status': 'CHECKING',
            'type': 'PREVIEW',
            'plans': [],
            'service_items': [],
        }

        currency = {'code': 'USD', 'name': 'United States dollar'}

        plan = {
            'price_per_month': 0,
            'price_per_quarter': 0,
            'price_per_half': 0,
            'price_per_year': 0,
            'is_renewable': False,
            'time_of_life': 0,
            'time_of_life_unit': None,
            'trial_duration': random.randint(1, 10),
        }

        service = {
            'price_per_unit': random.random() * 100,
        }

        how_many1 = random.randint(1, 5)
        how_many2 = random.choice([x for x in range(1, 6) if x != how_many1])
        service_item = {'how_many': how_many1}
        plan_financing = {
            'valid_until': UTC_NOW - timedelta(seconds=1),
            'plan_expires_at': UTC_NOW - timedelta(seconds=1),
            'monthly_price': random.randint(1, 100),
        }

        model = self.bc.database.create(user=1,
                                        bag=bag,
                                        academy=1,
                                        plan_financing=plan_financing,
                                        cohort=1,
                                        service_item=service_item,
                                        service=service,
                                        plan=plan,
                                        plan_service_item=1,
                                        currency=currency)
        self.bc.request.authenticate(model.user)

        service_item = self.bc.database.get('payments.ServiceItem', 1, dict=False)
        service_item.how_many = how_many2

        url = reverse_lazy('payments:checking')
        data = {
            'academy': 1,
            'type': 'PREVIEW',
            'plans': [1],
            'cohort': 1,
        }

        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('rest_framework.authtoken.models.Token.generate_key', MagicMock(return_value=token)):
            response = self.client.put(url, data, format='json')

        json = response.json()

        expected = {'detail': 'plan-already-financed', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [
            {
                **self.bc.format.to_dict(model.bag),
            },
        ])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({
                'lang': 'en',
                'id': model.user.id,
                'user_id': model.user.id,
            }),
        ])
        self.bc.check.queryset_with_pks(model.bag.service_items.all(), [])
        self.bc.check.queryset_with_pks(model.bag.plans.all(), [])
        self.assertEqual(actions.check_dependencies_in_bag.call_args_list, [])

    """
    🔽🔽🔽 Get with one Bag, type is PREVIEW, passing type preview and many ServiceItem and Plan found,
    with the correct Currency and Price, Plan with trial_duration and price et 0 and Subscription that end in
    future
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.actions.check_dependencies_in_bag', MagicMock())
    def test__with_bag__type_bag__passing_type_preview__items_found__plan_already_bought__cancelled(self):
        bag = {
            'status': 'CHECKING',
            'type': 'PREVIEW',
            'plans': [],
            'service_items': [],
        }

        currency = {'code': 'USD', 'name': 'United States dollar'}

        plan = {
            'price_per_month': random.random() * 100,
            'price_per_quarter': random.random() * 100,
            'price_per_half': random.random() * 100,
            'price_per_year': random.random() * 100,
            'is_renewable': True,
            'time_of_life': 1,
            'time_of_life_unit': 'MONTH',
            'trial_duration': random.randint(1, 10),
        }

        service = {
            'price_per_unit': random.random() * 100,
        }

        how_many1 = random.randint(1, 5)
        how_many2 = random.choice([x for x in range(1, 6) if x != how_many1])
        service_item = {'how_many': how_many1}
        subscription = {
            'valid_until': None,
            'next_payment_at': UTC_NOW + timedelta(seconds=1),
            'status': random.choice(['CANCELLED', 'DEPRECATED']),
        }

        model = self.bc.database.create(user=1,
                                        bag=bag,
                                        academy=1,
                                        subscription=subscription,
                                        cohort=1,
                                        service_item=service_item,
                                        service=service,
                                        plan=plan,
                                        plan_service_item=1,
                                        financing_option=1,
                                        currency=currency)
        self.bc.request.authenticate(model.user)

        service_item = self.bc.database.get('payments.ServiceItem', 1, dict=False)
        service_item.how_many = how_many2

        url = reverse_lazy('payments:checking')
        data = {
            'academy': 1,
            'type': 'PREVIEW',
            'plans': [1],
            'cohort': 1,
        }

        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('rest_framework.authtoken.models.Token.generate_key', MagicMock(return_value=token)):
            response = self.client.put(url, data, format='json')

        json = response.json()

        expected = {'detail': 'plan-already-bought', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [
            {
                **self.bc.format.to_dict(model.bag),
            },
        ])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({
                'lang': 'en',
                'id': model.user.id,
                'user_id': model.user.id,
            }),
        ])
        self.bc.check.queryset_with_pks(model.bag.service_items.all(), [])
        self.bc.check.queryset_with_pks(model.bag.plans.all(), [])
        self.assertEqual(actions.check_dependencies_in_bag.call_args_list, [])

    """
    🔽🔽🔽 Get with one Bag, type is PREVIEW, passing type preview and many ServiceItem and Plan found,
    with the correct Currency and Price, Plan with trial_duration and price et 0 and Subscription that end in
    future
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.actions.check_dependencies_in_bag', MagicMock())
    def test__with_bag__type_bag__passing_type_preview__items_found__plan_already_bought__no_cancelled(self):
        bag = {
            'status': 'CHECKING',
            'type': 'PREVIEW',
            'plans': [],
            'service_items': [],
        }

        currency = {'code': 'USD', 'name': 'United States dollar'}

        plan = {
            'price_per_month': random.random() * 100,
            'price_per_quarter': random.random() * 100,
            'price_per_half': random.random() * 100,
            'price_per_year': random.random() * 100,
            'is_renewable': True,
            'time_of_life': 1,
            'time_of_life_unit': 'MONTH',
            'trial_duration': random.randint(1, 10),
        }

        service = {
            'price_per_unit': random.random() * 100,
        }

        how_many1 = random.randint(1, 5)
        how_many2 = random.choice([x for x in range(1, 6) if x != how_many1])
        service_item = {'how_many': how_many1}
        subscription = {
            'valid_until':
            UTC_NOW + timedelta(seconds=1),
            'status':
            random.choice(['CANCELLED', 'ACTIVE', 'DEPRECATED', 'PAYMENT_ISSUE', 'ERROR', 'FULLY_PAID']),
        }

        model = self.bc.database.create(user=1,
                                        bag=bag,
                                        academy=1,
                                        subscription=subscription,
                                        cohort=1,
                                        service_item=service_item,
                                        service=service,
                                        plan=plan,
                                        plan_service_item=1,
                                        financing_option=1,
                                        currency=currency)
        self.bc.request.authenticate(model.user)

        service_item = self.bc.database.get('payments.ServiceItem', 1, dict=False)
        service_item.how_many = how_many2

        url = reverse_lazy('payments:checking')
        data = {
            'academy': 1,
            'type': 'PREVIEW',
            'plans': [1],
            'cohort': 1,
        }

        token = self.bc.random.string(lower=True, upper=True, number=True, size=40)
        with patch('rest_framework.authtoken.models.Token.generate_key', MagicMock(return_value=token)):
            response = self.client.put(url, data, format='json')

        json = response.json()

        expected = {'detail': 'plan-already-bought', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [
            {
                **self.bc.format.to_dict(model.bag),
            },
        ])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({
                'lang': 'en',
                'id': model.user.id,
                'user_id': model.user.id,
            }),
        ])
        self.bc.check.queryset_with_pks(model.bag.service_items.all(), [])
        self.bc.check.queryset_with_pks(model.bag.plans.all(), [])
        self.assertEqual(actions.check_dependencies_in_bag.call_args_list, [])
