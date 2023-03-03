import logging
import random
from unittest.mock import patch, MagicMock, call

from breathecode.tests.mixins.breathecode_mixin.breathecode import fake
from breathecode.feedback.tasks import recalculate_survey_scores
from ..mixins import FeedbackTestCase
from ... import actions

RESPONSE_RATE = random.random() * 100
TOTAL = random.random() * 10
ACADEMY = random.random() * 10
COHORT = random.random() * 10
MENTOR1 = random.random() * 10
MENTOR1_NAME = fake.name()
MENTOR2 = random.random() * 10
MENTOR2_NAME = fake.name()


def get_scores():

    return {
        'total': TOTAL,
        'academy': ACADEMY,
        'cohort': COHORT,
        'mentors': [
            {
                'name': MENTOR1_NAME,
                'score': MENTOR1,
            },
            {
                'name': MENTOR2_NAME,
                'score': MENTOR2,
            },
        ],
    }


class SurveyAnsweredTestSuite(FeedbackTestCase):
    """
    🔽🔽🔽 With 0 Survey
    """

    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    @patch('breathecode.feedback.actions.calculate_survey_scores', MagicMock(return_value=get_scores()))
    @patch('breathecode.feedback.actions.calculate_survey_response_rate',
           MagicMock(return_value=RESPONSE_RATE))
    def test_with_zero_surveys(self):
        recalculate_survey_scores.delay(1)

        self.assertEqual(logging.Logger.debug.call_args_list, [call('Starting recalculate_survey_score')])
        self.assertEqual(logging.Logger.error.call_args_list, [call('Survey not found')])
        self.assertEqual(actions.calculate_survey_scores.call_args_list, [])
        self.assertEqual(actions.calculate_survey_response_rate.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [])

    """
    🔽🔽🔽 With 1 Survey
    """

    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    @patch('breathecode.feedback.actions.calculate_survey_scores', MagicMock(return_value=get_scores()))
    @patch('breathecode.feedback.actions.calculate_survey_response_rate',
           MagicMock(return_value=RESPONSE_RATE))
    def test_with_one_surveys(self):
        with patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock()):
            model = self.bc.database.create(survey=1)

        logging.Logger.debug.call_args_list = []

        recalculate_survey_scores.delay(1)

        self.assertEqual(logging.Logger.debug.call_args_list, [call('Starting recalculate_survey_score')])
        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(actions.calculate_survey_scores.call_args_list, [call(1)])
        self.assertEqual(actions.calculate_survey_response_rate.call_args_list, [call(1)])
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [
            {
                **self.bc.format.to_dict(model.survey),
                'response_rate': RESPONSE_RATE,
                'scores': get_scores(),
            },
        ])
