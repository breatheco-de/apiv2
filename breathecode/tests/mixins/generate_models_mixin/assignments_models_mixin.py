"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer
from .utils import is_valid, create_models, just_one


class AssignmentsModelsMixin(ModelsMixin):
    def generate_assignments_models(self,
                                    task=False,
                                    task_status='',
                                    task_type='',
                                    task_revision_status='',
                                    models={},
                                    task_kwargs={},
                                    **kwargs):
        models = models.copy()

        if not 'task' in models and is_valid(task):
            kargs = {}

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            if 'cohort' in models:
                kargs['cohort'] = just_one(models['cohort'])

            if task_revision_status:
                kargs['revision_status'] = just_one(kargs['revision_status'])

            models['task'] = create_models(task, 'assignments.Task', **{**kargs, **task_kwargs})

        return models
