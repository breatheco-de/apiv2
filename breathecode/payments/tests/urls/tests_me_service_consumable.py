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


def format_user_setting(data={}):
    return {
        'id': 1,
        'user_id': 1,
        'main_currency_id': None,
        'lang': 'en',
        **data,
    }


def format_invoice_item(data={}):
    return {
        'academy_id': None,
        'amount': 0.0,
        'currency_id': 1,
        'bag_id': None,
        'id': 1,
        'paid_at': UTC_NOW,
        'status': 'FULFILLED',
        'stripe_id': None,
        'user_id': 1,
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


def generate_amounts_by_time():
    return {
        'amount_per_month': random.random() * 100 + 1,
        'amount_per_quarter': random.random() * 100 + 1,
        'amount_per_half': random.random() * 100 + 1,
        'amount_per_year': random.random() * 100 + 1,
    }


def generate_three_amounts_by_time():
    l = random.shuffle([
        0,
        random.random() * 100 + 1,
        random.random() * 100 + 1,
        random.random() * 100 + 1,
    ])
    return {
        'amount_per_month': l[0],
        'amount_per_quarter': l[1],
        'amount_per_half': l[2],
        'amount_per_year': l[3],
    }


def which_amount_is_zero(data={}):
    for key in data:
        if key == 'amount_per_quarter':
            return 'MONTH', 1


CHOSEN_PERIOD = {
    'MONTH': 'amount_per_month',
    'QUARTER': 'amount_per_quarter',
    'HALF': 'amount_per_half',
    'YEAR': 'amount_per_year',
}


def get_amount_per_period(period, data):
    return data[CHOSEN_PERIOD[period]]


def serialize_consumable(consumable, data={}):
    return {
        'how_many': consumable.how_many,
        'id': consumable.id,
        'unit_type': consumable.unit_type,
        'valid_until': consumable.valid_until,
        **data,
    }


class SignalTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 GET without auth
    """

    def test__without_auth(self):
        url = reverse_lazy('payments:me_service_consumable')
        response = self.client.get(url)

        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    """
    🔽🔽🔽 Get with zero Consumable
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__without_consumables(self):
        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable')
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {'mentorship_services': [], 'cohorts': [], 'event_types': []}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    """
    🔽🔽🔽 Get with one Consumable, how_many = 0
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__one_consumable__how_many_is_zero(self):
        model = self.bc.database.create_v2(user=1, consumable=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable')
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {'mentorship_services': [], 'cohorts': [], 'event_types': []}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [
            self.bc.format.to_dict(model.consumable),
        ])

    """
    🔽🔽🔽 Get with nine Consumable and three Cohort, random how_many
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__random_how_many__related_to_three_cohorts__without_cohorts_in_querystring(
            self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'cohort_id': math.floor(n / 3) + 1
        } for n in range(9)]

        model = self.bc.database.create(user=1, consumable=consumables, cohort=3)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable')
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_services': [],
            'cohorts': [],
            'event_types': [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__random_how_many__related_to_three_cohorts__with_cohorts_in_querystring(self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'cohort_id': math.floor(n / 3) + 1
        } for n in range(9)]
        belong_to_cohort1 = consumables[:3]
        belong_to_cohort2 = consumables[3:6]
        belong_to_cohort3 = consumables[6:]

        how_many_belong_to_cohort1 = sum([x['how_many'] for x in belong_to_cohort1])
        how_many_belong_to_cohort2 = sum([x['how_many'] for x in belong_to_cohort2])
        how_many_belong_to_cohort3 = sum([x['how_many'] for x in belong_to_cohort3])

        model = self.bc.database.create(user=1, consumable=consumables, cohort=3)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable') + '?cohort=1,2,3'
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_services': [],
            'cohorts': [
                {
                    'balance': {
                        'unit': how_many_belong_to_cohort1
                    },
                    'id': model.cohort[0].id,
                    'slug': model.cohort[0].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to_cohort2,
                    },
                    'id': model.cohort[1].id,
                    'slug': model.cohort[1].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to_cohort3,
                    },
                    'id': model.cohort[2].id,
                    'slug': model.cohort[2].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            'event_types': [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    """
    🔽🔽🔽 Get with nine Consumable and three MentorshipService, random how_many
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_mentorship_services__without_cohorts_in_querystring(self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'mentorship_service_id': math.floor(n / 3) + 1
        } for n in range(9)]

        model = self.bc.database.create(user=1, consumable=consumables, mentorship_service=3)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable')
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_services': [],
            'cohorts': [],
            'event_types': [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_mentorship_services__with_cohorts_in_querystring(self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'mentorship_service_id': math.floor(n / 3) + 1
        } for n in range(9)]
        belong_to_cohort1 = consumables[:3]
        belong_to_cohort2 = consumables[3:6]
        belong_to_cohort3 = consumables[6:]

        how_many_belong_to_cohort1 = sum([x['how_many'] for x in belong_to_cohort1])
        how_many_belong_to_cohort2 = sum([x['how_many'] for x in belong_to_cohort2])
        how_many_belong_to_cohort3 = sum([x['how_many'] for x in belong_to_cohort3])

        model = self.bc.database.create(user=1, consumable=consumables, mentorship_service=3)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable') + '?mentorship_service=1,2,3'
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'cohorts': [],
            'mentorship_services': [
                {
                    'balance': {
                        'unit': how_many_belong_to_cohort1,
                    },
                    'id': model.mentorship_service[0].id,
                    'slug': model.mentorship_service[0].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to_cohort2,
                    },
                    'id': model.mentorship_service[1].id,
                    'slug': model.mentorship_service[1].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to_cohort3,
                    },
                    'id': model.mentorship_service[2].id,
                    'slug': model.mentorship_service[2].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            'event_types': [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    """
    🔽🔽🔽 Get with nine Consumable and three EventType, random how_many
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_event_types__without_cohorts_in_querystring(self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'event_type_id': math.floor(n / 3) + 1
        } for n in range(9)]

        model = self.bc.database.create(user=1, consumable=consumables, event_type=3)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable')
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_services': [],
            'cohorts': [],
            'event_types': [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_event_types__with_cohorts_in_querystring(self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'event_type_id': math.floor(n / 3) + 1
        } for n in range(9)]
        belong_to_cohort1 = consumables[:3]
        belong_to_cohort2 = consumables[3:6]
        belong_to_cohort3 = consumables[6:]

        how_many_belong_to_cohort1 = sum([x['how_many'] for x in belong_to_cohort1])
        how_many_belong_to_cohort2 = sum([x['how_many'] for x in belong_to_cohort2])
        how_many_belong_to_cohort3 = sum([x['how_many'] for x in belong_to_cohort3])

        model = self.bc.database.create(user=1, consumable=consumables, event_type=3)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable') + '?event_type=1,2,3'
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'cohorts': [],
            'event_types': [
                {
                    'balance': {
                        'unit': how_many_belong_to_cohort1,
                    },
                    'id': model.event_type[0].id,
                    'slug': model.event_type[0].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to_cohort2,
                    },
                    'id': model.event_type[1].id,
                    'slug': model.event_type[1].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to_cohort3,
                    },
                    'id': model.event_type[2].id,
                    'slug': model.event_type[2].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            'mentorship_services': [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    """
    🔽🔽🔽 Get with nine Consumable and three Cohort, random how_many
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__random_how_many__related_to_three_cohorts__without_cohort_slugs_in_querystring(
            self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'cohort_id': math.floor(n / 3) + 1
        } for n in range(9)]

        model = self.bc.database.create(user=1, consumable=consumables, cohort=3)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable')
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_services': [],
            'cohorts': [],
            'event_types': [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__random_how_many__related_to_three_cohorts__with_cohort_slugs_in_querystring(
            self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'cohort_id': math.floor(n / 3) + 1
        } for n in range(9)]
        belong_to_cohort1 = consumables[:3]
        belong_to_cohort2 = consumables[3:6]
        belong_to_cohort3 = consumables[6:]

        how_many_belong_to_cohort1 = sum([x['how_many'] for x in belong_to_cohort1])
        how_many_belong_to_cohort2 = sum([x['how_many'] for x in belong_to_cohort2])
        how_many_belong_to_cohort3 = sum([x['how_many'] for x in belong_to_cohort3])

        model = self.bc.database.create(user=1, consumable=consumables, cohort=3)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy(
            'payments:me_service_consumable') + f'?cohort_slug={",".join([x.slug for x in model.cohort])}'
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_services': [],
            'cohorts': [
                {
                    'balance': {
                        'unit': how_many_belong_to_cohort1,
                    },
                    'id': model.cohort[0].id,
                    'slug': model.cohort[0].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to_cohort2,
                    },
                    'id': model.cohort[1].id,
                    'slug': model.cohort[1].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to_cohort3,
                    },
                    'id': model.cohort[2].id,
                    'slug': model.cohort[2].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            'event_types': [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    """
    🔽🔽🔽 Get with nine Consumable and three MentorshipService, random how_many
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_mentorship_services__without_cohort_slugs_in_querystring(
            self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'mentorship_service_id': math.floor(n / 3) + 1
        } for n in range(9)]

        model = self.bc.database.create(user=1, consumable=consumables, mentorship_service=3)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable')
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_services': [],
            'cohorts': [],
            'event_types': [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_mentorship_services__with_cohort_slugs_in_querystring(self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'mentorship_service_id': math.floor(n / 3) + 1
        } for n in range(9)]
        belong_to_cohort1 = consumables[:3]
        belong_to_cohort2 = consumables[3:6]
        belong_to_cohort3 = consumables[6:]

        how_many_belong_to_cohort1 = sum([x['how_many'] for x in belong_to_cohort1])
        how_many_belong_to_cohort2 = sum([x['how_many'] for x in belong_to_cohort2])
        how_many_belong_to_cohort3 = sum([x['how_many'] for x in belong_to_cohort3])

        model = self.bc.database.create(user=1, consumable=consumables, mentorship_service=3)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy(
            'payments:me_service_consumable'
        ) + f'?mentorship_service_slug={",".join([x.slug for x in model.mentorship_service])}'
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'cohorts': [],
            'mentorship_services': [
                {
                    'balance': {
                        'unit': how_many_belong_to_cohort1,
                    },
                    'id': model.mentorship_service[0].id,
                    'slug': model.mentorship_service[0].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to_cohort2,
                    },
                    'id': model.mentorship_service[1].id,
                    'slug': model.mentorship_service[1].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to_cohort3,
                    },
                    'id': model.mentorship_service[2].id,
                    'slug': model.mentorship_service[2].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            'event_types': [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    """
    🔽🔽🔽 Get with nine Consumable and three EventType, random how_many
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_event_types__without_cohort_slugs_in_querystring(self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'event_type_id': math.floor(n / 3) + 1
        } for n in range(9)]

        model = self.bc.database.create(user=1, consumable=consumables, event_type=3)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable')
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_services': [],
            'cohorts': [],
            'event_types': [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_event_types__with_cohort_slugs_in_querystring(self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'event_type_id': math.floor(n / 3) + 1
        } for n in range(9)]
        belong_to_cohort1 = consumables[:3]
        belong_to_cohort2 = consumables[3:6]
        belong_to_cohort3 = consumables[6:]

        how_many_belong_to_cohort1 = sum([x['how_many'] for x in belong_to_cohort1])
        how_many_belong_to_cohort2 = sum([x['how_many'] for x in belong_to_cohort2])
        how_many_belong_to_cohort3 = sum([x['how_many'] for x in belong_to_cohort3])

        model = self.bc.database.create(user=1, consumable=consumables, event_type=3)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable'
                           ) + f'?event_type_slug={",".join([x.slug for x in model.event_type])}'
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'cohorts': [],
            'event_types': [
                {
                    'balance': {
                        'unit': how_many_belong_to_cohort1,
                    },
                    'id': model.event_type[0].id,
                    'slug': model.event_type[0].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to_cohort2,
                    },
                    'id': model.event_type[1].id,
                    'slug': model.event_type[1].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to_cohort3,
                    },
                    'id': model.event_type[2].id,
                    'slug': model.event_type[2].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            'mentorship_services': [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    """
    🔽🔽🔽 Get with six Consumable, one EventType, one MentorshipService and Cohort, with one -1
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__six_consumables__related_to_all_the_Resources__with_all_slugs_in_querystring(self):
        r1 = [-1, random.randint(1, 30)]
        random.shuffle(r1)

        r2 = [-1, random.randint(1, 30)]
        random.shuffle(r2)

        r3 = [-1, random.randint(1, 30)]
        random.shuffle(r3)

        consumables = [{
            'how_many': n,
            'event_type_id': 1,
            'cohort_id': None,
            'mentorship_service_id': None,
        } for n in r1] + [{
            'how_many': n,
            'event_type_id': None,
            'cohort_id': 1,
            'mentorship_service_id': None,
        } for n in r2] + [{
            'how_many': n,
            'event_type_id': None,
            'cohort_id': None,
            'mentorship_service_id': 1,
        } for n in r3]
        belong_to_cohort1 = consumables[:3]
        belong_to_cohort2 = consumables[3:6]
        belong_to_cohort3 = consumables[6:]

        how_many_belong_to_cohort1 = sum([x['how_many'] for x in belong_to_cohort1])
        how_many_belong_to_cohort2 = sum([x['how_many'] for x in belong_to_cohort2])
        how_many_belong_to_cohort3 = sum([x['how_many'] for x in belong_to_cohort3])

        model = self.bc.database.create(user=1,
                                        consumable=consumables,
                                        event_type=1,
                                        cohort=1,
                                        mentorship_service=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable'
                           ) + f'?event_type_slug={model.event_type.slug}' \
                           f'&cohort_slug={model.cohort.slug}' \
                           f'&mentorship_service_slug={model.mentorship_service.slug}'

        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'cohorts': [
                {
                    'balance': {
                        'unit': -1,
                    },
                    'id':
                    model.cohort.id,
                    'slug':
                    model.cohort.slug,
                    'items': [
                        serialize_consumable(model.consumable[2]),
                        serialize_consumable(model.consumable[3]),
                    ],
                },
            ],
            'event_types': [
                {
                    'balance': {
                        'unit': -1,
                    },
                    'id':
                    model.event_type.id,
                    'slug':
                    model.event_type.slug,
                    'items': [
                        serialize_consumable(model.consumable[0]),
                        serialize_consumable(model.consumable[1]),
                    ],
                },
            ],
            'mentorship_services': [
                {
                    'balance': {
                        'unit': -1,
                    },
                    'id':
                    model.mentorship_service.id,
                    'slug':
                    model.mentorship_service.slug,
                    'items': [
                        serialize_consumable(model.consumable[4]),
                        serialize_consumable(model.consumable[5]),
                    ],
                },
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )
