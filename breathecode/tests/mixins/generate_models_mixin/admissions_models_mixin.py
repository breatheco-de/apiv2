"""
Collections of mixins used to login in authorize microservice
"""
from random import choice, randint

from breathecode.tests.mixins.models_mixin import ModelsMixin
from breathecode.admissions.models import Cohort
from mixer.backend.django import mixer
from .utils import is_valid, create_models, just_one

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
                                   user_specialty=False,
                                   country=False,
                                   skip_cohort=False,
                                   syllabus=False,
                                   academy_specialty_mode=False,
                                   cohort_time_slot=False,
                                   syllabus_version=False,
                                   specialty_mode_time_slot=False,
                                   monitor_script=False,
                                   country_kwargs={},
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

        if not 'country' in models and is_valid(country):
            kargs = {}

            models['country'] = create_models(specialty_mode, 'admissions.Country', **{
                **kargs,
                **country_kwargs
            })

        if not 'city' in models and (is_valid(city) or is_valid(country)):
            kargs = {}

            if 'country' in models:
                kargs['country'] = just_one(models['country'])

            models['city'] = create_models(city, 'admissions.City', **{**kargs, **city_kwargs})

        if not 'academy' in models and (is_valid(academy) or is_valid(profile_academy) or is_valid(syllabus)
                                        or is_valid(academy_specialty_mode) or is_valid(cohort)
                                        or is_valid(monitor_script)):
            kargs = {}

            if 'country' in models:
                kargs['country'] = just_one(models['country'])

            if 'city' in models:
                kargs['city'] = just_one(models['city'])

            models['academy'] = create_models(academy, 'admissions.Academy', **{**kargs, **academy_kwargs})

        if not 'syllabus' in models and (is_valid(syllabus) or is_valid(syllabus_version)):
            kargs = {}

            if 'academy' in models:
                kargs['academy_owner'] = just_one(models['academy'])

            models['syllabus'] = create_models(syllabus, 'admissions.Syllabus', **{
                **kargs,
                **syllabus_kwargs
            })

        if not 'syllabus_version' in models and is_valid(syllabus_version):
            kargs = {}

            if 'syllabus' in models:
                kargs['syllabus'] = just_one(models['syllabus'])

            models['syllabus_version'] = create_models(syllabus_version, 'admissions.SyllabusVersion', **{
                **kargs,
                **syllabus_version_kwargs
            })

        if not 'specialty_mode' in models and is_valid(specialty_mode):
            kargs = {}

            if 'syllabus' in models:
                kargs['syllabus'] = just_one(models['syllabus'])

            models['specialty_mode'] = create_models(specialty_mode, 'admissions.SpecialtyMode', **{
                **kargs,
                **specialty_mode_kwargs
            })

        if not 'academy_specialty_mode' in models and is_valid(academy_specialty_mode):
            kargs = {}

            if 'specialty_mode' in models:
                kargs['specialty_mode'] = just_one(models['specialty_mode'])

            if 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            models['academy_specialty_mode'] = create_models(academy_specialty_mode,
                                                             'admissions.AcademySpecialtyMode', **{
                                                                 **kargs,
                                                                 **academy_specialty_mode_kwargs
                                                             })

        if not 'cohort' in models and not skip_cohort and (is_valid(cohort) or is_valid(profile_academy)
                                                           or is_valid(cohort_user) or is_valid(academy)):
            kargs = {}

            if profile_academy or 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            if 'syllabus_version' in models or syllabus_version:
                kargs['syllabus_version'] = just_one(models['syllabus_version'])

            if 'specialty_mode' in models or specialty_mode:
                kargs['specialty_mode'] = just_one(models['specialty_mode'])

            if 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            models['cohort'] = create_models(cohort, 'admissions.Cohort', **{**kargs, **cohort_kwargs})

        if not 'cohort_user' in models and not skip_cohort and is_valid(cohort_user):
            kargs = {}

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            if 'cohort' in models:
                kargs['cohort'] = just_one(models['cohort'])

            models['cohort_user'] = create_models(cohort_user, 'admissions.CohortUser', **{
                **kargs,
                **cohort_user_kwargs
            })

        if not 'specialty_mode_time_slot' in models and is_valid(specialty_mode_time_slot):
            kargs = {
                'starting_at': random_datetime_interger(),
                'ending_at': random_datetime_interger(),
                'timezone': choice(TIMEZONES),
            }

            if 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            if 'specialty_mode' in models:
                kargs['specialty_mode'] = just_one(models['specialty_mode'])

            models['specialty_mode_time_slot'] = create_models(specialty_mode_time_slot,
                                                               'admissions.SpecialtyModeTimeSlot', **{
                                                                   **kargs,
                                                                   **specialty_mode_time_slot_kwargs
                                                               })

        if not 'cohort_time_slot' in models and is_valid(cohort_time_slot):
            kargs = {
                'starting_at': random_datetime_interger(),
                'ending_at': random_datetime_interger(),
                'timezone': choice(TIMEZONES),
            }

            if 'cohort' in models:
                kargs['cohort'] = just_one(models['cohort'])

            models['cohort_time_slot'] = create_models(cohort_time_slot, 'admissions.CohortTimeSlot', **{
                **kargs,
                **cohort_time_slot_kwargs
            })

        return models
