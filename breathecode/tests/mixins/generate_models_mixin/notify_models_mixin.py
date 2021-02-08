"""
Collections of mixins used to login in authorize microservice
"""
import os
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer

class NotifyModelsMixin(ModelsMixin):
    def generate_notify_models(self, device=False, user=False, slack_team=False,
            academy=False, slack_user=False, slack_user_team=False,
            slack_channel=False, cohort=False, models={}, **kwargs):
        """Generate models"""
        models = models.copy()

        if not 'device' in models or device:
            kargs = {}

            if 'user' in models or user:
                kargs['user'] = models['user']

            models['device'] = mixer.blend('notify.Device', **kargs)

        if not 'slack_team' in models or slack_team:
            kargs = {}

            if 'user' in models or user:
                kargs['owner'] = models['user']

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            models['slack_team'] = mixer.blend('notify.SlackTeam', **kargs)

        if not 'slack_user' in models or slack_user:
            kargs = {}

            if 'user' in models or user:
                kargs['user'] = models['user']

            models['slack_user'] = mixer.blend('notify.SlackUser', **kargs)

        if not 'slack_user_team' in models or slack_user_team:
            kargs = {}

            if 'slack_user' in models or slack_user:
                kargs['slack_user'] = models['slack_user']

            if 'slack_team' in models or slack_team:
                kargs['slack_team'] = models['slack_team']

            models['slack_user_team'] = mixer.blend('notify.SlackUserTeam', **kargs)

        if not 'slack_channel' in models or slack_channel:
            kargs = {}

            if 'cohort' in models or cohort:
                kargs['cohort'] = models['cohort']

            if 'slack_team' in models or slack_team:
                kargs['team'] = models['slack_team']

            models['slack_channel'] = mixer.blend('notify.SlackChannel', **kargs)

        return models
