"""
Test /answer/:id
"""
import os
from unittest.mock import MagicMock, call, patch
from breathecode.marketing.tasks import add_downloadable_slug_as_acp_tag
from breathecode.tests.mocks import apply_requests_request_mock
from ..mixins import MarketingTestCase

GOOGLE_CLOUD_KEY = os.getenv('GOOGLE_CLOUD_KEY', None)
AC_HOST = 'https://ac.ca'
AC_URL = f'{AC_HOST}/api/3/tags'
AC_RESPONSE = {
    'tag': {
        'id': 1,
        'tag': 'event-they-killed-kenny',
    },
}
AC_ERROR_RESPONSE = {
    'message': 'they-killed-kenny',
}
TASK_STARTED_MESSAGE = 'Task add_downloadable_slug_as_acp_tag started'


class AnswerIdTestSuite(MarketingTestCase):
    """
    🔽🔽🔽 Create a Tag in active campaign
    """
    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.events.signals.event_saved.send', MagicMock())
    @patch('requests.post', apply_requests_request_mock([(201, AC_URL, AC_RESPONSE)]))
    def test_add_event_slug_as_acp_tag(self):
        import logging

        active_campaign_academy_kwargs = {'ac_url': AC_HOST}
        model = self.generate_models(academy=True,
                                     downloadable=True,
                                     active_campaign_academy=True,
                                     active_campaign_academy_kwargs=active_campaign_academy_kwargs)

        add_downloadable_slug_as_acp_tag.delay(1, 1)
        self.assertEqual(self.all_tag_dict(), [{
            'ac_academy_id': 1,
            'acp_id': 1,
            'automation_id': None,
            'id': 1,
            'slug': 'they-killed-kenny',
            'subscribers': 0,
            'tag_type': 'DOWNLOADABLE',
        }])

        self.assertEqual(logging.Logger.warn.call_args_list, [
            call(TASK_STARTED_MESSAGE),
            call(f'Creating tag `{model.downloadable.slug}` on active campaign'),
            call('Tag created successfully'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [])
