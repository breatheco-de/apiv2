"""
Collections of mixins used to login in authorize microservice
"""
import os
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer


class FeedbackModelsMixin(ModelsMixin):
    def generate_feedback_models(self,
                                 answer=False,
                                 event=False,
                                 survey=False,
                                 cohort=False,
                                 mentor=False,
                                 academy=False,
                                 token=False,
                                 user=False,
                                 language='',
                                 answer_status='',
                                 answer_score='',
                                 survey_kwargs={},
                                 answer_kwargs={},
                                 models={},
                                 **kwargs):
        """Generate models"""
        os.environ['EMAIL_NOTIFICATIONS_ENABLED'] = 'TRUE'
        models = models.copy()

        if not 'survey' in models and survey:
            kargs = {}

            if 'cohort' in models or cohort:
                kargs['cohort'] = models['cohort']

            kargs = {**kargs, **survey_kwargs}
            models['survey'] = mixer.blend('feedback.Survey', **kargs)

        if not 'answer' in models and answer:
            kargs = {}

            if 'event' in models or event:
                kargs['event'] = models['event']

            if 'user' in models or mentor:
                kargs['mentor'] = models['user']

            if 'cohort' in models or cohort:
                kargs['cohort'] = models['cohort']

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            if 'token' in models or token:
                kargs['token'] = models['token']

            if 'survey' in models or survey:
                kargs['survey'] = models['survey']

            if 'user' in models or user:
                kargs['user'] = models['user']

            if answer_status:
                kargs['status'] = answer_status

            if answer_score:
                kargs['score'] = answer_score

            if language:
                kargs['lang'] = language

            kargs = {**kargs, **answer_kwargs}
            models['answer'] = mixer.blend('feedback.Answer', **kargs)

        return models
