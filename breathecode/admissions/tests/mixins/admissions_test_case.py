"""
Collections of mixins used to login in authorize microservice
"""
from datetime import datetime
from rest_framework.test import APITestCase
from mixer.backend.django import mixer
from breathecode.tests.mixins import DevelopmentEnvironment, DateFormatter
from ...models import CohortUser, Cohort
# from .models import Academy, CohortUser, Certificate, Cohort

class AdmissionsTestCase(APITestCase, DevelopmentEnvironment, DateFormatter):
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

    def get_cohort(self, id):
        return Cohort.objects.filter(id=id).first()
        
    def get_cohort_user(self, id):
        return CohortUser.objects.filter(id=id).first()

    def count_cohort_user(self):
        return CohortUser.objects.count()

    def count_cohort_stage(self, cohort_id):
        cohort = Cohort.objects.get(id=cohort_id)
        return cohort.stage

    def generate_models(self, user=False, authenticate=False, certificate=False, academy=False,
            cohort=False, profile_academy=False, cohort_user=False, impossible_kickoff_date=False,
            finantial_status='', educational_status='', city=False, country=False, user_two=True,
            cohort_two=False, task=False, task_status='', task_type=''):
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

        if cohort or profile_academy or cohort_user:
            kargs = {}

            if profile_academy:
                kargs['certificate'] = self.certificate
                kargs['academy'] = self.academy

            if impossible_kickoff_date:
                kargs['kickoff_date'] = datetime(year=3000, month=1, day=1)

            self.cohort = mixer.blend('admissions.Cohort', **kargs)

        if cohort_two:
            kargs = {}

            if profile_academy:
                kargs['certificate'] = self.certificate
                kargs['academy'] = self.academy

            self.cohort_two = mixer.blend('admissions.Cohort', **kargs)

        if user or authenticate or profile_academy or cohort_user or task:
            self.user = mixer.blend('auth.User')
            self.user.set_password(self.password)
            self.user.save()

        if task:
            kargs = {
                'user': self.user
            }

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
            self.profile_academy = mixer.blend('authenticate.ProfileAcademy', user=self.user,
                certificate=self.certificate, academy=self.academy)

