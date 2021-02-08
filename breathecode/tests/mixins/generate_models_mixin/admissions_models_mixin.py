"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from breathecode.admissions.models import CohortUser, Cohort, Academy, Certificate, Syllabus
from datetime import datetime
from mixer.backend.django import mixer

class AdmissionsModelsMixin(ModelsMixin):

    def get_academy(self, id):
        return Academy.objects.filter(id=id).first()

    def get_academy_dict(self, id):
        data = Academy.objects.filter(id=id).first()
        return self.remove_dinamics_fields(data.__dict__.copy()) if data else None

    def get_certificate_dict(self, id):
        data = Certificate.objects.filter(id=id).first()
        return self.remove_dinamics_fields(data.__dict__.copy()) if data else None

    def get_cohort_user_dict(self, id):
        data = CohortUser.objects.filter(id=id).first()
        return self.remove_dinamics_fields(data.__dict__.copy()) if data else None

    def get_syllabus_dict(self, id):
        data = Syllabus.objects.filter(id=id).first()
        return self.remove_dinamics_fields(data.__dict__.copy()) if data else None

    def get_cohort_dict(self, id):
        data = Cohort.objects.filter(id=id).first()
        return self.remove_dinamics_fields(data.__dict__.copy()) if data else None

    def all_cohort_dict(self):
        return [self.remove_dinamics_fields(data.__dict__.copy()) for data in
            Cohort.objects.filter()]

    def all_academy_dict(self):
        return [self.remove_dinamics_fields(data.__dict__.copy()) for data in
            Academy.objects.filter()]

    def all_certificate_dict(self):
        return [self.remove_dinamics_fields(data.__dict__.copy()) for data in
            Certificate.objects.filter()]

    def all_syllabus_dict(self):
        return [self.remove_dinamics_fields(data.__dict__.copy()) for data in
            Syllabus.objects.filter()]

    def all_cohort_user_dict(self):
        return [self.remove_dinamics_fields(data.__dict__.copy()) for data in
            CohortUser.objects.filter()]

    def get_cohort(self, id):
        return Cohort.objects.filter(id=id).first()

    def get_syllabus(self, id):
        return Syllabus.objects.filter(id=id).first()
        
    def get_cohort_user(self, id):
        return CohortUser.objects.filter(id=id).first()

    def count_syllabus(self):
        return Syllabus.objects.count()

    def count_cohort_user(self):
        return CohortUser.objects.count()

    def count_cohort_stage(self, cohort_id):
        cohort = Cohort.objects.get(id=cohort_id)
        return cohort.stage

    def count_academy(self):
        return Academy.objects.count()

    def count_certificate(self):
        return Certificate.objects.count()

    def count_cohort(self):
        return Cohort.objects.count()

    def generate_admissions_models(self, certificate=False, academy=False,
            cohort=False, profile_academy=False, cohort_user=False, 
            impossible_kickoff_date=False, cohort_user_finantial_status='',
            cohort_user_educational_status='', city=False, country=False,
            skip_cohort=False, specialty=False, cohort_finished=False,
            cohort_stage='', language='', cohort_user_role='', syllabus=False,
            academy_certificate=False, models={}, **kwargs):
        models = models.copy()

        if not 'country' in models and country:
            models['country'] = mixer.blend('admissions.Country')

        if not 'city' in models and (city or country):
            kargs = {}

            if 'country' in models:
                kargs['country'] = models['country']

            models['city'] = mixer.blend('admissions.City', **kargs)

        if not 'academy' in models and (academy or profile_academy or syllabus or
                academy_certificate):
            kargs = {}

            if 'country' in models:
                kargs['country'] = models['country']

            if 'city' in models:
                kargs['city'] = models['city']

            models['academy'] = mixer.blend('admissions.Academy', **kargs)

        if not 'certificate' in models and (certificate or profile_academy or
                specialty or cohort or cohort_user or academy_certificate):
            models['certificate'] = mixer.blend('admissions.Certificate')

        if not 'academy_certificate' in models and academy_certificate:
            kargs = {}

            if 'certificate' in models:
                kargs['certificate'] = models['certificate']

            if 'academy' in models:
                kargs['academy'] = models['academy']

            models['academy_certificate'] = mixer.blend('admissions.AcademyCertificate', **kargs)

        if not 'syllabus' in models and syllabus:
            kargs = {}

            if certificate or 'certificate' in models:
                kargs['certificate'] = models['certificate']

            if academy or 'academy' in models:
                kargs['academy_owner'] = models['academy']

            models['syllabus'] = mixer.blend('admissions.Syllabus', **kargs)

        if not 'cohort' in models and not skip_cohort and (cohort or profile_academy or cohort_user):
            kargs = {}

            if 'syllabus' in models or syllabus:
                kargs['syllabus'] = models['syllabus']

            if profile_academy or 'academy' in models:
                kargs['academy'] = models['academy']

            if impossible_kickoff_date:
                kargs['kickoff_date'] = datetime(year=3000, month=1, day=1)

            if cohort_finished:
                kargs['current_day'] = models['certificate'].duration_in_days

            if cohort_stage:
                kargs['stage'] = cohort_stage

            if language:
                kargs['language'] = language

            models['cohort'] = mixer.blend('admissions.Cohort', **kargs)

        if not 'cohort_user' in models and not skip_cohort and cohort_user:
            kargs = {}

            if 'user' in models:
                kargs['user'] = models['user']

            if 'cohort' in models:
                kargs['cohort'] = models['cohort']

            if cohort_user_finantial_status:
                kargs['finantial_status'] = cohort_user_finantial_status

            if cohort_user_educational_status:
                kargs['educational_status'] = cohort_user_educational_status

            if cohort_user_role:
                kargs['role'] = cohort_user_role

            models['cohort_user'] = mixer.blend('admissions.CohortUser', **kargs)

        return models
