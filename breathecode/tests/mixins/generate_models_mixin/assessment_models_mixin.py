"""
Collections of mixins used to login in authorize microservice
"""
import os
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer


class AssessmentModelsMixin(ModelsMixin):
    def generate_assessment_models(self,
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
                                   **kwargs):
        """Generate models"""
        models = models.copy()

        if not 'assessment' in models and assessment:
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            if 'user' in models or user:
                kargs['author'] = models['user']

            kargs = {**kargs, **assessment_kwargs}
            models['assessment'] = mixer.blend('assessment.Assessment',
                                               **kargs)

        if not 'question' in models and question:
            kargs = {}

            if 'assessment' in models or assessment:
                kargs['assessment'] = models['assessment']

            if 'user' in models or user:
                kargs['author'] = models['user']

            kargs = {**kargs, **question_kwargs}
            models['question'] = mixer.blend('assessment.Question', **kargs)

        if not 'option' in models and option:
            kargs = {}

            if 'question' in models or question:
                kargs['question'] = models['question']

            kargs = {**kargs, **option_kwargs}
            models['option'] = mixer.blend('assessment.Option', **kargs)

        if not 'student_assessment' in models and student_assessment:
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            if 'assessment' in models or assessment:
                kargs['assessment'] = models['assessment']

            if 'user' in models or user:
                kargs['student'] = models['user']

            kargs = {**kargs, **student_assessment_kwargs}
            models['student_assessment'] = mixer.blend(
                'assessment.StudentAssessment', **kargs)

        if not 'answer' in models and answer:
            kargs = {}

            if 'student_assessment' in models or student_assessment:
                kargs['student_assesment'] = models['student_assessment']

            kargs = {**kargs, **answer_kwargs}
            models['answer'] = mixer.blend('assessment.Answer', **kargs)

        return models
