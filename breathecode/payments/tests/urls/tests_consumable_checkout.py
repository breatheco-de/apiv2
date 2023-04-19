import math
import random
import stripe
from unittest.mock import MagicMock, call, patch
from django.urls import reverse_lazy
from rest_framework import status

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


def format_consumable_item(data={}):
    return {
        'cohort_id': None,
        'event_type_set_id': None,
        'how_many': -1,
        'id': 1,
        'mentorship_service_set_id': None,
        'service_item_id': 0,
        'unit_type': 'UNIT',
        'user_id': 0,
        'valid_until': None,
        **data,
    }


def format_bag_item(data={}):
    return {
        'academy_id': 1,
        'amount_per_half': 0.0,
        'amount_per_month': 0.0,
        'amount_per_quarter': 0.0,
        'amount_per_year': 0.0,
        'chosen_period': 'NO_SET',
        'currency_id': 1,
        'expires_at': None,
        'how_many_installments': 0,
        'id': 1,
        'is_recurrent': False,
        'status': 'PAID',
        'token': None,
        'type': 'CHARGE',
        'user_id': 1,
        'was_delivered': True,
        **data,
    }


def format_invoice_item(data={}):
    return {
        'academy_id': 1,
        'amount': 0.0,
        'currency_id': 1,
        'bag_id': 1,
        'id': 1,
        'paid_at': UTC_NOW,
        'status': 'FULFILLED',
        'stripe_id': None,
        'user_id': 1,
        'refund_stripe_id': None,
        'refunded_at': None,
        **data,
    }


def get_serializer(self, currency, user, data={}):
    return {
        'amount': 0,
        'currency': {
            'code': currency.code,
            'name': currency.name,
        },
        'paid_at': self.bc.datetime.to_iso_string(UTC_NOW),
        'status': 'FULFILLED',
        'user': {
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        },
        **data,
    }


class SignalTestSuite(PaymentsTestCase):
    # When: no auth
    # Then: return 401
    def test__without_auth(self):
        url = reverse_lazy('payments:consumable_checkout')
        response = self.client.post(url)

        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [])

    # Given: 1 User
    # When: is auth and no service in body
    # Then: return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__no_service(self):
        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:consumable_checkout')
        response = self.client.post(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {'detail': 'service-is-required', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({'lang': 'en'}),
        ])

    # Given: 1 User
    # When: is auth and service that not found in body
    # Then: return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__service_not_found(self):
        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:consumable_checkout')
        data = {'service': 1}
        response = self.client.post(url, data, format='json')
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {'detail': 'service-not-found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({'lang': 'en'}),
        ])

    # Given: 1 User and 1 Service
    # When: is auth, with a service in body
    # Then: return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__with_service(self):
        model = self.bc.database.create(user=1, service=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:consumable_checkout')
        data = {'service': 1}
        response = self.client.post(url, data, format='json')
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {'detail': 'how-many-is-required', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({'lang': 'en'}),
        ])

    # Given: 1 User and 1 Service
    # When: is auth, with a service and how_many in body
    # Then: return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__academy_is_required(self):
        model = self.bc.database.create(user=1, service=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:consumable_checkout')
        data = {'service': 1, 'how_many': 1}
        response = self.client.post(url, data, format='json')
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {'detail': 'academy-is-required', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({'lang': 'en'}),
        ])

    # Given: 1 User and 1 Service
    # When: is auth, with a service, how_many and academy in body, and academy not found
    # Then: return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__academy_not_found(self):
        model = self.bc.database.create(user=1, service=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:consumable_checkout')
        data = {'service': 1, 'how_many': 1, 'academy': 1}
        response = self.client.post(url, data, format='json')
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {'detail': 'academy-not-found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({'lang': 'en'}),
        ])

    # Given: 1 User, 1 Service and 1 Academy
    # When: is auth, with a service, how_many and academy in body, resource is required
    # Then: return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__resourse_is_required(self):
        model = self.bc.database.create(user=1, service=1, academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:consumable_checkout')
        data = {'service': 1, 'how_many': 1, 'academy': 1}
        response = self.client.post(url, data, format='json')
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {'detail': 'mentorship-service-set-or-event-type-set-is-required', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({'lang': 'en'}),
        ])

    # Given: 1 User, 1 Service and 1 Academy
    # When: is auth, with a service, how_many, academy and event_type_set in body,
    # ----> service type is MENTORSHIP_SERVICE_SET
    # Then: return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__bad_service_type_for_event_type_set(self):
        service = {'type': 'MENTORSHIP_SERVICE_SET'}
        model = self.bc.database.create(user=1, service=service, academy=1, event_type_set=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:consumable_checkout')
        data = {'service': 1, 'how_many': 1, 'academy': 1, 'event_type_set': 1}
        response = self.client.post(url, data, format='json')
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {'detail': 'bad-service-type-mentorship-service-set', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({'lang': 'en'}),
        ])

    # Given: 1 User, 1 Service and 1 Academy
    # When: is auth, with a service, how_many, academy and mentorship_service_set in body,
    # ----> service type is EVENT_TYPE_SET
    # Then: return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__bad_service_type_for_mentorship_service_set(self):
        service = {'type': 'EVENT_TYPE_SET'}
        model = self.bc.database.create(user=1, service=service, academy=1, mentorship_service_set=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:consumable_checkout')
        data = {'service': 1, 'how_many': 1, 'academy': 1, 'mentorship_service_set': 1}
        response = self.client.post(url, data, format='json')
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {'detail': 'bad-service-type-event-type-set', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({'lang': 'en'}),
        ])

    # Given: 1 User, 1 Service and 1 Academy
    # When: is auth, with a service, how_many and academy in body,
    # ----> mentorship_service_set or event_type_set in body
    # ----> service type is COHORT
    # Then: return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__service_is_cohort(self):
        service = {'type': 'COHORT'}
        kwargs = {}

        if random.randint(0, 1) == 0:
            kwargs['mentorship_service_set'] = 1
        else:
            kwargs['event_type_set'] = 1

        model = self.bc.database.create(user=1, service=service, academy=1, **kwargs)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:consumable_checkout')
        data = {'service': 1, 'how_many': 1, 'academy': 1, 'mentorship_service_set': 1}
        response = self.client.post(url, data, format='json')
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {'detail': 'service-type-no-implemented', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({'lang': 'en'}),
        ])

    # Given: 1 User, 1 Service and 1 Academy
    # When: is auth, with a service, how_many and academy in body,
    # ----> mentorship_service_set and service type is MENTORSHIP_SERVICE_SET or
    # ----> event_type_set in body and service type is EVENT_TYPE_SET
    # Then: return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__academy_service_not_found(self):
        kwargs = {}

        if random.randint(0, 1) == 0:
            service = {'type': 'MENTORSHIP_SERVICE_SET'}
            kwargs['mentorship_service_set'] = 1
        else:
            service = {'type': 'EVENT_TYPE_SET'}
            kwargs['event_type_set'] = 1

        model = self.bc.database.create(user=1, service=service, academy=1, **kwargs)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:consumable_checkout')
        data = {'service': 1, 'how_many': 1, 'academy': 1, **kwargs}
        response = self.client.post(url, data, format='json')
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {'detail': 'academy-service-not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({'lang': 'en'}),
        ])

    # Given: 1 User, 1 Service, 1 Academy and 1 AcademyService
    # When: is auth, with a service, how_many and academy in body,
    # ----> mentorship_service_set and service type is MENTORSHIP_SERVICE_SET or
    # ----> event_type_set in body and service type is EVENT_TYPE_SET,
    # ----> academy_service price_per_unit is less than 0.50
    # Then: return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('stripe.Charge.create', MagicMock(return_value={'id': 1}))
    @patch('stripe.Customer.create', MagicMock(return_value={'id': 1}))
    @patch('stripe.Refund.create', MagicMock(return_value={'id': 1}))
    def test__value_too_low(self):
        kwargs = {}

        how_many = random.randint(1, 10)

        if random.randint(0, 1) == 0:
            service = {'type': 'MENTORSHIP_SERVICE_SET'}
            kwargs['mentorship_service_set'] = 1

        else:
            service = {'type': 'EVENT_TYPE_SET'}
            kwargs['event_type_set'] = 1

        academy_service = {'price_per_unit': random.random() / 2.01 / how_many}
        model = self.bc.database.create(user=1,
                                        service=service,
                                        academy=1,
                                        academy_service=academy_service,
                                        **kwargs)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:consumable_checkout')
        data = {'service': 1, 'how_many': how_many, 'academy': 1, **kwargs}
        response = self.client.post(url, data, format='json')
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {'detail': 'the-amount-is-too-low', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({'lang': 'en'}),
        ])

        self.assertEqual(stripe.Charge.create.call_args_list, [])
        self.assertEqual(stripe.Customer.create.call_args_list, [])
        self.assertEqual(stripe.Refund.create.call_args_list, [])

    # Given: 1 User, 1 Service, 1 Academy, 1 AcademyService and 1 MentorshipServiceSet
    # When: is auth, with a service, how_many, academy and mentorship_service_set in body,
    # ----> academy_service price_per_unit is greater than 0.50
    # Then: return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('stripe.Charge.create', MagicMock(return_value={'id': 1}))
    @patch('stripe.Customer.create', MagicMock(return_value={'id': 1}))
    @patch('stripe.Refund.create', MagicMock(return_value={'id': 1}))
    def test__x_mentorship_service_set_bought(self):
        how_many = random.randint(1, 10)

        service = {'type': 'MENTORSHIP_SERVICE_SET'}
        price_per_unit = (random.random() + 0.50) * 100 / how_many
        academy_service = {'price_per_unit': price_per_unit}

        model = self.bc.database.create(user=1,
                                        service=service,
                                        academy=1,
                                        academy_service=academy_service,
                                        mentorship_service_set=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:consumable_checkout')
        data = {'service': 1, 'how_many': how_many, 'academy': 1, 'mentorship_service_set': 1}
        response = self.client.post(url, data, format='json')
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = get_serializer(self,
                                  model.currency,
                                  model.user,
                                  data={
                                      'amount': math.ceil(price_per_unit * how_many),
                                  })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [format_bag_item()])
        self.assertEqual(
            self.bc.database.list_of('payments.Invoice'),
            [format_invoice_item({
                'stripe_id': '1',
                'amount': math.ceil(price_per_unit * how_many),
            })])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [
            format_consumable_item(data={
                'mentorship_service_set_id': 1,
                'service_item_id': 1,
                'user_id': 1,
                'how_many': how_many,
            }),
        ])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({'lang': 'en'}),
        ])

        self.bc.check.calls(stripe.Charge.create.call_args_list, [
            call(customer='1',
                 amount=math.ceil(price_per_unit * how_many),
                 currency=model.currency.code.lower(),
                 description=f'Can join to {how_many} mentorships'),
        ])
        self.assertEqual(stripe.Customer.create.call_args_list, [
            call(email=model.user.email, name=f'{model.user.first_name} {model.user.last_name}'),
        ])
        self.assertEqual(stripe.Refund.create.call_args_list, [])

    # Given: 1 User, 1 Service, 1 Academy, 1 AcademyService and 1 EventTypeSet
    # When: is auth, with a service, how_many, academy and event_type_set in body,
    # ----> academy_service price_per_unit is greater than 0.50
    # Then: return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('stripe.Charge.create', MagicMock(return_value={'id': 1}))
    @patch('stripe.Customer.create', MagicMock(return_value={'id': 1}))
    @patch('stripe.Refund.create', MagicMock(return_value={'id': 1}))
    def test__x_event_type_set_bought(self):
        how_many = random.randint(1, 10)

        service = {'type': 'EVENT_TYPE_SET'}
        price_per_unit = (random.random() + 0.50) * 100 / how_many
        academy_service = {'price_per_unit': price_per_unit}

        model = self.bc.database.create(user=1,
                                        service=service,
                                        academy=1,
                                        academy_service=academy_service,
                                        event_type_set=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:consumable_checkout')
        data = {'service': 1, 'how_many': how_many, 'academy': 1, 'event_type_set': 1}
        response = self.client.post(url, data, format='json')
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = get_serializer(self,
                                  model.currency,
                                  model.user,
                                  data={
                                      'amount': math.ceil(price_per_unit * how_many),
                                  })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [format_bag_item()])
        self.assertEqual(
            self.bc.database.list_of('payments.Invoice'),
            [format_invoice_item({
                'stripe_id': '1',
                'amount': math.ceil(price_per_unit * how_many),
            })])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [
            format_consumable_item(data={
                'event_type_set_id': 1,
                'service_item_id': 1,
                'user_id': 1,
                'how_many': how_many,
            }),
        ])
        self.assertEqual(self.bc.database.list_of('authenticate.UserSetting'), [
            format_user_setting({'lang': 'en'}),
        ])

        self.bc.check.calls(stripe.Charge.create.call_args_list, [
            call(customer='1',
                 amount=math.ceil(price_per_unit * how_many),
                 currency=model.currency.code.lower(),
                 description=f'Can join to {how_many} events'),
        ])
        self.assertEqual(stripe.Customer.create.call_args_list, [
            call(email=model.user.email, name=f'{model.user.first_name} {model.user.last_name}'),
        ])
        self.assertEqual(stripe.Refund.create.call_args_list, [])
