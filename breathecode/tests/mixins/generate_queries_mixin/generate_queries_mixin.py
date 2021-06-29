"""
Collections of mixins used to login in authorize microservice
"""
import re

from breathecode.tests.mixins.models_mixin import ModelsMixin
from django.contrib.auth.models import User
from .admissions_queries_mixin import AdmissionsQueriesMixin
from .assignments_queries_mixin import AssignmentsQueriesMixin
from .authenticate_queries_mixin import AuthenticateQueriesMixin
from .feedback_queries_mixin import FeedbackQueriesMixin
from .notify_queries_mixin import NotifyQueriesMixin
from .certificate_queries_mixin import CertificateQueriesMixin
from .events_queries_mixin import EventsQueriesMixin
from .assessment_queries_mixin import AssessmentQueriesMixin
from .freelance_queries_mixin import FreelanceQueriesMixin
from .marketing_queries_mixin import MarketingQueriesMixin
from .monitoring_queries_mixin import MonitoringQueriesMixin
from .media_queries_mixin import MediaQueriesMixin


class GenerateQueriesMixin(ModelsMixin, AdmissionsQueriesMixin,
                           AssessmentQueriesMixin, AssignmentsQueriesMixin,
                           AuthenticateQueriesMixin, CertificateQueriesMixin,
                           EventsQueriesMixin, FeedbackQueriesMixin,
                           FreelanceQueriesMixin, MarketingQueriesMixin,
                           NotifyQueriesMixin, MonitoringQueriesMixin,
                           MediaQueriesMixin):
    __project__ = 'breathecode'
    __generate_queries_was_loaded__ = False

    def __get_model__(self, Model, key='id'):
        def get_model(pk):
            kwargs = {key: pk}

            return Model.objects.filter(**kwargs).first()

        return get_model

    def __get_model_dict__(self, Model, key='id'):
        def get_model_dict(pk):
            kwargs = {key: pk}

            data = Model.objects.filter(**kwargs).first()
            return self.remove_dinamics_fields(
                data.__dict__.copy()) if data else None

        return get_model_dict

    def __all_model__(self, Model):
        def all_model():
            return Model.objects.filter()

        return all_model

    def __all_model_dict__(self, Model):
        def all_model_dict():
            return [
                self.remove_dinamics_fields(data.__dict__.copy())
                for data in Model.objects.filter()
            ]

        return all_model_dict

    def __count_model__(self, Model):
        def count_model():
            return Model.objects.count()

        return count_model

    def __set_queries__(self, Model):
        snake_case_name = re.sub(r'(?<!^)(?=[A-Z])', '_',
                                 Model.__name__).lower()

        setattr(self, f'get_{snake_case_name}', self.__get_model__(Model))
        setattr(self, f'get_{snake_case_name}_dict',
                self.__get_model_dict__(Model))
        setattr(self, f'all_{snake_case_name}', self.__all_model__(Model))
        setattr(self, f'all_{snake_case_name}_dict',
                self.__all_model_dict__(Model))
        setattr(self, f'count_{snake_case_name}', self.__count_model__(Model))

    def generate_queries(self):
        if self.__generate_queries_was_loaded__:
            return

        descriptors = [
            self.generate_admissions_queries,
            # self.generate_assessment_queries,
            self.generate_assignments_queries,
            self.generate_authenticate_queries,
            self.generate_certificate_queries,
            self.generate_events_queries,
            self.generate_feedback_queries,
            self.generate_freelance_queries,
            self.generate_marketing_queries,
            self.generate_media_queries,
            self.generate_monitoring_queries,
            self.generate_notify_queries,
        ]

        for descriptor in descriptors:
            obj = descriptor()
            models = obj['models']
            module_name = obj['module']

            for model in models:
                path = f'{self.__project__}.{module_name}.models'
                import importlib
                module = importlib.import_module(path)

                if hasattr(module, model):
                    Model = getattr(module, model)
                    self.__set_queries__(Model)
                else:
                    print(f'{model} not exist in current path `{path}`')

        self.__set_queries__(User)
        self.__generate_queries_was_loaded__ = True

    def setUp(self):
        self.generate_queries()
