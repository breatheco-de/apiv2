"""
Collections of mixins used to login in authorize microservice
"""
from rest_framework.test import APITestCase
from mixer.backend.django import mixer
from breathecode.tests.mixins import DevelopmentEnvironment

class AdmissionsTestCase(APITestCase, DevelopmentEnvironment):
    """AdmissionsTestCase with auth methods"""
     # token = None
    user = None
    password = 'pass1234'
    certificate = None
    academy = None
    cohort = None
    profile_academy = None
    cohort_user = None

    def generate_models(self, user=False, authenticate=False, certificate=False, academy=False,
            cohort=False, profile_academy=False, cohort_user=False):
        if academy or profile_academy:
            self.academy = mixer.blend('admissions.Academy')

        if certificate or profile_academy:
            self.certificate = mixer.blend('admissions.Certificate')

        if cohort or profile_academy or cohort_user:
            if profile_academy:
                self.cohort = mixer.blend('admissions.Cohort', certificate=self.certificate,
                    academy=self.academy)
            else:
                self.cohort = mixer.blend('admissions.Cohort')

        if user or authenticate or profile_academy or cohort_user:
            self.user = mixer.blend('auth.User')
            self.user.set_password(self.password)
            self.user.save()

        if cohort_user:
            self.cohort_user = mixer.blend('admissions.CohortUser', user=self.user,
                cohort=self.cohort)

        if authenticate:
            self.client.force_authenticate(user=self.user)

        if profile_academy:
            self.profile_academy = mixer.blend('authenticate.ProfileAcademy', user=self.user,
                certificate=self.certificate, academy=self.academy)

