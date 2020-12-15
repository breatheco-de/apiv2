"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.authenticate.actions import create_token
from breathecode.authenticate.models import Token
from datetime import datetime
from rest_framework.test import APITestCase
from mixer.backend.django import mixer
from django.contrib.auth.models import User
from breathecode.tests.mixins import DevelopmentEnvironment, DateFormatter
from ...models import Answer
# from .models import Academy, CohortUser, Certificate, Cohort

class FeedbackTestCase(APITestCase, DevelopmentEnvironment, DateFormatter):
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

    # def get_academy(self, id):
    #     return Academy.objects.filter(id=id).first()

    # def get_academy_dict(self, id):
    #     data = Academy.objects.filter(id=id).first()
    #     return self.remove_dinamics_fields(data.__dict__.copy()) if data else None

    # def get_certificate_dict(self, id):
    #     data = Certificate.objects.filter(id=id).first()
    #     return self.remove_dinamics_fields(data.__dict__.copy()) if data else None

    # def get_cohort_user_dict(self, id):
    #     data = CohortUser.objects.filter(id=id).first()
    #     return self.remove_dinamics_fields(data.__dict__.copy()) if data else None

    # def get_user_dict(self, id):
    #     data = User.objects.filter(id=id).first()
    #     return self.remove_dinamics_fields(data.__dict__.copy()) if data else None

    # def get_cohort_dict(self, id):
    #     data = Cohort.objects.filter(id=id).first()
    #     return self.remove_dinamics_fields(data.__dict__.copy()) if data else None

    def all_cohort_dict(self):
        return [self.remove_dinamics_fields(data.__dict__.copy()) for data in
            Answer.objects.filter()]

    def model_to_dict(self, models: dict, key: str) -> dict:
        if key in models:
            return self.remove_dinamics_fields(models[key].__dict__)

    # def all_academy_dict(self):
    #     return [self.remove_dinamics_fields(data.__dict__.copy()) for data in
    #         Academy.objects.filter()]

    # def all_cohort_user_dict(self):
    #     return [self.remove_dinamics_fields(data.__dict__.copy()) for data in
    #         CohortUser.objects.filter()]

    # def all_user_dict(self):
    #     return [self.remove_dinamics_fields(data.__dict__.copy()) for data in
    #         User.objects.filter()]

    def all_answer_dict(self):
        return [self.remove_dinamics_fields(data.__dict__.copy()) for data in
            Answer.objects.filter()]

    def remove_all_answer(self):
        Answer.objects.all().delete()

    # def get_answer(self, id: int):
    #     return Answer.objects.filter(id=id).first()
        
    # def get_cohort_user(self, id):
    #     return CohortUser.objects.filter(id=id).first()

    # def get_user(self, id):
    #     return User.objects.filter(id=id).first()

    # def count_cohort_user(self):
    #     return CohortUser.objects.count()

    def count_answer(self):
        return Answer.objects.count()

    # def count_cohort_stage(self, cohort_id):
    #     cohort = Cohort.objects.get(id=cohort_id)
    #     return cohort.stage

    # def count_academy(self):
    #     return Academy.objects.count()

    # def count_certificate(self):
    #     return Certificate.objects.count()

    # def count_cohort(self):
    #     return Cohort.objects.count()

    def check_opened_at_and_remove_it(self, model: dict) -> dict:
        self.assertTrue('opened_at' in model)
        self.assertTrue(isinstance(model['opened_at'], datetime))

        model['opened_at'] = None # remove dinamic datetime after test it

        return model

    def check_all_opened_at_and_remove_it(self, models: list[dict]) -> list[dict]:
        return [self.check_opened_at_and_remove_it(model) for model in models]

    def generate_models(self, user=False, authenticate=False, certificate=False, academy=False,
            cohort=False, profile_academy=False, cohort_user=False, impossible_kickoff_date=False,
            finantial_status='', educational_status='', city=False, country=False, mentor=False,
            cohort_two=False, task=False, task_status='', task_type='', answer=False,
            answer_status='', lang='', event=False, answer_score=0, cohort_user_role=''):
        # isinstance(True, bool)
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

        if user or authenticate or profile_academy or cohort_user or task:
            models['user'] = mixer.blend('auth.User')
            models['user'].set_password(self.password)
            models['user'].save()

        if task:
            kargs = {
                'user': models['user']
            }

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

            models['cohort_user'] = mixer.blend('admissions.CohortUser', **kargs)

        if authenticate:
            self.client.force_authenticate(user=models['user'])

        if profile_academy:
            models['profile_academy'] = mixer.blend('authenticate.ProfileAcademy',
                user=models['user'], certificate=models['certificate'], academy=models['academy'])

        if answer:
            token = create_token(models['user'], hours_length=48)

            kargs = {
                'token_id': Token.objects.filter(key=token).values_list('id', flat=True).first()
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

            models['answer'] = mixer.blend('feedback.Answer', **kargs)
        
        return models

