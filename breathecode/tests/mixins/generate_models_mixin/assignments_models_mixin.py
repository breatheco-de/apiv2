"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from breathecode.assignments.models import Task
from mixer.backend.django import mixer

class AssignmentsModelsMixin(ModelsMixin):

    def get_task(self, id):
        return Task.objects.filter(id=id).first()

    def get_task_dict(self, id):
        data = Task.objects.filter(id=id).first()
        return self.remove_dinamics_fields(data.__dict__.copy()) if data else None

    def all_task_dict(self):
        return [self.remove_dinamics_fields(data.__dict__.copy()) for data in
            Task.objects.filter()]

    def count_task_user(self):
        return Task.objects.count()

    def generate_assignments_models(self, task=False, task_status='',
            task_type='', task_revision_status='', models={}, **kwargs):
        self.maxDiff = None
        models = models.copy()

        if not 'task' in models and task:
            kargs = {}

            if 'user' in models:
                kargs['user'] = models['user']

            if task_status:
                kargs['task_status'] = task_status

            if task_type:
                kargs['task_type'] = task_type

            if task_revision_status:
                kargs['revision_status'] = task_revision_status

            models['task'] = mixer.blend('assignments.Task', **kargs)

        return models
