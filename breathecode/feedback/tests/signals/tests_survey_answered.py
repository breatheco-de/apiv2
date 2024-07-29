"""
Test /academy/survey
"""

from unittest.mock import patch, MagicMock, call
from breathecode.tests.mixins.legacy import LegacyAPITestCase


class TestSurveyAnswered(LegacyAPITestCase):
    """Test /academy/survey"""

    @patch("breathecode.feedback.tasks.process_answer_received.delay", MagicMock())
    def test_survey_answered_signal_pending(self, enable_signals):
        enable_signals()

        from breathecode.feedback.tasks import process_answer_received

        model = self.generate_models(answer=True)
        answer_db = self.model_to_dict(model, "answer")

        self.assertEqual(process_answer_received.delay.call_args_list, [])
        self.assertEqual(self.bc.database.list_of("feedback.Answer"), [answer_db])

    @patch("breathecode.feedback.tasks.process_answer_received.delay", MagicMock())
    def test_survey_answered_signal_answered(self, enable_signals):
        enable_signals()

        from breathecode.feedback.tasks import process_answer_received

        answer = {"status": "ANSWERED"}
        model = self.generate_models(answer=answer)
        answer_db = self.model_to_dict(model, "answer")

        self.assertEqual(process_answer_received.delay.call_args_list, [call(1)])
        self.assertEqual(self.bc.database.list_of("feedback.Answer"), [answer_db])
