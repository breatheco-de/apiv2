"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from .utils import is_valid, create_models, just_one


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

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            models['device'] = create_models(device, 'notify.Device', **{**kargs, **device_kwargs})

        if not 'slack_team' in models and is_valid(slack_team):
            kargs = {}

            if 'user' in models:
                kargs['owner'] = just_one(models['user'])

            if 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            models['slack_team'] = create_models(slack_team, 'notify.SlackTeam', **{
                **kargs,
                **slack_team_kwargs
            })

        if not 'slack_user' in models and is_valid(slack_user):
            kargs = {}

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            models['slack_user'] = create_models(slack_user, 'notify.SlackUser', **{
                **kargs,
                **slack_user_kwargs
            })

        if not 'slack_user_team' in models and is_valid(slack_user_team):
            kargs = {}

            if 'slack_user' in models:
                kargs['slack_user'] = just_one(models['slack_user'])

            if 'slack_team' in models:
                kargs['slack_team'] = just_one(models['slack_team'])

            models['slack_user_team'] = create_models(slack_user_team, 'notify.SlackUserTeam', **{
                **kargs,
                **slack_user_team_kwargs
            })

        if not 'slack_channel' in models and is_valid(slack_channel):
            kargs = {}

            if 'cohort' in models:
                kargs['cohort'] = just_one(models['cohort'])

            if 'slack_team' in models:
                kargs['team'] = just_one(models['slack_team'])

            models['slack_channel'] = create_models(slack_channel, 'notify.SlackChannel', **{
                **kargs,
                **slack_channel_kwargs
            })

        return models
