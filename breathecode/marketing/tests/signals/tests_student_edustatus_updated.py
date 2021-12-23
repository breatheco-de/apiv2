from unittest.mock import MagicMock, call, patch
from rest_framework import status
from ..mixins import MarketingTestCase


class LeadTestSuite(MarketingTestCase):
    """
    🔽🔽🔽 CohortUser without educational_status ACTIVE
    """
    @patch('breathecode.marketing.tasks.add_cohort_task_to_student.delay', MagicMock())
    @patch('logging.Logger.warn', MagicMock())
    def test_cohort_saved__create__without_educational_status_active(self):
        from breathecode.marketing.tasks import add_cohort_task_to_student
        import logging

        model = self.generate_models(cohort_user=True)

        self.assertEqual(self.all_cohort_user_dict(), [self.model_to_dict(model, 'cohort_user')])
        self.assertEqual(add_cohort_task_to_student.delay.call_args_list, [])
        self.assertEqual(logging.Logger.warn.call_args_list, [])

    """
    🔽🔽🔽 CohortUser with status ACTIVE
    """

    @patch('breathecode.marketing.tasks.add_cohort_task_to_student.delay', MagicMock())
    @patch('logging.Logger.warn', MagicMock())
    def test_cohort_saved__create__with_educational_status_active(self):
        from breathecode.marketing.tasks import add_cohort_task_to_student
        import logging

        cohort_user_kwargs = {'educational_status': 'ACTIVE'}
        model = self.generate_models(cohort_user=True, cohort_user_kwargs=cohort_user_kwargs)

        self.assertEqual(self.all_cohort_user_dict(), [self.model_to_dict(model, 'cohort_user')])
        self.assertEqual(add_cohort_task_to_student.delay.call_args_list, [
            call(model.user.id, model.cohort.id, model.cohort.academy.id),
        ])
        self.assertEqual(logging.Logger.warn.call_args_list, [
            call(f'Student is now active in cohort `{model.cohort.slug}`, processing task'),
        ])
