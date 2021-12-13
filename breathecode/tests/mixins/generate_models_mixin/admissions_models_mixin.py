"""
Collections of mixins used to login in authorize microservice
"""
from random import choice, randint
from breathecode.tests.mixins.models_mixin import ModelsMixin
from breathecode.admissions.models import Cohort
from mixer.backend.django import mixer

TIMEZONES = [
    'America/New_York', 'America/Bogota', 'America/Santiago', 'America/Buenos_Aires', 'Europe/Madrid',
    'America/Caracas'
]


def random_datetime_interger():
    year = '{:04d}'.format(randint(2021, 2999))
    month = '{:02d}'.format(randint(1, 12))
    day = '{:02d}'.format(randint(1, 28))
    hour = '{:02d}'.format(randint(0, 23))
    minute = '{:02d}'.format(randint(0, 59))

    return int(year + month + day + hour + minute)


class AdmissionsModelsMixin(ModelsMixin):
    def count_cohort_stage(self, cohort_id):
        cohort = Cohort.objects.get(id=cohort_id)
        return cohort.stage

    def generate_admissions_models(self,
                                   specialty_mode=False,
                                   academy=False,
                                   cohort=False,
                                   profile_academy=False,
                                   cohort_user=False,
                                   city=False,
                                   country=False,
                                   skip_cohort=False,
                                   syllabus=False,
                                   academy_specialty_mode=False,
                                   cohort_time_slot=False,
                                   time_slot=False,
                                   syllabus_version=False,
                                   specialty_mode_time_slot=False,
                                   country_kwargs={},
                                   time_slot_kwargs={},
                                   city_kwargs={},
                                   cohort_time_slot_kwargs={},
                                   academy_kwargs={},
                                   specialty_mode_kwargs={},
                                   academy_specialty_mode_kwargs={},
                                   syllabus_kwargs={},
                                   cohort_kwargs={},
                                   cohort_user_kwargs={},
                                   specialty_mode_time_slot_kwargs={},
                                   syllabus_version_kwargs={},
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

        if not 'academy' in models and (academy or profile_academy or syllabus or academy_specialty_mode):
            kargs = {}

            if 'country' in models:
                kargs['country'] = models['country']

            if 'city' in models:
                kargs['city'] = models['city']

            kargs = {**kargs, **academy_kwargs}
            models['academy'] = mixer.blend('admissions.Academy', **kargs)

        if not 'syllabus' in models and (syllabus or syllabus_version):
            kargs = {}

            if 'academy' in models:
                kargs['academy_owner'] = models['academy']

            kargs = {**kargs, **syllabus_kwargs}
            models['syllabus'] = mixer.blend('admissions.Syllabus', **kargs)

        if not 'syllabus_version' in models and syllabus_version:
            kargs = {}

            if 'syllabus' in models:
                kargs['syllabus'] = models['syllabus']

            kargs = {**kargs, **syllabus_version_kwargs}
            models['syllabus_version'] = mixer.blend('admissions.SyllabusVersion', **kargs)

        if not 'specialty_mode' in models and specialty_mode:
            kargs = {}

            if 'syllabus' in models:
                kargs['syllabus'] = models['syllabus']

            kargs = {**kargs, **specialty_mode_kwargs}
            models['specialty_mode'] = mixer.blend('admissions.SpecialtyMode', **kargs)

        if not 'academy_specialty_mode' in models and academy_specialty_mode:
            kargs = {}

            if 'specialty_mode' in models:
                kargs['specialty_mode'] = models['specialty_mode']

            if 'academy' in models:
                kargs['academy'] = models['academy']

            kargs = {**kargs, **academy_specialty_mode_kwargs}
            models['academy_specialty_mode'] = mixer.blend('admissions.AcademySpecialtyMode', **kargs)

        if not 'cohort' in models and not skip_cohort and (cohort or profile_academy or cohort_user
                                                           or academy):
            kargs = {}

            if profile_academy or 'academy' in models:
                kargs['academy'] = models['academy']

            if 'syllabus_version' in models or syllabus_version:
                kargs['syllabus_version'] = models['syllabus_version']

            if 'specialty_mode' in models or specialty_mode:
                kargs['specialty_mode'] = models['specialty_mode']

            kargs = {**kargs, **cohort_kwargs}
            models['cohort'] = mixer.blend('admissions.Cohort', **kargs)

        if not 'cohort_user' in models and not skip_cohort and cohort_user:
            kargs = {}

            if 'user' in models:
                kargs['user'] = models['user']

            if 'cohort' in models:
                kargs['cohort'] = models['cohort']

            kargs = {**kargs, **cohort_user_kwargs}
            models['cohort_user'] = mixer.blend('admissions.CohortUser', **kargs)

        if not 'time_slot' in models and time_slot:
            kargs = {
                'starting_at': random_datetime_interger(),
                'ending_at': random_datetime_interger(),
                'timezone': choice(TIMEZONES),
            }

            kargs = {**kargs, **time_slot_kwargs}
            models['time_slot'] = mixer.blend('admissions.TimeSlot', **kargs)

        if not 'specialty_mode_time_slot' in models and specialty_mode_time_slot:
            kargs = {
                'starting_at': random_datetime_interger(),
                'ending_at': random_datetime_interger(),
                'timezone': choice(TIMEZONES),
            }

            if 'academy' in models:
                kargs['academy'] = models['academy']

            if 'specialty_mode' in models:
                kargs['specialty_mode'] = models['specialty_mode']

            kargs = {**kargs, **specialty_mode_time_slot_kwargs}
            models['specialty_mode_time_slot'] = mixer.blend('admissions.SpecialtyModeTimeSlot', **kargs)

        if not 'cohort_time_slot' in models and cohort_time_slot:
            kargs = {
                'starting_at': random_datetime_interger(),
                'ending_at': random_datetime_interger(),
                'timezone': choice(TIMEZONES),
            }

            if 'cohort' in models:
                kargs['cohort'] = models['cohort']

            kargs = {**kargs, **cohort_time_slot_kwargs}
            models['cohort_time_slot'] = mixer.blend('admissions.CohortTimeSlot', **kargs)

        return models
