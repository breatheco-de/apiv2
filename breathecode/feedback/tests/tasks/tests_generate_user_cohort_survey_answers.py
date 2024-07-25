"""
Test /academy/survey
"""

from unittest.mock import MagicMock, patch

from django.utils import timezone

from breathecode.feedback.tasks import generate_user_cohort_survey_answers
from capyc.rest_framework.exceptions import ValidationException

from ..mixins import FeedbackTestCase

UTC_NOW = timezone.now()


def answer(data={}):
    return {
        "academy_id": 0,
        "cohort_id": 0,
        "comment": None,
        "event_id": None,
        "highest": "very good",
        "id": 0,
        "lang": "en",
        "lowest": "not good",
        "mentor_id": None,
        "mentorship_session_id": None,
        "opened_at": UTC_NOW,
        "score": None,
        "sent_at": None,
        "status": "OPENED",
        "survey_id": 0,
        "title": "",
        "token_id": None,
        "user_id": 0,
        "aditional_question": None,
        **data,
    }


class SendCohortSurvey(FeedbackTestCase):

    def test_when_student_is_not_assigned(self):

        model = self.generate_models(cohort=1, user=1, survey=1)

        with self.assertRaisesMessage(ValidationException, "This student does not belong to this cohort"):
            generate_user_cohort_survey_answers(model.user, model.survey, status="OPENED")

        self.assertEqual(self.bc.database.list_of("feedback.Answer"), [])

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    def test_when_teacher_is_not_assigned(self):
        statuses = ["ACTIVE", "GRADUATED"]

        for c in statuses:
            cohort_user = {"educational_status": c}
            model = self.generate_models(cohort=1, user=1, survey=1, cohort_user=cohort_user)

            with self.assertRaisesMessage(
                ValidationException, "This cohort must have a teacher assigned to be able to survey it"
            ):
                generate_user_cohort_survey_answers(model.user, model.survey, status="OPENED")

            self.assertEqual(self.bc.database.list_of("feedback.Answer"), [])

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_when_teacher_is_assigned(self):
        statuses = ["ACTIVE", "GRADUATED"]

        for n in range(0, 2):
            c = statuses[n]
            cohort_users = [{"educational_status": c}, {"role": "TEACHER", "educational_status": c}]

            model = self.bc.database.create(cohort=1, user=1, survey=1, cohort_user=cohort_users)

            generate_user_cohort_survey_answers(model.user, model.survey, status="OPENED")

            answers = [
                {
                    "title": f"How has been your experience studying {model.cohort.name} so far?",
                    "lowest": "not good",
                    "highest": "very good",
                    "cohort_id": n + 1,
                    "academy_id": n + 1,
                    "token_id": None,
                },
                {
                    "title": f"How has been your experience with your mentor {model.user.first_name} {model.user.last_name} so far?",
                    "lang": "en",
                    "mentor_id": n + 1,
                    "lowest": "not good",
                    "mentorship_session_id": None,
                    "score": None,
                    "sent_at": None,
                    "status": "OPENED",
                    "highest": "very good",
                    "cohort_id": n + 1,
                    "academy_id": n + 1,
                },
                {
                    "title": f"How likely are you to recommend {model.academy.name} to your friends " "and family?",
                    "lowest": "not likely",
                    "highest": "very likely",
                    "cohort_id": None,
                    "academy_id": n + 1,
                },
                {
                    "title": f"How has been your experience with the platform and content?",
                    "lowest": "not good",
                    "highest": "very good",
                    "cohort_id": None,
                    "academy_id": None,
                    "aditional_question": "PLATFORM",
                },
            ]

            self.assertEqual(
                self.bc.database.list_of("feedback.Answer"),
                [
                    answer(
                        {
                            "id": (n * len(answers)) + (index + 1),
                            "user_id": n + 1,
                            "survey_id": n + 1,
                            **elem,
                        }
                    )
                    for index, elem in enumerate(answers)
                ],
            )

            # teardown
            self.bc.database.delete("feedback.Answer")

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_when_cohort_has_syllabus(self):
        statuses = ["ACTIVE", "GRADUATED"]

        for n in range(0, 2):
            c = statuses[n]
            cohort_users = [{"educational_status": c}, {"role": "TEACHER", "educational_status": c}]

            model = self.bc.database.create(cohort=1, user=1, survey=1, cohort_user=cohort_users, syllabus_version=1)

            generate_user_cohort_survey_answers(model.user, model.survey, status="OPENED")

            answers = [
                {
                    "title": f"How has been your experience studying {model.cohort.name} so far?",
                    "lowest": "not good",
                    "cohort_id": n + 1,
                    "academy_id": n + 1,
                    "highest": "very good",
                    "token_id": None,
                },
                {
                    "title": f"How has been your experience with your mentor {model.user.first_name} {model.user.last_name} so far?",
                    "lang": "en",
                    "mentor_id": n + 1,
                    "cohort_id": n + 1,
                    "academy_id": n + 1,
                    "lowest": "not good",
                    "mentorship_session_id": None,
                    "score": None,
                    "sent_at": None,
                    "status": "OPENED",
                    "highest": "very good",
                },
                {
                    "title": f"How likely are you to recommend {model.academy.name} to your friends " "and family?",
                    "academy_id": n + 1,
                    "lowest": "not likely",
                    "highest": "very likely",
                    "cohort_id": None,
                },
                {
                    "title": f"How has been your experience with the platform and content?",
                    "lowest": "not good",
                    "highest": "very good",
                    "cohort_id": None,
                    "academy_id": None,
                    "aditional_question": "PLATFORM",
                },
            ]
            self.assertEqual(
                self.bc.database.list_of("feedback.Answer"),
                [
                    answer(
                        {
                            "id": (n * len(answers)) + (index + 1),
                            "user_id": n + 1,
                            "survey_id": n + 1,
                            **elem,
                        }
                    )
                    for index, elem in enumerate(answers)
                ],
            )

            # teardown
            self.bc.database.delete("feedback.Answer")

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_when_cohort_is_available_as_saas(self):
        statuses = ["ACTIVE", "GRADUATED"]

        for n in range(0, 2):
            c = statuses[n]
            cohort_users = [{"educational_status": c}, {"role": "TEACHER", "educational_status": c}]

            model = self.bc.database.create(
                cohort={"available_as_saas": True}, user=1, survey=1, cohort_user=cohort_users, syllabus_version=1
            )

            generate_user_cohort_survey_answers(model.user, model.survey, status="OPENED")

            answers = [
                {
                    "title": f"How has been your experience studying {model.cohort.name} so far?",
                    "lowest": "not good",
                    "cohort_id": n + 1,
                    "academy_id": n + 1,
                    "highest": "very good",
                    "token_id": None,
                },
                {
                    "title": f"How likely are you to recommend {model.academy.name} to your friends " "and family?",
                    "academy_id": n + 1,
                    "lowest": "not likely",
                    "highest": "very likely",
                    "cohort_id": None,
                },
                {
                    "title": f"How has been your experience with the platform and content?",
                    "lowest": "not good",
                    "highest": "very good",
                    "cohort_id": None,
                    "academy_id": None,
                    "aditional_question": "PLATFORM",
                },
            ]
            self.assertEqual(
                self.bc.database.list_of("feedback.Answer"),
                [
                    answer(
                        {
                            "id": (n * len(answers)) + (index + 1),
                            "user_id": n + 1,
                            "survey_id": n + 1,
                            **elem,
                        }
                    )
                    for index, elem in enumerate(answers)
                ],
            )

            # teardown
            self.bc.database.delete("feedback.Answer")

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_role_assistant(self):
        statuses = ["ACTIVE", "GRADUATED"]

        for n in range(0, 2):
            c = statuses[n]
            cohort_users = [
                {"role": "TEACHER", "educational_status": c},
                {"role": "ASSISTANT", "educational_status": c},
                {"educational_status": c},
            ]

            model = self.bc.database.create(cohort=1, user=1, survey=1, cohort_user=cohort_users)

            generate_user_cohort_survey_answers(model.user, model.survey, status="OPENED")

            answers = [
                {
                    "title": f"How has been your experience studying {model.cohort.name} so far?",
                    "lowest": "not good",
                    "highest": "very good",
                    "cohort_id": n + 1,
                    "academy_id": n + 1,
                    "token_id": None,
                },
                {
                    "title": f"How has been your experience with your mentor {model.user.first_name} {model.user.last_name} so far?",
                    "lang": "en",
                    "mentor_id": n + 1,
                    "lowest": "not good",
                    "mentorship_session_id": None,
                    "score": None,
                    "sent_at": None,
                    "status": "OPENED",
                    "highest": "very good",
                    "cohort_id": n + 1,
                    "academy_id": n + 1,
                },
                {
                    "title": f"How has been your experience with your mentor {model.user.first_name} {model.user.last_name} so far?",
                    "lowest": "not good",
                    "highest": "very good",
                    "cohort_id": n + 1,
                    "academy_id": n + 1,
                    "mentor_id": n + 1,
                },
                {
                    "title": f"How likely are you to recommend {model.academy.name} to your friends " "and family?",
                    "lowest": "not likely",
                    "highest": "very likely",
                    "cohort_id": None,
                    "academy_id": n + 1,
                },
                {
                    "title": f"How has been your experience with the platform and content?",
                    "lowest": "not good",
                    "highest": "very good",
                    "cohort_id": None,
                    "academy_id": None,
                    "aditional_question": "PLATFORM",
                },
            ]

            self.assertEqual(
                self.bc.database.list_of("feedback.Answer"),
                [
                    answer(
                        {
                            "id": (n * len(answers)) + (index + 1),
                            "user_id": n + 1,
                            "survey_id": n + 1,
                            **elem,
                        }
                    )
                    for index, elem in enumerate(answers)
                ],
            )

            # teardown
            self.bc.database.delete("feedback.Answer")
