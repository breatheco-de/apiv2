from breathecode.events.actions import publish_event_from_eventbrite
from unittest.mock import MagicMock, call, patch
from django.utils import timezone
from ..mixins import EventTestCase

now = timezone.now()


class SyncOrgVenuesTestSuite(EventTestCase):
    """
    🔽🔽🔽 Empty data
    """
    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.events.signals.event_saved.send', MagicMock())
    def test_publish_event_from_eventbrite__empty_data(self):
        """
        Descriptions of models are being generated:

          Organization(id=1): {}
        """
        from logging import Logger

        organization = {'eventbrite_id': '1'}
        model = self.bc.database.create(organization=organization)

        with self.assertRaisesMessage(ValueError, 'data is empty'):
            publish_event_from_eventbrite({}, model.organization)

        self.assertEqual(Logger.debug.call_args_list, [call('Ignored event')])
        self.assertEqual(Logger.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('events.Organization'), [
            self.bc.format.to_dict(model.organization),
        ])
        self.assertEqual(self.bc.database.list_of('events.Event'), [])

    """
    🔽🔽🔽 Bad data
    """

    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.events.signals.event_saved.send', MagicMock())
    def test_publish_event_from_eventbrite__bad_data(self):
        """
        Descriptions of models are being generated:

          Organization(id=1): {}
        """
        from logging import Logger

        organization = {'eventbrite_id': '1'}
        model = self.bc.database.create(organization=organization)

        with self.assertRaisesMessage(KeyError, 'id'):
            publish_event_from_eventbrite({'irrelevant': 'value'}, model.organization)

        self.assertEqual(Logger.debug.call_args_list, [])
        self.assertEqual(Logger.error.call_args_list, [
            call(f'{now} => the body is coming from eventbrite has change', exc_info=True),
        ])

        self.assertEqual(self.bc.database.list_of('events.Organization'), [
            self.bc.format.to_dict(model.organization),
        ])
        self.assertEqual(self.bc.database.list_of('events.Event'), [])

    """
    🔽🔽🔽 Event not found
    """

    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.events.signals.event_saved.send', MagicMock())
    def test_publish_event_from_eventbrite__event_not_found(self):
        """
        Descriptions of models are being generated:

          Organization(id=1): {}
        """
        from logging import Logger

        organization = {'eventbrite_id': 1}
        model = self.bc.database.create(organization=organization)
        exception_message = 'The event with the eventbrite id `1` doesn\'t exist in breathecode yet'

        with self.assertRaisesMessage(Warning, exception_message):
            publish_event_from_eventbrite({'id': '1'}, model.organization)

        self.assertEqual(Logger.debug.call_args_list, [])
        self.assertEqual(Logger.error.call_args_list, [call(f'{now} => {exception_message}')])

        self.assertEqual(self.bc.database.list_of('events.Organization'), [
            self.bc.format.to_dict(model.organization),
        ])
        self.assertEqual(self.bc.database.list_of('events.Event'), [])

    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.events.signals.event_saved.send', MagicMock())
    def test_publish_event_from_eventbrite__event_not_found__with_one_event(self):
        """
        Descriptions of models are being generated:

          Event(id=1):
            organization: Organization(id=1)

          Organization(id=1): {}
        """
        from logging import Logger

        organization = {'eventbrite_id': 1}
        model = self.bc.database.create(organization=organization, event=1)
        exception_message = 'The event with the eventbrite id `1` doesn\'t exist in breathecode yet'

        with self.assertRaisesMessage(Warning, exception_message):
            publish_event_from_eventbrite({'id': '1'}, model.organization)

        self.assertEqual(Logger.debug.call_args_list, [])
        self.assertEqual(Logger.error.call_args_list, [call(f'{now} => {exception_message}')])

        self.assertEqual(self.bc.database.list_of('events.Organization'), [
            self.bc.format.to_dict(model.organization),
        ])
        self.assertEqual(self.bc.database.list_of('events.Event'), [
            self.bc.format.to_dict(model.event),
        ])

    """
    🔽🔽🔽 With a correct Event
    """

    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=now))
    @patch('breathecode.events.signals.event_saved.send', MagicMock())
    def test_publish_event_from_eventbrite__event_not_found__with_one_event(self):
        """
        Descriptions of models are being generated:

          Event(id=1):
            organization: Organization(id=1)

          Organization(id=1): {}
        """

        from logging import Logger

        organization = {'eventbrite_id': 1}
        event = {'eventbrite_id': 1}
        model = self.bc.database.create(organization=organization, event=event)

        publish_event_from_eventbrite({'id': '1', 'status': 'they-killed-kenny'}, model.organization)
        self.assertEqual(Logger.debug.call_args_list,
                         [call('The event with the eventbrite id `1` was saved')])
        self.assertEqual(Logger.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('events.Organization'), [
            self.bc.format.to_dict(model.organization),
        ])
        self.assertEqual(self.bc.database.list_of('events.Event'), [
            {
                **self.bc.format.to_dict(model.event),
                'eventbrite_status': 'they-killed-kenny',
                'eventbrite_sync_description': str(now),
                'eventbrite_sync_status': 'PERSISTED',
                'status': 'ACTIVE',
            },
        ])
