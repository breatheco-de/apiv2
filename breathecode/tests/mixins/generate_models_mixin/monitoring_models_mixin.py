"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer
from .utils import is_valid, create_models, just_one


class MonitoringModelsMixin(ModelsMixin):
    def generate_monitoring_models(self,
                                   application=False,
                                   academy=False,
                                   slack_channel=False,
                                   endpoint=False,
                                   monitor_script=False,
                                   application_kwargs={},
                                   endpoint_kwargs={},
                                   monitor_script_kwargs={},
                                   models={},
                                   **kwargs):
        """Generate models"""
        models = models.copy()

        if not 'application' in models and (is_valid(application) or is_valid(monitor_script)):
            kargs = {}

            if 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            if 'slack_channel' in models:
                kargs['notify_slack_channel'] = just_one(models['slack_channel'])

            models['application'] = create_models(application, 'monitoring.Application', **{
                **kargs,
                **application_kwargs
            })

        if not 'endpoint' in models and is_valid(endpoint):
            kargs = {}

            if 'application' in models:
                kargs['application'] = just_one(models['application'])

            models['endpoint'] = create_models(endpoint, 'monitoring.Endpoint', **{
                **kargs,
                **endpoint_kwargs
            })

        if not 'monitor_script' in models and is_valid(monitor_script):
            kargs = {}

            if 'application' in models:
                kargs['application'] = just_one(models['application'])

            models['monitor_script'] = create_models(monitor_script, 'monitoring.MonitorScript', **{
                **kargs,
                **monitor_script_kwargs
            })

        return models
