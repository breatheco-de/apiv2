"""
Test /academy/cohort
"""
import re
from django.utils import timezone
from breathecode.admissions.caches import CohortCache
from breathecode.services import datetime_to_iso_format
from random import choice
from datetime import datetime, timedelta
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AdmissionsTestCase


class AcademyCohortTestSuite(AdmissionsTestCase):
    """Test /academy/cohort"""

    cache = CohortCache()
    """
    🔽🔽🔽 Auth
    """
    def test_academy_cohort__post__without_authorization(self):
        """Test /academy/cohort without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort')
        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort__without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': 1})
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.post(url, data)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: crud_cohort for academy 1",
            'status_code': 403
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 Post
    """

    def test_academy_cohort__post__without_profile_academy(self):
        """Test /academy/cohort without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus=True)
        url = reverse_lazy('admissions:academy_cohort')
        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'detail': 'missing-syllabus-field',
            'status_code': status.HTTP_400_BAD_REQUEST,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort__post__with_bad_fields(self):
        """Test /academy/cohort without auth"""
        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     specialty_mode=True,
                                     syllabus=True,
                                     syllabus_kwargs=syllabus_kwargs)
        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'syllabus': model['syllabus'].id,
            'specialty_mode': 1,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'slug': ['This field is required.'],
            'name': ['This field is required.'],
            'kickoff_date': ['This field is required.'],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort__post__with_bad_current_day(self):
        """Test /academy/cohort without auth"""
        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus=True,
                                     specialty_mode=True,
                                     syllabus_kwargs=syllabus_kwargs)
        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'syllabus': model['syllabus'].id,
            'current_day': 999,
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'kickoff_date': datetime.today().isoformat(),
            'specialty_mode': 1,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'current-day-not-allowed', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    # def test_academy_cohort__post__without_specialty_mode(self):
    #     """Test /academy/cohort without auth"""
    #     self.headers(academy=1)
    #     model = self.generate_models(authenticate=True,
    #                                  user=True,
    #                                  profile_academy=True,
    #                                  capability='crud_cohort',
    #                                  role='potato',
    #                                  specialty_mode=True,
    #                                  syllabus=True,
    #                                  syllabus_version=True,
    #                                  skip_cohort=True,
    #                                  specialty_mode_time_slot=True)
    #     url = reverse_lazy('admissions:academy_cohort')
    #     data = {
    #         'syllabus': f'{model.syllabus.slug}.v{model.syllabus_version.version}',
    #         'slug': 'they-killed-kenny',
    #         'name': 'They killed kenny',
    #         'kickoff_date': datetime.today().isoformat(),
    #     }
    #     response = self.client.post(url, data)
    #     json = response.json()
    #     expected = {
    #         'detail': 'specialty-mode-field',
    #         'status_code': 400,
    #     }

    #     self.assertEqual(json, expected)
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    #     self.assertEqual(self.all_cohort_dict(), [])
    #     self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort__post__without_ending_date_or_never_ends(self):
        """Test /academy/cohort without auth"""
        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        model = self.generate_models(authenticate=True,
                                     user=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     specialty_mode=True,
                                     syllabus=True,
                                     syllabus_version=True,
                                     skip_cohort=True,
                                     specialty_mode_time_slot=True,
                                     syllabus_kwargs=syllabus_kwargs)
        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'syllabus': f'{model.syllabus.slug}.v{model.syllabus_version.version}',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'kickoff_date': datetime.today().isoformat(),
            'specialty_mode': 1,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'detail': 'cohort-without-ending-date-and-never-ends',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort__post__with_ending_date_and_never_ends_true(self):
        """Test /academy/cohort without auth"""
        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        model = self.generate_models(authenticate=True,
                                     user=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     specialty_mode=True,
                                     syllabus=True,
                                     syllabus_version=True,
                                     skip_cohort=True,
                                     specialty_mode_time_slot=True,
                                     syllabus_kwargs=syllabus_kwargs)
        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'syllabus': f'{model.syllabus.slug}.v{model.syllabus_version.version}',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'kickoff_date': datetime.today().isoformat(),
            'ending_date': datetime.today().isoformat(),
            'never_ends': True,
            'specialty_mode': 1,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'detail': 'cohort-with-ending-date-and-never-ends',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort__post__without_ending_date_and_never_ends_false(self):
        """Test /academy/cohort without auth"""
        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        model = self.generate_models(authenticate=True,
                                     user=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     specialty_mode=True,
                                     syllabus=True,
                                     syllabus_version=True,
                                     skip_cohort=True,
                                     specialty_mode_time_slot=True,
                                     syllabus_kwargs=syllabus_kwargs)
        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'syllabus': f'{model.syllabus.slug}.v{model.syllabus_version.version}',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'kickoff_date': datetime.today().isoformat(),
            'never_ends': False,
            'specialty_mode': 1,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'detail': 'cohort-without-ending-date-and-never-ends',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort__post__without_timezone(self):
        """Test /academy/cohort without auth"""
        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        model = self.generate_models(authenticate=True,
                                     user=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     specialty_mode=True,
                                     syllabus=True,
                                     syllabus_version=True,
                                     skip_cohort=True,
                                     specialty_mode_time_slot=True,
                                     syllabus_kwargs=syllabus_kwargs)
        models_dict = self.all_cohort_dict()
        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'syllabus': f'{model.syllabus.slug}.v{model.syllabus_version.version}',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'kickoff_date': datetime.today().isoformat(),
            'never_ends': True,
            'specialty_mode': 1,
        }
        response = self.client.post(url, data)
        json = response.json()
        cohort = self.get_cohort(1)
        expected = {
            'id': cohort.id,
            'slug': cohort.slug,
            'name': cohort.name,
            'never_ends': True,
            'kickoff_date': self.datetime_to_iso(cohort.kickoff_date),
            'current_day': cohort.current_day,
            'specialty_mode': cohort.specialty_mode.id,
            'online_meeting_url': cohort.online_meeting_url,
            'timezone': cohort.timezone,
            'academy': {
                'id': cohort.academy.id,
                'slug': cohort.academy.slug,
                'name': cohort.academy.name,
                'street_address': cohort.academy.street_address,
                'country': cohort.academy.country.code,
                'city': cohort.academy.city.id,
            },
            'syllabus_version': model['syllabus'].slug + '.v' + str(model['syllabus_version'].version),
            'ending_date': cohort.ending_date,
            'stage': cohort.stage,
            'language': cohort.language,
            'created_at': self.datetime_to_iso(cohort.created_at),
            'updated_at': self.datetime_to_iso(cohort.updated_at),
        }

        del data['kickoff_date']
        cohort_two = cohort.__dict__.copy()
        cohort_two.update(data)
        del cohort_two['syllabus']
        del cohort_two['specialty_mode']

        models_dict.append(self.remove_dinamics_fields({**cohort_two}))

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_cohort_dict(), models_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort__post__with_timezone(self):
        """Test /academy/cohort without auth"""
        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        academy_kwargs = {'timezone': 'America/Caracas'}
        model = self.generate_models(authenticate=True,
                                     user=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     specialty_mode=True,
                                     syllabus=True,
                                     syllabus_version=True,
                                     skip_cohort=True,
                                     specialty_mode_time_slot=True,
                                     syllabus_kwargs=syllabus_kwargs,
                                     academy_kwargs=academy_kwargs)
        models_dict = self.all_cohort_dict()
        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'syllabus': f'{model.syllabus.slug}.v{model.syllabus_version.version}',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'kickoff_date': datetime.today().isoformat(),
            'never_ends': True,
            'specialty_mode': 1,
        }
        response = self.client.post(url, data)
        json = response.json()
        cohort = self.get_cohort(1)
        expected = {
            'id': cohort.id,
            'slug': cohort.slug,
            'name': cohort.name,
            'never_ends': True,
            'kickoff_date': self.datetime_to_iso(cohort.kickoff_date),
            'current_day': cohort.current_day,
            'specialty_mode': cohort.specialty_mode.id,
            'online_meeting_url': cohort.online_meeting_url,
            'timezone': cohort.timezone,
            'academy': {
                'id': cohort.academy.id,
                'slug': cohort.academy.slug,
                'name': cohort.academy.name,
                'street_address': cohort.academy.street_address,
                'country': cohort.academy.country.code,
                'city': cohort.academy.city.id,
            },
            'syllabus_version': model['syllabus'].slug + '.v' + str(model['syllabus_version'].version),
            'ending_date': cohort.ending_date,
            'stage': cohort.stage,
            'language': cohort.language,
            'created_at': self.datetime_to_iso(cohort.created_at),
            'updated_at': self.datetime_to_iso(cohort.updated_at),
        }

        del data['kickoff_date']
        cohort_two = cohort.__dict__.copy()
        cohort_two.update(data)
        del cohort_two['syllabus']
        del cohort_two['specialty_mode']

        models_dict.append(self.remove_dinamics_fields({**cohort_two}))

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_cohort_dict(), models_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(),
                         [{
                             'id': 1,
                             'cohort_id': 1,
                             'starting_at': model.specialty_mode_time_slot.starting_at,
                             'ending_at': model.specialty_mode_time_slot.ending_at,
                             'recurrent': model.specialty_mode_time_slot.recurrent,
                             'recurrency_type': model.specialty_mode_time_slot.recurrency_type,
                             'timezone': model.academy.timezone,
                         }])

    # """

    # NEW TESTS HERE!!!
    """
    🔽🔽🔽 Without data
    """

    def test_academy_cohort_without_data(self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort')
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_cohort',
                                     role='potato',
                                     syllabus=True,
                                     skip_cohort=True)

        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 0)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 With data (this method is reusable)
    """

    def test_academy_cohort__with_data(self, models=None):
        """Test /cohort without auth"""
        self.headers(academy=1)

        cohort_time_slots = self.all_cohort_time_slot_dict()
        if cohort_time_slots:
            cohort_time_slot = cohort_time_slots[0]

        if models is None:
            syllabus_kwargs = {'slug': 'they-killed-kenny'}
            academy_kwargs = {'timezone': 'America/Caracas'}
            models = [
                self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_cohort',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True,
                                     specialty_mode=True,
                                     specialty_mode_time_slot=True,
                                     syllabus_kwargs=syllabus_kwargs,
                                     academy_kwargs=academy_kwargs)
            ]

        models.sort(key=lambda x: x.cohort.kickoff_date, reverse=True)

        url = reverse_lazy('admissions:academy_cohort')
        response = self.client.get(url)
        json = response.json()

        expected = [{
            'id':
            model['cohort'].id,
            'slug':
            model['cohort'].slug,
            'name':
            model['cohort'].name,
            'never_ends':
            model['cohort'].never_ends,
            'private':
            model['cohort'].private,
            'kickoff_date':
            re.sub(r'\+00:00$', 'Z', model['cohort'].kickoff_date.isoformat()),
            'ending_date':
            model['cohort'].ending_date,
            'stage':
            model['cohort'].stage,
            'language':
            model['cohort'].language,
            'current_day':
            model['cohort'].current_day,
            'online_meeting_url':
            model['cohort'].online_meeting_url,
            'timezone':
            model['cohort'].timezone,
            'timeslots': [{
                'ending_at':
                self.interger_to_iso(cohort_time_slot['timezone'], cohort_time_slot['ending_at']),
                'id':
                cohort_time_slot['id'],
                'recurrency_type':
                cohort_time_slot['recurrency_type'],
                'recurrent':
                cohort_time_slot['recurrent'],
                'starting_at':
                self.interger_to_iso(cohort_time_slot['timezone'], cohort_time_slot['starting_at']),
            }] if cohort_time_slots and model.cohort.id != 1 else [],
            'specialty_mode': {
                'id': model['cohort'].specialty_mode.id,
                'name': model['cohort'].specialty_mode.name,
                'syllabus': model['cohort'].specialty_mode.syllabus.id,
            },
            'syllabus_version': {
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'version': model['cohort'].syllabus_version.version,
                'syllabus': model['cohort'].syllabus_version.syllabus.id,
                'duration_in_days': model.syllabus.duration_in_days,
                'duration_in_hours': model.syllabus.duration_in_hours,
                'github_url': model.syllabus.github_url,
                'logo': model.syllabus.logo,
                'private': model.syllabus.private,
                'week_hours': model.syllabus.week_hours,
            },
            'academy': {
                'id': model['cohort'].academy.id,
                'slug': model['cohort'].academy.slug,
                'name': model['cohort'].academy.name,
                'country': {
                    'code': model['cohort'].academy.country.code,
                    'name': model['cohort'].academy.country.name,
                },
                'city': {
                    'name': model['cohort'].academy.city.name,
                },
                'logo_url': model['cohort'].academy.logo_url,
            },
        } for model in models]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), self.all_model_dict([x.cohort for x in models]))
        return models

    """
    🔽🔽🔽 Put
    """

    def test_academy_cohort__put__without_id(self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort')
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus=True)
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(json, {'detail': 'Missing cohort_id', 'status_code': 400})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 Get
    """

    def test_academy_cohort__with_data__with_upcoming_false(self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_cohort',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True,
                                     specialty_mode=True)
        model_dict = self.remove_dinamics_fields(model['cohort'].__dict__)
        base_url = reverse_lazy('admissions:academy_cohort')
        url = f'{base_url}?upcoming=false'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort'].id,
            'slug': model['cohort'].slug,
            'name': model['cohort'].name,
            'never_ends': model['cohort'].never_ends,
            'private': model['cohort'].private,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', model['cohort'].kickoff_date.isoformat()),
            'ending_date': model['cohort'].ending_date,
            'stage': model['cohort'].stage,
            'language': model['cohort'].language,
            'current_day': model['cohort'].current_day,
            'online_meeting_url': model['cohort'].online_meeting_url,
            'timezone': model['cohort'].timezone,
            'timeslots': [],
            'specialty_mode': {
                'id': model['cohort'].specialty_mode.id,
                'name': model['cohort'].specialty_mode.name,
                'syllabus': model['cohort'].specialty_mode.syllabus.id,
            },
            'syllabus_version': {
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'version': model['cohort'].syllabus_version.version,
                'syllabus': model['cohort'].syllabus_version.syllabus.id,
                'duration_in_days': model.syllabus.duration_in_days,
                'duration_in_hours': model.syllabus.duration_in_hours,
                'github_url': model.syllabus.github_url,
                'logo': model.syllabus.logo,
                'private': model.syllabus.private,
                'week_hours': model.syllabus.week_hours,
            },
            'academy': {
                'id': model['cohort'].academy.id,
                'slug': model['cohort'].academy.slug,
                'name': model['cohort'].academy.name,
                'country': {
                    'code': model['cohort'].academy.country.code,
                    'name': model['cohort'].academy.country.name,
                },
                'city': {
                    'name': model['cohort'].academy.city.name,
                },
                'logo_url': model['cohort'].academy.logo_url,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort__with_data__with_upcoming_true__without_data(self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        self.clear_cache()
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_cohort',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True,
                                     specialty_mode=True)
        model_dict = self.remove_dinamics_fields(model['cohort'].__dict__)
        base_url = reverse_lazy('admissions:academy_cohort')
        url = f'{base_url}?upcoming=true'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort__with_data__with_upcoming_true(self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        cohort_kwargs = {
            'kickoff_date': timezone.now() + timedelta(days=1),
        }
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_cohort',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True,
                                     specialty_mode=True,
                                     cohort_kwargs=cohort_kwargs)

        model_dict = self.get_cohort_dict(1)
        base_url = reverse_lazy('admissions:academy_cohort')
        url = f'{base_url}?upcoming=true'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort'].id,
            'slug': model['cohort'].slug,
            'name': model['cohort'].name,
            'never_ends': model['cohort'].never_ends,
            'private': model['cohort'].private,
            'kickoff_date': self.datetime_to_iso(model['cohort'].kickoff_date),
            'ending_date': model['cohort'].ending_date,
            'stage': model['cohort'].stage,
            'language': model['cohort'].language,
            'current_day': model['cohort'].current_day,
            'online_meeting_url': model['cohort'].online_meeting_url,
            'timezone': model['cohort'].timezone,
            'timeslots': [],
            'specialty_mode': {
                'id': model['cohort'].specialty_mode.id,
                'name': model['cohort'].specialty_mode.name,
                'syllabus': model['cohort'].specialty_mode.syllabus.id,
            },
            'syllabus_version': {
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'version': model['cohort'].syllabus_version.version,
                'syllabus': model['cohort'].syllabus_version.syllabus.id,
                'duration_in_days': model.syllabus.duration_in_days,
                'duration_in_hours': model.syllabus.duration_in_hours,
                'github_url': model.syllabus.github_url,
                'logo': model.syllabus.logo,
                'private': model.syllabus.private,
                'week_hours': model.syllabus.week_hours,
            },
            'academy': {
                'id': model['cohort'].academy.id,
                'slug': model['cohort'].academy.slug,
                'name': model['cohort'].academy.name,
                'country': {
                    'code': model['cohort'].academy.country.code,
                    'name': model['cohort'].academy.country.name,
                },
                'city': {
                    'name': model['cohort'].academy.city.name,
                },
                'logo_url': model['cohort'].academy.logo_url,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort__with_data__with_bad_academy(self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     impossible_kickoff_date=True,
                                     profile_academy=True,
                                     capability='read_cohort',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True,
                                     specialty_mode=True)

        model_dict = self.get_cohort_dict(1)
        base_url = reverse_lazy('admissions:academy_cohort')
        url = f'{base_url}?academy=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort_with_data_with_academy(self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_cohort',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True,
                                     specialty_mode=True)

        model_dict = self.get_cohort_dict(1)
        base_url = reverse_lazy('admissions:academy_cohort')
        url = f'{base_url}?academy=' + model['academy'].slug
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort'].id,
            'slug': model['cohort'].slug,
            'name': model['cohort'].name,
            'never_ends': model['cohort'].never_ends,
            'private': model['cohort'].private,
            'kickoff_date': self.datetime_to_iso(model['cohort'].kickoff_date),
            'ending_date': model['cohort'].ending_date,
            'stage': model['cohort'].stage,
            'language': model['cohort'].language,
            'current_day': model['cohort'].current_day,
            'online_meeting_url': model['cohort'].online_meeting_url,
            'timezone': model['cohort'].timezone,
            'timeslots': [],
            'specialty_mode': {
                'id': model['cohort'].specialty_mode.id,
                'name': model['cohort'].specialty_mode.name,
                'syllabus': model['cohort'].specialty_mode.syllabus.id,
            },
            'syllabus_version': {
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'version': model['cohort'].syllabus_version.version,
                'syllabus': model['cohort'].syllabus_version.syllabus.id,
                'duration_in_days': model.syllabus.duration_in_days,
                'duration_in_hours': model.syllabus.duration_in_hours,
                'github_url': model.syllabus.github_url,
                'logo': model.syllabus.logo,
                'private': model.syllabus.private,
                'week_hours': model.syllabus.week_hours,
            },
            'academy': {
                'id': model['cohort'].academy.id,
                'slug': model['cohort'].academy.slug,
                'name': model['cohort'].academy.name,
                'country': {
                    'code': model['cohort'].academy.country.code,
                    'name': model['cohort'].academy.country.name,
                },
                'city': {
                    'name': model['cohort'].academy.city.name,
                },
                'logo_url': model['cohort'].academy.logo_url,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort_with_data_with_academy_with_comma(self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_cohort',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True,
                                     specialty_mode=True)

        model_dict = self.get_cohort_dict(1)
        base_url = reverse_lazy('admissions:academy_cohort')
        url = f'{base_url}?academy=' + model['academy'].slug + ',they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort'].id,
            'slug': model['cohort'].slug,
            'name': model['cohort'].name,
            'never_ends': model['cohort'].never_ends,
            'private': model['cohort'].private,
            'kickoff_date': self.datetime_to_iso(model['cohort'].kickoff_date),
            'ending_date': model['cohort'].ending_date,
            'stage': model['cohort'].stage,
            'language': model['cohort'].language,
            'current_day': model['cohort'].current_day,
            'online_meeting_url': model['cohort'].online_meeting_url,
            'timezone': model['cohort'].timezone,
            'timeslots': [],
            'specialty_mode': {
                'id': model['cohort'].specialty_mode.id,
                'name': model['cohort'].specialty_mode.name,
                'syllabus': model['cohort'].specialty_mode.syllabus.id,
            },
            'syllabus_version': {
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'version': model['cohort'].syllabus_version.version,
                'syllabus': model['cohort'].syllabus_version.syllabus.id,
                'duration_in_days': model.syllabus.duration_in_days,
                'duration_in_hours': model.syllabus.duration_in_hours,
                'github_url': model.syllabus.github_url,
                'logo': model.syllabus.logo,
                'private': model.syllabus.private,
                'week_hours': model.syllabus.week_hours,
            },
            'academy': {
                'id': model['cohort'].academy.id,
                'slug': model['cohort'].academy.slug,
                'name': model['cohort'].academy.name,
                'country': {
                    'code': model['cohort'].academy.country.code,
                    'name': model['cohort'].academy.country.name,
                },
                'city': {
                    'name': model['cohort'].academy.city.name,
                },
                'logo_url': model['cohort'].academy.logo_url,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort_with_ten_datas_with_academy_with_comma(self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        models = [
            self.generate_models(authenticate=True,
                                 cohort=True,
                                 profile_academy=True,
                                 capability='read_cohort',
                                 role='potato',
                                 syllabus=True,
                                 syllabus_version=True,
                                 specialty_mode=True)
        ]

        base = models[0].copy()
        del base['cohort']

        models = models + [self.generate_models(cohort=True, models=base) for index in range(0, 9)]
        models.sort(key=lambda x: x.cohort.kickoff_date, reverse=True)

        self.client.force_authenticate(user=models[0]['user'])
        base_url = reverse_lazy('admissions:academy_cohort')
        params = ','.join([model['academy'].slug for model in models])
        url = f'{base_url}?academy={params}'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort'].id,
            'slug': model['cohort'].slug,
            'name': model['cohort'].name,
            'never_ends': model['cohort'].never_ends,
            'private': model['cohort'].private,
            'language': model['cohort'].language,
            'kickoff_date': datetime_to_iso_format(model['cohort'].kickoff_date),
            'ending_date': model['cohort'].ending_date,
            'stage': model['cohort'].stage,
            'current_day': model['cohort'].current_day,
            'online_meeting_url': model['cohort'].online_meeting_url,
            'timezone': model['cohort'].timezone,
            'timeslots': [],
            'specialty_mode': {
                'id': model['cohort'].specialty_mode.id,
                'name': model['cohort'].specialty_mode.name,
                'syllabus': model['cohort'].specialty_mode.syllabus.id,
            },
            'syllabus_version': {
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'version': model['cohort'].syllabus_version.version,
                'syllabus': model['cohort'].syllabus_version.syllabus.id,
                'duration_in_days': model.syllabus.duration_in_days,
                'duration_in_hours': model.syllabus.duration_in_hours,
                'github_url': model.syllabus.github_url,
                'logo': model.syllabus.logo,
                'private': model.syllabus.private,
                'week_hours': model.syllabus.week_hours,
            },
            'academy': {
                'id': model['cohort'].academy.id,
                'slug': model['cohort'].academy.slug,
                'name': model['cohort'].academy.name,
                'country': {
                    'code': model['cohort'].academy.country.code,
                    'name': model['cohort'].academy.country.name,
                },
                'city': {
                    'name': model['cohort'].academy.city.name,
                },
                'logo_url': model['cohort'].academy.logo_url,
            },
        } for model in models]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), self.all_model_dict([x.cohort for x in models]))
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 Sort in querystring
    """

    def test_academy_cohort__with_data__with_sort(self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_cohort',
                                    role='potato',
                                    skip_cohort=True)

        models = [
            self.generate_models(cohort=True,
                                 syllabus=True,
                                 syllabus_version=True,
                                 specialty_mode=True,
                                 models=base) for _ in range(0, 2)
        ]
        ordened_models = sorted(models, key=lambda x: x['cohort'].slug, reverse=True)

        url = reverse_lazy('admissions:academy_cohort') + '?sort=-slug'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort'].id,
            'slug': model['cohort'].slug,
            'name': model['cohort'].name,
            'current_day': model.cohort.current_day,
            'never_ends': model['cohort'].never_ends,
            'private': model['cohort'].private,
            'kickoff_date': self.datetime_to_iso(model['cohort'].kickoff_date),
            'ending_date': model['cohort'].ending_date,
            'stage': model['cohort'].stage,
            'language': model['cohort'].language,
            'online_meeting_url': model['cohort'].online_meeting_url,
            'timezone': model['cohort'].timezone,
            'timeslots': [],
            'specialty_mode': {
                'id': model['cohort'].specialty_mode.id,
                'name': model['cohort'].specialty_mode.name,
                'syllabus': model['cohort'].specialty_mode.syllabus.id,
            },
            'syllabus_version': {
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'version': model['cohort'].syllabus_version.version,
                'syllabus': model['cohort'].syllabus_version.syllabus.id,
                'duration_in_days': model.syllabus.duration_in_days,
                'duration_in_hours': model.syllabus.duration_in_hours,
                'github_url': model.syllabus.github_url,
                'logo': model.syllabus.logo,
                'private': model.syllabus.private,
                'week_hours': model.syllabus.week_hours,
            },
            'academy': {
                'id': model['cohort'].academy.id,
                'slug': model['cohort'].academy.slug,
                'name': model['cohort'].academy.name,
                'country': {
                    'code': model['cohort'].academy.country.code,
                    'name': model['cohort'].academy.country.name,
                },
                'city': {
                    'name': model['cohort'].academy.city.name,
                },
                'logo_url': model['cohort'].academy.logo_url,
            },
        } for model in ordened_models]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        } for model in models])

    def test_academy_cohort_with_data_with_bad_location(self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_cohort',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True,
                                     specialty_mode=True)

        model_dict = self.get_cohort_dict(1)
        base_url = reverse_lazy('admissions:academy_cohort')
        url = f'{base_url}?location=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort_with_data_with_location(self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_cohort',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True,
                                     specialty_mode=True)

        model_dict = self.get_cohort_dict(1)
        base_url = reverse_lazy('admissions:academy_cohort')
        url = f'{base_url}?location=' + model['academy'].slug
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort'].id,
            'slug': model['cohort'].slug,
            'name': model['cohort'].name,
            'never_ends': model['cohort'].never_ends,
            'private': model['cohort'].private,
            'kickoff_date': self.datetime_to_iso(model['cohort'].kickoff_date),
            'ending_date': model['cohort'].ending_date,
            'stage': model['cohort'].stage,
            'language': model['cohort'].language,
            'current_day': model['cohort'].current_day,
            'online_meeting_url': model['cohort'].online_meeting_url,
            'timezone': model['cohort'].timezone,
            'timeslots': [],
            'specialty_mode': {
                'id': model['cohort'].specialty_mode.id,
                'name': model['cohort'].specialty_mode.name,
                'syllabus': model['cohort'].specialty_mode.syllabus.id,
            },
            'syllabus_version': {
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'version': model['cohort'].syllabus_version.version,
                'syllabus': model['cohort'].syllabus_version.syllabus.id,
                'duration_in_days': model.syllabus.duration_in_days,
                'duration_in_hours': model.syllabus.duration_in_hours,
                'github_url': model.syllabus.github_url,
                'logo': model.syllabus.logo,
                'private': model.syllabus.private,
                'week_hours': model.syllabus.week_hours,
            },
            'academy': {
                'id': model['cohort'].academy.id,
                'slug': model['cohort'].academy.slug,
                'name': model['cohort'].academy.name,
                'country': {
                    'code': model['cohort'].academy.country.code,
                    'name': model['cohort'].academy.country.name,
                },
                'city': {
                    'name': model['cohort'].academy.city.name,
                },
                'logo_url': model['cohort'].academy.logo_url,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort_with_data_with_location_with_comma(self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_cohort',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True,
                                     specialty_mode=True)

        model_dict = self.get_cohort_dict(1)
        base_url = reverse_lazy('admissions:academy_cohort')
        url = f'{base_url}?location=' + model['academy'].slug + ',they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort'].id,
            'slug': model['cohort'].slug,
            'name': model['cohort'].name,
            'never_ends': model['cohort'].never_ends,
            'private': model['cohort'].private,
            'kickoff_date': self.datetime_to_iso(model['cohort'].kickoff_date),
            'ending_date': model['cohort'].ending_date,
            'stage': model['cohort'].stage,
            'language': model['cohort'].language,
            'current_day': model['cohort'].current_day,
            'online_meeting_url': model['cohort'].online_meeting_url,
            'timezone': model['cohort'].timezone,
            'timeslots': [],
            'specialty_mode': {
                'id': model['cohort'].specialty_mode.id,
                'name': model['cohort'].specialty_mode.name,
                'syllabus': model['cohort'].specialty_mode.syllabus.id,
            },
            'syllabus_version': {
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'version': model['cohort'].syllabus_version.version,
                'syllabus': model['cohort'].syllabus_version.syllabus.id,
                'duration_in_days': model.syllabus.duration_in_days,
                'duration_in_hours': model.syllabus.duration_in_hours,
                'github_url': model.syllabus.github_url,
                'logo': model.syllabus.logo,
                'private': model.syllabus.private,
                'week_hours': model.syllabus.week_hours,
            },
            'academy': {
                'id': model['cohort'].academy.id,
                'slug': model['cohort'].academy.slug,
                'name': model['cohort'].academy.name,
                'country': {
                    'code': model['cohort'].academy.country.code,
                    'name': model['cohort'].academy.country.name,
                },
                'city': {
                    'name': model['cohort'].academy.city.name,
                },
                'logo_url': model['cohort'].academy.logo_url,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort_with_ten_datas_with_location_with_comma(self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        models = [
            self.generate_models(authenticate=True,
                                 cohort=True,
                                 profile_academy=True,
                                 capability='read_cohort',
                                 role='potato',
                                 syllabus=True,
                                 syllabus_version=True,
                                 specialty_mode=True)
        ]

        base = models[0].copy()
        del base['cohort']

        models = models + [self.generate_models(cohort=True, models=base) for index in range(0, 9)]
        models.sort(key=lambda x: x.cohort.kickoff_date, reverse=True)

        self.client.force_authenticate(user=models[0]['user'])
        base_url = reverse_lazy('admissions:academy_cohort')
        params = ','.join([model['academy'].slug for model in models])
        url = f'{base_url}?location={params}'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort'].id,
            'slug': model['cohort'].slug,
            'name': model['cohort'].name,
            'never_ends': model['cohort'].never_ends,
            'private': model['cohort'].private,
            'language': model['cohort'].language,
            'kickoff_date': datetime_to_iso_format(model['cohort'].kickoff_date),
            'ending_date': model['cohort'].ending_date,
            'stage': model['cohort'].stage,
            'current_day': model['cohort'].current_day,
            'online_meeting_url': model['cohort'].online_meeting_url,
            'timezone': model['cohort'].timezone,
            'timeslots': [],
            'specialty_mode': {
                'id': model['cohort'].specialty_mode.id,
                'name': model['cohort'].specialty_mode.name,
                'syllabus': model['cohort'].specialty_mode.syllabus.id,
            },
            'syllabus_version': {
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'version': model['cohort'].syllabus_version.version,
                'syllabus': model['cohort'].syllabus_version.syllabus.id,
                'duration_in_days': model.syllabus.duration_in_days,
                'duration_in_hours': model.syllabus.duration_in_hours,
                'github_url': model.syllabus.github_url,
                'logo': model.syllabus.logo,
                'private': model.syllabus.private,
                'week_hours': model.syllabus.week_hours,
            },
            'academy': {
                'id': model['cohort'].academy.id,
                'slug': model['cohort'].academy.slug,
                'name': model['cohort'].academy.name,
                'country': {
                    'code': model['cohort'].academy.country.code,
                    'name': model['cohort'].academy.country.name,
                },
                'city': {
                    'name': model['cohort'].academy.city.name,
                },
                'logo_url': model['cohort'].academy.logo_url,
            },
        } for model in models]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), self.all_model_dict([x.cohort for x in models]))
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort_with_ten_datas_with_location_with_comma_just_get_100(self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        models = [
            self.generate_models(authenticate=True,
                                 cohort=True,
                                 profile_academy=True,
                                 capability='read_cohort',
                                 role='potato',
                                 syllabus=True,
                                 syllabus_version=True,
                                 specialty_mode=True)
        ]

        base = models[0].copy()
        del base['cohort']

        models = models + [self.generate_models(cohort=True, models=base) for index in range(0, 105)]
        models.sort(key=lambda x: x.cohort.kickoff_date, reverse=True)

        self.client.force_authenticate(user=models[0]['user'])
        base_url = reverse_lazy('admissions:academy_cohort')
        params = ','.join([model['academy'].slug for model in models])
        url = f'{base_url}?location={params}'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort'].id,
            'slug': model['cohort'].slug,
            'name': model['cohort'].name,
            'never_ends': model['cohort'].never_ends,
            'private': model['cohort'].private,
            'language': model['cohort'].language,
            'kickoff_date': datetime_to_iso_format(model['cohort'].kickoff_date),
            'ending_date': model['cohort'].ending_date,
            'stage': model['cohort'].stage,
            'current_day': model['cohort'].current_day,
            'online_meeting_url': model['cohort'].online_meeting_url,
            'timezone': model['cohort'].timezone,
            'timeslots': [],
            'specialty_mode': {
                'id': model['cohort'].specialty_mode.id,
                'name': model['cohort'].specialty_mode.name,
                'syllabus': model['cohort'].specialty_mode.syllabus.id,
            },
            'syllabus_version': {
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'version': model['cohort'].syllabus_version.version,
                'syllabus': model['cohort'].syllabus_version.syllabus.id,
                'duration_in_days': model.syllabus.duration_in_days,
                'duration_in_hours': model.syllabus.duration_in_hours,
                'github_url': model.syllabus.github_url,
                'logo': model.syllabus.logo,
                'private': model.syllabus.private,
                'week_hours': model.syllabus.week_hours,
            },
            'academy': {
                'id': model['cohort'].academy.id,
                'slug': model['cohort'].academy.slug,
                'name': model['cohort'].academy.name,
                'country': {
                    'code': model['cohort'].academy.country.code,
                    'name': model['cohort'].academy.country.name,
                },
                'city': {
                    'name': model['cohort'].academy.city.name,
                },
                'logo_url': model['cohort'].academy.logo_url,
            },
        } for model in models[:100]]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), self.all_model_dict([x.cohort for x in models]))
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort_with_ten_datas_with_location_with_comma_pagination_first_five(self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        models = [
            self.generate_models(authenticate=True,
                                 cohort=True,
                                 profile_academy=True,
                                 capability='read_cohort',
                                 role='potato',
                                 syllabus=True,
                                 syllabus_version=True,
                                 specialty_mode=True)
        ]

        base = models[0].copy()
        del base['cohort']

        models = models + [self.generate_models(cohort=True, models=base) for index in range(0, 9)]
        models.sort(key=lambda x: x.cohort.kickoff_date, reverse=True)

        self.client.force_authenticate(user=models[0]['user'])
        base_url = reverse_lazy('admissions:academy_cohort')
        params = ','.join([model['academy'].slug for model in models])
        url = f'{base_url}?limit=5&location={params}&offset=0'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count':
            10,
            'first':
            None,
            'next':
            'http://testserver/v1/admissions/academy/cohort?limit=5&'
            f'location={params}&offset=5',
            'previous':
            None,
            'last':
            'http://testserver/v1/admissions/academy/cohort?limit=5&'
            f'location={params}&offset=5',
            'results': [{
                'id': model['cohort'].id,
                'slug': model['cohort'].slug,
                'name': model['cohort'].name,
                'never_ends': model['cohort'].never_ends,
                'private': model['cohort'].private,
                'language': model['cohort'].language,
                'kickoff_date': datetime_to_iso_format(model['cohort'].kickoff_date),
                'ending_date': model['cohort'].ending_date,
                'stage': model['cohort'].stage,
                'current_day': model['cohort'].current_day,
                'online_meeting_url': model['cohort'].online_meeting_url,
                'timezone': model['cohort'].timezone,
                'timeslots': [],
                'specialty_mode': {
                    'id': model['cohort'].specialty_mode.id,
                    'name': model['cohort'].specialty_mode.name,
                    'syllabus': model['cohort'].specialty_mode.syllabus.id,
                },
                'syllabus_version': {
                    'name': model.syllabus.name,
                    'slug': model.syllabus.slug,
                    'version': model['cohort'].syllabus_version.version,
                    'syllabus': model['cohort'].syllabus_version.syllabus.id,
                    'duration_in_days': model.syllabus.duration_in_days,
                    'duration_in_hours': model.syllabus.duration_in_hours,
                    'github_url': model.syllabus.github_url,
                    'logo': model.syllabus.logo,
                    'private': model.syllabus.private,
                    'week_hours': model.syllabus.week_hours,
                },
                'academy': {
                    'id': model['cohort'].academy.id,
                    'slug': model['cohort'].academy.slug,
                    'name': model['cohort'].academy.name,
                    'country': {
                        'code': model['cohort'].academy.country.code,
                        'name': model['cohort'].academy.country.name,
                    },
                    'city': {
                        'name': model['cohort'].academy.city.name,
                    },
                    'logo_url': model['cohort'].academy.logo_url,
                },
            } for model in models[:5]],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), self.all_model_dict([x.cohort for x in models]))
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort_with_ten_datas_with_location_with_comma_pagination_last_five(self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        models = [
            self.generate_models(authenticate=True,
                                 cohort=True,
                                 profile_academy=True,
                                 capability='read_cohort',
                                 role='potato',
                                 syllabus=True,
                                 syllabus_version=True,
                                 specialty_mode=True)
        ]

        base = models[0].copy()
        del base['cohort']

        models = models + [self.generate_models(cohort=True, models=base) for index in range(0, 9)]
        models.sort(key=lambda x: x.cohort.kickoff_date, reverse=True)

        self.client.force_authenticate(user=models[0]['user'])
        base_url = reverse_lazy('admissions:academy_cohort')
        params = ','.join([model['academy'].slug for model in models])
        url = f'{base_url}?limit=5&location={params}&offset=5'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count':
            10,
            'first':
            'http://testserver/v1/admissions/academy/cohort?limit=5&'
            f'location={params}',
            'next':
            None,
            'previous':
            'http://testserver/v1/admissions/academy/cohort?limit=5&'
            f'location={params}',
            'last':
            None,
            'results': [{
                'id': model['cohort'].id,
                'slug': model['cohort'].slug,
                'name': model['cohort'].name,
                'never_ends': model['cohort'].never_ends,
                'private': model['cohort'].private,
                'language': model['cohort'].language,
                'kickoff_date': datetime_to_iso_format(model['cohort'].kickoff_date),
                'ending_date': model['cohort'].ending_date,
                'stage': model['cohort'].stage,
                'current_day': model['cohort'].current_day,
                'online_meeting_url': model['cohort'].online_meeting_url,
                'timezone': model['cohort'].timezone,
                'timeslots': [],
                'specialty_mode': {
                    'id': model['cohort'].specialty_mode.id,
                    'name': model['cohort'].specialty_mode.name,
                    'syllabus': model['cohort'].specialty_mode.syllabus.id,
                },
                'syllabus_version': {
                    'name': model.syllabus.name,
                    'slug': model.syllabus.slug,
                    'version': model['cohort'].syllabus_version.version,
                    'syllabus': model['cohort'].syllabus_version.syllabus.id,
                    'duration_in_days': model.syllabus.duration_in_days,
                    'duration_in_hours': model.syllabus.duration_in_hours,
                    'github_url': model.syllabus.github_url,
                    'logo': model.syllabus.logo,
                    'private': model.syllabus.private,
                    'week_hours': model.syllabus.week_hours,
                },
                'academy': {
                    'id': model['cohort'].academy.id,
                    'slug': model['cohort'].academy.slug,
                    'name': model['cohort'].academy.name,
                    'country': {
                        'code': model['cohort'].academy.country.code,
                        'name': model['cohort'].academy.country.name,
                    },
                    'city': {
                        'name': model['cohort'].academy.city.name,
                    },
                    'logo_url': model['cohort'].academy.logo_url,
                },
            } for model in models[5:]],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), self.all_model_dict([x.cohort for x in models]))
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort_with_ten_datas_with_location_with_comma_pagination_after_last_five(self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        models = [
            self.generate_models(authenticate=True,
                                 cohort=True,
                                 profile_academy=True,
                                 capability='read_cohort',
                                 role='potato',
                                 syllabus=True,
                                 syllabus_version=True,
                                 specialty_mode=True)
        ]

        base = models[0].copy()
        del base['cohort']

        models = models + [self.generate_models(cohort=True, models=base) for index in range(0, 9)]

        models_dict = self.all_cohort_dict()
        self.client.force_authenticate(user=models[0]['user'])
        base_url = reverse_lazy('admissions:academy_cohort')
        params = ','.join([model['academy'].slug for model in models])
        url = f'{base_url}?limit=5&location={params}&offset=10'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count': 10,
            'first': 'http://testserver/v1/admissions/academy/cohort?limit=5&'
            f'location={params}',
            'next': None,
            'previous': 'http://testserver/v1/admissions/academy/cohort?limit=5&'
            f'location={params}&offset=5',
            'last': None,
            'results': [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), models_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort_delete_without_args_in_url_or_bulk(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')
        url = reverse_lazy('admissions:academy_cohort')
        response = self.client.delete(url)
        json = response.json()
        expected = {'detail': 'Missing cohort_id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort'),
        }])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort_delete_in_bulk_with_students(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields = ['id']

        base = self.generate_models(academy=True, capability='crud_cohort', role='potato')

        expected = {
            'detail': 'cohort-has-students',
            'status_code': 400,
        }

        for field in many_fields:
            model = self.generate_models(authenticate=True,
                                         profile_academy=True,
                                         cohort_user=True,
                                         models=base)

            value = getattr(model['cohort'], field)

            url = (reverse_lazy('admissions:academy_cohort') + f'?{field}=' + str(value))
            response = self.client.delete(url)
            json = response.json()

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

            self.assertEqual(self.all_cohort_dict(), [{**self.model_to_dict(model, 'cohort')}])

    def test_academy_cohort_delete_in_bulk_with_one(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields = ['id']

        base = self.generate_models(academy=True, capability='crud_cohort', role='potato')

        for field in many_fields:
            cohort_kwargs = {
                'kickoff_date': datetime.now(),
                'ending_date': datetime.now(),
                'timezone': choice(['-1', '-2', '-3', '-4', '-5']),
            }
            model = self.generate_models(authenticate=True,
                                         profile_academy=True,
                                         cohort_kwargs=cohort_kwargs,
                                         models=base)

            value = getattr(model['cohort'], field)

            url = (reverse_lazy('admissions:academy_cohort') + f'?{field}=' + str(value))
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.count_cohort_user(), 0)
            self.assertEqual(self.count_cohort_stage(model['cohort'].id), 'DELETED')

    def test_academy_cohort_delete_in_bulk_with_two(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields = ['id']

        base = self.generate_models(academy=True, capability='crud_cohort', role='potato')

        for field in many_fields:
            cohort_kwargs = {
                'kickoff_date': datetime.now(),
                'ending_date': datetime.now(),
                'timezone': choice(['-1', '-2', '-3', '-4', '-5']),
            }
            model1 = self.generate_models(authenticate=True,
                                          profile_academy=True,
                                          syllabus=True,
                                          cohort_kwargs=cohort_kwargs,
                                          models=base)

            cohort_kwargs = {
                'kickoff_date': datetime.now(),
                'ending_date': datetime.now(),
                'timezone': choice(['-1', '-2', '-3', '-4', '-5']),
            }
            model2 = self.generate_models(profile_academy=True,
                                          syllabus=True,
                                          cohort_kwargs=cohort_kwargs,
                                          models=base)

            value1 = getattr(model1['cohort'], field)
            value1 = self.datetime_to_iso(value1) if isinstance(value1, datetime) else value1

            value2 = getattr(model2['cohort'], field)
            value2 = self.datetime_to_iso(value2) if isinstance(value2, datetime) else value2

            url = (reverse_lazy('admissions:academy_cohort') + f'?{field}=' + str(value1) + ',' + str(value2))
            response = self.client.delete(url)

            self.assertEqual(self.count_cohort_user(), 0)
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

            self.assertEqual(self.count_cohort_stage(model1['cohort'].id), 'DELETED')
            self.assertEqual(self.count_cohort_stage(model2['cohort'].id), 'DELETED')

    def test_academy_cohort_with_data_testing_cache(self):
        """Test /cohort without auth"""
        cache_keys = [
            'Cohort__resource=None&academy_id=1&upcoming=None&academy='
            'None&location=None&like=None&limit=None&offset=None'
        ]

        self.assertEqual(self.cache.keys(), [])

        old_models = self.test_academy_cohort__with_data()
        self.assertEqual(self.cache.keys(), cache_keys)

        self.test_academy_cohort__with_data(old_models)
        self.assertEqual(self.cache.keys(), cache_keys)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort_with_data_testing_cache_and_remove_in_post(self):
        """Test /cohort without auth"""
        cache_keys = [
            'Cohort__resource=None&academy_id=1&upcoming=None&academy='
            'None&location=None&like=None&limit=None&offset=None'
        ]

        self.assertEqual(self.cache.keys(), [])

        old_models = self.test_academy_cohort__with_data()
        self.assertEqual(self.cache.keys(), cache_keys)

        self.headers(academy=1)

        base = old_models[0].copy()

        del base['profile_academy']
        del base['capability']
        del base['role']
        del base['user']

        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        academy_kwargs = {'timezone': 'America/Caracas'}
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato2',
                                     syllabus=True,
                                     syllabus_version=True,
                                     specialty_mode=True,
                                     specialty_mode_time_slot=True,
                                     syllabus_kwargs=syllabus_kwargs,
                                     academy_kwargs=academy_kwargs,
                                     models=base)

        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'syllabus': f'{model.syllabus.slug}.v{model.syllabus_version.version}',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'kickoff_date': self.datetime_to_iso(datetime.today()),
            'never_ends': True,
            'specialty_mode': 1,
        }

        response = self.client.post(url, data)
        json = response.json()
        cohort = self.get_cohort(2)

        data['syllabus_version'] = data['syllabus']
        del data['syllabus']

        expected = {
            'id': cohort.id,
            'current_day': cohort.current_day,
            'academy': {
                'id': cohort.academy.id,
                'slug': cohort.academy.slug,
                'name': cohort.academy.name,
                'street_address': cohort.academy.street_address,
                'country': cohort.academy.country.code,
                'city': cohort.academy.city.id,
            },
            'ending_date': cohort.ending_date,
            'stage': cohort.stage,
            'language': cohort.language,
            'online_meeting_url': model['cohort'].online_meeting_url,
            'timezone': model['cohort'].timezone,
            'created_at': self.datetime_to_iso(cohort.created_at),
            'updated_at': self.datetime_to_iso(cohort.updated_at),
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(self.cache.keys(), [])

        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(old_models[0], 'cohort')
        }, {
            **self.model_to_dict({
                **model, 'cohort': cohort
            }, 'cohort')
        }])

        self.assertEqual(
            self.all_cohort_time_slot_dict(),
            [{
                **self.fill_cohort_timeslot(1, 2, model.specialty_mode_time_slot),
                'timezone': 'America/Caracas',
            }])

        base = [
            self.generate_models(authenticate=True, models=old_models[0]),
            self.generate_models(cohort=cohort, models=base)
        ]

        self.test_academy_cohort__with_data(base)
        self.assertEqual(self.cache.keys(), cache_keys)
