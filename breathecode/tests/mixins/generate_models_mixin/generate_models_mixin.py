"""
Collections of mixins used to login in authorize microservice
"""
from django.db.models import Model
from .events_models_mixin import EventsModelsMixin
from .notify_models_mixin import NotifyModelsMixin
from .certificate_models_mixin import CertificateModelsMixin
from .assignments_models_mixin import AssignmentsModelsMixin
from .authenticate_models_mixin import AuthenticateMixin
from .admissions_models_mixin import AdmissionsModelsMixin
from .feedback_models_mixin import FeedbackModelsMixin
from .auth_mixin import AuthMixin

class GenerateModelsMixin(AuthMixin, AssignmentsModelsMixin,
        AdmissionsModelsMixin, AuthenticateMixin, CertificateModelsMixin,
        FeedbackModelsMixin, NotifyModelsMixin, EventsModelsMixin):

    def __flow_wrapper__(self, *args, **kwargs):
        models = {}

        if 'models' in kwargs:
            models = kwargs['models'].copy()
            del kwargs['models']

        for func in args:
            models = func(models=models, **kwargs)

        return models

    def __flow__(self, *args):
        def inner_wrapper(**kwargs):
            return self.__flow_wrapper__(*args, **kwargs)

        return inner_wrapper

    def __inject_models__(self, models={}, **kwargs):
        models = models.copy()

        for key in kwargs:
            kwarg = kwargs[key]
            if isinstance(kwarg, Model):
                models[key] = kwarg

        return models

    def generate_models(self, models={}, **kwargs):
        self.maxDiff = None
        models = models.copy()
        models = self.__inject_models__(models, **kwargs)

        fn = self.__flow__(
            self.generate_credentials,
            self.generate_assignments_models,
            self.generate_admissions_models,
            self.generate_events_models,
            self.generate_authenticate_models,
            self.generate_feedback_models,
            self.generate_notify_models,
            self.generate_certificate_models,
        )

        return fn(models=models, **kwargs)
