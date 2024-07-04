"""
Test /answer
"""

from ..mixins import FeedbackTestCase
from ...actions import get_student_answer_avg


class AnswerTestSuite(FeedbackTestCase):
    """
    🔽🔽🔽 Without Cohort
    """

    def test_get_answer_avg(self):

        model = self.generate_models(
            authenticate=True, answer=True, profile_academy=True, answer_status="ANSWERED", answer_score=8
        )

        average = get_student_answer_avg(model["user"].id, model["answer"].cohort.id)

        self.assertEqual(average, model["answer"].score)
