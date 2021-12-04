import logging
import breathecode.events.actions as actions
from unittest.mock import MagicMock, call, patch
from breathecode.events.utils import Eventbrite

from breathecode.tests.mocks.requests import REQUESTS_PATH, apply_requests_request_mock
from ..mixins import EventTestCase

export_event_to_eventbrite = actions.export_event_to_eventbrite
sync_desc = '2021-11-23 09:10:58.295264+00:00'
eventbrite_post_url = 'https://www.eventbriteapi.com/v3/organizations/1/events/'
eventbrite_put_url = 'https://www.eventbriteapi.com/v3/events/1/'
eventbrite_event = {'id': 1}
status_map = {
    'draft': 'DRAFT',
    'live': 'ACTIVE',
    'completed': 'COMPLETED',
    'started': 'ACTIVE',
    'ended': 'ACTIVE',
    'canceled': 'DELETED',
}


def log_mock():
    def log(self, *args):
        print(*args)

    return MagicMock(side_effect=log)


def get_current_iso_string_mock():
    def get_current_iso_string():
        return sync_desc

    return MagicMock(side_effect=get_current_iso_string)


class SyncOrgVenuesTestSuite(EventTestCase):
    """
    🔽🔽🔽 Without academy
    """
    @patch.object(logging.Logger, 'warn', log_mock())
    @patch.object(logging.Logger, 'error', log_mock())
    @patch.object(actions, 'get_current_iso_string', get_current_iso_string_mock())
    @patch(REQUESTS_PATH['request'],
           apply_requests_request_mock([
               (201, eventbrite_post_url, eventbrite_event),
               (200, eventbrite_put_url, eventbrite_event),
           ]))
    def test_export_event_to_eventbrite__without_academy(self):
        import logging

        organization_kwargs = {'eventbrite_id': '1'}
        model = self.generate_models(organization=True, organization_kwargs=organization_kwargs)

        export_event_to_eventbrite(None, model.organization)

        self.assertEqual(logging.Logger.warn.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list,
                         [call('The organization (1) not have a academy assigned')])

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, 'organization')])
        self.assertEqual(self.all_event_dict(), [])

    """
    🔽🔽🔽 With academy and event with title
    """

    @patch.object(logging.Logger, 'warn', log_mock())
    @patch.object(logging.Logger, 'error', log_mock())
    @patch.object(actions, 'get_current_iso_string', get_current_iso_string_mock())
    @patch(REQUESTS_PATH['request'],
           apply_requests_request_mock([
               (201, eventbrite_post_url, eventbrite_event),
               (200, eventbrite_put_url, eventbrite_event),
           ]))
    def test_export_event_to_eventbrite__with_event(self):
        import logging

        organization_kwargs = {'eventbrite_id': '1'}
        event_kwargs = {'title': 'They killed kenny'}
        model = self.generate_models(academy=True,
                                     event=True,
                                     organization=True,
                                     event_kwargs=event_kwargs,
                                     organization_kwargs=organization_kwargs)

        export_event_to_eventbrite(model.event, model.organization)

        self.assertEqual(logging.Logger.warn.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, 'organization')])
        self.assertEqual(self.all_event_dict(),
                         [{
                             **self.model_to_dict(model, 'event'),
                             'eventbrite_sync_status': 'SYNCHED',
                             'eventbrite_sync_description': '2021-11-23 09:10:58.295264+00:00',
                         }])

    """
    🔽🔽🔽 Check the payload without eventbrite_id
    """

    @patch.object(logging.Logger, 'warn', log_mock())
    @patch.object(logging.Logger, 'error', log_mock())
    @patch.object(actions, 'get_current_iso_string', get_current_iso_string_mock())
    @patch.object(Eventbrite, 'request', MagicMock())
    @patch(REQUESTS_PATH['request'],
           apply_requests_request_mock([
               (201, eventbrite_post_url, eventbrite_event),
               (200, eventbrite_put_url, eventbrite_event),
           ]))
    def test_export_event_to_eventbrite__check_the_payload__without_eventbrite_id(self):
        import logging
        from breathecode.events.utils import Eventbrite

        organization_kwargs = {'eventbrite_id': '1'}
        event_kwargs = {'title': 'They killed kenny'}
        model = self.generate_models(academy=True,
                                     event=True,
                                     organization=True,
                                     event_kwargs=event_kwargs,
                                     organization_kwargs=organization_kwargs)

        export_event_to_eventbrite(model.event, model.organization)

        self.assertEqual(logging.Logger.warn.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(Eventbrite.request.call_args_list, [
            call(
                'POST',
                '/organizations/1/events/',
                data={
                    'event.name.html': 'They killed kenny',
                    'event.description.html': model.event.description,
                    'event.start.utc': self.datetime_to_iso(model.event.starting_at),
                    'event.end.utc': self.datetime_to_iso(model.event.ending_at),
                    'event.summary': model.event.excerpt,
                    'event.capacity': model.event.capacity,
                    'event.online_event': model.event.online_event,
                    'event.url': model.event.eventbrite_url,
                    'event.currency': model.event.currency,
                },
            ),
        ])

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, 'organization')])
        self.assertEqual(self.all_event_dict(),
                         [{
                             **self.model_to_dict(model, 'event'),
                             'eventbrite_sync_status': 'SYNCHED',
                             'eventbrite_sync_description': '2021-11-23 09:10:58.295264+00:00',
                         }])

    """
    🔽🔽🔽 Check the payload with eventbrite_id
    """

    @patch.object(logging.Logger, 'warn', log_mock())
    @patch.object(logging.Logger, 'error', log_mock())
    @patch.object(actions, 'get_current_iso_string', get_current_iso_string_mock())
    @patch.object(Eventbrite, 'request', MagicMock())
    @patch(REQUESTS_PATH['request'],
           apply_requests_request_mock([
               (201, eventbrite_post_url, eventbrite_event),
               (200, eventbrite_put_url, eventbrite_event),
           ]))
    def test_export_event_to_eventbrite__check_the_payload__with_eventbrite_id(self):
        import logging
        from breathecode.events.utils import Eventbrite

        organization_kwargs = {'eventbrite_id': '1'}
        event_kwargs = {'title': 'They killed kenny', 'eventbrite_id': '1'}
        model = self.generate_models(academy=True,
                                     event=True,
                                     organization=True,
                                     event_kwargs=event_kwargs,
                                     organization_kwargs=organization_kwargs)

        export_event_to_eventbrite(model.event, model.organization)

        self.assertEqual(logging.Logger.warn.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(Eventbrite.request.call_args_list, [
            call(
                'PUT',
                '/events/1/',
                data={
                    'event.name.html': 'They killed kenny',
                    'event.description.html': model.event.description,
                    'event.start.utc': self.datetime_to_iso(model.event.starting_at),
                    'event.end.utc': self.datetime_to_iso(model.event.ending_at),
                    'event.summary': model.event.excerpt,
                    'event.capacity': model.event.capacity,
                    'event.online_event': model.event.online_event,
                    'event.url': model.event.eventbrite_url,
                    'event.currency': model.event.currency,
                },
            ),
        ])

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, 'organization')])
        self.assertEqual(self.all_event_dict(),
                         [{
                             **self.model_to_dict(model, 'event'),
                             'eventbrite_sync_status': 'SYNCHED',
                             'eventbrite_sync_description': '2021-11-23 09:10:58.295264+00:00',
                         }])
