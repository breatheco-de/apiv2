"""
Test /academy/survey
"""

from unittest.mock import MagicMock, call, patch

from breathecode.feedback.tasks import process_answer_received

from ... import actions
from ..mixins import FeedbackTestCase


def apply_get_env(configuration={}):

    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


class SurveyAnsweredTestSuite(FeedbackTestCase):
    """Test /academy/survey"""

    @patch("logging.Logger.warning", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.feedback.signals.survey_answered.send_robust", MagicMock())
    @patch("breathecode.feedback.actions.calculate_survey_scores", MagicMock(wraps=actions.calculate_survey_scores))
    @patch(
        "breathecode.feedback.actions.calculate_survey_response_rate",
        MagicMock(wraps=actions.calculate_survey_response_rate),
    )
    def test_survey_answered_task_without_answer(self):

        import logging

        process_answer_received.delay(1)

        self.assertEqual(
            logging.Logger.warning.call_args_list,
            [
                call("Answer not found"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("Answer not found", exc_info=True),
            ],
        )
        self.assertEqual(actions.calculate_survey_scores.call_args_list, [])
        self.assertEqual(actions.calculate_survey_response_rate.call_args_list, [])
        self.assertEqual(self.bc.database.list_of("feedback.Survey"), [])

    @patch("logging.Logger.warning", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.feedback.signals.survey_answered.send_robust", MagicMock())
    @patch("breathecode.feedback.actions.calculate_survey_scores", MagicMock(wraps=actions.calculate_survey_scores))
    @patch(
        "breathecode.feedback.actions.calculate_survey_response_rate",
        MagicMock(wraps=actions.calculate_survey_response_rate),
    )
    @patch(
        "os.getenv",
        MagicMock(side_effect=apply_get_env({"SYSTEM_EMAIL": "a@a.a", "ADMIN_URL": "https://www.whatever.com"})),
    )
    def test_survey_answered_task_without_survey(self):

        import logging

        model = self.generate_models(answer=1)

        process_answer_received.delay(1)

        self.assertEqual(logging.Logger.warning.call_args_list, [])
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("No survey connected to answer.", exc_info=True),
            ],
        )
        self.assertEqual(actions.calculate_survey_scores.call_args_list, [])
        self.assertEqual(actions.calculate_survey_response_rate.call_args_list, [])
        self.assertEqual(self.bc.database.list_of("feedback.Survey"), [])

    @patch("logging.Logger.warning", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.feedback.signals.survey_answered.send_robust", MagicMock())
    @patch("breathecode.feedback.actions.calculate_survey_scores", MagicMock(wraps=actions.calculate_survey_scores))
    @patch(
        "breathecode.feedback.actions.calculate_survey_response_rate",
        MagicMock(wraps=actions.calculate_survey_response_rate),
    )
    def test_survey_answered_task_with_survey(self):

        import logging

        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.generate_models(answer=1, survey=1)
        survey_db = self.model_to_dict(model, "survey")

        process_answer_received.delay(1)

        self.assertEqual(logging.Logger.warning.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(actions.calculate_survey_scores.call_args_list, [call(1)])
        self.assertEqual(actions.calculate_survey_response_rate.call_args_list, [call(1)])
        self.assertEqual(
            self.bc.database.list_of("feedback.Survey"),
            [
                {
                    **survey_db,
                    "response_rate": 0.0,
                    "scores": {"academy": None, "cohort": None, "live_class": None, "mentors": [], "total": None},
                }
            ],
        )

    @patch("logging.Logger.warning", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.feedback.signals.survey_answered.send_robust", MagicMock())
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("breathecode.feedback.actions.calculate_survey_scores", MagicMock(wraps=actions.calculate_survey_scores))
    @patch(
        "breathecode.feedback.actions.calculate_survey_response_rate",
        MagicMock(wraps=actions.calculate_survey_response_rate),
    )
    def test_survey_answered_task_with_survey_score_seven(self):

        import logging

        from breathecode.notify.actions import send_email_message

        answer = {"score": 7, "status": "ANSWERED"}
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.generate_models(answer=answer, survey=1)
        survey_db = self.model_to_dict(model, "survey")

        process_answer_received.delay(1)

        self.assertEqual(logging.Logger.warning.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(send_email_message.call_args_list, [])
        self.assertEqual(actions.calculate_survey_scores.call_args_list, [call(1)])
        self.assertEqual(actions.calculate_survey_response_rate.call_args_list, [call(1)])
        self.assertEqual(
            self.bc.database.list_of("feedback.Survey"),
            [
                {
                    **survey_db,
                    "response_rate": 100.0,
                    "scores": {"academy": None, "cohort": None, "live_class": None, "mentors": [], "total": 7.0},
                }
            ],
        )

    @patch("logging.Logger.warning", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.feedback.signals.survey_answered.send_robust", MagicMock())
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("breathecode.feedback.actions.calculate_survey_scores", MagicMock(wraps=actions.calculate_survey_scores))
    @patch(
        "breathecode.feedback.actions.calculate_survey_response_rate",
        MagicMock(wraps=actions.calculate_survey_response_rate),
    )
    def test_survey_answered_task_with_survey_score_seven__with_academy(self):

        import logging

        from breathecode.notify.actions import send_email_message

        base_model = self.generate_models(academy=1)

        answer = {
            "score": 7,
            "status": "ANSWERED",
            "mentor": None,
            "cohort": None,
        }
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.generate_models(answer=answer, survey=1, academy=1)
        survey_db = self.model_to_dict(model, "survey")

        process_answer_received.delay(1)

        self.assertEqual(logging.Logger.warning.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(send_email_message.call_args_list, [])
        self.assertEqual(actions.calculate_survey_scores.call_args_list, [call(1)])
        self.assertEqual(actions.calculate_survey_response_rate.call_args_list, [call(1)])
        self.assertEqual(
            self.bc.database.list_of("feedback.Survey"),
            [
                {
                    **survey_db,
                    "response_rate": 100.0,
                    "scores": {"academy": 7, "cohort": None, "live_class": None, "mentors": [], "total": 7.0},
                }
            ],
        )

    @patch("logging.Logger.error", MagicMock())
    @patch("os.getenv", MagicMock(return_value=None))
    @patch("breathecode.feedback.signals.survey_answered.send_robust", MagicMock())
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("breathecode.feedback.actions.calculate_survey_scores", MagicMock(wraps=actions.calculate_survey_scores))
    @patch(
        "breathecode.feedback.actions.calculate_survey_response_rate",
        MagicMock(wraps=actions.calculate_survey_response_rate),
    )
    def test_survey_answered_task_with_survey_score_seven__with_academy__with_user__no_emails(self):

        import logging
        import os

        from breathecode.notify.actions import send_email_message

        answer_kwargs = {"score": 7}
        academy = {"feedback_email": None}
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.generate_models(answer=answer_kwargs, survey=1, academy=academy, user=1, cohort=1)
        survey_db = self.model_to_dict(model, "survey")

        process_answer_received.delay(1)

        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("No email found.", exc_info=True),
            ],
        )
        self.assertEqual(os.getenv.call_args_list, [call("ENV", ""), call("SYSTEM_EMAIL"), call("ADMIN_URL")])
        self.assertEqual(send_email_message.call_args_list, [])
        self.assertEqual(actions.calculate_survey_scores.call_args_list, [call(1)])
        self.assertEqual(actions.calculate_survey_response_rate.call_args_list, [call(1)])
        self.assertEqual(
            self.bc.database.list_of("feedback.Survey"),
            [
                {
                    **survey_db,
                    "response_rate": 0.0,
                    "scores": {"academy": None, "cohort": None, "live_class": None, "mentors": [], "total": None},
                }
            ],
        )

    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.feedback.signals.survey_answered.send_robust", MagicMock())
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("breathecode.feedback.actions.calculate_survey_scores", MagicMock(wraps=actions.calculate_survey_scores))
    @patch(
        "breathecode.feedback.actions.calculate_survey_response_rate",
        MagicMock(wraps=actions.calculate_survey_response_rate),
    )
    @patch(
        "os.getenv",
        MagicMock(side_effect=apply_get_env({"SYSTEM_EMAIL": "a@a.a", "ADMIN_URL": "https://www.whatever.com"})),
    )
    def test_survey_answered_task_with_survey_score_seven__with_academy__with_user__without_feedback_email(self):

        import logging
        import os

        from breathecode.notify.actions import send_email_message

        answer_kwargs = {"score": 7}
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.generate_models(answer=answer_kwargs, survey=1, academy=1, user=1, cohort=1)
        survey_db = self.model_to_dict(model, "survey")

        process_answer_received.delay(1)

        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(os.getenv.call_args_list, [call("ENV", ""), call("SYSTEM_EMAIL"), call("ADMIN_URL")])
        assert send_email_message.call_args_list == [
            call(
                "negative_answer",
                ["a@a.a"],
                data={
                    "SUBJECT": f"A student answered with a bad NPS score at {model.answer.academy.name}",
                    "FULL_NAME": f"{model.answer.user.first_name} {model.answer.user.last_name}",
                    "QUESTION": model.answer.title,
                    "SCORE": model.answer.score,
                    "COMMENTS": model.answer.comment,
                    "ACADEMY": model.answer.academy.name,
                    "LINK": f"https://www.whatever.com/feedback/surveys/{model.answer.academy.slug}/1",
                },
                academy=model.academy,
            )
        ]
        self.assertEqual(actions.calculate_survey_scores.call_args_list, [call(1)])
        self.assertEqual(actions.calculate_survey_response_rate.call_args_list, [call(1)])
        self.assertEqual(
            self.bc.database.list_of("feedback.Survey"),
            [
                {
                    **survey_db,
                    "response_rate": 0.0,
                    "scores": {"academy": None, "cohort": None, "live_class": None, "mentors": [], "total": None},
                }
            ],
        )

    @patch("logging.Logger.error", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(side_effect=apply_get_env({"SYSTEM_EMAIL": None, "ADMIN_URL": "https://www.whatever.com"})),
    )
    @patch("breathecode.feedback.signals.survey_answered.send_robust", MagicMock())
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("breathecode.feedback.actions.calculate_survey_scores", MagicMock(wraps=actions.calculate_survey_scores))
    @patch(
        "breathecode.feedback.actions.calculate_survey_response_rate",
        MagicMock(wraps=actions.calculate_survey_response_rate),
    )
    def test_survey_answered_task_with_survey_score_seven__with_academy__with_user__without_system_email__with_feedback_email(
        self,
    ):

        import logging

        from breathecode.notify.actions import send_email_message

        answer_kwargs = {"score": 7}
        academy_kwargs = {"feedback_email": "someone@email.com"}
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.generate_models(answer=answer_kwargs, survey=1, academy=academy_kwargs, user=1)
        survey_db = self.model_to_dict(model, "survey")

        process_answer_received.delay(1)

        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(
            send_email_message.call_args_list,
            [
                call(
                    "negative_answer",
                    [f"{model.academy.feedback_email}"],
                    data={
                        "SUBJECT": f"A student answered with a bad NPS score at {model.answer.academy.name}",
                        "FULL_NAME": f"{model.answer.user.first_name} {model.answer.user.last_name}",
                        "QUESTION": model.answer.title,
                        "SCORE": model.answer.score,
                        "COMMENTS": model.answer.comment,
                        "ACADEMY": model.answer.academy.name,
                        "LINK": f"https://www.whatever.com/feedback/surveys/{model.answer.academy.slug}/1",
                    },
                    academy=model.academy,
                )
            ],
        )
        self.assertEqual(actions.calculate_survey_scores.call_args_list, [call(1)])
        self.assertEqual(actions.calculate_survey_response_rate.call_args_list, [call(1)])
        self.assertEqual(
            self.bc.database.list_of("feedback.Survey"),
            [
                {
                    **survey_db,
                    "response_rate": 0.0,
                    "scores": {"academy": None, "cohort": None, "live_class": None, "mentors": [], "total": None},
                }
            ],
        )

    @patch("logging.Logger.error", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env({"SYSTEM_EMAIL": "test@email.com", "ADMIN_URL": "https://www.whatever.com"})
        ),
    )
    @patch("breathecode.feedback.signals.survey_answered.send_robust", MagicMock())
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("breathecode.feedback.actions.calculate_survey_scores", MagicMock(wraps=actions.calculate_survey_scores))
    @patch(
        "breathecode.feedback.actions.calculate_survey_response_rate",
        MagicMock(wraps=actions.calculate_survey_response_rate),
    )
    def test_survey_answered_task_with_survey_score_seven__with_academy__with_user__with_system_email__without_feedback_email(
        self,
    ):

        import logging

        from breathecode.notify.actions import send_email_message

        answer_kwargs = {"score": 7}
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.generate_models(answer=answer_kwargs, survey=1, academy=1, user=1)
        survey_db = self.model_to_dict(model, "survey")

        process_answer_received.delay(1)

        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(
            send_email_message.call_args_list,
            [
                call(
                    "negative_answer",
                    ["test@email.com"],
                    data={
                        "SUBJECT": f"A student answered with a bad NPS score at {model.answer.academy.name}",
                        "FULL_NAME": f"{model.answer.user.first_name} {model.answer.user.last_name}",
                        "QUESTION": model.answer.title,
                        "SCORE": model.answer.score,
                        "COMMENTS": model.answer.comment,
                        "ACADEMY": model.answer.academy.name,
                        "LINK": f"https://www.whatever.com/feedback/surveys/{model.answer.academy.slug}/1",
                    },
                    academy=model.academy,
                )
            ],
        )
        self.assertEqual(actions.calculate_survey_scores.call_args_list, [call(1)])
        self.assertEqual(actions.calculate_survey_response_rate.call_args_list, [call(1)])
        self.assertEqual(
            self.bc.database.list_of("feedback.Survey"),
            [
                {
                    **survey_db,
                    "response_rate": 0.0,
                    "scores": {"academy": None, "cohort": None, "live_class": None, "mentors": [], "total": None},
                }
            ],
        )

    @patch("logging.Logger.error", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env({"SYSTEM_EMAIL": "test@email.com", "ADMIN_URL": "https://www.whatever.com"})
        ),
    )
    @patch("breathecode.feedback.signals.survey_answered.send_robust", MagicMock())
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("breathecode.feedback.actions.calculate_survey_scores", MagicMock(wraps=actions.calculate_survey_scores))
    @patch(
        "breathecode.feedback.actions.calculate_survey_response_rate",
        MagicMock(wraps=actions.calculate_survey_response_rate),
    )
    def test_survey_answered_task_with_survey_score_seven__with_academy__with_user__with_system_email__with_feedback_email(
        self,
    ):

        import logging
        import os

        from breathecode.notify.actions import send_email_message

        answer_kwargs = {"score": 7}
        academy_kwargs = {"feedback_email": "someone@email.com"}
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.generate_models(answer=answer_kwargs, survey=1, academy=academy_kwargs, user=1)
        survey_db = self.model_to_dict(model, "survey")

        process_answer_received.delay(1)

        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(
            send_email_message.call_args_list,
            [
                call(
                    "negative_answer",
                    ["test@email.com", model.academy.feedback_email],
                    data={
                        "SUBJECT": f"A student answered with a bad NPS score at {model.answer.academy.name}",
                        "FULL_NAME": f"{model.answer.user.first_name} {model.answer.user.last_name}",
                        "QUESTION": model.answer.title,
                        "SCORE": model.answer.score,
                        "COMMENTS": model.answer.comment,
                        "ACADEMY": model.answer.academy.name,
                        "LINK": f"https://www.whatever.com/feedback/surveys/{model.answer.academy.slug}/1",
                    },
                    academy=model.academy,
                )
            ],
        )
        self.assertEqual(actions.calculate_survey_scores.call_args_list, [call(1)])
        self.assertEqual(actions.calculate_survey_response_rate.call_args_list, [call(1)])
        self.assertEqual(
            self.bc.database.list_of("feedback.Survey"),
            [
                {
                    **survey_db,
                    "response_rate": 0.0,
                    "scores": {"academy": None, "cohort": None, "live_class": None, "mentors": [], "total": None},
                }
            ],
        )

    @patch("logging.Logger.warning", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.feedback.signals.survey_answered.send_robust", MagicMock())
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("breathecode.feedback.actions.calculate_survey_scores", MagicMock(wraps=actions.calculate_survey_scores))
    @patch(
        "breathecode.feedback.actions.calculate_survey_response_rate",
        MagicMock(wraps=actions.calculate_survey_response_rate),
    )
    def test_survey_answered_task_with_survey_score_ten__with_academy__with_user(self):

        import logging

        from breathecode.notify.actions import send_email_message

        answer = {"score": 10, "status": "ANSWERED", "mentor": None, "academy": None}
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.generate_models(answer=answer, survey=1, academy=1, user=1)
        survey_db = self.model_to_dict(model, "survey")

        process_answer_received.delay(1)

        self.assertEqual(logging.Logger.warning.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(send_email_message.call_args_list, [])
        self.assertEqual(actions.calculate_survey_scores.call_args_list, [call(1)])
        self.assertEqual(actions.calculate_survey_response_rate.call_args_list, [call(1)])
        self.assertEqual(
            self.bc.database.list_of("feedback.Survey"),
            [
                {
                    **survey_db,
                    "response_rate": 100.0,
                    "scores": {"academy": None, "cohort": None, "live_class": None, "mentors": [], "total": 10.0},
                }
            ],
        )
