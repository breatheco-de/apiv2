"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.generate_models_mixin.assignments_models_mixin import AssignmentsModelsMixin
from datetime import datetime
from mixer.backend.django import mixer
from .authenticate_models_mixin import AuthenticateMixin
from .admissions_models_mixin import AdmissionsModelsMixin
from .auth_mixin import AuthMixin

class GenerateModelsMixin(AuthMixin, AssignmentsModelsMixin,
        AdmissionsModelsMixin, AuthenticateMixin):

    def generate_models(self, models={}, **kwargs):
        self.maxDiff = None
        models = models.copy()

        models = self.generate_credentials(models=models, **kwargs)
        models = self.generate_assignments_models(models=models, **kwargs)
        models = self.generate_admissions_models(models=models, **kwargs)
        models = self.generate_authenticate_models(models=models, **kwargs)

        return models
