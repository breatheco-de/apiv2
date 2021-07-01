"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer


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

        if not 'application' in models and (application or monitor_script):
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            if 'slack_channel' in models or slack_channel:
                kargs['notify_slack_channel'] = models['slack_channel']

            kargs = {**kargs, **application_kwargs}
            models['application'] = mixer.blend('monitoring.Application',
                                                **kargs)

        if not 'endpoint' in models and endpoint:
            kargs = {}

            if 'application' in models or application:
                kargs['application'] = models['application']

            kargs = {**kargs, **endpoint_kwargs}
            models['endpoint'] = mixer.blend('monitoring.Endpoint', **kargs)

        if not 'monitor_script' in models and monitor_script:
            kargs = {}

            if 'application' in models or application:
                kargs['application'] = models['application']

            kargs = {**kargs, **monitor_script_kwargs}
            models['monitor_script'] = mixer.blend('monitoring.MonitorScript',
                                                   **kargs)

        return models
