"""
Collections of mixins used to login in authorize microservice
"""
from datetime import datetime
from rest_framework.test import APITestCase
from mixer.backend.django import mixer
from breathecode.tests.mixins import DevelopmentEnvironment, DateFormatterMixin


class GenerateModels(APITestCase, DevelopmentEnvironment, DateFormatterMixin):
    """AdmissionsTestCase wrapper to allow multiple instances"""
    # token = None
    user = None
    password = 'pass1234'
    certificate = None
    academy = None
    cohort = None
    profile_academy = None
    cohort_user = None

    def __init__(self,
                 user=False,
                 authenticate=False,
                 certificate=False,
                 academy=False,
                 cohort=False,
                 profile_academy=False,
                 cohort_user=False,
                 impossible_kickoff_date=False,
                 finantial_status='',
                 educational_status=''):
        # super()

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

        if user or authenticate or profile_academy or cohort_user:
            self.user = mixer.blend('auth.User')
            self.user.set_password(self.password)
            self.user.save()

        # if cohort_user:
        #     kargs = {}

        #     kargs['user'] = self.user
        #     kargs['cohort'] = self.cohort

        #     if finantial_status:
        #         kargs['finantial_status'] = finantial_status

        #     if educational_status:
        #         kargs['educational_status'] = educational_status

        #     self.cohort_user = mixer.blend('admissions.CohortUser', **kargs)

        if profile_academy:
            self.profile_academy = mixer.blend('authenticate.ProfileAcademy',
                                               user=self.user,
                                               certificate=self.certificate,
                                               academy=self.academy)

    # def authenticate(self):
    #     if self.user:
    #         self.client.force_authenticate(user=self.user)
