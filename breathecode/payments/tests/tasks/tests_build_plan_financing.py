"""
Test /answer
"""
import logging
import random
from unittest.mock import MagicMock, call, patch

from django.utils import timezone
from breathecode.payments import tasks
from breathecode.payments.actions import calculate_relative_delta

from ...tasks import build_plan_financing

from ..mixins import PaymentsTestCase
from dateutil.relativedelta import relativedelta

UTC_NOW = timezone.now()


def plan_financing_item(data={}):
    return {
        'id': 1,
        'academy_id': 1,
        'monthly_price': 0,
        'plan_expires_at': UTC_NOW,
        'status': 'ACTIVE',
        'status_message': None,
        'user_id': 1,
        'valid_until': UTC_NOW,
        'next_payment_at': UTC_NOW,
        'selected_cohort_id': None,
        'selected_event_type_set_id': None,
        'selected_mentorship_service_set_id': None,
        **data,
    }


#FIXME: create_v2 fail in this test file
class PaymentsTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 Bag not found
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_bag_not_found(self):
        build_plan_financing.delay(1, 1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [])

        self.assertEqual(logging.Logger.info.call_args_list,
                         [call('Starting build_plan_financing for bag 1')])
        self.assertEqual(logging.Logger.error.call_args_list, [call('Bag with id 1 not found')])

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [])
        self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [])

    """
    🔽🔽🔽 With Bag
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_invoice_not_found(self):
        bag = {'status': 'PAID', 'was_delivered': False}
        model = self.bc.database.create_v2(bag=bag)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_plan_financing.delay(1, 1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [])

        self.assertEqual(logging.Logger.info.call_args_list,
                         [call('Starting build_plan_financing for bag 1')])
        self.assertEqual(logging.Logger.error.call_args_list, [call('Invoice with id 1 not found')])

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [self.bc.format.to_dict(model.bag)])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [])
        self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [])

    """
    🔽🔽🔽 With Bag and Invoice
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch.object(timezone, 'now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.tasks.build_service_stock_scheduler_from_plan_financing.delay', MagicMock())
    def test_invoice_with_wrong_amount(self):
        bag = {
            'status': 'PAID',
            'was_delivered': False,
            'chosen_period': random.choice(['MONTH', 'QUARTER', 'HALF', 'YEAR']),
        }
        invoice = {'status': 'FULFILLED'}
        months = 1

        if bag['chosen_period'] == 'QUARTER':
            months = 3

        elif bag['chosen_period'] == 'HALF':
            months = 6

        elif bag['chosen_period'] == 'YEAR':
            months = 12

        model = self.bc.database.create(bag=bag, invoice=invoice)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_plan_financing.delay(1, 1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [])

        self.assertEqual(logging.Logger.info.call_args_list, [
            call('Starting build_plan_financing for bag 1'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [
            call('An invoice without amount is prohibited (id: 1)'),
        ])

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [
            {
                **self.bc.format.to_dict(model.bag),
                'was_delivered': False,
            },
        ])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [
            self.bc.format.to_dict(model.invoice),
        ])
        self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [])

        self.assertEqual(tasks.build_service_stock_scheduler_from_plan_financing.delay.call_args_list, [])

    """
    🔽🔽🔽 With Bag and Invoice with amount
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch.object(timezone, 'now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.tasks.build_service_stock_scheduler_from_plan_financing.delay', MagicMock())
    def test_subscription_was_created(self):
        amount = (random.random() * 99) + 1
        bag = {
            'status': 'PAID',
            'was_delivered': False,
            'chosen_period': random.choice(['MONTH', 'QUARTER', 'HALF', 'YEAR']),
        }
        invoice = {'status': 'FULFILLED', 'amount': amount}

        model = self.bc.database.create(bag=bag, invoice=invoice, plan=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        months = model.bag.how_many_installments

        build_plan_financing.delay(1, 1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [])

        self.assertEqual(logging.Logger.info.call_args_list, [
            call('Starting build_plan_financing for bag 1'),
            call('PlanFinancing was created with id 1'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [
            {
                **self.bc.format.to_dict(model.bag),
                'was_delivered': True,
            },
        ])
        self.assertEqual(
            self.bc.database.list_of('payments.Invoice'),
            [
                {
                    **self.bc.format.to_dict(model.invoice),
                    # 'monthly_price': amount,
                },
            ])
        self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [
            plan_financing_item({
                'monthly_price':
                model.invoice.amount,
                'valid_until':
                model.invoice.paid_at + relativedelta(months=months),
                'next_payment_at':
                model.invoice.paid_at + relativedelta(months=1),
                'plan_expires_at':
                model.invoice.paid_at +
                calculate_relative_delta(model.plan.time_of_life, model.plan.time_of_life_unit),
            }),
        ])

        self.assertEqual(tasks.build_service_stock_scheduler_from_plan_financing.delay.call_args_list,
                         [call(1)])

    """
    🔽🔽🔽 With Bag with Cohort and Invoice with amount
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch.object(timezone, 'now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.tasks.build_service_stock_scheduler_from_plan_financing.delay', MagicMock())
    def test_subscription_was_created__bag_with_cohort(self):
        amount = (random.random() * 99) + 1
        bag = {
            'status': 'PAID',
            'was_delivered': False,
            'chosen_period': random.choice(['MONTH', 'QUARTER', 'HALF', 'YEAR']),
        }
        invoice = {'status': 'FULFILLED', 'amount': amount}

        model = self.bc.database.create(bag=bag, invoice=invoice, plan=1, cohort=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        months = model.bag.how_many_installments

        build_plan_financing.delay(1, 1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [
            self.bc.format.to_dict(model.cohort),
        ])

        self.assertEqual(logging.Logger.info.call_args_list, [
            call('Starting build_plan_financing for bag 1'),
            call('PlanFinancing was created with id 1'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [
            {
                **self.bc.format.to_dict(model.bag),
                'was_delivered': True,
            },
        ])
        self.assertEqual(
            self.bc.database.list_of('payments.Invoice'),
            [
                {
                    **self.bc.format.to_dict(model.invoice),
                    # 'monthly_price': amount,
                },
            ])
        self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [
            plan_financing_item({
                'monthly_price':
                model.invoice.amount,
                'selected_cohort_id':
                1,
                'valid_until':
                model.invoice.paid_at + relativedelta(months=months),
                'next_payment_at':
                model.invoice.paid_at + relativedelta(months=1),
                'plan_expires_at':
                model.invoice.paid_at +
                calculate_relative_delta(model.plan.time_of_life, model.plan.time_of_life_unit),
            }),
        ])

        self.assertEqual(tasks.build_service_stock_scheduler_from_plan_financing.delay.call_args_list, [
            call(1),
        ])

    """
    🔽🔽🔽 With Bag with EventTypeSet and Invoice with amount
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch.object(timezone, 'now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.tasks.build_service_stock_scheduler_from_plan_financing.delay', MagicMock())
    def test_subscription_was_created__bag_with_event_type_set(self):
        amount = (random.random() * 99) + 1
        bag = {
            'status': 'PAID',
            'was_delivered': False,
            'chosen_period': random.choice(['MONTH', 'QUARTER', 'HALF', 'YEAR']),
        }
        invoice = {'status': 'FULFILLED', 'amount': amount}

        model = self.bc.database.create(bag=bag, invoice=invoice, plan=1, event_type_set=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        months = model.bag.how_many_installments

        build_plan_financing.delay(1, 1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [])

        self.assertEqual(logging.Logger.info.call_args_list, [
            call('Starting build_plan_financing for bag 1'),
            call('PlanFinancing was created with id 1'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [
            {
                **self.bc.format.to_dict(model.bag),
                'was_delivered': True,
            },
        ])
        self.assertEqual(
            self.bc.database.list_of('payments.Invoice'),
            [
                {
                    **self.bc.format.to_dict(model.invoice),
                    # 'monthly_price': amount,
                },
            ])
        self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [
            plan_financing_item({
                'monthly_price':
                model.invoice.amount,
                'selected_event_type_set_id':
                1,
                'valid_until':
                model.invoice.paid_at + relativedelta(months=months),
                'next_payment_at':
                model.invoice.paid_at + relativedelta(months=1),
                'plan_expires_at':
                model.invoice.paid_at +
                calculate_relative_delta(model.plan.time_of_life, model.plan.time_of_life_unit),
            }),
        ])

        self.assertEqual(tasks.build_service_stock_scheduler_from_plan_financing.delay.call_args_list, [
            call(1),
        ])

    """
    🔽🔽🔽 With Bag with MentorshipServiceSet and Invoice with amount
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch.object(timezone, 'now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.tasks.build_service_stock_scheduler_from_plan_financing.delay', MagicMock())
    def test_subscription_was_created__bag_with_mentorship_service_set(self):
        amount = (random.random() * 99) + 1
        bag = {
            'status': 'PAID',
            'was_delivered': False,
            'chosen_period': random.choice(['MONTH', 'QUARTER', 'HALF', 'YEAR']),
        }
        invoice = {'status': 'FULFILLED', 'amount': amount}

        model = self.bc.database.create(bag=bag, invoice=invoice, plan=1, mentorship_service_set=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        months = model.bag.how_many_installments

        build_plan_financing.delay(1, 1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [])

        self.assertEqual(logging.Logger.info.call_args_list, [
            call('Starting build_plan_financing for bag 1'),
            call('PlanFinancing was created with id 1'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [
            {
                **self.bc.format.to_dict(model.bag),
                'was_delivered': True,
            },
        ])
        self.assertEqual(
            self.bc.database.list_of('payments.Invoice'),
            [
                {
                    **self.bc.format.to_dict(model.invoice),
                    # 'monthly_price': amount,
                },
            ])
        self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [
            plan_financing_item({
                'monthly_price':
                model.invoice.amount,
                'selected_mentorship_service_set_id':
                1,
                'valid_until':
                model.invoice.paid_at + relativedelta(months=months),
                'next_payment_at':
                model.invoice.paid_at + relativedelta(months=1),
                'plan_expires_at':
                model.invoice.paid_at +
                calculate_relative_delta(model.plan.time_of_life, model.plan.time_of_life_unit),
            }),
        ])

        self.assertEqual(tasks.build_service_stock_scheduler_from_plan_financing.delay.call_args_list, [
            call(1),
        ])
