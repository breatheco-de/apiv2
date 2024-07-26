"""
Test /answer
"""

import random
from unittest.mock import MagicMock, patch

from breathecode.tests.mocks import (
    MAILGUN_INSTANCES,
    MAILGUN_PATH,
    SLACK_INSTANCES,
    SLACK_PATH,
    apply_mailgun_requests_post_mock,
    apply_slack_requests_request_mock,
)

from ...actions import send_question, strings
from ..mixins import FeedbackTestCase


class SendSurveyTestSuite(FeedbackTestCase):
    """
    🔽🔽🔽 Without Cohort
    """

    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_send_question__without_cohort(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        model = self.bc.database.create(user=True)

        try:
            send_question(model["user"])
        except Exception as e:
            self.assertEqual(str(e), "without-cohort-or-cannot-determine-cohort")

        self.assertEqual(self.bc.database.list_of("feedback.Answer"), [])
        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])

        mock_mailgun.call_args_list = []
        mock_slack.call_args_list = []

    """
    🔽🔽🔽 Can't determine the Cohort
    """

    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_send_question__with_same_user_in_two_cohort(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        cohort_user = {"educational_status": random.choice(["POSTPONED", "SUSPENDED", "DROPPED"])}

        model1 = self.bc.database.create(cohort_user=cohort_user)

        base = model1.copy()
        del base["cohort_user"]

        self.bc.database.create(cohort_user=cohort_user, models=base)

        try:
            send_question(model1["user"])
        except Exception as e:
            self.assertEqual(str(e), "without-cohort-or-cannot-determine-cohort")

        self.assertEqual(self.bc.database.list_of("feedback.Answer"), [])
        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])

        mock_mailgun.call_args_list = []
        mock_slack.call_args_list = []

    """
    🔽🔽🔽 Cohort without SyllabusVersion
    """

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_send_question__cohort_without_syllabus_version(self):
        statuses = ["ACTIVE", "GRADUATED"]

        for n in range(0, 2):
            c = statuses[n]
            cohort_user = {"educational_status": c}

            mock_mailgun = MAILGUN_INSTANCES["post"]
            mock_mailgun.call_args_list = []

            mock_slack = SLACK_INSTANCES["request"]
            mock_slack.call_args_list = []

            model = self.bc.database.create(user=True, cohort_user=cohort_user)

            try:
                send_question(model["user"])
            except Exception as e:
                message = str(e)
                self.assertEqual(message, "cohort-without-syllabus-version")

            translations = strings[model["cohort"].language]
            expected = [
                {
                    "id": n + 1,
                    "title": "",
                    "lowest": translations["event"]["lowest"],
                    "highest": translations["event"]["highest"],
                    "lang": "en",
                    "event_id": None,
                    "mentor_id": None,
                    "cohort_id": n + 1,
                    "academy_id": None,
                    "token_id": None,
                    "score": None,
                    "comment": None,
                    "mentorship_session_id": None,
                    "sent_at": None,
                    "survey_id": None,
                    "status": "PENDING",
                    "user_id": n + 1,
                    "opened_at": None,
                    "question_by_slug": None,
                }
            ]

            self.assertEqual(self.bc.database.list_of("feedback.Answer"), expected)
            self.assertEqual(mock_mailgun.call_args_list, [])
            self.assertEqual(mock_slack.call_args_list, [])

            mock_mailgun.call_args_list = []
            mock_slack.call_args_list = []
            self.bc.database.delete("feedback.Answer")

    """
    🔽🔽🔽 Cohort without SyllabusSchedule
    """

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_send_question__cohort_without_syllabus_schedule(self):
        statuses = ["ACTIVE", "GRADUATED"]

        for n in range(0, 2):
            c = statuses[n]
            cohort_user = {"educational_status": c}

            mock_mailgun = MAILGUN_INSTANCES["post"]
            mock_mailgun.call_args_list = []

            mock_slack = SLACK_INSTANCES["request"]
            mock_slack.call_args_list = []

            model = self.bc.database.create(user=True, cohort_user=cohort_user, syllabus_version=True)

            try:
                send_question(model["user"])
            except Exception as e:
                message = str(e)
                self.assertEqual(message, "cohort-without-specialty-mode")

            translations = strings[model["cohort"].language]
            expected = [
                {
                    "id": n + 1,
                    "title": "",
                    "lowest": translations["event"]["lowest"],
                    "highest": translations["event"]["highest"],
                    "lang": "en",
                    "event_id": None,
                    "mentor_id": None,
                    "cohort_id": n + 1,
                    "academy_id": None,
                    "token_id": None,
                    "score": None,
                    "comment": None,
                    "mentorship_session_id": None,
                    "sent_at": None,
                    "survey_id": None,
                    "status": "PENDING",
                    "user_id": n + 1,
                    "question_by_slug": None,
                    "opened_at": None,
                }
            ]

            self.assertEqual(self.bc.database.list_of("feedback.Answer"), expected)
            self.assertEqual(mock_mailgun.call_args_list, [])
            self.assertEqual(mock_slack.call_args_list, [])

            mock_mailgun.call_args_list = []
            mock_slack.call_args_list = []
            self.bc.database.delete("feedback.Answer")

    """
    🔽🔽🔽 Answer are generate and send in a email
    """

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_send_question__just_send_by_email(self):
        statuses = ["ACTIVE", "GRADUATED"]

        for n in range(0, 2):
            c = statuses[n]
            cohort_user = {"educational_status": c}

            mock_mailgun = MAILGUN_INSTANCES["post"]
            mock_mailgun.call_args_list = []

            mock_slack = SLACK_INSTANCES["request"]
            mock_slack.call_args_list = []

            model = self.bc.database.create(
                user=True,
                cohort_user=cohort_user,
                syllabus_version=True,
                syllabus_schedule=True,
                syllabus={"name": self.bc.fake.name()},
            )

            certificate = model.syllabus.name
            send_question(model["user"])

            expected = [
                {
                    "academy_id": None,
                    "cohort_id": n + 1,
                    "comment": None,
                    "event_id": None,
                    "highest": "very good",
                    "id": n + 1,
                    "lang": "en",
                    "lowest": "not good",
                    "mentor_id": None,
                    "mentorship_session_id": None,
                    "opened_at": None,
                    "sent_at": None,
                    "score": None,
                    "status": "SENT",
                    "survey_id": None,
                    "title": f"How has been your experience studying {certificate} so far?",
                    "token_id": n + 1,
                    "question_by_slug": None,
                    "user_id": n + 1,
                }
            ]

            dicts = self.bc.database.list_of("feedback.Answer")
            self.assertEqual(dicts, expected)
            self.assertEqual(self.count_token(), 1)
            self.check_email_contain_a_correct_token("en", dicts, mock_mailgun, model)
            self.assertEqual(mock_slack.call_args_list, [])

            mock_mailgun.call_args_list = []
            mock_slack.call_args_list = []
            self.bc.database.delete("feedback.Answer")
            self.bc.database.delete("authenticate.Token")

    """
    🔽🔽🔽 Answer are generate and send in a email, passing cohort
    """

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_send_question__just_send_by_email__passing_cohort(self):
        statuses = ["ACTIVE", "GRADUATED"]

        for n in range(0, 2):
            c = statuses[n]
            cohort_user = {"educational_status": c}

            mock_mailgun = MAILGUN_INSTANCES["post"]
            mock_mailgun.call_args_list = []

            mock_slack = SLACK_INSTANCES["request"]
            mock_slack.call_args_list = []

            model = self.bc.database.create(
                user=True,
                cohort_user=cohort_user,
                syllabus_version=True,
                syllabus_schedule=True,
                syllabus={"name": self.bc.fake.name()},
            )

            certificate = model.syllabus.name
            send_question(model.user, model.cohort)

            expected = [
                {
                    "academy_id": None,
                    "cohort_id": n + 1,
                    "comment": None,
                    "event_id": None,
                    "highest": "very good",
                    "id": n + 1,
                    "lang": "en",
                    "lowest": "not good",
                    "mentor_id": None,
                    "mentorship_session_id": None,
                    "opened_at": None,
                    "sent_at": None,
                    "score": None,
                    "status": "SENT",
                    "survey_id": None,
                    "title": f"How has been your experience studying {certificate} so far?",
                    "token_id": n + 1,
                    "user_id": n + 1,
                    "question_by_slug": None,
                }
            ]

            dicts = self.bc.database.list_of("feedback.Answer")
            self.assertEqual(dicts, expected)
            self.assertEqual(self.count_token(), 1)
            self.check_email_contain_a_correct_token("en", dicts, mock_mailgun, model)
            self.assertEqual(mock_slack.call_args_list, [])

            mock_mailgun.call_args_list = []
            mock_slack.call_args_list = []
            self.bc.database.delete("feedback.Answer")
            self.bc.database.delete("authenticate.Token")

    """
    🔽🔽🔽 Answer are generate and send in a email and slack
    """

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_send_question__send_by_email_and_slack(self):
        statuses = ["ACTIVE", "GRADUATED"]

        for n in range(0, 2):
            c = statuses[n]
            cohort_user = {"educational_status": c}

            mock_mailgun = MAILGUN_INSTANCES["post"]
            mock_mailgun.call_args_list = []

            mock_slack = SLACK_INSTANCES["request"]
            mock_slack.call_args_list = []

            cohort_kwargs = {"language": "en"}
            model = self.bc.database.create(
                user=True,
                cohort_user=cohort_user,
                slack_user=True,
                slack_team=True,
                credentials_slack=True,
                academy=True,
                syllabus_version=True,
                syllabus_schedule=True,
                cohort_kwargs=cohort_kwargs,
                syllabus={"name": self.bc.fake.name()},
            )

            certificate = model.syllabus.name
            send_question(model["user"])

            expected = [
                {
                    "id": n + 1,
                    "title": f"How has been your experience studying {certificate} so far?",
                    "lowest": "not good",
                    "highest": "very good",
                    "lang": "en",
                    "cohort_id": n + 1,
                    "academy_id": None,
                    "mentor_id": None,
                    "event_id": None,
                    "token_id": n + 1,
                    "mentorship_session_id": None,
                    "sent_at": None,
                    "score": None,
                    "comment": None,
                    "survey_id": None,
                    "status": "SENT",
                    "user_id": n + 1,
                    "opened_at": None,
                    "question_by_slug": None,
                }
            ]

            dicts = [answer for answer in self.bc.database.list_of("feedback.Answer")]
            self.assertEqual(dicts, expected)

            self.check_email_contain_a_correct_token("en", dicts, mock_mailgun, model)
            self.check_slack_contain_a_correct_token("en", dicts, mock_slack, model, answer_id=model.user.id)

            mock_mailgun.call_args_list = []
            mock_slack.call_args_list = []
            self.bc.database.delete("feedback.Answer")
            self.bc.database.delete("authenticate.Token")

    """
    🔽🔽🔽 Send question in english
    """

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_send_question__with_cohort_lang_en(self):
        statuses = ["ACTIVE", "GRADUATED"]

        for n in range(0, 2):
            c = statuses[n]
            cohort_user = {"educational_status": c}

            mock_mailgun = MAILGUN_INSTANCES["post"]
            mock_mailgun.call_args_list = []

            mock_slack = SLACK_INSTANCES["request"]
            mock_slack.call_args_list = []

            cohort_kwargs = {"language": "en"}
            model = self.bc.database.create(
                user=True,
                cohort_user=cohort_user,
                slack_user=True,
                slack_team=True,
                credentials_slack=True,
                academy=True,
                slack_team_owner=True,
                syllabus_version=True,
                syllabus_schedule=True,
                cohort_kwargs=cohort_kwargs,
                syllabus={"name": self.bc.fake.name()},
            )

            certificate = model.syllabus.name
            send_question(model["user"])

            expected = [
                {
                    "id": n + 1,
                    "title": f"How has been your experience studying {certificate} so far?",
                    "lowest": "not good",
                    "highest": "very good",
                    "lang": "en",
                    "cohort_id": n + 1,
                    "academy_id": None,
                    "mentor_id": None,
                    "event_id": None,
                    "mentorship_session_id": None,
                    "sent_at": None,
                    "token_id": n + 1,
                    "score": None,
                    "comment": None,
                    "status": "SENT",
                    "user_id": n + 1,
                    "survey_id": None,
                    "opened_at": None,
                    "question_by_slug": None,
                }
            ]

            dicts = self.bc.database.list_of("feedback.Answer")
            self.assertEqual(dicts, expected)

            self.check_email_contain_a_correct_token("en", dicts, mock_mailgun, model)
            self.check_slack_contain_a_correct_token("en", dicts, mock_slack, model, answer_id=model.user.id)

            mock_mailgun.call_args_list = []
            mock_slack.call_args_list = []
            self.bc.database.delete("feedback.Answer")
            self.bc.database.delete("authenticate.Token")

    """
    🔽🔽🔽 Send question in spanish
    """

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_send_question__with_cohort_lang_es(self):
        statuses = ["ACTIVE", "GRADUATED"]

        for n in range(0, 2):
            c = statuses[n]
            cohort_user = {"educational_status": c}

            mock_mailgun = MAILGUN_INSTANCES["post"]
            mock_mailgun.call_args_list = []

            mock_slack = SLACK_INSTANCES["request"]
            mock_slack.call_args_list = []

            cohort_kwargs = {"language": "es"}
            model = self.bc.database.create(
                user=True,
                cohort_user=cohort_user,
                slack_user=True,
                slack_team=True,
                credentials_slack=True,
                academy=True,
                slack_team_owner=True,
                syllabus_version=True,
                syllabus_schedule=True,
                cohort_kwargs=cohort_kwargs,
                syllabus={"name": self.bc.fake.name()},
            )

            certificate = model.syllabus.name
            send_question(model["user"])

            expected = [
                {
                    "academy_id": None,
                    "cohort_id": n + 1,
                    "comment": None,
                    "event_id": None,
                    "highest": "muy buena",
                    "id": n + 1,
                    "lang": "es",
                    "lowest": "mala",
                    "mentor_id": None,
                    "mentorship_session_id": None,
                    "sent_at": None,
                    "opened_at": None,
                    "score": None,
                    "status": "SENT",
                    "survey_id": None,
                    "title": f"¿Cómo ha sido tu experiencia estudiando {certificate}?",
                    "token_id": n + 1,
                    "user_id": n + 1,
                    "question_by_slug": None,
                }
            ]

            dicts = self.bc.database.list_of("feedback.Answer")
            self.assertEqual(dicts, expected)
            self.assertEqual(self.count_token(), 1)

            self.check_email_contain_a_correct_token("es", dicts, mock_mailgun, model)
            self.check_slack_contain_a_correct_token("es", dicts, mock_slack, model, answer_id=model.user.id)

            mock_mailgun.call_args_list = []
            mock_slack.call_args_list = []
            self.bc.database.delete("feedback.Answer")
            self.bc.database.delete("authenticate.Token")
