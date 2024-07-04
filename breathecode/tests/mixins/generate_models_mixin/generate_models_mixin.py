"""
Collections of mixins used to login in authorize microservice
"""

from django.db.models import Model

from breathecode.utils.attr_dict import AttrDict

from .admissions_models_mixin import AdmissionsModelsMixin
from .assessment_models_mixin import AssessmentModelsMixin
from .assignments_models_mixin import AssignmentsModelsMixin
from .auth_mixin import AuthMixin
from .authenticate_models_mixin import AuthenticateMixin
from .career_models_mixin import CareerModelsMixin
from .certificate_models_mixin import CertificateModelsMixin
from .commons_models_mixin import CommonsModelsMixin
from .content_types_mixin import ContentTypesMixin
from .events_models_mixin import EventsModelsMixin
from .feedback_models_mixin import FeedbackModelsMixin
from .freelance_models_mixin import FreelanceModelsMixin
from .linked_services_models_mixin import LinkedServicesMixin
from .marketing_models_mixin import MarketingModelsMixin
from .media_models_mixin import MediaModelsMixin
from .mentorship_models_mixin import MentorshipModelsMixin
from .monitoring_models_mixin import MonitoringModelsMixin
from .notify_models_mixin import NotifyModelsMixin
from .payments_models_mixin import PaymentsModelsMixin
from .provisioning_models_mixin import ProvisioningModelsMixin
from .registry_models_mixin import RegistryModelsMixin
from .task_manager_models_mixin import TaskManagerModelsMixin

__all__ = ["GenerateModelsMixin"]


class GenerateModelsMixin(
    AuthMixin,
    AssignmentsModelsMixin,
    AdmissionsModelsMixin,
    AuthenticateMixin,
    CertificateModelsMixin,
    FeedbackModelsMixin,
    NotifyModelsMixin,
    EventsModelsMixin,
    AssessmentModelsMixin,
    FreelanceModelsMixin,
    MarketingModelsMixin,
    MonitoringModelsMixin,
    MediaModelsMixin,
    MentorshipModelsMixin,
    CareerModelsMixin,
    ContentTypesMixin,
    RegistryModelsMixin,
    PaymentsModelsMixin,
    ProvisioningModelsMixin,
    CommonsModelsMixin,
    LinkedServicesMixin,
    TaskManagerModelsMixin,
):

    def __detect_invalid_arguments__(self, models={}, **kwargs):
        """check if one argument is invalid to prevent errors"""
        for key in kwargs:
            if key != "authenticate" and not key.endswith("_kwargs") and not key in models:
                print(f"key `{key}` should not be implemented in self.generate_models")

    def __inject_models_in_instance__(self, models={}):
        """Add support to model.name instead of model['name']"""
        models = models.copy()
        return AttrDict(**models)

    def __flow_wrapper__(self, *args, **kwargs):
        models = {}

        if "models" in kwargs:
            models = kwargs["models"].copy()
            del kwargs["models"]

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
            if isinstance(kwarg, Model) or (
                isinstance(kwarg, list) and len([x for x in kwarg if isinstance(x, Model)])
            ):
                models[key] = kwarg

        return models

    def generate_models(self, models={}, **kwargs):
        if "_new_implementation" not in kwargs:
            print(f"The method `generate_models` is deprecated, use `self.bc.database.create` instead")

        else:
            del kwargs["_new_implementation"]

        if "authenticate" in kwargs:
            print(f"The argument `authenticate` is deprecated, use `self.bc.request.authenticate` instead")

        self.maxDiff = None
        models = models.copy()
        models = self.__inject_models__(models, **kwargs)

        fn = self.__flow__(
            self.generate_contenttypes_models,
            self.generate_credentials,
            self.generate_linked_services_models,
            self.generate_task_manager_models,
            self.generate_admissions_models,
            self.generate_registry_models,
            self.generate_provisioning_models,
            self.generate_assignments_models,
            self.generate_media_models,
            self.generate_marketing_models,
            self.generate_events_models,
            # self.generate_assessment_models,
            self.generate_authenticate_models,
            self.generate_freelance_models,
            self.generate_mentorship_models,
            self.generate_payments_models,
            self.generate_feedback_models,
            self.generate_notify_models,
            self.generate_monitoring_models,
            self.generate_certificate_models,
            self.generate_career_models,
            self.generate_commons_models,
        )

        return fn(models=models, **kwargs)
