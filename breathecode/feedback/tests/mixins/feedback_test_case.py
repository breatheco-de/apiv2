"""
Collections of mixins used to login in authorize microservice
"""
import os
from unittest.mock import call

from django.db.models.expressions import F
from breathecode.authenticate.actions import create_token
from breathecode.authenticate.models import Token
from datetime import datetime
from rest_framework.test import APITestCase
from mixer.backend.django import mixer
from django.contrib.auth.models import User
from breathecode.tests.mixins import DevelopmentEnvironment, DateFormatterMixin
from breathecode.notify.actions import get_template_content
from django.core.cache import cache
from ...models import Answer
from ...actions import strings


class FeedbackTestCase(APITestCase, DevelopmentEnvironment,
                       DateFormatterMixin):
    """FeedbackTestCase with auth methods"""
    # token = None
    user = None
    password = 'pass1234'
    certificate = None
    academy = None
    cohort = None
    profile_academy = None
    cohort_user = None
    city = None
    country = None
    user_two = None
    cohort_two = None
    task = None

    def remove_model_state(self, dict):
        result = None
        if dict:
            result = dict.copy()
            del result['_state']
        return result

    def remove_updated_at(self, dict):
        result = None
        if dict:
            result = dict.copy()
            if 'updated_at' in result:
                del result['updated_at']
        return result

    def remove_dinamics_fields(self, dict):
        return self.remove_updated_at(self.remove_model_state(dict))

    def all_cohort_dict(self):
        return [
            self.remove_dinamics_fields(data.__dict__.copy())
            for data in Answer.objects.filter()
        ]

    def model_to_dict(self, models: dict, key: str) -> dict:
        if key in models:
            return self.remove_dinamics_fields(models[key].__dict__)

    def all_answer_dict(self):
        return [
            self.remove_dinamics_fields(data.__dict__.copy())
            for data in Answer.objects.filter()
        ]

    def remove_all_answer(self):
        Answer.objects.all().delete()

    def all_token(self):
        return Token.objects.filter().values_list('key', flat=True)

    def get_token(self, id=None):
        kwargs = {}
        if id:
            kwargs['id'] = id
        return Token.objects.filter(**kwargs).values_list('key',
                                                          flat=True).first()

    def count_token(self):
        return Token.objects.count()

    def count_answer(self):
        return Answer.objects.count()

    def check_opened_at_and_remove_it(self, model: dict) -> dict:
        self.assertTrue('opened_at' in model)
        self.assertTrue(isinstance(model['opened_at'], datetime))

        model['opened_at'] = None  # remove dinamic datetime after test it

        return model

    def check_all_opened_at_and_remove_it(self,
                                          models: list[dict]) -> list[dict]:
        return [self.check_opened_at_and_remove_it(model) for model in models]

    def check_email_contain_a_correct_token(self, lang, academy, dicts, mock,
                                            model):
        token = self.get_token()
        question = 'asdasd'
        link = f"https://nps.breatheco.de/{dicts[0]['id']}?token={token}"

        args_list = mock.call_args_list

        template = get_template_content(
            "nps", {
                "QUESTION": question,
                "HIGHEST": dicts[0]['highest'],
                "LOWEST": dicts[0]['lowest'],
                "SUBJECT": question,
                "ANSWER_ID": dicts[0]['id'],
                "BUTTON": strings[lang]["button_label"],
                "LINK": link,
            }, ["email"])

        self.assertEqual(args_list, [
            call(
                'https://api.mailgun.net/v3/None/messages',
                auth=('api', os.environ.get('MAILGUN_API_KEY', "")),
                data={
                    "from":
                    f"BreatheCode <mailgun@{os.environ.get('MAILGUN_DOMAIN')}>",
                    "to": model['user'].email,
                    "subject": template['subject'],
                    "text": template['text'],
                    "html": template['html']
                })
        ])

        html = template['html']
        del template['html']
        self.assertEqual(
            template, {
                'SUBJECT':
                question,
                'subject':
                question,
                'text':
                '\n'
                '\n'
                'Please take 2 min to answer the following question:\n'
                '\n'
                '{{ QUESTION }}\n'
                '\n'
                'Click here to vote: '
                f'{link}'
                '\n'
                '\n'
                '\n'
                '\n'
                'The BreatheCode Team'
            })
        self.assertTrue(isinstance(token, str))
        self.assertTrue(token)
        self.assertTrue(link in html)

    def check_stack_contain_a_correct_token(self, lang, academy, mock, model):
        token = self.get_token()
        slack_token = model['slack_team'].credentials.token
        slack_id = model['slack_user'].slack_id
        args_list = mock.call_args_list
        question = "question title"
        answer = strings[lang]["button_label"]

        expected = [
            call(method='POST',
                 url='https://slack.com/api/chat.postMessage',
                 headers={
                     'Authorization': f'Bearer {slack_token}',
                     'Content-type': 'application/json'
                 },
                 params=None,
                 json={
                     'channel':
                     slack_id,
                     'private_metadata':
                     '',
                     'blocks': [{
                         'type': 'header',
                         'text': {
                             'type': 'plain_text',
                             'text': question,
                             'emoji': True
                         }
                     }, {
                         'type':
                         'actions',
                         'elements': [{
                             'type':
                             'button',
                             'text': {
                                 'type': 'plain_text',
                                 'text': answer,
                                 'emoji': True
                             },
                             'url':
                             f'https://nps.breatheco.de/1?token={token}'
                         }]
                     }],
                     'parse':
                     'full'
                 })
        ]

        self.assertEqual(args_list, expected)

    def auth_with_token(self, user):
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def setUp(self):
        cache.clear()

    def generate_models(self,
                        user=False,
                        authenticate=False,
                        certificate=False,
                        academy=False,
                        cohort=False,
                        profile_academy=False,
                        cohort_user=False,
                        impossible_kickoff_date=False,
                        finantial_status='',
                        educational_status='',
                        mentor=False,
                        cohort_two=False,
                        task=False,
                        task_status='',
                        task_type='',
                        answer=False,
                        answer_status='',
                        lang='',
                        event=False,
                        answer_score=0,
                        cohort_user_role='',
                        cohort_user_two=False,
                        slack_user=False,
                        slack_team=False,
                        credentials_slack=False,
                        manual_authenticate=False,
                        slack_team_owner=False):
        os.environ['EMAIL_NOTIFICATIONS_ENABLED'] = 'TRUE'
        self.maxDiff = None

        models = {}

        if academy or profile_academy:
            models['academy'] = mixer.blend('admissions.Academy')

        if certificate or profile_academy:
            models['certificate'] = mixer.blend('admissions.Certificate')

        if cohort or profile_academy or cohort_user:
            kargs = {}

            if lang:
                kargs['language'] = lang

            if profile_academy:
                kargs['certificate'] = models['certificate']

            if academy or profile_academy:
                kargs['academy'] = models['academy']

            if impossible_kickoff_date:
                kargs['kickoff_date'] = datetime(year=3000, month=1, day=1)

            models['cohort'] = mixer.blend('admissions.Cohort', **kargs)

        if cohort_two:
            kargs = {}

            if profile_academy:
                kargs['certificate'] = models['certificate']
                kargs['academy'] = models['academy']

            models['cohort_two'] = mixer.blend('admissions.Cohort', **kargs)

        if (user or authenticate or profile_academy or cohort_user or task
                or slack_user or manual_authenticate or slack_team):
            models['user'] = mixer.blend('auth.User')
            models['user'].set_password(self.password)
            models['user'].save()

        if credentials_slack:
            models['credentials_slack'] = mixer.blend(
                'authenticate.CredentialsSlack', user=models['user'])

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

        if task:
            kargs = {'user': models['user']}

            if task_status:
                kargs['task_status'] = task_status

            if task_type:
                kargs['task_type'] = task_type

            models['task'] = mixer.blend('assignments.Task', **kargs)

        if mentor:
            models['mentor'] = mixer.blend('auth.User')
            models['mentor'].set_password(self.password)
            models['mentor'].save()

        if event:
            kargs = {}

            if academy:
                kargs['academy'] = models['academy']

            models['event'] = mixer.blend('events.Event', **kargs)

        if cohort_user:
            kargs = {}

            kargs['user'] = models['user']
            kargs['cohort'] = models['cohort']

            if cohort_user_role:
                kargs['role'] = cohort_user_role

            if finantial_status:
                kargs['finantial_status'] = finantial_status

            if educational_status:
                kargs['educational_status'] = educational_status

            models['cohort_user'] = mixer.blend('admissions.CohortUser',
                                                **kargs)

        if cohort_user_two:
            kargs = {}

            kargs['user'] = models['user']

            if cohort_user_role:
                kargs['role'] = cohort_user_role

            if finantial_status:
                kargs['finantial_status'] = finantial_status

            if educational_status:
                kargs['educational_status'] = educational_status

            models['cohort_user_two'] = mixer.blend('admissions.CohortUser',
                                                    **kargs)

        if authenticate:
            self.client.force_authenticate(user=models['user'])

        if manual_authenticate:
            self.auth_with_token(models['user'])

        if profile_academy:
            models['profile_academy'] = mixer.blend(
                'authenticate.ProfileAcademy',
                user=models['user'],
                certificate=models['certificate'],
                academy=models['academy'])

        if answer:
            # token = create_token(models['user'], hours_length=48)

            kargs = {
                # 'token_id': Token.objects.filter(key=token).values_list('id', flat=True).first()
            }

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
