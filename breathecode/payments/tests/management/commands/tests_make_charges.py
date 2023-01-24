from unittest.mock import patch, MagicMock, call
from breathecode.payments import tasks
from breathecode.payments.management.commands.make_charges import Command
from breathecode.payments.tests.mixins import PaymentsTestCase
from django.utils import timezone
from dateutil.relativedelta import relativedelta


class SlackTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 Subscription cases
    """

    @patch('breathecode.payments.tasks.charge_subscription.delay', MagicMock())
    def test_with_zero_subscriptions(self):
        """Testing when context is None or not provided."""

        command = Command()
        result = command.handle()

        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of('payments.Subscription'), [])
        self.assertEqual(tasks.charge_subscription.delay.call_args_list, [])

    @patch('breathecode.payments.tasks.charge_subscription.delay', MagicMock())
    def test_with_two_subscriptions__wrong_cases(self):
        """Testing when context is None or not provided."""
        utc_now = timezone.now()
        cases = [
            (utc_now + relativedelta(days=1, minutes=1), 'ACTIVE'),
            (utc_now + relativedelta(days=1, minutes=1), 'ERROR'),
            (utc_now + relativedelta(days=1, minutes=1), 'PAYMENT_ISSUE'),
            (utc_now - relativedelta(days=1, seconds=1), 'CANCELLED'),
            (utc_now - relativedelta(days=1, seconds=1), 'FREE_TRIAL'),
            (utc_now - relativedelta(days=1, seconds=1), 'DEPRECATED'),
        ]
        for valid_until, status in cases:
            subscription = {'valid_until': valid_until, 'status': status}

            model = self.bc.database.create(subscription=(2, subscription))

            command = Command()
            result = command.handle()

            self.assertEqual(result, None)
            self.assertEqual(
                self.bc.database.list_of('payments.Subscription'),
                self.bc.format.to_dict(model.subscription),
            )
            self.assertEqual(tasks.charge_subscription.delay.call_args_list, [])

            # teardown
            self.bc.database.delete('payments.Subscription')

    @patch('breathecode.payments.tasks.charge_subscription.delay', MagicMock())
    def test_with_two_subscriptions__valid_cases(self):
        """Testing when context is None or not provided."""
        utc_now = timezone.now()
        cases = [
            (utc_now - relativedelta(days=1, seconds=1), 'ACTIVE'),
            (utc_now - relativedelta(days=1, seconds=1), 'ERROR'),
            (utc_now - relativedelta(days=1, seconds=1), 'PAYMENT_ISSUE'),
        ]
        for valid_until, status in cases:
            subscription = {'valid_until': valid_until, 'status': status}

            model = self.bc.database.create(subscription=(2, subscription))

            command = Command()
            result = command.handle()

            self.assertEqual(result, None)
            self.assertEqual(
                self.bc.database.list_of('payments.Subscription'),
                self.bc.format.to_dict(model.subscription),
            )
            self.assertEqual(tasks.charge_subscription.delay.call_args_list, [
                call(model.subscription[0].id),
                call(model.subscription[1].id),
            ])

            # teardown
            self.bc.database.delete('payments.Subscription')
            tasks.charge_subscription.delay.call_args_list = []

    """
    🔽🔽🔽 PlanFinancing cases
    """

    @patch('breathecode.payments.tasks.charge_plan_financing.delay', MagicMock())
    def test_with_zero_plan_financings(self):
        """Testing when context is None or not provided."""

        command = Command()
        result = command.handle()

        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [])
        self.assertEqual(tasks.charge_plan_financing.delay.call_args_list, [])

    @patch('breathecode.payments.tasks.charge_plan_financing.delay', MagicMock())
    def test_with_two_plan_financings__wrong_cases(self):
        """Testing when context is None or not provided."""
        utc_now = timezone.now()
        cases = [
            (utc_now + relativedelta(days=1, minutes=1), 'ACTIVE'),
            (utc_now + relativedelta(days=1, minutes=1), 'ERROR'),
            (utc_now + relativedelta(days=1, minutes=1), 'PAYMENT_ISSUE'),
            (utc_now - relativedelta(days=1, seconds=1), 'CANCELLED'),
            (utc_now - relativedelta(days=1, seconds=1), 'FREE_TRIAL'),
            (utc_now - relativedelta(days=1, seconds=1), 'DEPRECATED'),
        ]
        for valid_until, status in cases:
            plan_financing = {'valid_until': valid_until, 'status': status}

            model = self.bc.database.create(plan_financing=(2, plan_financing))

            command = Command()
            result = command.handle()

            self.assertEqual(result, None)
            self.assertEqual(
                self.bc.database.list_of('payments.PlanFinancing'),
                self.bc.format.to_dict(model.plan_financing),
            )
            self.assertEqual(tasks.charge_plan_financing.delay.call_args_list, [])

            # teardown
            self.bc.database.delete('payments.PlanFinancing')

    @patch('breathecode.payments.tasks.charge_plan_financing.delay', MagicMock())
    def test_with_two_plan_financings__valid_cases(self):
        """Testing when context is None or not provided."""
        utc_now = timezone.now()
        cases = [
            (utc_now - relativedelta(days=1, seconds=1), 'ACTIVE'),
            (utc_now - relativedelta(days=1, seconds=1), 'ERROR'),
            (utc_now - relativedelta(days=1, seconds=1), 'PAYMENT_ISSUE'),
        ]
        for valid_until, status in cases:
            plan_financing = {'valid_until': valid_until, 'status': status}

            model = self.bc.database.create(plan_financing=(2, plan_financing))

            command = Command()
            result = command.handle()

            self.assertEqual(result, None)
            self.assertEqual(
                self.bc.database.list_of('payments.PlanFinancing'),
                self.bc.format.to_dict(model.plan_financing),
            )
            self.assertEqual(tasks.charge_plan_financing.delay.call_args_list, [
                call(model.plan_financing[0].id),
                call(model.plan_financing[1].id),
            ])

            # teardown
            self.bc.database.delete('payments.PlanFinancing')
            tasks.charge_plan_financing.delay.call_args_list = []
