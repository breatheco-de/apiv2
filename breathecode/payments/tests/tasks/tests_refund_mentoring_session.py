"""
Test /answer
"""
import logging
import random
from unittest.mock import MagicMock, call, patch

from django.utils import timezone

from breathecode.tests.mixins.legacy import LegacyAPITestCase

from ...tasks import refund_mentoring_session

UTC_NOW = timezone.now()


class TestPayments(LegacyAPITestCase):
    # When: no mentoring session
    # Then: do nothing
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('breathecode.payments.signals.grant_service_permissions.send', MagicMock())
    def test_0_items(self, enable_signals):
        enable_signals()

        refund_mentoring_session.delay(1)

        self.bc.check.calls(logging.Logger.info.call_args_list, [
            call('Starting refund_mentoring_session for mentoring session 1'),
        ])
        self.bc.check.calls(logging.Logger.error.call_args_list, [
            call('MentoringSession with id 1 not found or is invalid'),
        ])

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    # Given: 1 MentoringSession
    # When: not have mentee, service and have a bad status
    # Then: not found mentorship session
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('breathecode.payments.signals.grant_service_permissions.send', MagicMock())
    def test_1_mentoring_session__nothing_provide(self, enable_signals):
        enable_signals()

        model = self.bc.database.create(mentorship_session=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        refund_mentoring_session.delay(1)

        self.bc.check.calls(logging.Logger.info.call_args_list, [
            call('Starting refund_mentoring_session for mentoring session 1'),
        ])
        self.bc.check.calls(logging.Logger.error.call_args_list, [
            call('MentoringSession with id 1 not found or is invalid'),
        ])

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    # Given: 1 MentoringSession and 1 User
    # When: have mentee and not have service and have a bad status
    # Then: not found mentorship session
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('breathecode.payments.signals.grant_service_permissions.send', MagicMock())
    def test_1_mentoring_session__just_with_mentee(self, enable_signals):
        enable_signals()

        user = {'groups': []}
        model = self.bc.database.create(mentorship_session=1, user=user, group=1, permission=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        refund_mentoring_session.delay(1)

        self.bc.check.calls(logging.Logger.info.call_args_list, [
            call('Starting refund_mentoring_session for mentoring session 1'),
        ])
        self.bc.check.calls(logging.Logger.error.call_args_list, [
            call('MentoringSession with id 1 not found or is invalid'),
        ])

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

        self.bc.check.queryset_with_pks(model.user.groups.all(), [])

    # Given: 1 MentoringSession and 1 MentorshipService
    # When: have service and not have mentee and have a bad status
    # Then: not found mentorship session
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('breathecode.payments.signals.grant_service_permissions.send', MagicMock())
    def test_1_mentoring_session__just_with_service(self, enable_signals):
        enable_signals()

        model = self.bc.database.create(mentorship_session=1, mentorship_service=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        refund_mentoring_session.delay(1)

        self.bc.check.calls(logging.Logger.info.call_args_list, [
            call('Starting refund_mentoring_session for mentoring session 1'),
        ])
        self.bc.check.calls(logging.Logger.error.call_args_list, [
            call('MentoringSession with id 1 not found or is invalid'),
        ])

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    # Given: 1 MentoringSession
    # When: not have service, mentee and have a right status
    # Then: not found mentorship session
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('breathecode.payments.signals.grant_service_permissions.send', MagicMock())
    def test_1_mentoring_session__just_with_right_status(self, enable_signals):
        enable_signals()

        mentorship_session = {'status': random.choice(['PENDING', 'STARTED', 'COMPLETED'])}
        model = self.bc.database.create(mentorship_session=mentorship_session)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        refund_mentoring_session.delay(1)

        self.bc.check.calls(logging.Logger.info.call_args_list, [
            call('Starting refund_mentoring_session for mentoring session 1'),
        ])
        self.bc.check.calls(logging.Logger.error.call_args_list, [
            call('MentoringSession with id 1 not found or is invalid'),
        ])

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    # Given: 1 MentoringSession, 1 User and 1 MentorshipService
    # When: have service, mentee and have a right status
    # Then: not found mentorship session
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('breathecode.payments.signals.grant_service_permissions.send', MagicMock())
    def test_1_mentoring_session__all_elements_given(self, enable_signals):
        enable_signals()

        mentorship_session = {'status': random.choice(['FAILED', 'IGNORED'])}

        user = {'groups': []}
        model = self.bc.database.create(mentorship_session=mentorship_session,
                                        user=user,
                                        mentorship_service=1,
                                        group=1,
                                        permission=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        refund_mentoring_session.delay(1)

        self.bc.check.calls(logging.Logger.info.call_args_list, [
            call('Starting refund_mentoring_session for mentoring session 1'),
        ])
        self.bc.check.calls(logging.Logger.error.call_args_list, [
            call('ConsumptionSession not found for mentorship session 1'),
        ])

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

        self.bc.check.queryset_with_pks(model.user.groups.all(), [])

    # Given: 1 MentoringSession, 1 User, 1 ConsumptionSession, 1 Consumable and 1 MentorshipServiceSet
    # When: consumption session is pending
    # Then: not refund consumable
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('breathecode.payments.signals.grant_service_permissions.send', MagicMock())
    def test_consumption_session_is_pending(self, enable_signals):
        enable_signals()

        mentorship_session = {'status': random.choice(['FAILED', 'IGNORED'])}
        how_many_consumables = random.randint(1, 10)
        how_mawy_will_consume = random.randint(1, how_many_consumables)
        consumable = {'how_many': how_many_consumables}
        consumption_session = {'how_many': how_mawy_will_consume, 'status': 'PENDING'}

        user = {'groups': []}
        model = self.bc.database.create(mentorship_session=mentorship_session,
                                        user=user,
                                        mentorship_service=1,
                                        consumption_session=consumption_session,
                                        consumable=consumable,
                                        mentorship_service_set=1,
                                        group=1,
                                        permission=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        refund_mentoring_session.delay(1)

        self.bc.check.calls(logging.Logger.info.call_args_list, [
            call('Starting refund_mentoring_session for mentoring session 1'),
        ])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            {
                **self.bc.format.to_dict(model.consumption_session),
                'status': 'CANCELLED',
            },
        ])

        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [
            self.bc.format.to_dict(model.consumable),
        ])

        self.bc.check.queryset_with_pks(model.user.groups.all(), [])

    # Given: 1 MentoringSession, 1 User, 1 ConsumptionSession, 1 Consumable and 1 MentorshipServiceSet
    # When: consumption session is done
    # Then: not refund consumable
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('breathecode.payments.signals.grant_service_permissions.send', MagicMock())
    def test_consumption_session_is_done(self, enable_signals):
        enable_signals()

        mentorship_session = {'status': random.choice(['FAILED', 'IGNORED'])}
        how_many_consumables = random.randint(1, 10)
        how_mawy_will_consume = random.randint(1, 10)
        consumable = {'how_many': how_many_consumables}
        consumption_session = {'how_many': how_mawy_will_consume, 'status': 'DONE'}

        user = {'groups': []}
        model = self.bc.database.create(mentorship_session=mentorship_session,
                                        user=user,
                                        mentorship_service=1,
                                        consumption_session=consumption_session,
                                        consumable=consumable,
                                        mentorship_service_set=1,
                                        group=1,
                                        permission=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        refund_mentoring_session.delay(1)

        self.bc.check.calls(logging.Logger.info.call_args_list, [
            call('Starting refund_mentoring_session for mentoring session 1'),
            call('Refunding consumption session because it was discounted'),
        ])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            {
                **self.bc.format.to_dict(model.consumption_session),
                'status': 'CANCELLED',
            },
        ])

        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [{
            **self.bc.format.to_dict(model.consumable),
            'how_many':
            how_many_consumables + how_mawy_will_consume,
        }])

        self.bc.check.queryset_with_pks(model.user.groups.all(), [])

    # Given: 1 MentoringSession, 1 User, 1 ConsumptionSession, 1 Consumable and 1 MentorshipServiceSet
    # When: consumption session is done
    # Then: not refund consumable
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('breathecode.payments.signals.grant_service_permissions.send', MagicMock())
    def test_consumption_session_is_cancelled(self, enable_signals):
        enable_signals()

        mentorship_session = {'status': random.choice(['FAILED', 'IGNORED'])}
        how_many_consumables = random.randint(1, 10)
        how_mawy_will_consume = random.randint(1, 10)
        consumable = {'how_many': how_many_consumables}
        consumption_session = {'how_many': how_mawy_will_consume, 'status': 'CANCELLED'}

        user = {'groups': []}
        model = self.bc.database.create(mentorship_session=mentorship_session,
                                        user=user,
                                        mentorship_service=1,
                                        consumption_session=consumption_session,
                                        consumable=consumable,
                                        mentorship_service_set=1,
                                        group=1,
                                        permission=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        refund_mentoring_session.delay(1)

        self.bc.check.calls(logging.Logger.info.call_args_list, [
            call('Starting refund_mentoring_session for mentoring session 1'),
        ])
        self.bc.check.calls(logging.Logger.error.call_args_list, [
            call('ConsumptionSession not found for mentorship session 1'),
        ])

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [
            self.bc.format.to_dict(model.consumable),
        ])

        self.bc.check.queryset_with_pks(model.user.groups.all(), [])

    # Given: 1 MentoringSession, 1 User, 1 ConsumptionSession, 1 Consumable and 1 MentorshipServiceSet
    # When: consumption session is done and consumable how many is 0
    # Then: not refund consumable
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test_consumable_wasted(self, enable_signals):
        enable_signals()

        mentorship_session = {'status': random.choice(['FAILED', 'IGNORED'])}
        how_many_consumables = 0
        how_mawy_will_consume = random.randint(1, 10)
        consumable = {'how_many': how_many_consumables}
        consumption_session = {'how_many': how_mawy_will_consume, 'status': 'DONE'}

        user = {'groups': []}
        groups = [{'permissions': n} for n in range(1, 4)]
        model = self.bc.database.create(mentorship_session=mentorship_session,
                                        user=user,
                                        mentorship_service=1,
                                        consumption_session=consumption_session,
                                        consumable=consumable,
                                        mentorship_service_set=1,
                                        group=groups,
                                        permission=2)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        refund_mentoring_session.delay(1)

        self.bc.check.calls(logging.Logger.info.call_args_list, [
            call('Starting refund_mentoring_session for mentoring session 1'),
            call('Refunding consumption session because it was discounted'),
        ])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            {
                **self.bc.format.to_dict(model.consumption_session),
                'status': 'CANCELLED',
            },
        ])

        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [{
            **self.bc.format.to_dict(model.consumable),
            'how_many':
            how_many_consumables + how_mawy_will_consume,
        }])

        self.bc.check.queryset_with_pks(model.user.groups.all(), [1, 2, 3])
