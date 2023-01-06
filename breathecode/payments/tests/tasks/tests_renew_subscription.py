"""
Test /answer
"""
import logging
import random
from unittest.mock import MagicMock, call, patch

from django.utils import timezone
from breathecode.payments import tasks

from ...tasks import renew_subscription
from breathecode.notify import actions as notify_actions
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


#FIXME: create_v2 fail in this test file
class PaymentsTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 Subscription not found
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_subscription_not_found(self):
        renew_subscription.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [])

        self.assertEqual(logging.Logger.info.call_args_list, [
            call('Starting renew_subscription for subscription 1'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [call('Subscription with id 1 not found')])

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [])
        self.assertEqual(self.bc.database.list_of('payments.Subscription'), [])

    """
    🔽🔽🔽 Subscription with zero Invoice
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_subscription_without_invoices(self):
        model = self.bc.database.create_v2(subscription=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_subscription.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [])

        self.assertEqual(logging.Logger.info.call_args_list, [
            call('Starting renew_subscription for subscription 1'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [
            call('Error getting bag from subscription 1: subscription-has-no-invoices'),
        ])

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [])
        self.maxDiff = None

        self.assertEqual(
            self.bc.database.list_of('payments.Subscription'),
            [
                {
                    **self.bc.format.to_dict(model.subscription),
                    # 'status': 'PAYMENT_ISSUE',,
                    'status': 'ERROR',
                    'status_message': 'subscription-has-no-invoices',
                },
            ])
        self.assertEqual(notify_actions.send_email_message.call_args_list, [])

    """
    🔽🔽🔽 Subscription with zero Invoice
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_subscription_without_invoices(self):
        model = self.bc.database.create_v2(subscription=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_subscription.delay(1)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [])

        self.assertEqual(logging.Logger.info.call_args_list, [
            call('Starting renew_subscription for subscription 1'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [
            call('Error getting bag from subscription 1: subscription-has-no-invoices'),
        ])

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [])
        self.assertEqual(self.bc.database.list_of('payments.Invoice'), [])
        self.maxDiff = None

        self.assertEqual(
            self.bc.database.list_of('payments.Subscription'),
            [
                {
                    **self.bc.format.to_dict(model.subscription),
                    # 'status': 'PAYMENT_ISSUE',,
                    'status': 'ERROR',
                    'status_message': 'subscription-has-no-invoices',
                },
            ])
        self.assertEqual(notify_actions.send_email_message.call_args_list, [])
