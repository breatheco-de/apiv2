"""
Collections of mixins used to login in authorize microservice
"""
import os
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer
from .utils import is_valid, create_models, just_one


class MentorshipModelsMixin(ModelsMixin):
    def generate_mentorship_models(self,
                                   mentor=False,
                                   mentee=False,
                                   session=False,
                                   bill=False,
                                   service=False,
                                   academy=False,
                                   token=False,
                                   user=False,
                                   models={},
                                   **kwargs):
        """Generate models"""
        os.environ['EMAIL_NOTIFICATIONS_ENABLED'] = 'TRUE'
        models = models.copy()

        if not 'mentee' in models and is_valid(mentee):
            kargs = {}

            models['mentee'] = create_models(mentor, 'auth.User', **{
                **kargs,
            })

        if not 'mentor' in models and is_valid(mentor):
            kargs = {}

            if 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            if 'service' in models:
                kargs['service'] = just_one(models['service'])

            models['mentor'] = create_models(mentor, 'mentorship.MentorProfile', **{
                **kargs,
            })

        if not 'session' in models and is_valid(session):
            kargs = {}

            if 'mentor' in models:
                kargs['mentor'] = just_one(models['mentor'])

            if 'mentee' in models:
                kargs['mentee'] = just_one(models['mentee'])

            if 'bill' in models:
                kargs['bill'] = just_one(models['bill'])

            if 'service' in models:
                kargs['service'] = just_one(models['service'])

            models['session'] = create_models(session, 'mentorship.MentorshipSession', **{
                **kargs,
            })

        return models
