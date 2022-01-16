"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer
from .utils import is_valid, create_models


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

        if not 'freelancer' in models and is_valid(freelancer):
            kargs = {}

            if 'user' in models or user:
                kargs['user'] = models['user']

            if 'credentials_github' in models or credentials_github:
                kargs['github_user'] = models['credentials_github']

            models['freelancer'] = create_models(freelancer, 'freelance.Freelancer', **{
                **kargs,
                **freelancer_kwargs
            })

        if not 'bill' in models and is_valid(bill):
            kargs = {}

            if 'user' in models or user:
                kargs['reviewer'] = models['user']

            if 'freelancer' in models or freelancer:
                kargs['freelancer'] = models['freelancer']

            models['bill'] = create_models(bill, 'freelance.Bill', **{**kargs, **bill_kwargs})

        if not 'issue' in models and is_valid(issue):
            kargs = {}

            if 'user' in models or user:
                kargs['author'] = models['user']

            if 'freelancer' in models or freelancer:
                kargs['freelancer'] = models['freelancer']

            if 'bill' in models or bill:
                kargs['bill'] = models['bill']

            models['issue'] = create_models(issue, 'freelance.Issue', **{**kargs, **issue_kwargs})

        return models
