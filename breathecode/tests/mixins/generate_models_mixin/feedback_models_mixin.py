"""
Collections of mixins used to login in authorize microservice
"""
import os
from breathecode.certificate.models import LayoutDesign, Specialty, UserSpecialty
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer

class FeedbackModelsMixin(ModelsMixin):
    def generate_certificate_models(self, layout_design=False, specialty=False,
            certificate=False, user_specialty=False, layout_design_slug='',
            user_specialty_preview_url='', user_specialty_token='', models={},
            **kwargs):
        """Generate models"""
        os.environ['EMAIL_NOTIFICATIONS_ENABLED'] = 'TRUE'
        models = models.copy()

        if slack_team:
            kargs = {}

            if academy or profile_academy:
                kargs['academy'] = models['academy']

            if slack_team_owner:
                kargs['owner'] = models['user']

            if credentials_slack:
                kargs['credentials'] = models['credentials_slack']

            models['slack_team'] = mixer.blend('notify.SlackTeam', **kargs)

        if slack_user:
            kargs = {
                'user': models['user'],
            }

            if slack_team:
                kargs['team'] = models['slack_team']

            models['slack_user'] = mixer.blend('notify.SlackUser', **kargs)

        if event:
            kargs = {}

            if academy:
                kargs['academy'] = models['academy']

            models['event'] = mixer.blend('events.Event', **kargs)

        if answer:
            kargs = {}

            if user:
                kargs['user'] = models['user']

            if mentor:
                kargs['mentor'] = models['mentor']

            if cohort:
                kargs['cohort'] = models['cohort']

            if academy:
                kargs['academy'] = models['academy']

            if event:
                kargs['event'] = models['event']
            else:
                kargs['event'] = None

            if answer_status:
                kargs['status'] = answer_status

            if answer_score:
                kargs['score'] = answer_score

            if lang:
                kargs['lang'] = lang

            models['answer'] = mixer.blend('feedback.Answer', **kargs)
        
        return models
