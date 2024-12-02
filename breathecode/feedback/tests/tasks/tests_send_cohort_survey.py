"""
Test /academy/survey
"""

import logging
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.utils import timezone

import breathecode.feedback.tasks as tasks
import breathecode.notify.actions as actions
from breathecode.feedback.tasks import send_cohort_survey

from ..mixins import FeedbackTestCase

now = timezone.now()


def apply_get_env(configuration={}):

    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


class SendCohortSurvey(FeedbackTestCase):
    """Test /academy/survey"""

    @patch("breathecode.feedback.tasks.generate_user_cohort_survey_answers", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("logging.Logger.info", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_when_survey_is_none(self):

        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.generate_models(cohort=1)
            logging.Logger.info.call_args_list = []

        send_cohort_survey.delay(user_id=None, survey_id=None)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting send_cohort_survey"),
                call("Starting send_cohort_survey"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("Survey not found", exc_info=True),
            ],
        )
        self.assertEqual(self.bc.database.list_of("feedback.Survey"), [])
        self.assertEqual(tasks.generate_user_cohort_survey_answers.call_args_list, [])

    @patch("breathecode.feedback.tasks.generate_user_cohort_survey_answers", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("logging.Logger.info", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_when_user_is_none(self):

        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.generate_models(cohort=1, survey=1)
            logging.Logger.info.call_args_list = []

        send_cohort_survey.delay(survey_id=1, user_id=None)

        self.assertEqual(logging.Logger.info.call_args_list, [call("Starting send_cohort_survey")])
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("User not found", exc_info=True),
            ],
        )
        self.assertEqual(self.bc.database.list_of("feedback.Survey"), [self.bc.format.to_dict(model.survey)])
        self.assertEqual(tasks.generate_user_cohort_survey_answers.call_args_list, [])

    @patch("breathecode.feedback.tasks.generate_user_cohort_survey_answers", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("logging.Logger.info", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_when_survey_has_expired(self):

        created = timezone.now() - timedelta(hours=48, minutes=1)
        duration = timedelta(hours=48)

        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.generate_models(cohort=1, survey={"duration": duration}, user=1)
            logging.Logger.info.call_args_list = []

        model.survey.created_at = created

        model.survey.save()

        send_cohort_survey.delay(survey_id=1, user_id=1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting send_cohort_survey"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("This survey has already expired", exc_info=True),
            ],
        )
        self.assertEqual(self.bc.database.list_of("feedback.Survey"), [self.bc.format.to_dict(model.survey)])
        self.assertEqual(tasks.generate_user_cohort_survey_answers.call_args_list, [])

    @patch("breathecode.feedback.tasks.generate_user_cohort_survey_answers", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("logging.Logger.info", MagicMock())
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_send_cohort_when_student_does_not_belong_to_cohort(self):

        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.generate_models(cohort=1, user=1, survey=1)
            logging.Logger.info.call_args_list = []

        send_cohort_survey.delay(survey_id=1, user_id=1)

        self.assertEqual(logging.Logger.info.call_args_list, [call("Starting send_cohort_survey")])
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("This student does not belong to this cohort", exc_info=True),
            ],
        )
        self.assertEqual(self.bc.database.list_of("feedback.Survey"), [self.bc.format.to_dict(model.survey)])
        self.assertEqual(tasks.generate_user_cohort_survey_answers.call_args_list, [])
        self.assertEqual(actions.send_email_message.call_args_list, [])

    @patch("os.getenv", MagicMock(side_effect=apply_get_env({"API_URL": "https://hello.com"})))
    @patch("breathecode.feedback.tasks.generate_user_cohort_survey_answers", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("logging.Logger.info", MagicMock())
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_when_student_not_found(self):

        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.generate_models(cohort=1, user=1, survey=1, cohort_user={"role": "STUDENT"})
            logging.Logger.info.call_args_list = []

        send_cohort_survey.delay(survey_id=1, user_id=1)

        self.assertEqual(logging.Logger.info.call_args_list, [call("Starting send_cohort_survey")])
        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(self.bc.database.list_of("feedback.Survey"), [self.bc.format.to_dict(model.survey)])
        self.assertEqual(
            tasks.generate_user_cohort_survey_answers.call_args_list, [call(model.user, model.survey, status="SENT")]
        )
        token = self.bc.database.get("authenticate.Token", 1, dict=False)
        assert actions.send_email_message.call_args_list == [
            call(
                "nps_survey",
                model.user.email,
                {
                    "SUBJECT": "How was the mentoring session at 4Geeks?",
                    "MESSAGE": "Please take 5 minutes to give us feedback about your experience at the academy so far.",
                    "TRACKER_URL": f"https://hello.com/v1/feedback/survey/{model.survey.id}/tracker.png",
                    "BUTTON": "Answer the question",
                    "LINK": f"https://nps.4geeks.com/survey/{model.survey.id}?token={token.key}",
                },
                academy=model.academy,
            )
        ]

    @patch("os.getenv", MagicMock(side_effect=apply_get_env({"API_URL": "https://hello.com"})))
    @patch("breathecode.feedback.tasks.generate_user_cohort_survey_answers", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("logging.Logger.info", MagicMock())
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_when_an_email_is_sent(self):
        statuses = ["ACTIVE", "GRADUATED"]

        for n in range(0, 2):
            c = statuses[n]
            cohort_users = [{"educational_status": c}, {"role": "STUDENT", "educational_status": c}]

            with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
                model = self.generate_models(cohort=1, user=1, survey=1, cohort_user=cohort_users)
                logging.Logger.info.call_args_list = []

            send_cohort_survey.delay(survey_id=model.survey.id, user_id=model.user.id)

            self.assertEqual(logging.Logger.info.call_args_list, [call("Starting send_cohort_survey")])
            self.assertEqual(logging.Logger.error.call_args_list, [])
            self.assertEqual(self.bc.database.list_of("feedback.Survey"), [self.bc.format.to_dict(model.survey)])
            self.assertEqual(
                tasks.generate_user_cohort_survey_answers.call_args_list,
                [call(model.user, model.survey, status="SENT")],
            )
            token = self.bc.database.get("authenticate.Token", model.survey.id, dict=False)
            assert actions.send_email_message.call_args_list == [
                call(
                    "nps_survey",
                    model.user.email,
                    {
                        "SUBJECT": "How was the mentoring session at 4Geeks?",
                        "MESSAGE": "Please take 5 minutes to give us feedback about your experience at the academy so far.",
                        "TRACKER_URL": f"https://hello.com/v1/feedback/survey/{model.survey.id}/tracker.png",
                        "BUTTON": "Answer the question",
                        "LINK": f"https://nps.4geeks.com/survey/{model.survey.id}?token={token.key}",
                    },
                    academy=model.academy,
                )
            ]

            logging.Logger.info.call_args_list = []
            logging.Logger.error.call_args_list = []
            tasks.generate_user_cohort_survey_answers.call_args_list = []
            actions.send_email_message.call_args_list = []
            self.bc.database.delete("feedback.Survey")

    @patch("os.getenv", MagicMock(side_effect=apply_get_env({"API_URL": "https://hello.com"})))
    @patch("breathecode.feedback.tasks.generate_user_cohort_survey_answers", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("logging.Logger.info", MagicMock())
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("breathecode.notify.actions.send_slack", MagicMock())
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_when_an_email_is_sent_with_slack_team_and_user(self):
        statuses = ["ACTIVE", "GRADUATED"]

        for n in range(0, 2):
            c = statuses[n]
            cohort_user = {"role": "STUDENT", "educational_status": c}

            with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
                model = self.generate_models(
                    cohort=1, slack_user=1, slack_team=1, user=1, survey=1, cohort_user=cohort_user
                )
                logging.Logger.info.call_args_list = []

            send_cohort_survey.delay(survey_id=model.survey.id, user_id=model.user.id)

            self.assertEqual(logging.Logger.info.call_args_list, [call("Starting send_cohort_survey")])
            self.assertEqual(logging.Logger.error.call_args_list, [])
            self.assertEqual(self.bc.database.list_of("feedback.Survey"), [self.bc.format.to_dict(model.survey)])
            self.assertEqual(
                tasks.generate_user_cohort_survey_answers.call_args_list,
                [call(model.user, model.survey, status="SENT")],
            )

            token = self.bc.database.get("authenticate.Token", model.survey.id, dict=False)

            assert actions.send_slack.call_args_list == [
                call(
                    "nps_survey",
                    model.slack_user,
                    model.slack_team,
                    data={
                        "SUBJECT": "How was the mentoring session at 4Geeks?",
                        "MESSAGE": "Please take 5 minutes to give us feedback about your experience at the academy so far.",
                        "TRACKER_URL": f"https://hello.com/v1/feedback/survey/{model.survey.id}/tracker.png",
                        "BUTTON": "Answer the question",
                        "LINK": f"https://nps.4geeks.com/survey/{model.survey.id}?token={token.key}",
                    },
                    academy=model.academy,
                )
            ]
            assert actions.send_email_message.call_args_list == [
                call(
                    "nps_survey",
                    model.user.email,
                    {
                        "SUBJECT": "How was the mentoring session at 4Geeks?",
                        "MESSAGE": "Please take 5 minutes to give us feedback about your experience at the academy so far.",
                        "TRACKER_URL": f"https://hello.com/v1/feedback/survey/{model.survey.id}/tracker.png",
                        "BUTTON": "Answer the question",
                        "LINK": f"https://nps.4geeks.com/survey/{model.survey.id}?token={token.key}",
                    },
                    academy=model.academy,
                )
            ]

            logging.Logger.info.call_args_list = []
            logging.Logger.error.call_args_list = []
            tasks.generate_user_cohort_survey_answers.call_args_list = []
            actions.send_email_message.call_args_list = []
            actions.send_slack.call_args_list = []
            self.bc.database.delete("feedback.Survey")
