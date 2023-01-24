"""
Test /answer
"""
import logging
import random
from unittest.mock import MagicMock, call, patch

from django.utils import timezone
from breathecode.payments import tasks

from ...tasks import charge_plan_financing
from breathecode.notify import actions as notify_actions
from ..mixins import PaymentsTestCase
from dateutil.relativedelta import relativedelta
from mixer.backend.django import mixer

UTC_NOW = timezone.now()


def plan_financing_item(data={}):
    return {
        'id': 1,
        'is_refundable': True,
        'paid_at': UTC_NOW,
        'pay_every': 1,
        'pay_every_unit': 'MONTH',
        'status': 'ACTIVE',
        'user_id': 1,
        'valid_until': UTC_NOW,
        **data,
    }


def bag_item(data={}):
    return {
        'id': 1,
        'amount_per_month': 0.0,
        'amount_per_quarter': 0.0,
        'amount_per_half': 0.0,
        'amount_per_year': 0.0,
        'currency_id': 0,
        'status': 'CHECKING',
        'type': 'CHARGE',
        'chosen_period': 'NO_SET',
        'how_many_installments': 0,
        'academy_id': 0,
        'user_id': 0,
        'is_recurrent': False,
        'was_delivered': False,
        'token': None,
        'expires_at': None,
        **data,
    }


def invoice_item(data={}):
    return {
        'academy_id': 0,
        'amount': 0.0,
        'bag_id': 2,
        'currency_id': 2,
        'id': 0,
        'paid_at': None,
        'status': 'PENDING',
        'stripe_id': None,
        'user_id': 0,
        **data,
    }


def fake_stripe_pay(**kwargs):

    def wrapper(user, bag, amount: int, currency='usd', description=''):
        return mixer.blend('payments.Invoice', user=user, bag=bag, **kwargs)

    return wrapper


def calculate_relative_delta(unit: float, unit_type: str):
    delta_args = {}
    if unit_type == 'DAY':
        delta_args['days'] = unit

    elif unit_type == 'WEEK':
        delta_args['weeks'] = unit

    elif unit_type == 'MONTH':
        delta_args['months'] = unit

    elif unit_type == 'YEAR':
        delta_args['years'] = unit

    return relativedelta(**delta_args)


#FIXME: create_v2 fail in this test file
class PaymentsTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 plan_financing not found
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_plan_financing_not_found(self):
        charge_plan_financing.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [])

        self.assertEqual(logging.Logger.info.call_args_list, [
            call('Starting charge_plan_financing for id 1'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [call('PlanFinancing with id 1 not found')])

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [])
        self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [])

    """
    🔽🔽🔽 plan_financing with zero Invoice
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_plan_financing_without_invoices(self):
        plan_financing = {'valid_until': UTC_NOW + relativedelta(minutes=1)}
        model = self.bc.database.create_v2(plan_financing=plan_financing, plan=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        charge_plan_financing.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [])

        self.assertEqual(logging.Logger.info.call_args_list, [
            call('Starting charge_plan_financing for id 1'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [
            call('Error getting bag from plan financing 1: plan-financing-has-no-invoices'),
        ])

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [])

        self.assertEqual(
            self.bc.database.list_of('payments.PlanFinancing'),
            [
                {
                    **self.bc.format.to_dict(model.plan_financing),
                    # 'status': 'PAYMENT_ISSUE',,
                    'status': 'ERROR',
                    'status_message': 'plan-financing-has-no-invoices',
                },
            ])
        self.assertEqual(notify_actions.send_email_message.call_args_list, [])

    """
    🔽🔽🔽 plan_financing process to charge
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('breathecode.payments.tasks.renew_plan_financing_consumables.delay', MagicMock())
    @patch('mixer.main.LOGGER.info', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_plan_financing_process_to_charge(self):
        plan_financing = {
            'valid_until': UTC_NOW + relativedelta(minutes=1),
        }
        model = self.bc.database.create(academy=1, plan_financing=plan_financing, invoice=1, plan=1)

        with patch('breathecode.payments.services.stripe.Stripe.pay',
                   MagicMock(side_effect=fake_stripe_pay(paid_at=UTC_NOW, academy=model.academy))):
            # remove prints from mixer
            logging.Logger.info.call_args_list = []
            logging.Logger.error.call_args_list = []

            charge_plan_financing.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [])

        self.assertEqual(logging.Logger.info.call_args_list, [
            call('Starting charge_plan_financing for id 1'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [
            self.bc.format.to_dict(model.bag),
            bag_item({
                'academy_id': 1,
                'currency_id': 1,
                'id': 2,
                'is_recurrent': True,
                'status': 'RENEWAL',
                'user_id': 1,
            }),
        ])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [
            self.bc.format.to_dict(model.invoice),
            invoice_item({
                'academy_id': 1,
                'id': 2,
                'user_id': 1,
                'paid_at': UTC_NOW,
            }),
        ])

        self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [
            {
                **self.bc.format.to_dict(model.plan_financing),
                'status': 'ACTIVE',
                'next_payment_at': UTC_NOW + relativedelta(months=1),
            },
        ])
        self.assertEqual(notify_actions.send_email_message.call_args_list, [
            call(
                'message', model.user.email, {
                    'SUBJECT': 'Your installment at 4Geeks was successfully charged',
                    'MESSAGE': 'The amount was $0.0',
                    'BUTTON': 'See the invoice',
                    'LINK': '/plan-financing/1'
                })
        ])

    """
    🔽🔽🔽 plan_financing error when try to charge
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('breathecode.payments.tasks.renew_plan_financing_consumables.delay', MagicMock())
    @patch('mixer.main.LOGGER.info', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_plan_financing_error_when_try_to_charge(self):
        plan_financing = {
            'valid_until': UTC_NOW + relativedelta(minutes=1),
        }
        model = self.bc.database.create(plan_financing=plan_financing, invoice=1)

        with patch('breathecode.payments.services.stripe.Stripe.pay',
                   MagicMock(side_effect=Exception('fake error'))):
            # remove prints from mixer
            logging.Logger.info.call_args_list = []
            logging.Logger.error.call_args_list = []

            charge_plan_financing.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [])

        self.assertEqual(logging.Logger.info.call_args_list, [
            call('Starting charge_plan_financing for id 1'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [
            self.bc.format.to_dict(model.bag),
        ])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [
            self.bc.format.to_dict(model.invoice),
        ])

        self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [
            {
                **self.bc.format.to_dict(model.plan_financing),
                'status': 'PAYMENT_ISSUE',
            },
        ])
        self.assertEqual(notify_actions.send_email_message.call_args_list, [
            call(
                'message', model.user.email, {
                    'SUBJECT': 'Your 4Geeks subscription could not be renewed',
                    'MESSAGE': 'Please update your payment methods',
                    'BUTTON': 'Please update your payment methods',
                    'LINK': '/plan-financing/1'
                })
        ])

    """
    🔽🔽🔽 plan_financing is over
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('breathecode.payments.tasks.renew_plan_financing_consumables.delay', MagicMock())
    @patch('mixer.main.LOGGER.info', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_plan_financing_is_over(self):
        plan_financing = {
            'valid_until': UTC_NOW - relativedelta(seconds=1),
        }
        model = self.bc.database.create(plan_financing=plan_financing, invoice=1)

        with patch('breathecode.payments.services.stripe.Stripe.pay',
                   MagicMock(side_effect=Exception('fake error'))):
            # remove prints from mixer
            logging.Logger.info.call_args_list = []
            logging.Logger.error.call_args_list = []

            charge_plan_financing.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [])

        self.assertEqual(logging.Logger.info.call_args_list, [
            call('Starting charge_plan_financing for id 1'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [call('PlanFinancing with id 1 is over')])

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [
            self.bc.format.to_dict(model.bag),
        ])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [
            self.bc.format.to_dict(model.invoice),
        ])

        self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [
            {
                **self.bc.format.to_dict(model.plan_financing),
            },
        ])
        self.assertEqual(notify_actions.send_email_message.call_args_list, [])
