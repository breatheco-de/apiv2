"""
Collections of mixins used to login in authorize microservice
"""

from mixer.backend.django import mixer

from breathecode.tests.mixins.generate_models_mixin.utils import get_list, just_one
from breathecode.tests.mixins.models_mixin import ModelsMixin

from .utils import create_models, is_valid


class TaskManagerModelsMixin(ModelsMixin):

    def generate_task_manager_models(self, task_manager=False, models={}, **kwargs):
        """Generate models"""
        models = models.copy()

        if not "task_manager" in models and is_valid(task_manager):
            kargs = {}

            models["task_manager"] = create_models(task_manager, "task_manager.TaskManager", **kargs)

        if not "task_watcher" in models and is_valid(task_manager):
            kargs = {}

            if "user" in models:
                kargs["user"] = just_one(models["user"])

            if "task_manager" in models:
                kargs["tasks"] = get_list(models["task_manager"])

            models["task_watcher"] = create_models(task_manager, "task_manager.TaskWatcher", **kargs)

        return models
