"""
Test /academy/survey
"""
import random
from unittest.mock import patch, MagicMock, call
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.feedback.actions import calculate_survey_scores

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from breathecode.utils.validation_exception import ValidationException
from ..mixins import FeedbackTestCase
from ...utils import strings
from ...caches import AnswerCache

calculate_survey_scores


class SurveyTestSuite(FeedbackTestCase):
    """Test /academy/survey"""
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

        with self.assertRaisesMessage(ValidationException, 'not-found'):
            calculate_survey_scores(1)

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

        json = calculate_survey_scores(1)
        expected = {'academy': None, 'cohort': None, 'mentors': [], 'total': None}

        self.assertEqual(json, expected)
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

        json = calculate_survey_scores(1)
        expected = {'academy': None, 'cohort': None, 'mentors': [], 'total': None}

        self.assertEqual(json, expected)
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

        json = calculate_survey_scores(1)
        expected = {'academy': None, 'cohort': None, 'mentors': [], 'total': None}

        self.assertEqual(json, expected)
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

        json = calculate_survey_scores(1)
        expected = {
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
        }

        self.assertEqual(json, expected)
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
