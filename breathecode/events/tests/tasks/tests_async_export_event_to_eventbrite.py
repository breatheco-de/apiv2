import logging
from unittest.mock import MagicMock, call, patch

from breathecode.events.tasks import async_export_event_to_eventbrite
from ..mixins.new_events_tests_case import EventTestCase
from ...signals import event_saved
import breathecode.events.actions as actions


class AcademyEventTestSuite(EventTestCase):
    """
    🔽🔽🔽 Without event
    """

    @patch.object(actions, 'export_event_to_eventbrite', MagicMock())
    @patch.object(logging.Logger, 'error', MagicMock())
    @patch.object(logging.Logger, 'debug', MagicMock())
    @patch.object(event_saved, 'send', MagicMock())
    def test_async_export_event_to_eventbrite__without_event(self):
        async_export_event_to_eventbrite(1)

        self.assertEqual(actions.export_event_to_eventbrite.call_args_list, [])
        self.assertEqual(logging.Logger.debug.call_args_list, [call('Starting async_eventbrite_webhook')])
        self.assertEqual(logging.Logger.error.call_args_list, [call('Event 1 not fount')])
        self.assertEqual(event_saved.send.call_args_list, [])
        self.assertEqual(self.all_event_dict(), [])

    """
    🔽🔽🔽 Without organization
    """

    @patch.object(actions, 'export_event_to_eventbrite', MagicMock())
    @patch.object(logging.Logger, 'error', MagicMock())
    @patch.object(logging.Logger, 'debug', MagicMock())
    @patch.object(event_saved, 'send', MagicMock())
    def test_async_export_event_to_eventbrite__without_organization(self):
        event_kwargs = {
            'sync_with_eventbrite': True,
            'eventbrite_sync_status': 'PENDING',
        }
        model = self.generate_models(event=True, event_kwargs=event_kwargs)
        event_db = self.model_to_dict(model, 'event')

        async_export_event_to_eventbrite(1)

        self.assertEqual(actions.export_event_to_eventbrite.call_args_list, [])
        self.assertEqual(logging.Logger.debug.call_args_list, [call('Starting async_eventbrite_webhook')])
        self.assertEqual(logging.Logger.error.call_args_list,
                         [call('Event 1 not have a organization assigned')])

        self.assertEqual(event_saved.send.call_args_list,
                         [call(instance=model.event, sender=model.event.__class__)])

        self.assertEqual(self.all_event_dict(), [event_db])

    """
    🔽🔽🔽 Call async_export_event_to_eventbrite
    """

    @patch.object(actions, 'export_event_to_eventbrite', MagicMock())
    @patch.object(logging.Logger, 'error', MagicMock())
    @patch.object(logging.Logger, 'debug', MagicMock())
    @patch.object(event_saved, 'send', MagicMock())
    def test_async_export_event_to_eventbrite(self):
        event_kwargs = {
            'sync_with_eventbrite': True,
            'eventbrite_sync_status': 'PENDING',
        }
        model = self.generate_models(event=True, organization=True, event_kwargs=event_kwargs)
        event_db = self.model_to_dict(model, 'event')

        async_export_event_to_eventbrite(1)

        self.assertEqual(actions.export_event_to_eventbrite.call_args_list,
                         [call(model.event, model.organization)])

        self.assertEqual(logging.Logger.debug.call_args_list, [call('Starting async_eventbrite_webhook')])
        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(event_saved.send.call_args_list,
                         [call(instance=model.event, sender=model.event.__class__)])

        self.assertEqual(self.all_event_dict(), [event_db])
