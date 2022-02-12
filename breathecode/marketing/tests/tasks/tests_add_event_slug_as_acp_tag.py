"""
Test /answer/:id
"""
import os
from unittest.mock import MagicMock, call, patch
from breathecode.marketing.tasks import add_event_slug_as_acp_tag
from breathecode.tests.mocks import apply_requests_request_mock
from ..mixins import MarketingTestCase

GOOGLE_CLOUD_KEY = os.getenv('GOOGLE_CLOUD_KEY', None)
AC_HOST = 'https://ac.ca'
AC_URL = f'{AC_HOST}/api/3/tags'
AC_RESPONSE = {
    'tag': {
        'id': 1,
        'tag_type': 'EVENT',
        'slug': 'event-they-killed-kenny',
    },
}
AC_ERROR_RESPONSE = {
    'message': 'they-killed-kenny',
}
TASK_STARTED_MESSAGE = 'Task add_event_slug_as_acp_tag started'


class AnswerIdTestSuite(MarketingTestCase):
    """
    🔽🔽🔽 Without Academy
    """
    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.events.signals.event_saved.send', MagicMock())
    @patch('requests.post', apply_requests_request_mock([(201, AC_URL, AC_RESPONSE)]))
    def test_add_event_slug_as_acp_tag__without_academy(self):
        import logging

        add_event_slug_as_acp_tag.delay(1, 1)

        self.assertEqual(self.bc.database.list_of('marketing.Tag'), [])
        self.assertEqual(logging.Logger.warn.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(logging.Logger.error.call_args_list, [call('Academy 1 not found')])

    """
    🔽🔽🔽 Without ActiveCampaignAcademy
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.events.signals.event_saved.send', MagicMock())
    @patch('requests.post', apply_requests_request_mock([(201, AC_URL, AC_RESPONSE)]))
    def test_add_event_slug_as_acp_tag__without_active_campaign_academy(self):
        import logging

        model = self.bc.database.create(academy=1)

        add_event_slug_as_acp_tag.delay(1, 1)

        self.assertEqual(self.bc.database.list_of('marketing.Tag'), [])

        self.assertEqual(logging.Logger.warn.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(logging.Logger.error.call_args_list, [call('ActiveCampaign Academy 1 not found')])

    """
    🔽🔽🔽 Without Event
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.events.signals.event_saved.send', MagicMock())
    @patch('requests.post', apply_requests_request_mock([(201, AC_URL, AC_RESPONSE)]))
    def test_add_event_slug_as_acp_tag__without_event(self):
        import logging

        active_campaign_academy = {'ac_url': AC_HOST}
        model = self.bc.database.create(academy=1, active_campaign_academy=active_campaign_academy)

        add_event_slug_as_acp_tag.delay(1, 1)

        self.assertEqual(self.bc.database.list_of('marketing.Tag'), [])

        self.assertEqual(logging.Logger.warn.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(logging.Logger.error.call_args_list, [call('Event 1 not found')])

    """
    🔽🔽🔽 Event without slug
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.events.signals.event_saved.send', MagicMock())
    @patch('requests.post', apply_requests_request_mock([(201, AC_URL, AC_RESPONSE)]))
    def test_add_event_slug_as_acp_tag__event_without_slug(self):
        import logging

        active_campaign_academy = {'ac_url': AC_HOST}
        model = self.bc.database.create(academy=1, event=1, active_campaign_academy=active_campaign_academy)

        add_event_slug_as_acp_tag.delay(1, 1)

        self.assertEqual(self.bc.database.list_of('marketing.Tag'), [])

        self.assertEqual(logging.Logger.warn.call_args_list, [
            call(TASK_STARTED_MESSAGE),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [call('Event 1 does not have slug')])

    """
    🔽🔽🔽 Event slug already exists
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.events.signals.event_saved.send', MagicMock())
    @patch('requests.post', apply_requests_request_mock([(201, AC_URL, AC_RESPONSE)]))
    def test_add_event_slug_as_acp_tag__event_slug_already_exists(self):
        import logging

        active_campaign_academy = {'ac_url': AC_HOST}
        event = {'slug': 'event-they-killed-kenny'}
        tag = {'slug': 'event-they-killed-kenny', 'tag_type': 'EVENT'}

        model = self.bc.database.create(academy=1,
                                        tag=tag,
                                        active_campaign_academy=active_campaign_academy,
                                        event=event)

        add_event_slug_as_acp_tag.delay(1, 1)

        self.assertEqual(self.bc.database.list_of('marketing.Tag'), [self.bc.format.to_dict(model.tag)])
        self.assertEqual(logging.Logger.error.call_args_list, [
            call('Tag for event `event-they-killed-kenny` already exists'),
        ])

    """
    🔽🔽🔽 Create tag in Active Campaign
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.events.signals.event_saved.send', MagicMock())
    @patch('requests.post', apply_requests_request_mock([(201, AC_URL, AC_RESPONSE)]))
    def test_add_event_slug_as_acp_tag(self):
        import logging

        active_campaign_academy = {'ac_url': AC_HOST}
        event = {'slug': 'event-they-killed-kenny'}

        model = self.bc.database.create(academy=1,
                                        active_campaign_academy=active_campaign_academy,
                                        event=event)

        add_event_slug_as_acp_tag.delay(1, 1)

        self.assertEqual(self.bc.database.list_of('marketing.Tag'), [{
            'ac_academy_id': 1,
            'acp_id': 1,
            'automation_id': None,
            'disputed_at': None,
            'disputed_reason': None,
            'id': 1,
            'slug': 'event-they-killed-kenny',
            'subscribers': 0,
            'tag_type': 'EVENT',
        }])

        self.assertEqual(logging.Logger.warn.call_args_list, [
            call(TASK_STARTED_MESSAGE),
            call(f'Creating tag `{model.event.slug}` on active campaign'),
            call('Tag created successfully'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [])

    """
    🔽🔽🔽 Active campaign return 404 (check cases status code are not equal to 201)
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.events.signals.event_saved.send', MagicMock())
    @patch('requests.post', apply_requests_request_mock([(404, AC_URL, AC_ERROR_RESPONSE)]))
    def test_add_event_slug_as_acp_tag__status_404(self):
        import logging

        active_campaign_academy = {'ac_url': AC_HOST}
        event = {'slug': 'event-they-killed-kenny'}
        model = self.bc.database.create(academy=1,
                                        event=event,
                                        active_campaign_academy=active_campaign_academy)

        add_event_slug_as_acp_tag.delay(1, 1)

        self.assertEqual(self.bc.database.list_of('marketing.Tag'), [])

        self.assertEqual(logging.Logger.warn.call_args_list, [
            call(TASK_STARTED_MESSAGE),
            call(f'Creating tag `{model.event.slug}` on active campaign'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [
            call(f'Error creating tag `{model.event.slug}` with status=404'),
            call(AC_ERROR_RESPONSE),
        ])
