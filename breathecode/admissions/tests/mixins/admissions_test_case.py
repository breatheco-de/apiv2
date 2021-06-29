"""
Collections of mixins used to login in authorize microservice
"""
from rest_framework.test import APITestCase
from breathecode.tests.mixins.authenticate_mixin import AuthenticateMixin
from datetime import datetime
from mixer.backend.django import mixer
from django.contrib.auth.models import User
from breathecode.tests.mixins import DateFormatterMixin
from django.core.cache import cache
from ...models import CohortUser, Cohort, Academy, Certificate, Cohort


class AdmissionsTestCase(APITestCase, AuthenticateMixin, DateFormatterMixin):
    """AdmissionsTestCase with auth methods"""
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

    def get_academy(self, id):
        return Academy.objects.filter(id=id).first()

    def get_academy_dict(self, id):
        data = Academy.objects.filter(id=id).first()
        return self.remove_dinamics_fields(
            data.__dict__.copy()) if data else None

    def get_certificate_dict(self, id):
        data = Certificate.objects.filter(id=id).first()
        return self.remove_dinamics_fields(
            data.__dict__.copy()) if data else None

    def get_cohort_user_dict(self, id):
        data = CohortUser.objects.filter(id=id).first()
        return self.remove_dinamics_fields(
            data.__dict__.copy()) if data else None

    def get_user_dict(self, id):
        data = User.objects.filter(id=id).first()
        return self.remove_dinamics_fields(
            data.__dict__.copy()) if data else None

    def get_cohort_dict(self, id):
        data = Cohort.objects.filter(id=id).first()
        return self.remove_dinamics_fields(
            data.__dict__.copy()) if data else None

    def all_cohort_dict(self):
        return [
            self.remove_dinamics_fields(data.__dict__.copy())
            for data in Cohort.objects.filter()
        ]

    def all_academy_dict(self):
        return [
            self.remove_dinamics_fields(data.__dict__.copy())
            for data in Academy.objects.filter()
        ]

    def all_cohort_user_dict(self):
        return [
            self.remove_dinamics_fields(data.__dict__.copy())
            for data in CohortUser.objects.filter()
        ]

    def all_user_dict(self):
        return [
            self.remove_dinamics_fields(data.__dict__.copy())
            for data in User.objects.filter()
        ]

    def get_cohort(self, id):
        return Cohort.objects.filter(id=id).first()

    def get_cohort_user(self, id):
        return CohortUser.objects.filter(id=id).first()

    def get_user(self, id):
        return User.objects.filter(id=id).first()

    def count_cohort_user(self):
        return CohortUser.objects.count()

    def count_user(self):
        return User.objects.count()

    def count_cohort_stage(self, cohort_id):
        cohort = Cohort.objects.get(id=cohort_id)
        return cohort.stage

    def count_academy(self):
        return Academy.objects.count()

    def count_certificate(self):
        return Certificate.objects.count()

    def count_cohort(self):
        return Cohort.objects.count()

    def setUp(self):
        cache.clear()

    def headers(self, **kargs):
        headers = {}

        items = [
            index for index in kargs if kargs[index] and (
                isinstance(kargs[index], str) or isinstance(kargs[index], int))
        ]

        for index in items:
            headers[f'HTTP_{index.upper()}'] = str(kargs[index])

        self.client.credentials(**headers)

    def generate_models(self,
                        user=False,
                        authenticate=False,
                        syllabus=False,
                        academy=False,
                        cohort=False,
                        profile_academy=False,
                        certificate=False,
                        cohort_user=False,
                        impossible_kickoff_date=False,
                        finantial_status='',
                        educational_status='',
                        city=False,
                        country=False,
                        user_two=False,
                        cohort_two=False,
                        task=False,
                        task_status='',
                        task_type=''):
        # isinstance(True, bool)
        self.maxDiff = None

        if city or country:
            self.city = mixer.blend('admissions.City')

        if country:
            self.country = mixer.blend('admissions.Country')

        if academy or profile_academy:
            self.academy = mixer.blend('admissions.Academy')

        if certificate or profile_academy:
            self.certificate = mixer.blend('admissions.Certificate')
            self.syllabus = mixer.blend('admissions.Syllabus',
                                        certificate=self.certificate)

        if cohort or profile_academy or cohort_user:
            kargs = {}

            if profile_academy:
                kargs['syllabus'] = self.syllabus
                kargs['academy'] = self.academy

            if impossible_kickoff_date:
                kargs['kickoff_date'] = datetime(year=3000, month=1, day=1)

            self.cohort = mixer.blend('admissions.Cohort', **kargs)

        if cohort_two:
            kargs = {}

            if profile_academy:
                kargs['syllabus'] = mixer.blend('admissions.Syllabus',
                                                certificate=self.certificate)
                kargs['academy'] = self.academy

            self.cohort_two = mixer.blend('admissions.Cohort', **kargs)

        if user or authenticate or profile_academy or cohort_user or task:
            self.user = mixer.blend('auth.User')
            self.user.set_password(self.password)
            self.user.save()

        if task:
            kargs = {'user': self.user}

            if task_status:
                kargs['task_status'] = task_status

            if task_type:
                kargs['task_type'] = task_type

            self.task = mixer.blend('assignments.Task', **kargs)

        if user_two:
            self.user_two = mixer.blend('auth.User')
            self.user_two.set_password(self.password)
            self.user_two.save()

        if cohort_user:
            kargs = {}

            kargs['user'] = self.user
            kargs['cohort'] = self.cohort

            if finantial_status:
                kargs['finantial_status'] = finantial_status

            if educational_status:
                kargs['educational_status'] = educational_status

            self.cohort_user = mixer.blend('admissions.CohortUser', **kargs)

        if authenticate:
            self.client.force_authenticate(user=self.user)

        if profile_academy:
            self.profile_academy = mixer.blend('authenticate.ProfileAcademy',
                                               user=self.user,
                                               certificate=self.certificate,
                                               academy=self.academy)
