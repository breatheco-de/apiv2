"""
Collections of mixins used to login in authorize microservice
"""

import os
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer
from .utils import is_valid, create_models, just_one


class AssessmentModelsMixin(ModelsMixin):

    def generate_assessment_models(
        self,
        assessment=False,
        question=False,
        academy=False,
        option=False,
        student_assessment=False,
        answer=False,
        user=False,
        assessment_kwargs={},
        question_kwargs={},
        option_kwargs={},
        student_assessment_kwargs={},
        answer_kwargs={},
        models={},
        **kwargs
    ):
        """Generate models"""
        models = models.copy()

        if not "assessment" in models and is_valid(assessment):
            kargs = {}

            if "academy" in models or academy:
                kargs["academy"] = just_one(models["academy"])

            if "user" in models or user:
                kargs["author"] = just_one(models["user"])

            models["assessment"] = create_models(assessment, "assessment.Assessment", **{**kargs, **assessment_kwargs})

        if not "question" in models and is_valid(question):
            kargs = {}

            if "assessment" in models or assessment:
                kargs["assessment"] = just_one(models["assessment"])

            if "user" in models or user:
                kargs["author"] = just_one(models["user"])

            models["question"] = create_models(question, "assessment.Question", **{**kargs, **question_kwargs})

        if not "option" in models and is_valid(option):
            kargs = {}

            if "question" in models or question:
                kargs["question"] = just_one(models["question"])

            models["option"] = create_models(option, "assessment.Option", **{**kargs, **option_kwargs})

        if not "student_assessment" in models and is_valid(student_assessment):
            kargs = {}

            if "academy" in models or academy:
                kargs["academy"] = just_one(models["academy"])

            if "assessment" in models or assessment:
                kargs["assessment"] = just_one(models["assessment"])

            if "user" in models or user:
                kargs["student"] = just_one(models["user"])

            models["student_assessment"] = create_models(
                student_assessment, "assessment.StudentAssessment", **{**kargs, **student_assessment_kwargs}
            )

        if not "answer" in models and is_valid(answer):
            kargs = {}

            if "student_assessment" in models or student_assessment:
                kargs["student_assesment"] = just_one(models["student_assessment"])

            models["answer"] = create_models(answer, "assessment.Answer", **{**kargs, **answer_kwargs})

        return models
