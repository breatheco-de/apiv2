"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer
from .utils import is_valid, create_models


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

        if not 'device' in models and is_valid(device):
            kargs = {}

            if 'user' in models or user:
                kargs['user'] = models['user']

            models['device'] = create_models(device, 'notify.Device', **{**kargs, **device_kwargs})

        if not 'slack_team' in models and is_valid(slack_team):
            kargs = {}

            if 'user' in models or user:
                kargs['owner'] = models['user']

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            models['slack_team'] = create_models(slack_team, 'notify.SlackTeam', **{
                **kargs,
                **slack_team_kwargs
            })

        if not 'slack_user' in models and is_valid(slack_user):
            kargs = {}

            if 'user' in models or user:
                kargs['user'] = models['user']

            models['slack_user'] = create_models(slack_user, 'notify.SlackUser', **{
                **kargs,
                **slack_user_kwargs
            })

        if not 'slack_user_team' in models and is_valid(slack_user_team):
            kargs = {}

            if 'slack_user' in models or slack_user:
                kargs['slack_user'] = models['slack_user']

            if 'slack_team' in models or slack_team:
                kargs['slack_team'] = models['slack_team']

            models['slack_user_team'] = create_models(slack_user_team, 'notify.SlackUserTeam', **{
                **kargs,
                **slack_user_team_kwargs
            })

        if not 'slack_channel' in models and is_valid(slack_channel):
            kargs = {}

            if 'cohort' in models or cohort:
                kargs['cohort'] = models['cohort']

            if 'slack_team' in models or slack_team:
                kargs['team'] = models['slack_team']

            models['slack_channel'] = create_models(slack_channel, 'notify.SlackChannel', **{
                **kargs,
                **slack_channel_kwargs
            })

        return models
