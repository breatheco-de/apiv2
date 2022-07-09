"""
Test /answer/:id
"""
import os
from unittest.mock import MagicMock, call, patch
from breathecode.marketing.tasks import add_cohort_slug_as_acp_tag
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
TASK_STARTED_MESSAGE = 'Task add_cohort_slug_as_acp_tag started'


class AnswerIdTestSuite(MarketingTestCase):
    """
    🔽🔽🔽 Without Academy
    """
    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    @patch('requests.post', apply_requests_request_mock([(201, AC_URL, AC_RESPONSE)]))
    def test_add_cohort_slug_as_acp_tag__without_academy(self):
        import logging

        add_cohort_slug_as_acp_tag.delay(1, 1)

        self.assertEqual(self.bc.database.list_of('marketing.Tag'), [])
        self.assertEqual(logging.Logger.warn.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(logging.Logger.error.call_args_list, [call('Academy 1 not found')])

    """
    🔽🔽🔽 Without ActiveCampaignAcademy
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    @patch('requests.post', apply_requests_request_mock([(201, AC_URL, AC_RESPONSE)]))
    def test_add_cohort_slug_as_acp_tag__without_active_campaign_academy(self):
        import logging

        model = self.generate_models(academy=True)

        add_cohort_slug_as_acp_tag.delay(1, 1)

        self.assertEqual(self.bc.database.list_of('marketing.Tag'), [])

        self.assertEqual(logging.Logger.warn.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(logging.Logger.error.call_args_list, [call('ActiveCampaign Academy 1 not found')])

    """
    🔽🔽🔽 Without Cohort
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    @patch('requests.post', apply_requests_request_mock([(201, AC_URL, AC_RESPONSE)]))
    def test_add_cohort_slug_as_acp_tag__without_cohort(self):
        import logging

        active_campaign_academy_kwargs = {'ac_url': AC_HOST}
        model = self.generate_models(academy=True,
                                     skip_cohort=True,
                                     active_campaign_academy=True,
                                     active_campaign_academy_kwargs=active_campaign_academy_kwargs)

        add_cohort_slug_as_acp_tag.delay(1, 1)

        self.assertEqual(self.bc.database.list_of('marketing.Tag'), [])

        self.assertEqual(logging.Logger.warn.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(logging.Logger.error.call_args_list, [call('Cohort 1 not found')])

    """
    🔽🔽🔽 Create a Tag in active campaign
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    @patch('requests.post', apply_requests_request_mock([(201, AC_URL, AC_RESPONSE)]))
    def test_add_cohort_slug_as_acp_tag(self):
        import logging

        active_campaign_academy_kwargs = {'ac_url': AC_HOST}
        model = self.generate_models(academy=True,
                                     active_campaign_academy=True,
                                     active_campaign_academy_kwargs=active_campaign_academy_kwargs)

        add_cohort_slug_as_acp_tag.delay(1, 1)
        self.assertEqual(self.bc.database.list_of('marketing.Tag'), [{
            'ac_academy_id': 1,
            'acp_id': 1,
            'automation_id': None,
            'id': 1,
            'slug': 'they-killed-kenny',
            'subscribers': 0,
            'tag_type': 'COHORT',
            'disputed_at': None,
            'description': None,
            'disputed_reason': None,
        }])

        self.assertEqual(logging.Logger.warn.call_args_list, [
            call(TASK_STARTED_MESSAGE),
            call(f'Creating tag `{model.cohort.slug}` on active campaign'),
            call('Tag created successfully'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [])

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    @patch('requests.post', apply_requests_request_mock([(201, AC_URL, AC_RESPONSE)]))
    def test_add_cohort_slug_as_acp_tag_type_cohort(self):
        import logging

        active_campaign_academy_kwargs = {'ac_url': AC_HOST}
        model = self.generate_models(academy=True,
                                     active_campaign_academy=True,
                                     active_campaign_academy_kwargs=active_campaign_academy_kwargs)

        add_cohort_slug_as_acp_tag.delay(1, 1)
        self.assertEqual(self.bc.database.list_of('marketing.Tag')[0]['tag_type'], 'COHORT')

        self.assertEqual(logging.Logger.warn.call_args_list, [
            call(TASK_STARTED_MESSAGE),
            call(f'Creating tag `{model.cohort.slug}` on active campaign'),
            call('Tag created successfully'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [])

    """
    🔽🔽🔽 Tag already exists in active campaign
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    @patch('requests.post', apply_requests_request_mock([(201, AC_URL, AC_RESPONSE)]))
    def test_add_cohort_slug_as_acp_tag__tag_exists(self):
        import logging

        active_campaign_academy_kwargs = {'ac_url': AC_HOST}
        tag_kwargs = {'slug': 'they-killed-kenny'}
        cohort_kwargs = {'slug': 'they-killed-kenny'}

        model = self.generate_models(tag=True,
                                     academy=True,
                                     active_campaign_academy=True,
                                     active_campaign_academy_kwargs=active_campaign_academy_kwargs,
                                     tag_kwargs=tag_kwargs,
                                     cohort_kwargs=cohort_kwargs)

        add_cohort_slug_as_acp_tag.delay(1, 1)

        self.assertEqual(self.bc.database.list_of('marketing.Tag'), [self.model_to_dict(model, 'tag')])

        self.assertEqual(logging.Logger.warn.call_args_list, [
            call(TASK_STARTED_MESSAGE),
            call(f'Tag for cohort `{model.cohort.slug}` already exists'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [])

    """
    🔽🔽🔽 Active campaign return 404 (check cases status code are not equal to 201)
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    @patch('requests.post', apply_requests_request_mock([(404, AC_URL, AC_ERROR_RESPONSE)]))
    def test_add_cohort_slug_as_acp_tag__status_404(self):
        import logging

        active_campaign_academy_kwargs = {'ac_url': AC_HOST}
        model = self.generate_models(academy=True,
                                     active_campaign_academy=True,
                                     active_campaign_academy_kwargs=active_campaign_academy_kwargs)

        add_cohort_slug_as_acp_tag.delay(1, 1)

        self.assertEqual(self.bc.database.list_of('marketing.Tag'), [])

        self.assertEqual(logging.Logger.warn.call_args_list, [
            call(TASK_STARTED_MESSAGE),
            call(f'Creating tag `{model.cohort.slug}` on active campaign'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [
            call(f'Error creating tag `{model.cohort.slug}` with status=404'),
            call(AC_ERROR_RESPONSE),
            call('exception-creating-tag-in-acp', exc_info=True),
        ])
