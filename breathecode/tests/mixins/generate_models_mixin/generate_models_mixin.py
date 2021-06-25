"""
Collections of mixins used to login in authorize microservice
"""
from django.db.models import Model
from breathecode.utils import AttrDict
from .events_models_mixin import EventsModelsMixin
from .notify_models_mixin import NotifyModelsMixin
from .certificate_models_mixin import CertificateModelsMixin
from .assignments_models_mixin import AssignmentsModelsMixin
from .authenticate_models_mixin import AuthenticateMixin
from .admissions_models_mixin import AdmissionsModelsMixin
from .feedback_models_mixin import FeedbackModelsMixin
from .auth_mixin import AuthMixin
from .assessment_models_mixin import AssessmentModelsMixin
from .freelance_models_mixin import FreelanceModelsMixin
from .marketing_models_mixin import MarketingModelsMixin
from .monitoring_models_mixin import MonitoringModelsMixin
from .media_models_mixin import MediaModelsMixin


class GenerateModelsMixin(AuthMixin, AssignmentsModelsMixin,
                          AdmissionsModelsMixin, AuthenticateMixin,
                          CertificateModelsMixin, FeedbackModelsMixin,
                          NotifyModelsMixin, EventsModelsMixin,
                          AssessmentModelsMixin, FreelanceModelsMixin,
                          MarketingModelsMixin, MonitoringModelsMixin,
                          MediaModelsMixin):
    def __detect_invalid_arguments__(self, models={}, **kwargs):
        """check if one argument is invalid to prevent errors"""
        for key in kwargs:
            if key != 'authenticate' and not key.endswith(
                    '_kwargs') and not key in models:
                print(
                    f'key `{key}` should not be implemented in self.generate_models'
                )

    def __inject_models_in_instance__(self, models={}):
        """Add support to model.name instead of model['name']"""
        models = models.copy()
        return AttrDict(**models)

    def __flow_wrapper__(self, *args, **kwargs):
        models = {}

        if 'models' in kwargs:
            models = kwargs['models'].copy()
            del kwargs['models']

        for func in args:
            models = func(models=models, **kwargs)

        self.__detect_invalid_arguments__(models, **kwargs)
        models = self.__inject_models_in_instance__(models)

        return models

    def __flow__(self, *args):
        def inner_wrapper(**kwargs):
            return self.__flow_wrapper__(*args, **kwargs)

        return inner_wrapper

    def __inject_models__(self, models={}, **kwargs):
        """Allow pass models passed in args instead of name=True"""
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
            self.generate_media_models,
            self.generate_marketing_models,
            self.generate_events_models,
            # self.generate_assessment_models,
            self.generate_authenticate_models,
            self.generate_freelance_models,
            self.generate_feedback_models,
            self.generate_notify_models,
            self.generate_monitoring_models,
            self.generate_certificate_models,
        )

        return fn(models=models, **kwargs)
