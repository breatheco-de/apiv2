"""
Test /answer/:id
"""
import os
from unittest.mock import MagicMock, call, patch
from breathecode.marketing.tasks import add_cohort_task_to_student
from breathecode.tests.mocks import apply_requests_request_mock
from breathecode.tests.mocks.requests import apply_requests_post_mock
from ..mixins import MarketingTestCase

GOOGLE_CLOUD_KEY = os.getenv('GOOGLE_CLOUD_KEY', None)
AC_HOST = 'https://ac.ca'
AC_URL = f'{AC_HOST}/api/3/contacts'
AC_POST_URL = f'{AC_HOST}/api/3/contactTags'
AC_RESPONSE = {
    'contacts': [
        {
            'id': 1,
            'tag': 'they-killed-kenny',
        },
    ]
}
AC_EMPTY_RESPONSE = {'contacts': []}
AC_POST_RESPONSE = {'contactTag': {}}
TASK_STARTED_MESSAGE = 'Task add_cohort_task_to_student started'


class AnswerIdTestSuite(MarketingTestCase):
    """
    🔽🔽🔽 Without Academy
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('requests.get', apply_requests_request_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch('requests.post', apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    def test_add_cohort_task_to_student__without_academy(self):
        import logging

        add_cohort_task_to_student.delay(1, 1, 1)

        self.assertEqual(logging.Logger.warn.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(logging.Logger.error.call_args_list, [call('Academy 1 not found')])

    """
    🔽🔽🔽 Without ActiveCampaignAcademy
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('requests.get', apply_requests_request_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch('requests.post', apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    def test_add_cohort_task_to_student__without_active_campaign_academy(self):
        import logging

        model = self.generate_models(academy=True)

        add_cohort_task_to_student.delay(1, 1, 1)

        self.assertEqual(logging.Logger.warn.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(logging.Logger.error.call_args_list, [call('ActiveCampaign Academy 1 not found')])

    """
    🔽🔽🔽 Without User
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('requests.get', apply_requests_request_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch('requests.post', apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    def test_add_cohort_task_to_student__without_user(self):
        import logging

        active_campaign_academy_kwargs = {'ac_url': AC_HOST}
        model = self.generate_models(academy=True,
                                     skip_cohort=True,
                                     active_campaign_academy=True,
                                     active_campaign_academy_kwargs=active_campaign_academy_kwargs)

        add_cohort_task_to_student.delay(1, 1, 1)

        self.assertEqual(logging.Logger.warn.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(logging.Logger.error.call_args_list, [call('User 1 not found')])

    """
    🔽🔽🔽 Without Cohort
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('requests.get', apply_requests_request_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch('requests.post', apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    def test_add_cohort_task_to_student__without_cohort(self):
        import logging

        active_campaign_academy_kwargs = {'ac_url': AC_HOST}
        model = self.generate_models(academy=True,
                                     skip_cohort=True,
                                     user=True,
                                     active_campaign_academy=True,
                                     active_campaign_academy_kwargs=active_campaign_academy_kwargs)

        add_cohort_task_to_student.delay(1, 1, 1)

        self.assertEqual(logging.Logger.warn.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(logging.Logger.error.call_args_list, [call('Cohort 1 not found')])

    """
    🔽🔽🔽 Tag not exists
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('requests.get', apply_requests_request_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch('requests.post', apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    def test_add_cohort_task_to_student(self):
        import logging

        active_campaign_academy_kwargs = {'ac_url': AC_HOST}
        with patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock()):
            model = self.generate_models(academy=True,
                                         cohort=1,
                                         user=True,
                                         active_campaign_academy=True,
                                         active_campaign_academy_kwargs=active_campaign_academy_kwargs)

        add_cohort_task_to_student.delay(1, 1, 1)

        self.assertEqual(logging.Logger.warn.call_args_list, [
            call(TASK_STARTED_MESSAGE),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [
            call(
                f'Cohort tag `{model.cohort.slug}` does not exist in the system, the tag could not be added to the '
                'student. This tag was supposed to be created by the system when creating a new cohort'),
        ])

    """
    🔽🔽🔽 Tag already exists in active campaign
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('requests.get', apply_requests_request_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch('requests.post', apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    def test_add_cohort_task_to_student__tag_exists(self):
        import logging

        active_campaign_academy_kwargs = {'ac_url': AC_HOST}
        tag_kwargs = {'slug': 'they-killed-kenny'}
        cohort_kwargs = {'slug': 'they-killed-kenny'}

        with patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock()):
            model = self.generate_models(tag=True,
                                         user=True,
                                         academy=True,
                                         active_campaign_academy=True,
                                         active_campaign_academy_kwargs=active_campaign_academy_kwargs,
                                         tag_kwargs=tag_kwargs,
                                         cohort=cohort_kwargs)

        add_cohort_task_to_student.delay(1, 1, 1)

        self.assertEqual(self.bc.database.list_of('marketing.Tag'), [self.model_to_dict(model, 'tag')])
        self.assertEqual(logging.Logger.warn.call_args_list, [
            call(TASK_STARTED_MESSAGE),
            call('Adding tag 1 to acp contact 1'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [])

    """
    🔽🔽🔽 Tag already exists in active campaign and return status 404 in post method
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('requests.get', apply_requests_request_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch('requests.post', apply_requests_post_mock([(404, AC_POST_URL, AC_POST_RESPONSE)]))
    def test_add_cohort_task_to_student__tag_exists__active_campaign_returns_404(self):
        import logging

        active_campaign_academy_kwargs = {'ac_url': AC_HOST}
        tag_kwargs = {'slug': 'they-killed-kenny'}
        cohort_kwargs = {'slug': 'they-killed-kenny'}

        with patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock()):
            model = self.generate_models(tag=True,
                                         user=True,
                                         academy=True,
                                         active_campaign_academy=True,
                                         active_campaign_academy_kwargs=active_campaign_academy_kwargs,
                                         tag_kwargs=tag_kwargs,
                                         cohort=cohort_kwargs)

        add_cohort_task_to_student.delay(1, 1, 1)

        self.assertEqual(self.bc.database.list_of('marketing.Tag'), [self.model_to_dict(model, 'tag')])
        self.assertEqual(logging.Logger.warn.call_args_list, [
            call(TASK_STARTED_MESSAGE),
            call('Adding tag 1 to acp contact 1'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [
            call(AC_POST_RESPONSE),
            call('Failed to add tag to contact 1 with status=404'),
        ])

    """
    🔽🔽🔽 Tag already exists in active campaign and return status 201 but the api was changed
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('requests.get', apply_requests_request_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch('requests.post', apply_requests_post_mock([(201, AC_POST_URL, {})]))
    def test_add_cohort_task_to_student__tag_exists__the_api_was_changed(self):
        import logging

        active_campaign_academy_kwargs = {'ac_url': AC_HOST}
        tag_kwargs = {'slug': 'they-killed-kenny'}
        cohort_kwargs = {'slug': 'they-killed-kenny'}

        with patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock()):
            model = self.generate_models(tag=True,
                                         user=True,
                                         academy=True,
                                         active_campaign_academy=True,
                                         active_campaign_academy_kwargs=active_campaign_academy_kwargs,
                                         tag_kwargs=tag_kwargs,
                                         cohort=cohort_kwargs)

        add_cohort_task_to_student.delay(1, 1, 1)

        self.assertEqual(self.bc.database.list_of('marketing.Tag'), [self.model_to_dict(model, 'tag')])
        self.assertEqual(logging.Logger.warn.call_args_list, [
            call(TASK_STARTED_MESSAGE),
            call('Adding tag 1 to acp contact 1'),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [
            call('Bad response format from ActiveCampaign when adding a new tag to contact'),
        ])

    """
    🔽🔽🔽 Active campaign return a empty list of contacts
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('requests.get', apply_requests_request_mock([(200, AC_URL, AC_EMPTY_RESPONSE)]))
    def test_add_cohort_task_to_student__status_404(self):
        import logging

        active_campaign_academy_kwargs = {'ac_url': AC_HOST}
        tag_kwargs = {'slug': 'they-killed-kenny'}
        cohort_kwargs = {'slug': 'they-killed-kenny'}
        with patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock()):
            model = self.generate_models(academy=True,
                                         tag=True,
                                         user=True,
                                         active_campaign_academy=True,
                                         active_campaign_academy_kwargs=active_campaign_academy_kwargs,
                                         tag_kwargs=tag_kwargs,
                                         cohort=cohort_kwargs)

        add_cohort_task_to_student.delay(1, 1, 1)

        self.assertEqual(logging.Logger.warn.call_args_list, [
            call(TASK_STARTED_MESSAGE),
        ])
        self.assertEqual(logging.Logger.error.call_args_list, [
            call(f'Problem fetching contact in activecampaign with email {model.user.email}'),
        ])
