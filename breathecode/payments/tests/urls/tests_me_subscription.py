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


def academy_serializer(academy):
    return {
        'id': academy.id,
        'name': academy.name,
        'slug': academy.slug,
    }


def currency_serializer(currency):
    return {
        'code': currency.code,
        'name': currency.name,
    }


def user_serializer(user):
    return {
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
    }


def invoice_serializer(self, invoice, currency, user):
    return {
        'amount': invoice.amount,
        'currency': currency_serializer(currency),
        'paid_at': self.bc.datetime.to_iso_string(invoice.paid_at),
        'status': invoice.status,
        'user': user_serializer(user),
    }


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


def plan_serializer(self, plan, service, groups=[], permissions=[], service_items=[]):
    return {
        'financing_options': [],
        'service_items': [
            service_item_serializer(self, service_item, service, groups, permissions)
            for service_item in service_items
        ],
        'slug':
        plan.slug,
        'status':
        plan.status,
        'trial_duration':
        plan.trial_duration,
        'trial_duration_unit':
        plan.trial_duration_unit,
    }


def get_plan_financing_serializer(self,
                                  plan_financing,
                                  academy,
                                  currency,
                                  user,
                                  service,
                                  invoices=[],
                                  financing_options=[],
                                  plans=[],
                                  groups=[],
                                  permissions=[],
                                  service_items=[]):
    return {
        'id': plan_financing.id,
        'academy': academy_serializer(academy),
        'invoices': [invoice_serializer(self, invoice, currency, user) for invoice in invoices],
        'paid_at': self.bc.datetime.to_iso_string(plan_financing.paid_at),
        'pay_until': self.bc.datetime.to_iso_string(plan_financing.pay_until),
        'plans': [plan_serializer(self, plan, service, groups, permissions, service_items) for plan in plans],
        'status': plan_financing.status,
        'status_message': plan_financing.status_message,
        'user': user_serializer(user),
    }


def get_subscription_serializer(self,
                                subscription,
                                academy,
                                currency,
                                user,
                                service,
                                invoices=[],
                                financing_options=[],
                                plans=[],
                                groups=[],
                                permissions=[],
                                service_items=[]):
    valid_until = self.bc.datetime.to_iso_string(
        subscription.valid_until) if subscription.valid_until else None
    return {
        'id':
        subscription.id,
        'academy':
        academy_serializer(academy),
        'invoices': [invoice_serializer(self, invoice, currency, user) for invoice in invoices],
        'paid_at':
        self.bc.datetime.to_iso_string(subscription.paid_at),
        'valid_until':
        valid_until,
        'plans': [plan_serializer(self, plan, service, groups, permissions, service_items) for plan in plans],
        'status':
        subscription.status,
        'status_message':
        subscription.status_message,
        'is_refundable':
        subscription.is_refundable,
        'next_payment_at':
        self.bc.datetime.to_iso_string(subscription.next_payment_at),
        'pay_every':
        subscription.pay_every,
        'pay_every_unit':
        subscription.pay_every_unit,
        'user':
        user_serializer(user),
        'service_items': [
            service_item_serializer(self, service_item, service, groups, permissions)
            for service_item in service_items
        ],
    }


class SignalTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 GET without auth
    """

    def test__without_auth(self):
        url = reverse_lazy('payments:me_subscription')
        response = self.client.get(url)

        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    """
    🔽🔽🔽 Get without items
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__without_items(self):
        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_subscription')
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {'plan_financings': [], 'subscriptions': []}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__with_many_items(self):
        subscriptions = [{'valid_until': x} for x in [None, UTC_NOW + timedelta(days=1)]]
        plan_financing = {'pay_until': UTC_NOW + timedelta(days=1)}
        plan_service_items = [{'service_item_id': x, 'plan_id': 1} for x in range(1, 3)]
        plan_service_items += [{'service_item_id': x, 'plan_id': 2} for x in range(1, 3)]
        subscription_service_items = [{'service_item_id': x, 'subscription_id': 1} for x in range(1, 3)]
        subscription_service_items += [{'service_item_id': x, 'subscription_id': 2} for x in range(1, 3)]
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=2,
            service_item=2,
        )
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_subscription')
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'plan_financings': [
                get_plan_financing_serializer(self,
                                              model.plan_financing[0],
                                              model.academy,
                                              model.currency,
                                              model.user,
                                              model.service,
                                              invoices=[model.invoice[0], model.invoice[1]],
                                              financing_options=[],
                                              plans=[model.plan[0], model.plan[1]],
                                              service_items=[model.service_item[0], model.service_item[1]]),
                get_plan_financing_serializer(self,
                                              model.plan_financing[1],
                                              model.academy,
                                              model.currency,
                                              model.user,
                                              model.service,
                                              invoices=[model.invoice[0], model.invoice[1]],
                                              financing_options=[],
                                              plans=[model.plan[0], model.plan[1]],
                                              service_items=[model.service_item[0], model.service_item[1]]),
            ],
            'subscriptions': [
                get_subscription_serializer(self,
                                            model.subscription[0],
                                            model.academy,
                                            model.currency,
                                            model.user,
                                            model.service,
                                            invoices=[model.invoice[0], model.invoice[1]],
                                            financing_options=[],
                                            plans=[model.plan[0], model.plan[1]],
                                            service_items=[model.service_item[0], model.service_item[1]]),
                get_subscription_serializer(self,
                                            model.subscription[1],
                                            model.academy,
                                            model.currency,
                                            model.user,
                                            model.service,
                                            invoices=[model.invoice[0], model.invoice[1]],
                                            financing_options=[],
                                            plans=[model.plan[0], model.plan[1]],
                                            service_items=[model.service_item[0], model.service_item[1]]),
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by subscription
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_subscription(self):
        subscriptions = [{'valid_until': x} for x in [None, UTC_NOW + timedelta(days=1)]]
        plan_financing = {'pay_until': UTC_NOW + timedelta(days=1)}
        plan_service_items = [{'service_item_id': x, 'plan_id': 1} for x in range(1, 3)]
        plan_service_items += [{'service_item_id': x, 'plan_id': 2} for x in range(1, 3)]
        subscription_service_items = [{'service_item_id': x, 'subscription_id': 1} for x in range(1, 3)]
        subscription_service_items += [{'service_item_id': x, 'subscription_id': 2} for x in range(1, 3)]
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=2,
            service_item=2,
        )
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_subscription') + f'?subscription={model.subscription[0].id}'
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'plan_financings': [],
            'subscriptions': [
                get_subscription_serializer(self,
                                            model.subscription[0],
                                            model.academy,
                                            model.currency,
                                            model.user,
                                            model.service,
                                            invoices=[model.invoice[0], model.invoice[1]],
                                            financing_options=[],
                                            plans=[model.plan[0], model.plan[1]],
                                            service_items=[model.service_item[0], model.service_item[1]]),
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by plan financing
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_plan_financing(self):
        subscriptions = [{'valid_until': x} for x in [None, UTC_NOW + timedelta(days=1)]]
        plan_financing = {'pay_until': UTC_NOW + timedelta(days=1)}
        plan_service_items = [{'service_item_id': x, 'plan_id': 1} for x in range(1, 3)]
        plan_service_items += [{'service_item_id': x, 'plan_id': 2} for x in range(1, 3)]
        subscription_service_items = [{'service_item_id': x, 'subscription_id': 1} for x in range(1, 3)]
        subscription_service_items += [{'service_item_id': x, 'subscription_id': 2} for x in range(1, 3)]
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=2,
            service_item=2,
        )
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_subscription') + f'?plan-financing={model.plan_financing[0].id}'
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'plan_financings': [
                get_plan_financing_serializer(self,
                                              model.plan_financing[0],
                                              model.academy,
                                              model.currency,
                                              model.user,
                                              model.service,
                                              invoices=[model.invoice[0], model.invoice[1]],
                                              financing_options=[],
                                              plans=[model.plan[0], model.plan[1]],
                                              service_items=[model.service_item[0], model.service_item[1]]),
            ],
            'subscriptions': [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by subscription and plan financing
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_subscription_and_plan_financing(self):
        subscriptions = [{'valid_until': x} for x in [None, UTC_NOW + timedelta(days=1)]]
        plan_financing = {'pay_until': UTC_NOW + timedelta(days=1)}
        plan_service_items = [{'service_item_id': x, 'plan_id': 1} for x in range(1, 3)]
        plan_service_items += [{'service_item_id': x, 'plan_id': 2} for x in range(1, 3)]
        subscription_service_items = [{'service_item_id': x, 'subscription_id': 1} for x in range(1, 3)]
        subscription_service_items += [{'service_item_id': x, 'subscription_id': 2} for x in range(1, 3)]
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=2,
            service_item=2,
        )
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_subscription') + (f'?subscription={model.subscription[0].id}&'
                                                          f'plan-financing={model.plan_financing[0].id}')
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'plan_financings': [
                get_plan_financing_serializer(self,
                                              model.plan_financing[0],
                                              model.academy,
                                              model.currency,
                                              model.user,
                                              model.service,
                                              invoices=[model.invoice[0], model.invoice[1]],
                                              financing_options=[],
                                              plans=[model.plan[0], model.plan[1]],
                                              service_items=[model.service_item[0], model.service_item[1]]),
            ],
            'subscriptions': [
                get_subscription_serializer(self,
                                            model.subscription[0],
                                            model.academy,
                                            model.currency,
                                            model.user,
                                            model.service,
                                            invoices=[model.invoice[0], model.invoice[1]],
                                            financing_options=[],
                                            plans=[model.plan[0], model.plan[1]],
                                            service_items=[model.service_item[0], model.service_item[1]]),
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, with wrong statuses
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__with_many_items__with_wrong_statuses(self):
        wrong_statuses = ['PAYMENT_ISSUE', 'DEPRECATED', 'CANCELLED']
        subscriptions = [{
            'valid_until': x,
            'status': random.choice(wrong_statuses),
        } for x in [None, UTC_NOW + timedelta(days=1)]]
        plan_financing = {
            'pay_until': UTC_NOW + timedelta(days=1),
            'status': random.choice(wrong_statuses),
        }
        plan_service_items = [{'service_item_id': x, 'plan_id': 1} for x in range(1, 3)]
        plan_service_items += [{'service_item_id': x, 'plan_id': 2} for x in range(1, 3)]
        subscription_service_items = [{'service_item_id': x, 'subscription_id': 1} for x in range(1, 3)]
        subscription_service_items += [{'service_item_id': x, 'subscription_id': 2} for x in range(1, 3)]
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=2,
            service_item=2,
        )
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_subscription')
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'plan_financings': [],
            'subscriptions': [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by status
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_statuses(self):
        statuses = ['FREE_TRIAL', 'ACTIVE', 'PAYMENT_ISSUE', 'DEPRECATED', 'CANCELLED', 'ERROR']
        chosen_statuses = [random.choice(statuses) for _ in range(2)]
        subscriptions = [{
            'valid_until': x,
            'status': random.choice(chosen_statuses),
        } for x in [None, UTC_NOW + timedelta(days=1)]]
        plan_financing = {
            'pay_until': UTC_NOW + timedelta(days=1),
            'status': random.choice(chosen_statuses),
        }
        plan_service_items = [{'service_item_id': x, 'plan_id': 1} for x in range(1, 3)]
        plan_service_items += [{'service_item_id': x, 'plan_id': 2} for x in range(1, 3)]
        subscription_service_items = [{'service_item_id': x, 'subscription_id': 1} for x in range(1, 3)]
        subscription_service_items += [{'service_item_id': x, 'subscription_id': 2} for x in range(1, 3)]
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=2,
            service_item=2,
        )
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_subscription') + (f'?status={chosen_statuses[0]},'
                                                          f'{chosen_statuses[1]}')
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'plan_financings': [
                get_plan_financing_serializer(self,
                                              model.plan_financing[0],
                                              model.academy,
                                              model.currency,
                                              model.user,
                                              model.service,
                                              invoices=[model.invoice[0], model.invoice[1]],
                                              financing_options=[],
                                              plans=[model.plan[0], model.plan[1]],
                                              service_items=[model.service_item[0], model.service_item[1]]),
                get_plan_financing_serializer(self,
                                              model.plan_financing[1],
                                              model.academy,
                                              model.currency,
                                              model.user,
                                              model.service,
                                              invoices=[model.invoice[0], model.invoice[1]],
                                              financing_options=[],
                                              plans=[model.plan[0], model.plan[1]],
                                              service_items=[model.service_item[0], model.service_item[1]]),
            ],
            'subscriptions': [
                get_subscription_serializer(self,
                                            model.subscription[0],
                                            model.academy,
                                            model.currency,
                                            model.user,
                                            model.service,
                                            invoices=[model.invoice[0], model.invoice[1]],
                                            financing_options=[],
                                            plans=[model.plan[0], model.plan[1]],
                                            service_items=[model.service_item[0], model.service_item[1]]),
                get_subscription_serializer(self,
                                            model.subscription[1],
                                            model.academy,
                                            model.currency,
                                            model.user,
                                            model.service,
                                            invoices=[model.invoice[0], model.invoice[1]],
                                            financing_options=[],
                                            plans=[model.plan[0], model.plan[1]],
                                            service_items=[model.service_item[0], model.service_item[1]]),
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by wrong invoice
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_wrong_invoice(self):
        statuses = ['FREE_TRIAL', 'ACTIVE', 'PAYMENT_ISSUE', 'DEPRECATED', 'CANCELLED', 'ERROR']
        chosen_statuses = [random.choice(statuses) for _ in range(2)]
        subscriptions = [{
            'valid_until': x,
            'status': random.choice(chosen_statuses),
        } for x in [None, UTC_NOW + timedelta(days=1)]]
        plan_financing = {
            'pay_until': UTC_NOW + timedelta(days=1),
            'status': random.choice(chosen_statuses),
        }
        plan_service_items = [{'service_item_id': x, 'plan_id': 1} for x in range(1, 3)]
        plan_service_items += [{'service_item_id': x, 'plan_id': 2} for x in range(1, 3)]
        subscription_service_items = [{'service_item_id': x, 'subscription_id': 1} for x in range(1, 3)]
        subscription_service_items += [{'service_item_id': x, 'subscription_id': 2} for x in range(1, 3)]
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=2,
            service_item=2,
        )
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_subscription') + (f'?invoice=3,4')
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'plan_financings': [],
            'subscriptions': [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by good invoice
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_good_invoice(self):
        subscriptions = [{
            'valid_until': x,
        } for x in [None, UTC_NOW + timedelta(days=1)]]
        plan_financing = {
            'pay_until': UTC_NOW + timedelta(days=1),
        }
        plan_service_items = [{'service_item_id': x, 'plan_id': 1} for x in range(1, 3)]
        plan_service_items += [{'service_item_id': x, 'plan_id': 2} for x in range(1, 3)]
        subscription_service_items = [{'service_item_id': x, 'subscription_id': 1} for x in range(1, 3)]
        subscription_service_items += [{'service_item_id': x, 'subscription_id': 2} for x in range(1, 3)]
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=2,
            service_item=2,
        )
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_subscription') + '?invoice=1,2'
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'plan_financings': [
                get_plan_financing_serializer(self,
                                              model.plan_financing[0],
                                              model.academy,
                                              model.currency,
                                              model.user,
                                              model.service,
                                              invoices=[model.invoice[0], model.invoice[1]],
                                              financing_options=[],
                                              plans=[model.plan[0], model.plan[1]],
                                              service_items=[model.service_item[0], model.service_item[1]]),
                get_plan_financing_serializer(self,
                                              model.plan_financing[1],
                                              model.academy,
                                              model.currency,
                                              model.user,
                                              model.service,
                                              invoices=[model.invoice[0], model.invoice[1]],
                                              financing_options=[],
                                              plans=[model.plan[0], model.plan[1]],
                                              service_items=[model.service_item[0], model.service_item[1]]),
            ],
            'subscriptions': [
                get_subscription_serializer(self,
                                            model.subscription[0],
                                            model.academy,
                                            model.currency,
                                            model.user,
                                            model.service,
                                            invoices=[model.invoice[0], model.invoice[1]],
                                            financing_options=[],
                                            plans=[model.plan[0], model.plan[1]],
                                            service_items=[model.service_item[0], model.service_item[1]]),
                get_subscription_serializer(self,
                                            model.subscription[1],
                                            model.academy,
                                            model.currency,
                                            model.user,
                                            model.service,
                                            invoices=[model.invoice[0], model.invoice[1]],
                                            financing_options=[],
                                            plans=[model.plan[0], model.plan[1]],
                                            service_items=[model.service_item[0], model.service_item[1]]),
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by wrong service
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_wrong_service(self):
        statuses = ['FREE_TRIAL', 'ACTIVE', 'PAYMENT_ISSUE', 'DEPRECATED', 'CANCELLED', 'ERROR']
        chosen_statuses = [random.choice(statuses) for _ in range(2)]
        subscriptions = [{
            'valid_until': x,
            'status': random.choice(chosen_statuses),
        } for x in [None, UTC_NOW + timedelta(days=1)]]
        plan_financing = {
            'pay_until': UTC_NOW + timedelta(days=1),
            'status': random.choice(chosen_statuses),
        }
        plan_service_items = [{'service_item_id': x, 'plan_id': 1} for x in range(1, 3)]
        plan_service_items += [{'service_item_id': x, 'plan_id': 2} for x in range(1, 3)]
        subscription_service_items = [{'service_item_id': x, 'subscription_id': 1} for x in range(1, 3)]
        subscription_service_items += [{'service_item_id': x, 'subscription_id': 2} for x in range(1, 3)]
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=2,
            service_item=2,
        )
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_subscription') + (f'?invoice={random.choice([3, "gangsters-i"])},'
                                                          f'{random.choice([4, "gangsters-ii"])}')
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'plan_financings': [],
            'subscriptions': [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by good service
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_good_service(self):
        subscriptions = [{
            'valid_until': x,
        } for x in [None, UTC_NOW + timedelta(days=1)]]
        plan_financing = {
            'pay_until': UTC_NOW + timedelta(days=1),
        }
        plan_service_items = [{'service_item_id': x, 'plan_id': 1} for x in range(1, 3)]
        plan_service_items += [{'service_item_id': x, 'plan_id': 2} for x in range(1, 3)]
        subscription_service_items = [{'service_item_id': x, 'subscription_id': 1} for x in range(1, 3)]
        subscription_service_items += [{'service_item_id': x, 'subscription_id': 2} for x in range(1, 3)]
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=2,
            service_item=2,
        )
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_subscription') + (
            f'?service={random.choice([model.service.id, model.service.slug])},'
            f'{random.choice([model.service.id, model.service.slug])}')
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'plan_financings': [
                get_plan_financing_serializer(self,
                                              model.plan_financing[0],
                                              model.academy,
                                              model.currency,
                                              model.user,
                                              model.service,
                                              invoices=[model.invoice[0], model.invoice[1]],
                                              financing_options=[],
                                              plans=[model.plan[0], model.plan[1]],
                                              service_items=[model.service_item[0], model.service_item[1]]),
                get_plan_financing_serializer(self,
                                              model.plan_financing[1],
                                              model.academy,
                                              model.currency,
                                              model.user,
                                              model.service,
                                              invoices=[model.invoice[0], model.invoice[1]],
                                              financing_options=[],
                                              plans=[model.plan[0], model.plan[1]],
                                              service_items=[model.service_item[0], model.service_item[1]]),
            ],
            'subscriptions': [
                get_subscription_serializer(self,
                                            model.subscription[0],
                                            model.academy,
                                            model.currency,
                                            model.user,
                                            model.service,
                                            invoices=[model.invoice[0], model.invoice[1]],
                                            financing_options=[],
                                            plans=[model.plan[0], model.plan[1]],
                                            service_items=[model.service_item[0], model.service_item[1]]),
                get_subscription_serializer(self,
                                            model.subscription[1],
                                            model.academy,
                                            model.currency,
                                            model.user,
                                            model.service,
                                            invoices=[model.invoice[0], model.invoice[1]],
                                            financing_options=[],
                                            plans=[model.plan[0], model.plan[1]],
                                            service_items=[model.service_item[0], model.service_item[1]]),
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by wrong plan
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_wrong_plan(self):
        statuses = ['FREE_TRIAL', 'ACTIVE', 'PAYMENT_ISSUE', 'DEPRECATED', 'CANCELLED', 'ERROR']
        chosen_statuses = [random.choice(statuses) for _ in range(2)]
        subscriptions = [{
            'valid_until': x,
            'status': random.choice(chosen_statuses),
        } for x in [None, UTC_NOW + timedelta(days=1)]]
        plan_financing = {
            'pay_until': UTC_NOW + timedelta(days=1),
            'status': random.choice(chosen_statuses),
        }
        plan_service_items = [{'service_item_id': x, 'plan_id': 1} for x in range(1, 3)]
        plan_service_items += [{'service_item_id': x, 'plan_id': 2} for x in range(1, 3)]
        subscription_service_items = [{'service_item_id': x, 'subscription_id': 1} for x in range(1, 3)]
        subscription_service_items += [{'service_item_id': x, 'subscription_id': 2} for x in range(1, 3)]
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=2,
            service_item=2,
        )
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_subscription') + (f'?plan={random.choice([3, "gangsters-i"])},'
                                                          f'{random.choice([4, "gangsters-ii"])}')
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'plan_financings': [],
            'subscriptions': [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    """
    🔽🔽🔽 Get with many PlanFinancing and Subscription, filter by good plan
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test__with_many_items__filter_by_good_plan(self):
        subscriptions = [{
            'valid_until': x,
        } for x in [None, UTC_NOW + timedelta(days=1)]]
        plan_financing = {
            'pay_until': UTC_NOW + timedelta(days=1),
        }
        plan_service_items = [{'service_item_id': x, 'plan_id': 1} for x in range(1, 3)]
        plan_service_items += [{'service_item_id': x, 'plan_id': 2} for x in range(1, 3)]
        subscription_service_items = [{'service_item_id': x, 'subscription_id': 1} for x in range(1, 3)]
        subscription_service_items += [{'service_item_id': x, 'subscription_id': 2} for x in range(1, 3)]
        model = self.bc.database.create(
            subscription=subscriptions,
            plan_financing=(2, plan_financing),
            plan_service_item=plan_service_items,
            subscription_service_item=subscription_service_items,
            invoice=2,
            plan=2,
            service_item=2,
        )
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('payments:me_subscription') + (
            f'?plan={random.choice([model.plan[0].id, model.plan[0].slug])},'
            f'{random.choice([model.plan[1].id, model.plan[1].slug])}')
        response = self.client.get(url)
        self.bc.request.authenticate(model.user)

        json = response.json()
        expected = {
            'plan_financings': [
                get_plan_financing_serializer(self,
                                              model.plan_financing[0],
                                              model.academy,
                                              model.currency,
                                              model.user,
                                              model.service,
                                              invoices=[model.invoice[0], model.invoice[1]],
                                              financing_options=[],
                                              plans=[model.plan[0], model.plan[1]],
                                              service_items=[model.service_item[0], model.service_item[1]]),
                get_plan_financing_serializer(self,
                                              model.plan_financing[1],
                                              model.academy,
                                              model.currency,
                                              model.user,
                                              model.service,
                                              invoices=[model.invoice[0], model.invoice[1]],
                                              financing_options=[],
                                              plans=[model.plan[0], model.plan[1]],
                                              service_items=[model.service_item[0], model.service_item[1]]),
            ],
            'subscriptions': [
                get_subscription_serializer(self,
                                            model.subscription[0],
                                            model.academy,
                                            model.currency,
                                            model.user,
                                            model.service,
                                            invoices=[model.invoice[0], model.invoice[1]],
                                            financing_options=[],
                                            plans=[model.plan[0], model.plan[1]],
                                            service_items=[model.service_item[0], model.service_item[1]]),
                get_subscription_serializer(self,
                                            model.subscription[1],
                                            model.academy,
                                            model.currency,
                                            model.user,
                                            model.service,
                                            invoices=[model.invoice[0], model.invoice[1]],
                                            financing_options=[],
                                            plans=[model.plan[0], model.plan[1]],
                                            service_items=[model.service_item[0], model.service_item[1]]),
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])
