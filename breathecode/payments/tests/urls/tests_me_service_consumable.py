import math
import random
from unittest.mock import MagicMock, patch

from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.tests.mixins.legacy import LegacyAPITestCase

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


class TestSignal(LegacyAPITestCase):
    """
    🔽🔽🔽 GET without auth
    """

    def test__without_auth(self):
        url = reverse_lazy('payments:me_service_consumable')
        response = self.client.get(url)

        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    """
    🔽🔽🔽 Get with zero Consumable
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__without_consumables(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable')
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_service_sets': [],
            'cohort_sets': [],
            'event_type_sets': [],
            'service_sets': [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    """
    🔽🔽🔽 Get with one Consumable, how_many = 0
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__one_consumable__how_many_is_zero(self):
        model = self.bc.database.create_v2(user=1, consumable=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable')
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_service_sets': [],
            'cohort_sets': [],
            'event_type_sets': [],
            'service_sets': [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [
            self.bc.format.to_dict(model.consumable),
        ])

    """
    🔽🔽🔽 Get with nine Consumable and three Cohort, random how_many
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__random_how_many__related_to_three_cohorts__without_cohorts_in_querystring(self):
        consumables = [{'how_many': random.randint(1, 30), 'cohort_set_id': math.floor(n / 3) + 1} for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x['how_many'] for x in belong_to1])
        how_many_belong_to2 = sum([x['how_many'] for x in belong_to2])
        how_many_belong_to3 = sum([x['how_many'] for x in belong_to3])

        academy = {'available_as_saas': True}

        model = self.bc.database.create(user=1, consumable=consumables, cohort_set=3, academy=academy)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable')
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_service_sets': [],
            'cohort_sets': [
                {
                    'balance': {
                        'unit': how_many_belong_to1
                    },
                    'id': model.cohort_set[0].id,
                    'slug': model.cohort_set[0].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to2,
                    },
                    'id': model.cohort_set[1].id,
                    'slug': model.cohort_set[1].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to3,
                    },
                    'id': model.cohort_set[2].id,
                    'slug': model.cohort_set[2].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            'event_type_sets': [],
            'service_sets': [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__random_how_many__related_to_three_cohorts__with_wrong_cohorts_in_querystring(self):
        consumables = [{'how_many': random.randint(1, 30), 'cohort_set_id': math.floor(n / 3) + 1} for n in range(9)]

        academy = {'available_as_saas': True}

        model = self.bc.database.create(user=1, consumable=consumables, cohort_set=3, academy=academy)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable') + '?cohort_set=4,5,6'
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_service_sets': [],
            'cohort_sets': [],
            'event_type_sets': [],
            'service_sets': [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__random_how_many__related_to_three_cohorts__with_cohorts_in_querystring(self):
        consumables = [{'how_many': random.randint(1, 30), 'cohort_set_id': math.floor(n / 3) + 1} for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x['how_many'] for x in belong_to1])
        how_many_belong_to2 = sum([x['how_many'] for x in belong_to2])
        how_many_belong_to3 = sum([x['how_many'] for x in belong_to3])

        academy = {'available_as_saas': True}

        model = self.bc.database.create(user=1, consumable=consumables, cohort_set=3, academy=academy)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable') + '?cohort_set=1,2,3'
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_service_sets': [],
            'cohort_sets': [
                {
                    'balance': {
                        'unit': how_many_belong_to1
                    },
                    'id': model.cohort_set[0].id,
                    'slug': model.cohort_set[0].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to2,
                    },
                    'id': model.cohort_set[1].id,
                    'slug': model.cohort_set[1].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to3,
                    },
                    'id': model.cohort_set[2].id,
                    'slug': model.cohort_set[2].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            'event_type_sets': [],
            'service_sets': [],
        }

        assert json == expected
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
            'mentorship_service_set_id': math.floor(n / 3) + 1
        } for n in range(9)]

        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x['how_many'] for x in belong_to1])
        how_many_belong_to2 = sum([x['how_many'] for x in belong_to2])
        how_many_belong_to3 = sum([x['how_many'] for x in belong_to3])

        model = self.bc.database.create(user=1, consumable=consumables, mentorship_service_set=3)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable')
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_service_sets': [
                {
                    'balance': {
                        'unit': how_many_belong_to1,
                    },
                    'id': model.mentorship_service_set[0].id,
                    'slug': model.mentorship_service_set[0].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to2,
                    },
                    'id': model.mentorship_service_set[1].id,
                    'slug': model.mentorship_service_set[1].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to3,
                    },
                    'id': model.mentorship_service_set[2].id,
                    'slug': model.mentorship_service_set[2].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            'cohort_sets': [],
            'event_type_sets': [],
            'service_sets': [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_mentorship_services__with_wrong_cohorts_in_querystring(self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'mentorship_service_set_id': math.floor(n / 3) + 1
        } for n in range(9)]

        model = self.bc.database.create(user=1, consumable=consumables, mentorship_service_set=3)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable') + '?mentorship_service_set=4,5,6'
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'cohort_sets': [],
            'mentorship_service_sets': [],
            'event_type_sets': [],
            'service_sets': [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_mentorship_services__with_cohorts_in_querystring(self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'mentorship_service_set_id': math.floor(n / 3) + 1
        } for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x['how_many'] for x in belong_to1])
        how_many_belong_to2 = sum([x['how_many'] for x in belong_to2])
        how_many_belong_to3 = sum([x['how_many'] for x in belong_to3])

        model = self.bc.database.create(user=1, consumable=consumables, mentorship_service_set=3)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable') + '?mentorship_service_set=1,2,3'
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'cohort_sets': [],
            'mentorship_service_sets': [
                {
                    'balance': {
                        'unit': how_many_belong_to1,
                    },
                    'id': model.mentorship_service_set[0].id,
                    'slug': model.mentorship_service_set[0].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to2,
                    },
                    'id': model.mentorship_service_set[1].id,
                    'slug': model.mentorship_service_set[1].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to3,
                    },
                    'id': model.mentorship_service_set[2].id,
                    'slug': model.mentorship_service_set[2].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            'event_type_sets': [],
            'service_sets': [],
        }

        assert json == expected
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
            'event_type_set_id': math.floor(n / 3) + 1
        } for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x['how_many'] for x in belong_to1])
        how_many_belong_to2 = sum([x['how_many'] for x in belong_to2])
        how_many_belong_to3 = sum([x['how_many'] for x in belong_to3])

        event_type_sets = [{'event_type_id': x} for x in range(1, 4)]

        model = self.bc.database.create(user=1,
                                        consumable=consumables,
                                        event_type_set=event_type_sets,
                                        event_type=[{
                                            'icon_url': 'https://www.google.com'
                                        }, {
                                            'icon_url': 'https://www.google.com'
                                        }, {
                                            'icon_url': 'https://www.google.com'
                                        }])
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable')
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_service_sets': [],
            'cohort_sets': [],
            'event_type_sets': [
                {
                    'balance': {
                        'unit': how_many_belong_to1,
                    },
                    'id': model.event_type_set[0].id,
                    'slug': model.event_type_set[0].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to2,
                    },
                    'id': model.event_type_set[1].id,
                    'slug': model.event_type_set[1].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to3,
                    },
                    'id': model.event_type_set[2].id,
                    'slug': model.event_type_set[2].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            'service_sets': [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_event_types__with_wrong_cohorts_in_querystring(self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'event_type_set_id': math.floor(n / 3) + 1
        } for n in range(9)]

        event_type_sets = [{'event_type_id': x} for x in range(1, 4)]
        model = self.bc.database.create(user=1,
                                        consumable=consumables,
                                        event_type_set=event_type_sets,
                                        event_type=[{
                                            'icon_url': 'https://www.google.com'
                                        }, {
                                            'icon_url': 'https://www.google.com'
                                        }, {
                                            'icon_url': 'https://www.google.com'
                                        }])
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable') + '?event_type_set=4,5,6'
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'cohort_sets': [],
            'event_type_sets': [],
            'mentorship_service_sets': [],
            'service_sets': [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_event_types__with_cohorts_in_querystring(self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'event_type_set_id': math.floor(n / 3) + 1
        } for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x['how_many'] for x in belong_to1])
        how_many_belong_to2 = sum([x['how_many'] for x in belong_to2])
        how_many_belong_to3 = sum([x['how_many'] for x in belong_to3])

        event_type_sets = [{'event_type_id': x} for x in range(1, 4)]
        model = self.bc.database.create(user=1,
                                        consumable=consumables,
                                        event_type_set=event_type_sets,
                                        event_type=[{
                                            'icon_url': 'https://www.google.com'
                                        }, {
                                            'icon_url': 'https://www.google.com'
                                        }, {
                                            'icon_url': 'https://www.google.com'
                                        }])
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable') + '?event_type_set=1,2,3'
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'cohort_sets': [],
            'event_type_sets': [
                {
                    'balance': {
                        'unit': how_many_belong_to1,
                    },
                    'id': model.event_type_set[0].id,
                    'slug': model.event_type_set[0].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to2,
                    },
                    'id': model.event_type_set[1].id,
                    'slug': model.event_type_set[1].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to3,
                    },
                    'id': model.event_type_set[2].id,
                    'slug': model.event_type_set[2].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            'mentorship_service_sets': [],
            'service_sets': [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    """
    🔽🔽🔽 Get with nine Consumable and three ServiceSet, random how_many
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__random_how_many__related_to_three_cohorts__without_cohort_slugs_in_querystring(self):
        consumables = [{'how_many': random.randint(1, 30), 'cohort_set_id': math.floor(n / 3) + 1} for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x['how_many'] for x in belong_to1])
        how_many_belong_to2 = sum([x['how_many'] for x in belong_to2])
        how_many_belong_to3 = sum([x['how_many'] for x in belong_to3])

        academy = {'available_as_saas': True}

        model = self.bc.database.create(user=1, consumable=consumables, service_set=3, academy=academy)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable')
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_service_sets': [],
            'cohort_sets': [],
            'event_type_sets': [],
            'service_sets': [
                {
                    'balance': {
                        'unit': how_many_belong_to1,
                    },
                    'id': model.service_set[0].id,
                    'slug': model.service_set[0].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to2,
                    },
                    'id': model.service_set[1].id,
                    'slug': model.service_set[1].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to3,
                    },
                    'id': model.service_set[2].id,
                    'slug': model.service_set[2].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__random_how_many__related_to_three_cohorts__with_wrong_cohort_slugs_in_querystring(self):
        consumables = [{'how_many': random.randint(1, 30), 'cohort_set_id': math.floor(n / 3) + 1} for n in range(9)]

        academy = {'available_as_saas': True}

        model = self.bc.database.create(user=1, consumable=consumables, service_set=3, academy=academy)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable') + f'?service_set_slug=blabla1,blabla2,blabla3'
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_service_sets': [],
            'cohort_sets': [],
            'event_type_sets': [],
            'service_sets': [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__random_how_many__related_to_three_cohorts__with_cohort_slugs_in_querystring(self):
        consumables = [{'how_many': random.randint(1, 30), 'cohort_set_id': math.floor(n / 3) + 1} for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x['how_many'] for x in belong_to1])
        how_many_belong_to2 = sum([x['how_many'] for x in belong_to2])
        how_many_belong_to3 = sum([x['how_many'] for x in belong_to3])

        academy = {'available_as_saas': True}

        model = self.bc.database.create(user=1, consumable=consumables, service_set=3, academy=academy)
        self.client.force_authenticate(model.user)

        url = reverse_lazy(
            'payments:me_service_consumable') + f'?service_set_slug={",".join([x.slug for x in model.service_set])}'
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_service_sets': [],
            'cohort_sets': [],
            'event_type_sets': [],
            'service_sets': [
                {
                    'balance': {
                        'unit': how_many_belong_to1,
                    },
                    'id': model.service_set[0].id,
                    'slug': model.service_set[0].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to2,
                    },
                    'id': model.service_set[1].id,
                    'slug': model.service_set[1].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to3,
                    },
                    'id': model.service_set[2].id,
                    'slug': model.service_set[2].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )
        """
    🔽🔽🔽 Get with nine Consumable and three Cohort, random how_many
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__random_how_many__related_to_three_cohorts__without_cohort_slugs_in_querystring(self):
        consumables = [{'how_many': random.randint(1, 30), 'cohort_set_id': math.floor(n / 3) + 1} for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x['how_many'] for x in belong_to1])
        how_many_belong_to2 = sum([x['how_many'] for x in belong_to2])
        how_many_belong_to3 = sum([x['how_many'] for x in belong_to3])

        academy = {'available_as_saas': True}

        model = self.bc.database.create(user=1, consumable=consumables, cohort_set=3, academy=academy)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable')
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_service_sets': [],
            'cohort_sets': [
                {
                    'balance': {
                        'unit': how_many_belong_to1,
                    },
                    'id': model.cohort_set[0].id,
                    'slug': model.cohort_set[0].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to2,
                    },
                    'id': model.cohort_set[1].id,
                    'slug': model.cohort_set[1].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to3,
                    },
                    'id': model.cohort_set[2].id,
                    'slug': model.cohort_set[2].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            'event_type_sets': [],
            'service_sets': [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__random_how_many__related_to_three_cohorts__with_wrong_cohort_slugs_in_querystring(self):
        consumables = [{'how_many': random.randint(1, 30), 'cohort_set_id': math.floor(n / 3) + 1} for n in range(9)]

        academy = {'available_as_saas': True}

        model = self.bc.database.create(user=1, consumable=consumables, cohort_set=3, academy=academy)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable') + f'?cohort_set_slug=blabla1,blabla2,blabla3'
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_service_sets': [],
            'cohort_sets': [],
            'event_type_sets': [],
            'service_sets': [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__random_how_many__related_to_three_cohorts__with_cohort_slugs_in_querystring(self):
        consumables = [{'how_many': random.randint(1, 30), 'cohort_set_id': math.floor(n / 3) + 1} for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x['how_many'] for x in belong_to1])
        how_many_belong_to2 = sum([x['how_many'] for x in belong_to2])
        how_many_belong_to3 = sum([x['how_many'] for x in belong_to3])

        academy = {'available_as_saas': True}

        model = self.bc.database.create(user=1, consumable=consumables, cohort_set=3, academy=academy)
        self.client.force_authenticate(model.user)

        url = reverse_lazy(
            'payments:me_service_consumable') + f'?cohort_set_slug={",".join([x.slug for x in model.cohort_set])}'
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_service_sets': [],
            'cohort_sets': [
                {
                    'balance': {
                        'unit': how_many_belong_to1,
                    },
                    'id': model.cohort_set[0].id,
                    'slug': model.cohort_set[0].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to2,
                    },
                    'id': model.cohort_set[1].id,
                    'slug': model.cohort_set[1].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to3,
                    },
                    'id': model.cohort_set[2].id,
                    'slug': model.cohort_set[2].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            'event_type_sets': [],
            'service_sets': [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    """
    🔽🔽🔽 Get with nine Consumable and three MentorshipService, random how_many
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_mentorship_services__without_cohort_slugs_in_querystring(self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'mentorship_service_set_id': math.floor(n / 3) + 1
        } for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x['how_many'] for x in belong_to1])
        how_many_belong_to2 = sum([x['how_many'] for x in belong_to2])
        how_many_belong_to3 = sum([x['how_many'] for x in belong_to3])

        model = self.bc.database.create(user=1, consumable=consumables, mentorship_service_set=3)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable')
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_service_sets': [
                {
                    'balance': {
                        'unit': how_many_belong_to1,
                    },
                    'id': model.mentorship_service_set[0].id,
                    'slug': model.mentorship_service_set[0].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to2,
                    },
                    'id': model.mentorship_service_set[1].id,
                    'slug': model.mentorship_service_set[1].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to3,
                    },
                    'id': model.mentorship_service_set[2].id,
                    'slug': model.mentorship_service_set[2].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            'cohort_sets': [],
            'event_type_sets': [],
            'service_sets': [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_mentorship_services__with_wrong_cohort_slugs_in_querystring(self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'mentorship_service_set_id': math.floor(n / 3) + 1
        } for n in range(9)]

        model = self.bc.database.create(user=1, consumable=consumables, mentorship_service_set=3)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable') + f'?mentorship_service_set_slug=blabla1,blabla2,blabla3'
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'cohort_sets': [],
            'mentorship_service_sets': [],
            'event_type_sets': [],
            'service_sets': [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_mentorship_services__with_cohort_slugs_in_querystring(self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'mentorship_service_set_id': math.floor(n / 3) + 1
        } for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x['how_many'] for x in belong_to1])
        how_many_belong_to2 = sum([x['how_many'] for x in belong_to2])
        how_many_belong_to3 = sum([x['how_many'] for x in belong_to3])

        model = self.bc.database.create(user=1, consumable=consumables, mentorship_service_set=3)
        self.client.force_authenticate(model.user)

        url = reverse_lazy(
            'payments:me_service_consumable'
        ) + f'?mentorship_service_set_slug={",".join([x.slug for x in model.mentorship_service_set])}'
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'cohort_sets': [],
            'mentorship_service_sets': [
                {
                    'balance': {
                        'unit': how_many_belong_to1,
                    },
                    'id': model.mentorship_service_set[0].id,
                    'slug': model.mentorship_service_set[0].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to2,
                    },
                    'id': model.mentorship_service_set[1].id,
                    'slug': model.mentorship_service_set[1].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to3,
                    },
                    'id': model.mentorship_service_set[2].id,
                    'slug': model.mentorship_service_set[2].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            'event_type_sets': [],
            'service_sets': [],
        }

        assert json == expected
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
            'event_type_set_id': math.floor(n / 3) + 1
        } for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x['how_many'] for x in belong_to1])
        how_many_belong_to2 = sum([x['how_many'] for x in belong_to2])
        how_many_belong_to3 = sum([x['how_many'] for x in belong_to3])

        event_type_sets = [{'event_type_id': x} for x in range(1, 4)]
        model = self.bc.database.create(user=1,
                                        consumable=consumables,
                                        event_type_set=event_type_sets,
                                        event_type=[{
                                            'icon_url': 'https://www.google.com'
                                        }, {
                                            'icon_url': 'https://www.google.com'
                                        }, {
                                            'icon_url': 'https://www.google.com'
                                        }])
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable')
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'mentorship_service_sets': [],
            'cohort_sets': [],
            'event_type_sets': [
                {
                    'balance': {
                        'unit': how_many_belong_to1,
                    },
                    'id': model.event_type_set[0].id,
                    'slug': model.event_type_set[0].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to2,
                    },
                    'id': model.event_type_set[1].id,
                    'slug': model.event_type_set[1].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to3,
                    },
                    'id': model.event_type_set[2].id,
                    'slug': model.event_type_set[2].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            'service_sets': [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_event_types__with_wrong_cohort_slugs_in_querystring(self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'event_type_set_id': math.floor(n / 3) + 1
        } for n in range(9)]

        event_type_sets = [{'event_type_id': x} for x in range(1, 4)]
        model = self.bc.database.create(user=1,
                                        consumable=consumables,
                                        event_type_set=event_type_sets,
                                        event_type=[{
                                            'icon_url': 'https://www.google.com'
                                        }, {
                                            'icon_url': 'https://www.google.com'
                                        }, {
                                            'icon_url': 'https://www.google.com'
                                        }])
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable') + f'?event_type_set_slug=blabla1,blabla2,blabla3'
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'cohort_sets': [],
            'event_type_sets': [],
            'mentorship_service_sets': [],
            'service_sets': [],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__nine_consumables__related_to_three_event_types__with_cohort_slugs_in_querystring(self):
        consumables = [{
            'how_many': random.randint(1, 30),
            'event_type_set_id': math.floor(n / 3) + 1
        } for n in range(9)]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x['how_many'] for x in belong_to1])
        how_many_belong_to2 = sum([x['how_many'] for x in belong_to2])
        how_many_belong_to3 = sum([x['how_many'] for x in belong_to3])

        event_type_sets = [{'event_type_id': x} for x in range(1, 4)]
        model = self.bc.database.create(user=1,
                                        consumable=consumables,
                                        event_type_set=event_type_sets,
                                        event_type=[{
                                            'icon_url': 'https://www.google.com'
                                        }, {
                                            'icon_url': 'https://www.google.com'
                                        }, {
                                            'icon_url': 'https://www.google.com'
                                        }])
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable'
                           ) + f'?event_type_set_slug={",".join([x.slug for x in model.event_type_set])}'
        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'cohort_sets': [],
            'event_type_sets': [
                {
                    'balance': {
                        'unit': how_many_belong_to1,
                    },
                    'id': model.event_type_set[0].id,
                    'slug': model.event_type_set[0].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to2,
                    },
                    'id': model.event_type_set[1].id,
                    'slug': model.event_type_set[1].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
                {
                    'balance': {
                        'unit': how_many_belong_to3,
                    },
                    'id': model.event_type_set[2].id,
                    'slug': model.event_type_set[2].slug,
                    'items': [serialize_consumable(model.consumable[n]) for n in range(9)],
                },
            ],
            'mentorship_service_sets': [],
            'service_sets': [],
        }

        assert json == expected
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

        r4 = [-1, random.randint(1, 30)]
        random.shuffle(r4)

        consumables = [{
            'how_many': n,
            'event_type_set_id': 1,
            'cohort_set_id': None,
            'mentorship_service_set_id': None,
            'service_set_id': None,
        } for n in r1] + [{
            'how_many': n,
            'event_type_set_id': None,
            'cohort_set_id': 1,
            'mentorship_service_set_id': None,
            'service_set_id': None,
        } for n in r2] + [{
            'how_many': n,
            'event_type_set_id': None,
            'cohort_set_id': None,
            'mentorship_service_set_id': 1,
            'service_set_id': None,
        } for n in r3] + [{
            'how_many': n,
            'event_type_set_id': None,
            'cohort_set_id': None,
            'mentorship_service_set_id': None,
            'service_set_id': 1,
        } for n in r4]
        belong_to1 = consumables[:3]
        belong_to2 = consumables[3:6]
        belong_to3 = consumables[6:]

        how_many_belong_to1 = sum([x['how_many'] for x in belong_to1])
        how_many_belong_to2 = sum([x['how_many'] for x in belong_to2])
        how_many_belong_to3 = sum([x['how_many'] for x in belong_to3])

        academy = {'available_as_saas': True}

        event_type_set = {'event_type_id': 1}
        model = self.bc.database.create(user=1,
                                        consumable=consumables,
                                        event_type_set=event_type_set,
                                        event_type={'icon_url': 'https://www.google.com'},
                                        cohort_set=1,
                                        mentorship_service_set=1,
                                        service_set=1,
                                        academy=academy)
        self.client.force_authenticate(model.user)

        url = reverse_lazy('payments:me_service_consumable'
                           ) + f'?event_type_set_slug={model.event_type_set.slug}' \
                           f'&cohort_set_slug={model.cohort_set.slug}' \
                           f'&mentorship_service_set_slug={model.mentorship_service_set.slug}' \
                            f'&service_set_slug={model.service_set.slug}' \

        response = self.client.get(url)
        self.client.force_authenticate(model.user)

        json = response.json()
        expected = {
            'cohort_sets': [
                {
                    'balance': {
                        'unit': -1,
                    },
                    'id': model.cohort_set.id,
                    'slug': model.cohort_set.slug,
                    'items': [
                        serialize_consumable(model.consumable[2]),
                        serialize_consumable(model.consumable[3]),
                    ],
                },
            ],
            'event_type_sets': [
                {
                    'balance': {
                        'unit': -1,
                    },
                    'id': model.event_type_set.id,
                    'slug': model.event_type_set.slug,
                    'items': [
                        serialize_consumable(model.consumable[0]),
                        serialize_consumable(model.consumable[1]),
                    ],
                },
            ],
            'mentorship_service_sets': [
                {
                    'balance': {
                        'unit': -1,
                    },
                    'id': model.mentorship_service_set.id,
                    'slug': model.mentorship_service_set.slug,
                    'items': [
                        serialize_consumable(model.consumable[4]),
                        serialize_consumable(model.consumable[5]),
                    ],
                },
            ],
            'service_sets': [
                {
                    'balance': {
                        'unit': -1,
                    },
                    'id': model.service_set.id,
                    'slug': model.service_set.slug,
                    'items': [
                        serialize_consumable(model.consumable[6]),
                        serialize_consumable(model.consumable[7]),
                    ],
                },
            ],
        }

        assert json == expected
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('payments.Consumable'),
            self.bc.format.to_dict(model.consumable),
        )
