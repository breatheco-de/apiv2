import logging
import breathecode.events.actions as actions
from unittest.mock import MagicMock, call, patch
from breathecode.events.utils import Eventbrite
from breathecode.tests.mocks.eventbrite.constants.events import EVENTBRITE_EVENTS
from django.utils import timezone

from breathecode.tests.mocks.requests import REQUESTS_PATH, apply_requests_request_mock
from ..mixins import EventTestCase

export_event_to_eventbrite = actions.export_event_to_eventbrite
sync_desc = '2021-11-23 09:10:58.295264+00:00'
eventbrite_url = 'https://www.eventbriteapi.com/v3/organizations/1/events/'
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
    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(201, eventbrite_url, dict())]))
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
    🔽🔽🔽 With academy and event, can't be synced because is managed by eventbrite
    """

    @patch.object(logging.Logger, 'warn', log_mock())
    @patch.object(logging.Logger, 'error', log_mock())
    @patch.object(actions, 'get_current_iso_string', get_current_iso_string_mock())
    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(201, eventbrite_url, dict())]))
    def test_export_event_to_eventbrite__with_academy(self):
        import logging

        organization_kwargs = {'eventbrite_id': '1'}
        model = self.generate_models(academy=True,
                                     event=True,
                                     organization=True,
                                     organization_kwargs=organization_kwargs)

        export_event_to_eventbrite(model.event, model.organization)

        self.assertEqual(logging.Logger.warn.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [call('The event (1) can\'t be synced')])

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, 'organization')])
        self.assertEqual(self.all_event_dict(), [{
            **self.model_to_dict(model, 'event'),
            'sync_status': 'PENDING',
            'sync_desc': None,
        }])

    """
    🔽🔽🔽 With academy and event with title, can't be synced because is managed by eventbrite
    """

    @patch.object(logging.Logger, 'warn', log_mock())
    @patch.object(logging.Logger, 'error', log_mock())
    @patch.object(actions, 'get_current_iso_string', get_current_iso_string_mock())
    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(201, eventbrite_url, dict())]))
    def test_export_event_to_eventbrite__with_academy__with_event_title(self):
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
        self.assertEqual(logging.Logger.error.call_args_list,
                         [call('The event `They killed kenny` (1) can\'t be synced')])

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, 'organization')])
        self.assertEqual(self.all_event_dict(), [{
            **self.model_to_dict(model, 'event'),
            'sync_status': 'PENDING',
            'sync_desc': None,
        }])

    """
    🔽🔽🔽 With academy and event with title, is managed by breathecode
    """

    @patch.object(logging.Logger, 'warn', log_mock())
    @patch.object(logging.Logger, 'error', log_mock())
    @patch.object(actions, 'get_current_iso_string', get_current_iso_string_mock())
    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(201, eventbrite_url, dict())]))
    def test_export_event_to_eventbrite__with_event_managed_by_breathecode(self):
        import logging

        organization_kwargs = {'eventbrite_id': '1'}
        event_kwargs = {'title': 'They killed kenny', 'managed_by': 'BREATHECODE'}
        model = self.generate_models(academy=True,
                                     event=True,
                                     organization=True,
                                     event_kwargs=event_kwargs,
                                     organization_kwargs=organization_kwargs)

        export_event_to_eventbrite(model.event, model.organization)

        self.assertEqual(logging.Logger.warn.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, 'organization')])
        self.assertEqual(self.all_event_dict(), [{
            **self.model_to_dict(model, 'event'),
            'sync_status': 'SYNCHED',
            'sync_desc': '2021-11-23 09:10:58.295264+00:00',
        }])

    """
    🔽🔽🔽 Check the payload
    """

    @patch.object(logging.Logger, 'warn', log_mock())
    @patch.object(logging.Logger, 'error', log_mock())
    @patch.object(actions, 'get_current_iso_string', get_current_iso_string_mock())
    @patch.object(Eventbrite, 'request', MagicMock())
    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(201, eventbrite_url, dict())]))
    def test_export_event_to_eventbrite__check_the_payload(self):
        import logging
        from breathecode.events.utils import Eventbrite

        organization_kwargs = {'eventbrite_id': '1'}
        event_kwargs = {'title': 'They killed kenny', 'managed_by': 'BREATHECODE'}
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
                    'name': {
                        'html': 'They killed kenny',
                    },
                    'description': {
                        'html': model.event.description,
                    },
                    'start': {
                        'utc': model.event.starting_at.isoformat(),
                    },
                    'end': {
                        'utc': model.event.ending_at.isoformat(),
                    },
                    'summary': model.event.excerpt,
                    'capacity': model.event.capacity,
                    'online_event': model.event.online_event,
                    'url': model.event.eventbrite_url,
                },
            ),
        ])

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, 'organization')])
        self.assertEqual(self.all_event_dict(), [{
            **self.model_to_dict(model, 'event'),
            'sync_status': 'SYNCHED',
            'sync_desc': '2021-11-23 09:10:58.295264+00:00',
        }])
