"""
Test /answer
"""
from datetime import datetime
from unittest.mock import patch
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
    MAILGUN_PATH,
    MAILGUN_INSTANCES,
    apply_requests_post_mock,
    SLACK_PATH,
    SLACK_INSTANCES,
    apply_slack_requests_request_mock,
)
from ..mixins import EventTestCase
from ...actions import sync_org_venues

class SyncOrgVenuesTestSuite(EventTestCase):
    """Test /answer"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_send_survey_without_cohort(self):
        """Test /answer without auth"""
        model = self.generate_models(organization=True)
        
        try:
            sync_org_venues(model['organization'])
        except Exception as e:
            self.assertEquals(str(e), ('The path you requested does not exist.'))

    # TODO: check why it's commented
    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # @patch(MAILGUN_PATH['post'], apply_requests_post_mock())
    # def test_send_survey_wit_one_user_with_two_cohort(self):
    #     """Test /answer without auth"""
    #     model = self.generate_models(cohort_user=True, cohort_user_two=True)
        
    #     try:
    #         send_survey(model['user'])
    #     except Exception as e:
    #         self.assertEquals(str(e), ('Impossible to determine the student cohort, maybe it has '
    #             'more than one, or cero.'))

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # @patch(MAILGUN_PATH['post'], apply_requests_post_mock())
    # def test_send_survey_with_cohort_with_slack_user_with_slack_team(self):
    #     """Test /answer without auth"""
    #     mock_mailgun = MAILGUN_INSTANCES['post']
    #     mock_mailgun.call_args_list = []

    #     mock_slack = SLACK_INSTANCES['request']
    #     mock_slack.call_args_list = []

    #     model = self.generate_models(user=True, cohort_user=True, lang='en', slack_user=True,
    #         slack_team=True)
    #     academy = model['cohort'].academy.name
        
    #     send_survey(model['user'])

    #     expected = [{
    #         'academy_id': 1,
    #         'cohort_id': 1,
    #         'comment': None,
    #         'event_id': None,
    #         'highest': 'very likely',
    #         'id': 1,
    #         'lang': 'en',
    #         'lowest': 'not likely',
    #         'mentor_id': None,
    #         'opened_at': None,
    #         'score': None,
    #         'status': 'SENT',
    #         'title': f'How likely are you to recommend {academy} to your friends and family?',
    #         'token_id': 1,
    #         'user_id': 1,
    #     }]

    #     dicts = [answer for answer in self.all_answer_dict() if isinstance(answer['created_at'],
    #         datetime) and answer.pop('created_at')]
    #     self.assertEqual(dicts, expected)
    #     self.check_email_contain_a_correct_token('en', academy, dicts, mock_mailgun, model)
    #     self.assertEqual(mock_slack.call_args_list, [])

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # @patch(MAILGUN_PATH['post'], apply_requests_post_mock())
    # @patch(SLACK_PATH['request'], apply_slack_requests_request_mock())
    # def test_send_survey_with_cohort_with_slack_user_with_slack_team_with_credentials_slack(self):
    #     """Test /answer without auth"""
    #     mock_mailgun = MAILGUN_INSTANCES['post']
    #     mock_mailgun.call_args_list = []

    #     mock_slack = SLACK_INSTANCES['request']
    #     mock_slack.call_args_list = []

    #     model = self.generate_models(user=True, cohort_user=True, lang='en', slack_user=True,
    #         slack_team=True, credentials_slack=True, academy=True)
    #     academy = model['cohort'].academy.name
        
    #     try:
    #         send_survey(model['user'])
    #     except Exception as e:
    #         self.assertEqual(str(e), f"Team owner not has slack credentials")

    #     expected = [{
    #         'id': 1,
    #         'title': f'How likely are you to recommend {academy} to your friends and family?',
    #         'lowest': 'not likely',
    #         'highest': 'very likely',
    #         'lang': 'en',
    #         'cohort_id': 1,
    #         'academy_id': 1,
    #         'mentor_id': None,
    #         'event_id': None,
    #         'token_id': 1,
    #         'score': None,
    #         'comment': None,
    #         'status': 'PENDING',
    #         'user_id': 1,
    #         'opened_at': None,
    #     }]

    #     dicts = [answer for answer in self.all_answer_dict() if isinstance(answer['created_at'],
    #         datetime) and answer.pop('created_at')]
    #     self.assertEqual(dicts, expected)
    #     self.check_email_contain_a_correct_token('en', academy, dicts, mock_mailgun, model)
    #     self.assertEqual(mock_slack.call_args_list, [])

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # @patch(MAILGUN_PATH['post'], apply_requests_post_mock())
    # @patch(SLACK_PATH['request'], apply_slack_requests_request_mock())
    # def test_send_survey_with_cohort_lang_en(self):
    #     """Test /answer without auth"""
    #     mock_mailgun = MAILGUN_INSTANCES['post']
    #     mock_mailgun.call_args_list = []

    #     mock_slack = SLACK_INSTANCES['request']
    #     mock_slack.call_args_list = []

    #     model = self.generate_models(user=True, cohort_user=True, lang='en', slack_user=True,
    #         slack_team=True, credentials_slack=True, academy=True, slack_team_owner=True)
    #     academy = model['cohort'].academy.name
        
    #     try:
    #         send_survey(model['user'])
    #     except Exception as e:
    #         self.assertEqual(str(e), f"Team owner not has slack credentials")

    #     expected = [{
    #         'id': 1,
    #         'title': f'How likely are you to recommend {academy} to your friends and family?',
    #         'lowest': 'not likely',
    #         'highest': 'very likely',
    #         'lang': 'en',
    #         'cohort_id': 1,
    #         'academy_id': 1,
    #         'mentor_id': None,
    #         'event_id': None,
    #         'token_id': 1,
    #         'score': None,
    #         'comment': None,
    #         'status': 'SENT',
    #         'user_id': 1,
    #         'opened_at': None,
    #     }]

    #     print('asdasd', model['slack_team'].__dict__)
    #     dicts = [answer for answer in self.all_answer_dict() if isinstance(answer['created_at'],
    #         datetime) and answer.pop('created_at')]
    #     self.assertEqual(dicts, expected)
    #     self.check_email_contain_a_correct_token('en', academy, dicts, mock_mailgun, model)
    #     self.check_stack_contain_a_correct_token('en', academy, mock_slack, model)

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # @patch(MAILGUN_PATH['post'], apply_requests_post_mock())
    # @patch(SLACK_PATH['request'], apply_slack_requests_request_mock())
    # def test_send_survey_with_cohort_lang_es(self):
    #     """Test /answer without auth"""
    #     mock_mailgun = MAILGUN_INSTANCES['post']
    #     mock_mailgun.call_args_list = []

    #     mock_slack = SLACK_INSTANCES['request']
    #     mock_slack.call_args_list = []

    #     model = self.generate_models(user=True, cohort_user=True, lang='es', slack_user=True,
    #         slack_team=True, credentials_slack=True, academy=True, slack_team_owner=True)
    #     academy = model['cohort'].academy.name

    #     send_survey(model['user'])
    #     expected = [{
    #         'academy_id': 1,
    #         'cohort_id': 1,
    #         'comment': None,
    #         'event_id': None,
    #         'highest': 'muy probable',
    #         'id': 1,
    #         'lang': 'es',
    #         'lowest': 'no es probable',
    #         'mentor_id': None,
    #         'opened_at': None,
    #         'score': None,
    #         'status': 'SENT',
    #         'title': f'¿Qué tan probable es que recomiendes {academy} a tus amigos y familiares?',
    #         'token_id': 1,
    #         'user_id': 1,
    #     }]

    #     dicts = [answer for answer in self.all_answer_dict() if isinstance(answer['created_at'],
    #         datetime) and answer.pop('created_at')]
    #     self.assertEqual(dicts, expected)
    #     self.assertEqual(self.count_token(), 1)
    #     self.check_email_contain_a_correct_token('es', academy, dicts, mock_mailgun, model)
    #     self.check_stack_contain_a_correct_token('es', academy, mock_slack, model)

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # @patch(MAILGUN_PATH['post'], apply_requests_post_mock())
    # @patch(SLACK_PATH['request'], apply_slack_requests_request_mock())
    # def test_send_survey_with_cohort_resent(self):
    #     """Test /answer without auth"""
    #     mock_mailgun = MAILGUN_INSTANCES['post']
    #     mock_mailgun.call_args_list = []

    #     mock_slack = SLACK_INSTANCES['request']
    #     mock_slack.call_args_list = []

    #     model = self.generate_models(user=True, cohort_user=True, lang='es', slack_user=True,
    #         slack_team=True, credentials_slack=True, academy=True, slack_team_owner=True)
    #     academy = model['cohort'].academy.name

    #     send_survey(model['user'])

    #     mock_mailgun.call_args_list = []
    #     mock_slack.call_args_list = []

    #     print(len(mock_mailgun.call_args_list))
    #     send_survey(model['user'])
    #     print(len(mock_mailgun.call_args_list))
    #     expected = [{
    #         'academy_id': 1,
    #         'cohort_id': 1,
    #         'comment': None,
    #         'event_id': None,
    #         'highest': 'muy probable',
    #         'id': 1,
    #         'lang': 'es',
    #         'lowest': 'no es probable',
    #         'mentor_id': None,
    #         'opened_at': None,
    #         'score': None,
    #         'status': 'SENT',
    #         'title': f'¿Qué tan probable es que recomiendes {academy} a tus amigos y familiares?',
    #         'token_id': 2,
    #         'user_id': 1,
    #     }]

    #     dicts = [answer for answer in self.all_answer_dict() if isinstance(answer['created_at'],
    #         datetime) and answer.pop('created_at')]
    #     self.assertEqual(dicts, expected)
    #     self.assertEqual(self.count_token(), 1)
    #     self.check_email_contain_a_correct_token('es', academy, dicts, mock_mailgun, model)
    #     self.check_stack_contain_a_correct_token('es', academy, mock_slack, model)

