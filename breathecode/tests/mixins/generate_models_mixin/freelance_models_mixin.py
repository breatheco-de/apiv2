"""
Collections of mixins used to login in authorize microservice
"""

from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer
from .utils import is_valid, create_models, just_one


class FreelanceModelsMixin(ModelsMixin):

    def generate_freelance_models(
        self,
        freelancer=False,
        user=False,
        credentials_github=False,
        bill=False,
        issue=False,
        freelancer_kwargs={},
        bill_kwargs={},
        issue_kwargs={},
        models={},
        **kwargs
    ):
        """Generate models"""
        models = models.copy()

        if not "freelancer" in models and is_valid(freelancer):
            kargs = {}

            if "user" in models:
                kargs["user"] = just_one(models["user"])

            if "credentials_github" in models:
                kargs["github_user"] = just_one(models["credentials_github"])

            models["freelancer"] = create_models(freelancer, "freelance.Freelancer", **{**kargs, **freelancer_kwargs})

        if not "bill" in models and is_valid(bill):
            kargs = {}

            if "user" in models:
                kargs["reviewer"] = just_one(models["user"])

            if "freelancer" in models:
                kargs["freelancer"] = just_one(models["freelancer"])

            models["bill"] = create_models(bill, "freelance.Bill", **{**kargs, **bill_kwargs})

        if not "issue" in models and is_valid(issue):
            kargs = {}

            if "user" in models or user:
                kargs["author"] = just_one(models["user"])

            if "freelancer" in models or freelancer:
                kargs["freelancer"] = just_one(models["freelancer"])

            if "bill" in models or bill:
                kargs["bill"] = just_one(models["bill"])

            models["issue"] = create_models(issue, "freelance.Issue", **{**kargs, **issue_kwargs})

        return models
