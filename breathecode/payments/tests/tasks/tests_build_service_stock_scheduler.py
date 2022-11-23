"""
Test /answer
"""
import logging
import random
from unittest.mock import MagicMock, call, patch

from django.utils import timezone
from breathecode.payments import tasks

from ...tasks import build_service_stock_scheduler

from ..mixins import PaymentsTestCase
from dateutil.relativedelta import relativedelta

UTC_NOW = timezone.now()


def subscription_item(data={}):
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


#FIXME: create fail in this test file
class PaymentsTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 Subscription not found
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_subscription_not_found(self):
        build_service_stock_scheduler.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [])

        self.assertEqual(logging.Logger.info.call_args_list,
                         [call('Starting build_service_stock_scheduler for subscription 1')])
        self.assertEqual(logging.Logger.error.call_args_list, [call('Subscription with id 1 not found')])

        self.assertEqual(self.bc.database.list_of('payments.Subscription'), [])

    """
    🔽🔽🔽 With Subscription
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.payments.tasks.renew_consumables.delay', MagicMock())
    def test_subscription_exists(self):
        model = self.bc.database.create(subscription=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_service_stock_scheduler.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [])

        self.assertEqual(logging.Logger.info.call_args_list,
                         [call('Starting build_service_stock_scheduler for subscription 1')])
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('payments.Subscription'), [
            self.bc.format.to_dict(model.subscription),
        ])
        self.assertEqual(tasks.renew_consumables.delay.call_args_list, [call(1)])
        self.bc.check.queryset_with_pks(model.subscription.service_items.all(), [])
        self.bc.check.queryset_with_pks(model.subscription.plans.all(), [])
        self.bc.check.queryset_with_pks(model.subscription.service_stock_schedulers.all(), [])
        self.bc.check.queryset_with_pks(model.subscription.service_stock_schedulers.all(), [])

        self.assertEqual(self.bc.database.list_of('payments.ServiceStockScheduler'), [])

    """
    🔽🔽🔽 With Subscription
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.payments.tasks.renew_consumables.delay', MagicMock())
    def test_subscription_not_found__(self):
        model = self.bc.database.create(subscription=1, service_item=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_service_stock_scheduler.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [])

        self.assertEqual(logging.Logger.info.call_args_list,
                         [call('Starting build_service_stock_scheduler for subscription 1')])
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('payments.Subscription'), [
            self.bc.format.to_dict(model.subscription),
        ])
        self.assertEqual(tasks.renew_consumables.delay.call_args_list, [call(1)])
        self.bc.check.queryset_with_pks(model.subscription.service_items.all(), [])
        self.bc.check.queryset_with_pks(model.subscription.plans.all(), [])
        self.bc.check.queryset_with_pks(model.subscription.service_stock_schedulers.all(), [])
        self.bc.check.queryset_with_pks(model.subscription.service_stock_schedulers.all(), [])

        self.assertEqual(self.bc.database.list_of('payments.ServiceStockScheduler'), [])
        assert False
