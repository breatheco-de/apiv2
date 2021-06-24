"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer


class NotifyModelsMixin(ModelsMixin):
    def generate_notify_models(self,
                               device=False,
                               user=False,
                               slack_team=False,
                               academy=False,
                               slack_user=False,
                               slack_user_team=False,
                               slack_channel=False,
                               cohort=False,
                               device_kwargs={},
                               slack_team_kwargs={},
                               slack_user_kwargs={},
                               slack_user_team_kwargs={},
                               slack_channel_kwargs={},
                               models={},
                               **kwargs):
        """Generate models"""
        models = models.copy()

        if not 'device' in models and device:
            kargs = {}

            if 'user' in models or user:
                kargs['user'] = models['user']

            kargs = {**kargs, **device_kwargs}
            models['device'] = mixer.blend('notify.Device', **kargs)

        if not 'slack_team' in models and slack_team:
            kargs = {}

            if 'user' in models or user:
                kargs['owner'] = models['user']

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            kargs = {**kargs, **slack_team_kwargs}
            models['slack_team'] = mixer.blend('notify.SlackTeam', **kargs)

        if not 'slack_user' in models and slack_user:
            kargs = {}

            if 'user' in models or user:
                kargs['user'] = models['user']

            kargs = {**kargs, **slack_user_kwargs}
            models['slack_user'] = mixer.blend('notify.SlackUser', **kargs)

        if not 'slack_user_team' in models and slack_user_team:
            kargs = {}

            if 'slack_user' in models or slack_user:
                kargs['slack_user'] = models['slack_user']

            if 'slack_team' in models or slack_team:
                kargs['slack_team'] = models['slack_team']

            kargs = {**kargs, **slack_user_team_kwargs}
            models['slack_user_team'] = mixer.blend('notify.SlackUserTeam',
                                                    **kargs)

        if not 'slack_channel' in models and slack_channel:
            kargs = {}

            if 'cohort' in models or cohort:
                kargs['cohort'] = models['cohort']

            if 'slack_team' in models or slack_team:
                kargs['team'] = models['slack_team']

            kargs = {**kargs, **slack_channel_kwargs}
            models['slack_channel'] = mixer.blend('notify.SlackChannel',
                                                  **kargs)

        return models
