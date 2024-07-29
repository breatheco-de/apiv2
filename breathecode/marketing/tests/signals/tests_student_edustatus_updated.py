import random
from unittest.mock import MagicMock, call, patch

from breathecode.tests.mixins.legacy import LegacyAPITestCase
from capyc.rest_framework.exceptions import ValidationException


class TestLead(LegacyAPITestCase):
    """
    🔽🔽🔽 CohortUser without educational_status ACTIVE
    """

    @patch("breathecode.marketing.tasks.add_cohort_task_to_student.delay", MagicMock())
    @patch("logging.Logger.warning", MagicMock())
    def test_cohort_saved__create__without_educational_status_active(self, enable_signals):
        enable_signals("breathecode.admissions.signals.student_edu_status_updated")

        import logging

        from breathecode.marketing.tasks import add_cohort_task_to_student

        educational_status = random.choice(["POSTPONED", "SUSPENDED", "GRADUATED", "DROPPED"])
        cohort_user = {
            "educational_status": educational_status,
        }

        with self.assertRaisesMessage(ValidationException, "user-not-found-in-org"):
            model = self.generate_models(cohort_user=cohort_user)

        self.assertEqual(
            self.bc.database.list_of("admissions.CohortUser"),
            [
                {
                    "cohort_id": 1,
                    "finantial_status": None,
                    "history_log": {},
                    "id": 1,
                    "role": "STUDENT",
                    "user_id": 1,
                    "watching": False,
                    "educational_status": educational_status,
                },
            ],
        )
        self.assertEqual(add_cohort_task_to_student.delay.call_args_list, [])
        self.assertEqual(logging.Logger.warning.call_args_list, [])

    """
    🔽🔽🔽 CohortUser with status ACTIVE
    """

    @patch("breathecode.marketing.tasks.add_cohort_task_to_student.delay", MagicMock())
    @patch("logging.Logger.warning", MagicMock())
    def test_cohort_saved__create__with_educational_status_active(self, enable_signals):
        enable_signals("breathecode.admissions.signals.student_edu_status_updated")

        import logging

        from breathecode.marketing.tasks import add_cohort_task_to_student

        cohort_user_kwargs = {"educational_status": "ACTIVE"}
        model = self.generate_models(cohort_user=True, cohort_user_kwargs=cohort_user_kwargs)

        self.assertEqual(self.bc.database.list_of("admissions.CohortUser"), [self.model_to_dict(model, "cohort_user")])
        self.assertEqual(
            add_cohort_task_to_student.delay.call_args_list,
            [
                call(model.user.id, model.cohort.id, model.cohort.academy.id),
            ],
        )
        self.assertEqual(
            logging.Logger.warning.call_args_list,
            [
                call(f"Student is now active in cohort `{model.cohort.slug}`, processing task"),
            ],
        )
