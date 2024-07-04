"""
Collections of mixins used to login in authorize microservice
"""

from mixer.backend.django import mixer

from breathecode.tests.mixins.models_mixin import ModelsMixin

from .utils import create_models, get_list, is_valid, just_one


class AssignmentsModelsMixin(ModelsMixin):

    def generate_assignments_models(
        self,
        task=False,
        cohort=False,
        task_revision_status="",
        models={},
        task_kwargs={},
        final_project=False,
        final_project_kwargs={},
        **kwargs
    ):
        models = models.copy()

        if not "cohort" in models and is_valid(cohort):
            kargs = {}

            models["cohort"] = create_models(cohort, "admissions.Cohort", **kargs)

        if not "task" in models and is_valid(task):
            kargs = {}

            if "user" in models:
                kargs["user"] = just_one(models["user"])

            if "cohort" in models:
                kargs["cohort"] = just_one(models["cohort"])

            if task_revision_status:
                kargs["revision_status"] = just_one(kargs["revision_status"])

            models["task"] = create_models(task, "assignments.Task", **{**kargs, **task_kwargs})

        if not "final_project" in models and is_valid(final_project):
            kargs = {}

            if "user" in models:
                kargs["members"] = get_list(models["user"])

            models["final_project"] = create_models(final_project, "assignments.FinalProject", **kargs)

        return models
