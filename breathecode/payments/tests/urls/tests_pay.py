import math
import random
from unittest.mock import MagicMock, call

import pytest
import stripe
from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import breathecode.activity.tasks as activity_tasks
from breathecode.admissions import tasks as admissions_tasks
from breathecode.payments import tasks
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

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


def get_serializer(bc, currency, user, data={}):
    return {
        'amount': 0,
        'currency': {
            'code': currency.code,
            'name': currency.name,
        },
        'paid_at': bc.datetime.to_iso_string(UTC_NOW),
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


def invoice_mock():

    class FakeInvoice:
        id = 1
        amount = 100

    return FakeInvoice()


@pytest.fixture(autouse=True)
def get_patch(db, monkeypatch):
    monkeypatch.setattr(activity_tasks.add_activity, 'delay', MagicMock())
    monkeypatch.setattr('breathecode.admissions.tasks.build_cohort_user.delay', MagicMock())
    monkeypatch.setattr('breathecode.admissions.tasks.build_profile_academy.delay', MagicMock())
    monkeypatch.setattr('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    monkeypatch.setattr('breathecode.payments.tasks.build_subscription.delay', MagicMock())
    monkeypatch.setattr('breathecode.payments.tasks.build_plan_financing.delay', MagicMock())
    monkeypatch.setattr('breathecode.payments.tasks.build_free_subscription.delay', MagicMock())
    monkeypatch.setattr('stripe.Charge.create', MagicMock(return_value={'id': 1}))
    monkeypatch.setattr('stripe.Customer.create', MagicMock(return_value={'id': 1}))

    def wrapper(charge={}, customer={}):
        monkeypatch.setattr('stripe.Charge.create', MagicMock(return_value=charge))
        monkeypatch.setattr('stripe.Customer.create', MagicMock(return_value=customer))

    yield wrapper


def test_without_auth(bc: Breathecode, client: APIClient):
    url = reverse_lazy('payments:pay')
    response = client.post(url)

    json = response.json()
    expected = {
        'detail': 'Authentication credentials were not provided.',
        'status_code': 401,
    }

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    assert bc.database.list_of('payments.Bag') == []
    assert bc.database.list_of('authenticate.UserSetting') == []

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])


@pytest.mark.parametrize('in_4geeks', [True, False])
@pytest.mark.parametrize('bad_reputation', ['BAD', 'FRAUD'])
@pytest.mark.parametrize('good_reputation', ['GOOD', 'UNKNOWN'])
def test_fraud_case(bc: Breathecode, client: APIClient, in_4geeks, bad_reputation, good_reputation):
    if in_4geeks:
        financial_reputation = {
            'in_4geeks': bad_reputation,
            'in_stripe': good_reputation,
        }
    else:
        financial_reputation = {
            'in_4geeks': good_reputation,
            'in_stripe': bad_reputation,
        }

    model = bc.database.create(user=1, financial_reputation=financial_reputation)
    client.force_authenticate(user=model.user)

    url = reverse_lazy('payments:pay')
    response = client.post(url)

    json = response.json()
    expected = {
        'detail': 'fraud-or-bad-reputation',
        'status_code': 402,
        'silent': True,
        'silent_code': 'fraud-or-bad-reputation',
    }

    assert json == expected
    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED

    assert bc.database.list_of('payments.Bag') == []
    assert bc.database.list_of('payments.Invoice') == []
    assert bc.database.list_of('authenticate.UserSetting') == [
        format_user_setting({'lang': 'en'}),
    ]

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])


@pytest.mark.parametrize('reputation1', ['GOOD', 'UNKNOWN'])
@pytest.mark.parametrize('reputation2', ['GOOD', 'UNKNOWN'])
def test_no_token(bc: Breathecode, client: APIClient, reputation1, reputation2):
    financial_reputation = {
        'in_4geeks': reputation1,
        'in_stripe': reputation2,
    }

    model = bc.database.create(user=1, financial_reputation=financial_reputation)
    client.force_authenticate(user=model.user)

    url = reverse_lazy('payments:pay')
    response = client.post(url)

    json = response.json()
    expected = {'detail': 'missing-token', 'status_code': 404}

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND

    assert bc.database.list_of('payments.Bag') == []
    assert bc.database.list_of('payments.Invoice') == []
    assert bc.database.list_of('authenticate.UserSetting') == [
        format_user_setting({'lang': 'en'}),
    ]

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])


def test_without_bag__passing_token(bc: Breathecode, client: APIClient):
    model = bc.database.create(user=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy('payments:pay')
    data = {'token': 'xdxdxdxdxdxdxdxdxdxd'}
    response = client.post(url, data, format='json')

    json = response.json()
    expected = {'detail': 'not-found-or-without-checking', 'status_code': 404}

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND

    assert bc.database.list_of('payments.Bag') == []
    assert bc.database.list_of('payments.Invoice') == []
    assert bc.database.list_of('authenticate.UserSetting') == [
        format_user_setting({'lang': 'en'}),
    ]

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])


def test_no_bag(bc: Breathecode, client: APIClient):
    bag = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
        'expires_at': UTC_NOW,
        'status': 'CHECKING',
        'type': 'BAG',
    }
    model = bc.database.create(user=1, bag=bag, currency=1, academy=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy('payments:pay')
    data = {'token': 'xdxdxdxdxdxdxdxdxdxd'}
    response = client.post(url, data, format='json')

    json = response.json()
    expected = {'detail': 'bag-is-empty', 'status_code': 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    assert bc.database.list_of('payments.Bag') == [bc.format.to_dict(model.bag)]
    assert bc.database.list_of('payments.Invoice') == []
    assert bc.database.list_of('authenticate.UserSetting') == [
        format_user_setting({'lang': 'en'}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [])

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, 'bag_created', related_type='payments.Bag', related_id=1),
        ],
    )


def test_with_bag__no_free_trial(bc: Breathecode, client: APIClient):
    bag = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
        'expires_at': UTC_NOW,
        'status': 'CHECKING',
        'type': 'BAG',
        random.choice([
            'amount_per_month',
            'amount_per_quarter',
            'amount_per_half',
            'amount_per_year',
        ]): 1,
    }

    plan = {'is_renewable': False}

    model = bc.database.create(user=1, bag=bag, academy=1, currency=1, plan=plan, service_item=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy('payments:pay')
    data = {'token': 'xdxdxdxdxdxdxdxdxdxd'}
    response = client.post(url, data, format='json')

    json = response.json()
    expected = {'detail': 'missing-chosen-period', 'status_code': 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    assert bc.database.list_of('payments.Bag') == [bc.format.to_dict(model.bag)]
    assert bc.database.list_of('payments.Invoice') == []
    assert bc.database.list_of('authenticate.UserSetting') == [
        format_user_setting({'lang': 'en'}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, 'bag_created', related_type='payments.Bag', related_id=1),
        ],
    )


def test_bad_choosen_period(bc: Breathecode, client: APIClient):
    bag = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
        'expires_at': UTC_NOW,
        'status': 'CHECKING',
        'type': 'BAG',
    }

    plan = {'is_renewable': False}

    model = bc.database.create(user=1, bag=bag, academy=1, currency=1, plan=plan, service_item=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy('payments:pay')
    data = {'token': 'xdxdxdxdxdxdxdxdxdxd', 'chosen_period': bc.fake.slug()}
    response = client.post(url, data, format='json')

    json = response.json()
    expected = {'detail': 'invalid-chosen-period', 'status_code': 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    assert bc.database.list_of('payments.Bag') == [bc.format.to_dict(model.bag)]
    assert bc.database.list_of('payments.Invoice') == []
    assert bc.database.list_of('authenticate.UserSetting') == [
        format_user_setting({'lang': 'en'}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, 'bag_created', related_type='payments.Bag', related_id=1),
        ],
    )


def test_free_trial__no_plan_offer(bc: Breathecode, client: APIClient):
    bag = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
        'expires_at': UTC_NOW,
        'status': 'CHECKING',
        'type': 'BAG',
    }

    plan = {'is_renewable': False}

    model = bc.database.create(user=1, bag=bag, academy=1, currency=1, plan=plan, service_item=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy('payments:pay')
    data = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
    }
    response = client.post(url, data, format='json')

    json = response.json()
    expected = {
        'detail': 'the-plan-was-chosen-is-not-ready-too-be-sold',
        'status_code': 400,
    }

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    assert bc.database.list_of('payments.Bag') == [
        bc.format.to_dict(model.bag),
    ]
    assert bc.database.list_of('payments.Invoice') == []
    assert bc.database.list_of('authenticate.UserSetting') == [
        format_user_setting({'lang': 'en'}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == []

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, 'bag_created', related_type='payments.Bag', related_id=1),
        ],
    )


def test_free_trial__with_plan_offer(bc: Breathecode, client: APIClient):
    bag = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
        'expires_at': UTC_NOW,
        'status': 'CHECKING',
        'type': 'BAG',
    }

    plan = {'is_renewable': False}

    model = bc.database.create(user=1,
                               bag=bag,
                               academy=1,
                               currency=1,
                               plan=plan,
                               service_item=1,
                               plan_offer=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy('payments:pay')
    data = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
    }
    response = client.post(url, data, format='json')

    json = response.json()
    expected = get_serializer(bc, model.currency, model.user, data={})

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    assert bc.database.list_of('payments.Bag') == [{
        **bc.format.to_dict(model.bag),
        'token': None,
        'status': 'PAID',
        'expires_at': None,
    }]
    assert bc.database.list_of('payments.Invoice') == [format_invoice_item()]
    assert bc.database.list_of('authenticate.UserSetting') == [
        format_user_setting({'lang': 'en'}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == [call(1, 1)]

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [call(1, 1)])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, 'bag_created', related_type='payments.Bag', related_id=1),
            call(1, 'checkout_completed', related_type='payments.Invoice', related_id=1),
        ],
    )


@pytest.mark.parametrize(
    'exc_cls,silent_code',
    [
        (stripe.error.CardError, 'card-error'),
        (stripe.error.RateLimitError, 'rate-limit-error'),
        (stripe.error.InvalidRequestError, 'invalid-request'),
        (stripe.error.AuthenticationError, 'authentication-error'),
        (stripe.error.APIConnectionError, 'payment-service-are-down'),
        (stripe.error.StripeError, 'stripe-error'),
        (Exception, 'unexpected-exception'),
    ],
)
def test_pay_for_subscription_has_failed(bc: Breathecode, client: APIClient, exc_cls, silent_code,
                                         monkeypatch, fake):

    def get_exp():
        args = [fake.slug()]
        kwargs = {}
        if exc_cls in [stripe.error.CardError, stripe.error.InvalidRequestError]:
            kwargs['param'] = {}

        if exc_cls == stripe.error.CardError:
            kwargs['code'] = fake.slug()

        return exc_cls(*args, **kwargs)

    monkeypatch.setattr(
        'breathecode.payments.services.stripe.Stripe._execute_callback',
        MagicMock(side_effect=get_exp()),
    )

    bag = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
        'expires_at': UTC_NOW,
        'status': 'CHECKING',
        'type': 'BAG',
        **generate_amounts_by_time(),
    }
    chosen_period = random.choice(['MONTH', 'QUARTER', 'HALF', 'YEAR'])
    amount = get_amount_per_period(chosen_period, bag)

    plan = {'is_renewable': False}

    model = bc.database.create(user=1, bag=bag, academy=1, currency=1, plan=plan, service_item=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy('payments:pay')
    data = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
        'chosen_period': chosen_period,
    }
    response = client.post(url, data, format='json')

    json = response.json()
    expected = {
        'detail': silent_code,
        'silent': True,
        'silent_code': silent_code,
        'status_code': 402,
    }

    assert json == expected
    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED

    assert bc.database.list_of('payments.Bag') == [
        bc.format.to_dict(model.bag),
    ]
    assert bc.database.list_of('payments.Invoice') == []
    assert bc.database.list_of('authenticate.UserSetting') == [
        format_user_setting({'lang': 'en'}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == []

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [
        call(1, 'bag_created', related_type='payments.Bag', related_id=1),
    ])
    assert 0


@pytest.mark.parametrize(
    'exc_cls,silent_code',
    [
        (stripe.error.CardError, 'card-error'),
        (stripe.error.RateLimitError, 'rate-limit-error'),
        (stripe.error.InvalidRequestError, 'invalid-request'),
        (stripe.error.AuthenticationError, 'authentication-error'),
        (stripe.error.APIConnectionError, 'payment-service-are-down'),
        (stripe.error.StripeError, 'stripe-error'),
        (Exception, 'unexpected-exception'),
    ],
)
def test_pay_for_plan_financing_has_failed(bc: Breathecode, client: APIClient, exc_cls, silent_code,
                                           monkeypatch, fake):

    def get_exp():
        args = [fake.slug()]
        kwargs = {}
        if exc_cls in [stripe.error.CardError, stripe.error.InvalidRequestError]:
            kwargs['param'] = {}

        if exc_cls == stripe.error.CardError:
            kwargs['code'] = fake.slug()

        return exc_cls(*args, **kwargs)

    monkeypatch.setattr(
        'breathecode.payments.services.stripe.Stripe._execute_callback',
        MagicMock(side_effect=get_exp()),
    )

    how_many_installments = random.randint(1, 12)
    charge = random.random() * 99 + 1
    bag = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
        'expires_at': UTC_NOW,
        'status': 'CHECKING',
        'type': 'BAG',
        **generate_amounts_by_time(),
    }
    financing_option = {
        'monthly_price': charge,
        'how_many_months': how_many_installments,
    }
    plan = {'is_renewable': False}

    model = bc.database.create(
        user=1,
        bag=bag,
        academy=1,
        currency=1,
        plan=plan,
        service_item=1,
        financing_option=financing_option,
    )
    client.force_authenticate(user=model.user)

    url = reverse_lazy('payments:pay')
    data = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
        'how_many_installments': how_many_installments,
    }
    response = client.post(url, data, format='json')

    json = response.json()
    expected = {
        'detail': silent_code,
        'silent': True,
        'silent_code': silent_code,
        'status_code': 402,
    }

    assert json == expected
    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED

    assert bc.database.list_of('payments.Bag') == [
        bc.format.to_dict(model.bag),
    ]
    assert bc.database.list_of('payments.Invoice') == []
    assert bc.database.list_of('authenticate.UserSetting') == [
        format_user_setting({'lang': 'en'}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == []

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [
        call(1, 'bag_created', related_type='payments.Bag', related_id=1),
    ])


def test_free_plan__is_renewable(bc: Breathecode, client: APIClient):
    bag = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
        'expires_at': UTC_NOW,
        'status': 'CHECKING',
        'type': 'BAG',
    }

    plan = {'is_renewable': True, 'trial_duration': 0}

    model = bc.database.create(user=1,
                               bag=bag,
                               academy=1,
                               currency=1,
                               plan=plan,
                               service_item=1,
                               plan_offer=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy('payments:pay')
    data = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
    }
    response = client.post(url, data, format='json')

    json = response.json()
    expected = get_serializer(bc, model.currency, model.user, data={})

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    assert bc.database.list_of('payments.Bag') == [{
        **bc.format.to_dict(model.bag),
        'token': None,
        'status': 'PAID',
        'expires_at': None,
    }]
    assert bc.database.list_of('payments.Invoice') == [format_invoice_item()]
    assert bc.database.list_of('authenticate.UserSetting') == [
        format_user_setting({'lang': 'en'}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == [call(1, 1)]

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [call(1, 1)])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, 'bag_created', related_type='payments.Bag', related_id=1),
            call(1, 'checkout_completed', related_type='payments.Invoice', related_id=1),
        ],
    )


def test_free_plan__not_is_renewable(bc: Breathecode, client: APIClient):
    bag = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
        'expires_at': UTC_NOW,
        'status': 'CHECKING',
        'type': 'BAG',
    }

    plan = {'is_renewable': False, 'trial_duration': 0}

    model = bc.database.create(user=1,
                               bag=bag,
                               academy=1,
                               currency=1,
                               plan=plan,
                               service_item=1,
                               plan_offer=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy('payments:pay')
    data = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
    }
    response = client.post(url, data, format='json')

    json = response.json()
    expected = get_serializer(bc, model.currency, model.user, data={})

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    assert bc.database.list_of('payments.Bag') == [{
        **bc.format.to_dict(model.bag),
        'token': None,
        'status': 'PAID',
        'expires_at': None,
    }]
    assert bc.database.list_of('payments.Invoice') == [format_invoice_item()]
    assert bc.database.list_of('authenticate.UserSetting') == [
        format_user_setting({'lang': 'en'}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == [call(1, 1)]

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [call(1, 1)])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, 'bag_created', related_type='payments.Bag', related_id=1),
            call(1, 'checkout_completed', related_type='payments.Invoice', related_id=1),
        ],
    )


def test_with_chosen_period__amount_set(bc: Breathecode, client: APIClient):
    bag = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
        'expires_at': UTC_NOW,
        'status': 'CHECKING',
        'type': 'BAG',
        **generate_amounts_by_time(),
    }
    chosen_period = random.choice(['MONTH', 'QUARTER', 'HALF', 'YEAR'])
    amount = get_amount_per_period(chosen_period, bag)

    plan = {'is_renewable': False}

    model = bc.database.create(user=1, bag=bag, academy=1, currency=1, plan=plan, service_item=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy('payments:pay')
    data = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
        'chosen_period': chosen_period,
    }
    response = client.post(url, data, format='json')

    json = response.json()
    expected = get_serializer(bc, model.currency, model.user, data={'amount': math.ceil(amount)})

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    assert bc.database.list_of('payments.Bag') == [{
        **bc.format.to_dict(model.bag),
        'token': None,
        'status': 'PAID',
        'expires_at': None,
        'chosen_period': chosen_period,
    }]
    assert bc.database.list_of('payments.Invoice') == [
        format_invoice_item({
            'amount': math.ceil(amount),
            'stripe_id': '1',
        }),
    ]
    assert bc.database.list_of('authenticate.UserSetting') == [
        format_user_setting({'lang': 'en'}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == [call(1, 1)]
    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == []

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [call(1, 1)])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, 'bag_created', related_type='payments.Bag', related_id=1),
            call(1, 'checkout_completed', related_type='payments.Invoice', related_id=1),
        ],
    )


def test_installments_not_found(bc: Breathecode, client: APIClient):
    bag = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
        'expires_at': UTC_NOW,
        'status': 'CHECKING',
        'type': 'BAG',
        **generate_amounts_by_time(),
    }
    chosen_period = random.choice(['MONTH', 'QUARTER', 'HALF', 'YEAR'])
    amount = get_amount_per_period(chosen_period, bag)

    plan = {'is_renewable': False}

    model = bc.database.create(user=1, bag=bag, academy=1, currency=1, plan=plan, service_item=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy('payments:pay')
    data = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
        'how_many_installments': random.randint(1, 12),
    }
    response = client.post(url, data, format='json')

    json = response.json()
    expected = {'detail': 'invalid-bag-configured-by-installments', 'status_code': 500}

    assert json == expected
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    assert bc.database.list_of('payments.Bag') == [{
        **bc.format.to_dict(model.bag),
    }]
    assert bc.database.list_of('payments.Invoice') == []
    assert bc.database.list_of('authenticate.UserSetting') == [
        format_user_setting({'lang': 'en'}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == []

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, 'bag_created', related_type='payments.Bag', related_id=1),
        ],
    )


def test_with_installments(bc: Breathecode, client: APIClient):
    how_many_installments = random.randint(1, 12)
    charge = random.random() * 99 + 1
    bag = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
        'expires_at': UTC_NOW,
        'status': 'CHECKING',
        'type': 'BAG',
        **generate_amounts_by_time(),
    }
    financing_option = {
        'monthly_price': charge,
        'how_many_months': how_many_installments,
    }
    plan = {'is_renewable': False}

    model = bc.database.create(
        user=1,
        bag=bag,
        academy=1,
        currency=1,
        plan=plan,
        service_item=1,
        financing_option=financing_option,
    )
    client.force_authenticate(user=model.user)

    url = reverse_lazy('payments:pay')
    data = {
        'token': 'xdxdxdxdxdxdxdxdxdxd',
        'how_many_installments': how_many_installments,
    }
    response = client.post(url, data, format='json')

    json = response.json()
    expected = get_serializer(bc, model.currency, model.user, data={'amount': math.ceil(charge)})

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    assert bc.database.list_of('payments.Bag') == [{
        **bc.format.to_dict(model.bag),
        'token': None,
        'status': 'PAID',
        #  'chosen_period': 'NO_SET',
        'expires_at': None,
        'how_many_installments': how_many_installments,
    }]
    assert bc.database.list_of('payments.Invoice') == [
        format_invoice_item({
            'amount': math.ceil(charge),
            'stripe_id': '1',
        }),
    ]
    assert bc.database.list_of('authenticate.UserSetting') == [
        format_user_setting({'lang': 'en'}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_plan_financing.delay.call_args_list == [call(1, 1)]
    assert tasks.build_free_subscription.delay.call_args_list == []

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [call(1, 1)])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, 'bag_created', related_type='payments.Bag', related_id=1),
            call(1, 'checkout_completed', related_type='payments.Invoice', related_id=1),
        ],
    )
