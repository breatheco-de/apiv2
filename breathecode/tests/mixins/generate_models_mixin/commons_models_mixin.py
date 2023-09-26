"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer
from .utils import is_valid, create_models, just_one, get_list


class CommonsModelsMixin(ModelsMixin):

    def generate_commons_models(self, task_manager=False, models={}, **kwargs):
        """Generate models"""
        models = models.copy()

        if not 'task_manager' in models and is_valid(task_manager):
            kargs = {}

            models['task_manager'] = create_models(task_manager, 'commons.TaskManager', **kargs)

        return models
