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
        'tag': 'they-killed-kenny',
    },
}
AC_ERROR_RESPONSE = {
    'message': 'they-killed-kenny',
}
TASK_STARTED_MESSAGE = 'Task add_downloadable_slug_as_acp_tag started'


class AnswerIdTestSuite(MarketingTestCase):
    """
    🔽🔽🔽 Without Academy
    """
    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    @patch('requests.post', apply_requests_request_mock([(201, AC_URL, AC_RESPONSE)]))
    def test_add_downloadable_slug_as_acp_tag__without_academy(self):
        import logging

        add_downloadable_slug_as_acp_tag.delay(1, 1)

        self.assertEqual(self.all_tag_dict(), [])
        self.assertEqual(logging.Logger.warn.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(logging.Logger.error.call_args_list, [call('Academy 1 not found')])

    """
    🔽🔽🔽 Without ActiveCampaignAcademy
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    @patch('requests.post', apply_requests_request_mock([(201, AC_URL, AC_RESPONSE)]))
    def test_add_downloadable_slug_as_acp_tag__without_active_campaign_academy(self):
        import logging

        model = self.generate_models(academy=True)

        add_downloadable_slug_as_acp_tag.delay(1, 1)

        self.assertEqual(self.all_tag_dict(), [])

        self.assertEqual(logging.Logger.warn.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(logging.Logger.error.call_args_list, [call('ActiveCampaign Academy 1 not found')])

    """
    🔽🔽🔽 Without Downloadable
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    @patch('requests.post', apply_requests_request_mock([(201, AC_URL, AC_RESPONSE)]))
    def test_add_downloadable_slug_as_acp_tag__without_event(self):
        import logging

        active_campaign_academy_kwargs = {'ac_url': AC_HOST}
        model = self.generate_models(academy=True,
                                     active_campaign_academy=True,
                                     active_campaign_academy_kwargs=active_campaign_academy_kwargs)

        add_downloadable_slug_as_acp_tag.delay(1, 1)

        self.assertEqual(self.all_tag_dict(), [])

        self.assertEqual(logging.Logger.warn.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(logging.Logger.error.call_args_list, [call('Downloadable 1 not found')])

    """
    🔽🔽🔽 Create a Tag in active campaign
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    @patch('requests.post', apply_requests_request_mock([(201, AC_URL, AC_RESPONSE)]))
    def test_add_downloadable_slug_as_acp_tag(self):
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

    """
    🔽🔽🔽 Tag already exists in active campaign
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    @patch('requests.post', apply_requests_request_mock([(201, AC_URL, AC_RESPONSE)]))
    def test_add_event_slug_as_acp_tag__tag_exists(self):
        import logging

        active_campaign_academy_kwargs = {'ac_url': AC_HOST}
        tag_kwargs = {'slug': 'they-killed-kenny', 'tag_type': 'DOWNLOADABLE'}
        downloadable_kwargs = {
            'slug': 'they-killed-kenny',
            'name': 'they-killed-kenny',
        }

        model = self.generate_models(tag=True,
                                     academy=True,
                                     active_campaign_academy=True,
                                     active_campaign_academy_kwargs=active_campaign_academy_kwargs,
                                     tag_kwargs=tag_kwargs,
                                     downloadable_kwargs=downloadable_kwargs)

        add_downloadable_slug_as_acp_tag.delay(1, 1)

        self.assertEqual(self.all_tag_dict(), [self.model_to_dict(model, 'tag')])

        self.assertEqual(logging.Logger.warn.call_args_list, [
            call(TASK_STARTED_MESSAGE),
            call(f'Tag for downloadable `{model.downloadable.slug}` already exists'),
        ])

        self.assertEqual(logging.Logger.error.call_args_list, [])
