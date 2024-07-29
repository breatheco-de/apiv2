"""
Collections of mixins used to login in authorize microservice
"""

import os
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer
from .utils import is_valid, create_models, just_one


class FeedbackModelsMixin(ModelsMixin):

    def generate_feedback_models(
        self,
        answer=False,
        event=False,
        survey=False,
        cohort=False,
        mentor=False,
        academy=False,
        token=False,
        user=False,
        language="",
        answer_status="",
        answer_score="",
        survey_kwargs={},
        answer_kwargs={},
        models={},
        **kwargs
    ):
        """Generate models"""
        os.environ["EMAIL_NOTIFICATIONS_ENABLED"] = "TRUE"
        models = models.copy()

        if not "survey" in models and is_valid(survey):
            kargs = {}

            if "cohort" in models:
                kargs["cohort"] = just_one(models["cohort"])

            models["survey"] = create_models(survey, "feedback.Survey", **{**kargs, **survey_kwargs})

        if not "answer" in models and is_valid(answer):
            kargs = {}

            if "event" in models:
                kargs["event"] = just_one(models["event"])

            if "user" in models or mentor:
                kargs["mentor"] = just_one(models["user"])

            if "cohort" in models:
                kargs["cohort"] = just_one(models["cohort"])

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            if "token" in models:
                kargs["token"] = just_one(models["token"])

            if "survey" in models:
                kargs["survey"] = just_one(models["survey"])

            if "user" in models:
                kargs["user"] = just_one(models["user"])

            if "mentorship_session" in models:
                kargs["mentorship_session"] = just_one(models["mentorship_session"])

            if answer_status:
                kargs["status"] = answer_status

            if answer_score:
                kargs["score"] = answer_score

            if language:
                kargs["lang"] = language

            models["answer"] = create_models(answer, "feedback.Answer", **{**kargs, **answer_kwargs})

        return models
