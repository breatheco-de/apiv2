"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer


class FreelanceModelsMixin(ModelsMixin):
    def generate_freelance_models(self,
                                  freelancer=False,
                                  user=False,
                                  credentials_github=False,
                                  bill=False,
                                  issue=False,
                                  freelancer_kwargs={},
                                  bill_kwargs={},
                                  issue_kwargs={},
                                  models={},
                                  **kwargs):
        """Generate models"""
        models = models.copy()

        if not 'freelancer' in models and freelancer:
            kargs = {}

            if 'user' in models or user:
                kargs['user'] = models['user']

            if 'credentials_github' in models or credentials_github:
                kargs['github_user'] = models['credentials_github']

            kargs = {**kargs, **freelancer_kwargs}
            models['freelancer'] = mixer.blend('freelance.Freelancer', **kargs)

        if not 'bill' in models and bill:
            kargs = {}

            if 'user' in models or user:
                kargs['reviewer'] = models['user']

            if 'freelancer' in models or freelancer:
                kargs['freelancer'] = models['freelancer']

            kargs = {**kargs, **bill_kwargs}
            models['bill'] = mixer.blend('freelance.Bill', **kargs)

        if not 'issue' in models and issue:
            kargs = {}

            if 'user' in models or user:
                kargs['author'] = models['user']

            if 'freelancer' in models or freelancer:
                kargs['freelancer'] = models['freelancer']

            if 'bill' in models or bill:
                kargs['bill'] = models['bill']

            kargs = {**kargs, **issue_kwargs}
            models['issue'] = mixer.blend('freelance.Issue', **kargs)

        return models
