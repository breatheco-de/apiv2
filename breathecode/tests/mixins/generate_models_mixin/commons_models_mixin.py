"""
Collections of mixins used to login in authorize microservice
"""

from mixer.backend.django import mixer

from breathecode.tests.mixins.models_mixin import ModelsMixin

from .utils import create_models, get_list, is_valid, just_one


class CommonsModelsMixin(ModelsMixin):

    def generate_commons_models(self, task_manager=False, models={}, **kwargs):
        """Generate models"""
        models = models.copy()

        return models
