"""
Test /answer
"""

import logging
import random
from unittest.mock import MagicMock, call, patch
from django.http.request import HttpRequest
from django.contrib.auth.models import User
from ..mixins import FeedbackTestCase
from ...admin import calculate_survey_scores, send_bulk_cohort_user_survey
from ... import tasks
from ..mixins import FeedbackTestCase
from ... import actions

from django.contrib.messages import api


class SendSurveyTestSuite(FeedbackTestCase):
    """
    🔽🔽🔽 With zero Surveys
    """

    @patch("breathecode.feedback.tasks.recalculate_survey_scores.delay", MagicMock())
    def test_with_zero_surveys(self):
        result = calculate_survey_scores(None, None, None)

        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of("feedback.Survey"), [])
        self.assertEqual(tasks.recalculate_survey_scores.delay.call_args_list, [])

    """
    🔽🔽🔽 With random number of Surveys
    """

    @patch("breathecode.feedback.tasks.recalculate_survey_scores.delay", MagicMock())
    def test_with_random_number_of_surveys(self):
        model = self.bc.database.create(survey=random.randint(2, 10))
        result = calculate_survey_scores(None, None, None)

        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of("feedback.Survey"), self.bc.format.to_dict(model.survey))
        self.assertEqual(
            tasks.recalculate_survey_scores.delay.call_args_list,
            [call(x.id) for x in model.survey],
        )
