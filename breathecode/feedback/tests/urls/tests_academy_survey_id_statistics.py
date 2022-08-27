"""
Test /academy/survey
"""
import random
from unittest.mock import patch, MagicMock, call
from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from ..mixins import FeedbackTestCase
from ...utils import strings
from ...caches import AnswerCache


class SurveyTestSuite(FeedbackTestCase):
    """Test /academy/survey"""
    """
    🔽🔽🔽 Auth
    """

    def test__get__without_auth(self):
        """Test /academy/survey get without authorization"""
        url = reverse_lazy('feedback:academy_survey_id_statistics', kwargs={'survey_id': 1})
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test__get__without_academy(self):
        """Test /academy/survey get without academy"""
        self.bc.database.create(authenticate=True)
        url = reverse_lazy('feedback:academy_survey_id_statistics', kwargs={'survey_id': 1})
        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET capability
    """

    def test__without_capabilities(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True)
        url = reverse_lazy('feedback:academy_survey_id_statistics', kwargs={'survey_id': 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: read_survey for academy 1",
            'status_code': 403,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 GET without Survey
    """

    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    def test__without_survey(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_survey',
                                     role=1)

        url = reverse_lazy('feedback:academy_survey_id_statistics', kwargs={'survey_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = {'detail': 'not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [])
        self.assertEqual(self.bc.database.list_of('feedback.Answer'), [])

    """
    🔽🔽🔽 GET with one Survey
    """

    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    def test__with_survey(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_survey',
                                     role=1,
                                     survey=1)

        url = reverse_lazy('feedback:academy_survey_id_statistics', kwargs={'survey_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = {
            'scores': {
                'academy': None,
                'cohort': None,
                'mentors': [],
                'total': None
            },
            'response_rate': None,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [
            self.bc.format.to_dict(model.survey),
        ])
        self.assertEqual(self.bc.database.list_of('feedback.Answer'), [])

    """
    🔽🔽🔽 GET with one Survey and many Answer with bad statuses
    """

    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    def test__with_survey__answers_with_bad_statuses(self):
        self.headers(academy=1)

        statuses = ['PENDING', 'SENT', 'OPENED', 'EXPIRED']
        answers = [{'status': s} for s in statuses]
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_survey',
                                     role=1,
                                     survey=1,
                                     answer=answers)

        url = reverse_lazy('feedback:academy_survey_id_statistics', kwargs={'survey_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = {
            'scores': {
                'academy': None,
                'cohort': None,
                'mentors': [],
                'total': None
            },
            'response_rate': None,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [
            self.bc.format.to_dict(model.survey),
        ])
        self.assertEqual(
            self.bc.database.list_of('feedback.Answer'),
            self.bc.format.to_dict(model.answer),
        )

    """
    🔽🔽🔽 GET with one Survey and many Answer with right status, score not set
    """

    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    def test__with_survey__answers_with_right_status__score_not_set(self):
        self.headers(academy=1)

        answers = [{'status': 'ANSWERED'} for _ in range(0, 2)]
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_survey',
                                     role=1,
                                     survey=1,
                                     answer=answers)

        url = reverse_lazy('feedback:academy_survey_id_statistics', kwargs={'survey_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = {
            'scores': {
                'academy': None,
                'cohort': None,
                'mentors': [],
                'total': None
            },
            'response_rate': None,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [
            self.bc.format.to_dict(model.survey),
        ])
        self.assertEqual(
            self.bc.database.list_of('feedback.Answer'),
            self.bc.format.to_dict(model.answer),
        )

    """
    🔽🔽🔽 GET with one Survey and many Answer with right status, score set
    """

    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    def test__with_survey__answers_with_right_status__score_set(self):
        self.headers(academy=1)

        size_of_academy_answers = random.randint(2, 5)
        size_of_cohort_answers = random.randint(2, 5)
        size_of_mentor1_answers = random.randint(2, 5)
        size_of_mentor2_answers = random.randint(2, 5)
        size_of_answers = (size_of_academy_answers + size_of_cohort_answers + size_of_mentor1_answers +
                           size_of_mentor2_answers)

        academy_answers = [{
            'status': 'ANSWERED',
            'score': random.randint(1, 11),
            'title': strings['en']['academy']['title'].format('asd'),
        } for _ in range(0, size_of_academy_answers)]

        cohort_answers = [{
            'status': 'ANSWERED',
            'score': random.randint(1, 11),
            'title': strings['en']['cohort']['title'].format('asd'),
        } for _ in range(0, size_of_cohort_answers)]

        mentor1_answers = [{
            'status': 'ANSWERED',
            'score': random.randint(1, 11),
            'title': strings['en']['mentor']['title'].format('asd1'),
        } for _ in range(0, size_of_mentor1_answers)]

        mentor2_answers = [{
            'status': 'ANSWERED',
            'score': random.randint(1, 11),
            'title': strings['en']['mentor']['title'].format('asd2'),
        } for _ in range(0, size_of_mentor2_answers)]

        answers = academy_answers + cohort_answers + mentor1_answers + mentor2_answers

        survey = {'response_rate': random.randint(1, 101)}
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_survey',
                                     role=1,
                                     survey=survey,
                                     answer=answers)

        url = reverse_lazy('feedback:academy_survey_id_statistics', kwargs={'survey_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = {
            'scores': {
                'academy':
                sum([x['score'] for x in academy_answers]) / size_of_academy_answers,
                'cohort':
                sum([x['score'] for x in cohort_answers]) / size_of_cohort_answers,
                'mentors': [
                    {
                        'name': 'asd1',
                        'score': sum([x['score'] for x in mentor1_answers]) / size_of_mentor1_answers,
                    },
                    {
                        'name': 'asd2',
                        'score': sum([x['score'] for x in mentor2_answers]) / size_of_mentor2_answers,
                    },
                ],
                'total':
                sum([x.score for x in model.answer]) / size_of_answers,
            },
            'response_rate': model.survey.response_rate,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [
            {
                **self.bc.format.to_dict(model.survey),
                'response_rate': model.survey.response_rate,
            },
        ])
        self.assertEqual(
            self.bc.database.list_of('feedback.Answer'),
            self.bc.format.to_dict(model.answer),
        )

    """
    🔽🔽🔽 Spy extensions
    """

    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    @patch.object(APIViewExtensionHandlers, '_spy_extensions', MagicMock())
    @patch.object(APIViewExtensionHandlers, '_spy_extension_arguments', MagicMock())
    def test__with_survey(self):
        self.headers(academy=1)
        self.generate_models(authenticate=True,
                             profile_academy=True,
                             capability='read_survey',
                             role=1,
                             survey=1)

        url = reverse_lazy('feedback:academy_survey_id_statistics', kwargs={'survey_id': 1})
        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extensions.call_args_list, [
            call(['CacheExtension']),
        ])

        self.assertEqual(APIViewExtensionHandlers._spy_extension_arguments.call_args_list, [
            call(cache=AnswerCache),
        ])
