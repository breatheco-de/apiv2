"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from breathecode.admissions.models import Cohort
from django.utils import timezone
from datetime import datetime, timedelta
from mixer.backend.django import mixer


class AdmissionsModelsMixin(ModelsMixin):
    def count_cohort_stage(self, cohort_id):
        cohort = Cohort.objects.get(id=cohort_id)
        return cohort.stage

    def generate_admissions_models(self,
                                   certificate=False,
                                   academy=False,
                                   cohort=False,
                                   profile_academy=False,
                                   cohort_user=False,
                                   impossible_kickoff_date=False,
                                   cohort_user_finantial_status='',
                                   cohort_user_educational_status='',
                                   city=False,
                                   country=False,
                                   skip_cohort=False,
                                   specialty=False,
                                   cohort_finished=False,
                                   cohort_stage='',
                                   language='',
                                   cohort_user_role='',
                                   syllabus=False,
                                   academy_certificate=False,
                                   cohort_time_slot=False,
                                   time_slot=False,
                                   certificate_time_slot=False,
                                   country_kwargs={},
                                   time_slot_kwargs={},
                                   city_kwargs={},
                                   cohort_time_slot_kwargs={},
                                   academy_kwargs={},
                                   certificate_kwargs={},
                                   academy_certificate_kwargs={},
                                   syllabus_kwargs={},
                                   cohort_kwargs={},
                                   cohort_user_kwargs={},
                                   certificate_time_slot_kwargs={},
                                   models={},
                                   **kwargs):
        models = models.copy()

        if not 'country' in models and country:
            kargs = {}

            kargs = {**kargs, **country_kwargs}
            models['country'] = mixer.blend('admissions.Country', **kargs)

        if not 'city' in models and (city or country):
            kargs = {}

            if 'country' in models:
                kargs['country'] = models['country']

            kargs = {**kargs, **city_kwargs}
            models['city'] = mixer.blend('admissions.City', **kargs)

        if not 'academy' in models and (academy or profile_academy or syllabus
                                        or academy_certificate):
            kargs = {}

            if 'country' in models:
                kargs['country'] = models['country']

            if 'city' in models:
                kargs['city'] = models['city']

            kargs = {**kargs, **academy_kwargs}
            models['academy'] = mixer.blend('admissions.Academy', **kargs)

        if not 'certificate' in models and (certificate or profile_academy or
                                            specialty or cohort or cohort_user
                                            or academy_certificate):
            kargs = {}

            kargs = {**kargs, **certificate_kwargs}
            models['certificate'] = mixer.blend('admissions.Certificate',
                                                **kargs)

        if not 'academy_certificate' in models and academy_certificate:
            kargs = {}

            if 'certificate' in models:
                kargs['certificate'] = models['certificate']

            if 'academy' in models:
                kargs['academy'] = models['academy']

            kargs = {**kargs, **academy_certificate_kwargs}
            models['academy_certificate'] = mixer.blend(
                'admissions.AcademyCertificate', **kargs)

        if not 'syllabus' in models and syllabus:
            kargs = {}

            if certificate or 'certificate' in models:
                kargs['certificate'] = models['certificate']

            if academy or 'academy' in models:
                kargs['academy_owner'] = models['academy']

            kargs = {**kargs, **syllabus_kwargs}
            models['syllabus'] = mixer.blend('admissions.Syllabus', **kargs)

        if not 'cohort' in models and not skip_cohort and (cohort
                                                           or profile_academy
                                                           or cohort_user):
            kargs = {}

            if 'syllabus' in models or syllabus:
                kargs['syllabus'] = models['syllabus']

            if profile_academy or 'academy' in models:
                kargs['academy'] = models['academy']

            if impossible_kickoff_date:
                kargs['kickoff_date'] = timezone.now() + timedelta(days=365 *
                                                                   2000)

            if cohort_finished:
                kargs['current_day'] = models['certificate'].duration_in_days

            if cohort_stage:
                kargs['stage'] = cohort_stage

            if language:
                kargs['language'] = language

            kargs = {**kargs, **cohort_kwargs}
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

            kargs = {**kargs, **cohort_user_kwargs}
            models['cohort_user'] = mixer.blend('admissions.CohortUser',
                                                **kargs)

        if not 'time_slot' in models and time_slot:
            kargs = {}

            kargs = {**kargs, **time_slot_kwargs}
            models['time_slot'] = mixer.blend('admissions.TimeSlot', **kargs)

        if not 'certificate_time_slot' in models and certificate_time_slot:
            kargs = {}

            if 'certificate' in models:
                kargs['certificate'] = models['certificate']

            if 'academy' in models:
                kargs['academy'] = models['academy']

            kargs = {**kargs, **certificate_time_slot_kwargs}
            models['certificate_time_slot'] = mixer.blend(
                'admissions.CertificateTimeSlot', **kargs)

        if not 'cohort_time_slot' in models and cohort_time_slot:
            kargs = {}

            if 'cohort' in models:
                kargs['cohort'] = models['cohort']

            kargs = {**kargs, **cohort_time_slot_kwargs}
            models['cohort_time_slot'] = mixer.blend(
                'admissions.CohortTimeSlot', **kargs)

        return models
