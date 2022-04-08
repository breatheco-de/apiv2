"""
Test /academy/cohort
"""
import re
from unittest.mock import MagicMock, call, patch
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
    def test_cohort_me__post__without_authorization(self):
        """Test /academy/cohort without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:cohort_me')
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_cohort_me__without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:cohort_me')
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': "You (user: 1) don't have this capability: read_single_cohort for academy 1",
                'status_code': 403
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    # """

    # NEW TESTS HERE!!!
    """
    🔽🔽🔽 Without data
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_me_without_data(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy('admissions:cohort_me')
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_single_cohort',
                                     role='potato',
                                     syllabus=True,
                                     skip_cohort=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 0)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 With data (this method is reusable)
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_me__with_data(self):
        """Test /cohort without auth"""
        self.check_cohort_me__with_data()

    """
    🔽🔽🔽 Get
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_me__with_data__with_upcoming_false(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_single_cohort',
                                     role='potato',
                                     cohort_user=1,
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_schedule=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        model_dict = self.remove_dinamics_fields(model['cohort'].__dict__)
        base_url = reverse_lazy('admissions:cohort_me')
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
            'current_module': None,
            'online_meeting_url': model['cohort'].online_meeting_url,
            'timezone': model['cohort'].timezone,
            'timeslots': [],
            'schedule': {
                'id': model['cohort'].schedule.id,
                'name': model['cohort'].schedule.name,
                'syllabus': model['cohort'].schedule.syllabus.id,
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
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_me__with_data__with_upcoming_true__without_data(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        self.clear_cache()
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_single_cohort',
                                     role='potato',
                                     cohort_user=1,
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_schedule=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        model_dict = self.remove_dinamics_fields(model['cohort'].__dict__)
        base_url = reverse_lazy('admissions:cohort_me')
        url = f'{base_url}?upcoming=true'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_me__with_data__with_upcoming_true(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        cohort_kwargs = {
            'kickoff_date': timezone.now() + timedelta(days=1),
        }
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_single_cohort',
                                     role='potato',
                                     cohort_user=1,
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_schedule=True,
                                     cohort_kwargs=cohort_kwargs)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        model_dict = self.get_cohort_dict(1)
        base_url = reverse_lazy('admissions:cohort_me')
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
            'current_module': None,
            'online_meeting_url': model['cohort'].online_meeting_url,
            'timezone': model['cohort'].timezone,
            'timeslots': [],
            'schedule': {
                'id': model['cohort'].schedule.id,
                'name': model['cohort'].schedule.name,
                'syllabus': model['cohort'].schedule.syllabus.id,
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
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_me_with_data_with_academy(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_single_cohort',
                                     role='potato',
                                     cohort_user=1,
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_schedule=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        model_dict = self.get_cohort_dict(1)
        base_url = reverse_lazy('admissions:cohort_me')
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
            'current_module': model['cohort'].current_module,
            'online_meeting_url': model['cohort'].online_meeting_url,
            'timezone': model['cohort'].timezone,
            'timeslots': [],
            'schedule': {
                'id': model['cohort'].schedule.id,
                'name': model['cohort'].schedule.name,
                'syllabus': model['cohort'].schedule.syllabus.id,
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
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_me_with_data_with_academy_with_comma(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_single_cohort',
                                     role='potato',
                                     cohort_user=1,
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_schedule=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        model_dict = self.get_cohort_dict(1)
        base_url = reverse_lazy('admissions:cohort_me')
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
            'current_module': None,
            'online_meeting_url': model['cohort'].online_meeting_url,
            'timezone': model['cohort'].timezone,
            'timeslots': [],
            'schedule': {
                'id': model['cohort'].schedule.id,
                'name': model['cohort'].schedule.name,
                'syllabus': model['cohort'].schedule.syllabus.id,
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
        self.assertEqual(cohort_saved.send.call_args_list, [])

    # @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    # def test_cohort_me_with_ten_datas_with_academy_with_comma(self):
    #     """Test /cohort without auth"""
    #     from breathecode.admissions.signals import cohort_saved

    #     self.headers(academy=1)
    #     models = [
    #         self.generate_models(authenticate=True,
    #                              cohort=True,
    #                              profile_academy=True,
    #                              capability='read_single_cohort',
    #                              role='potato',
    #                              syllabus=True,
    #                              syllabus_version=True,
    #                              syllabus_schedule=True)
    #     ]

    #     base = models[0].copy()
    #     del base['cohort']

    #     models = models + [self.generate_models(cohort=True, models=base) for index in range(0, 9)]
    #     models.sort(key=lambda x: x.cohort.kickoff_date, reverse=True)

    #     # reset because this call are coming from mixer
    #     cohort_saved.send.call_args_list = []

    #     self.client.force_authenticate(user=models[0]['user'])
    #     base_url = reverse_lazy('admissions:cohort_me')
    #     params = ','.join([model['academy'].slug for model in models])
    #     url = f'{base_url}?academy={params}'
    #     response = self.client.get(url)
    #     json = response.json()
    #     expected = [{
    #         'id': model['cohort'].id,
    #         'slug': model['cohort'].slug,
    #         'name': model['cohort'].name,
    #         'never_ends': model['cohort'].never_ends,
    #         'private': model['cohort'].private,
    #         'language': model['cohort'].language,
    #         'kickoff_date': datetime_to_iso_format(model['cohort'].kickoff_date),
    #         'ending_date': model['cohort'].ending_date,
    #         'stage': model['cohort'].stage,
    #         'current_day': model['cohort'].current_day,
    #         'current_module': None,
    #         'online_meeting_url': model['cohort'].online_meeting_url,
    #         'timezone': model['cohort'].timezone,
    #         'timeslots': [],
    #         'schedule': {
    #             'id': model['cohort'].schedule.id,
    #             'name': model['cohort'].schedule.name,
    #             'syllabus': model['cohort'].schedule.syllabus.id,
    #         },
    #         'syllabus_version': {
    #             'name': model.syllabus.name,
    #             'slug': model.syllabus.slug,
    #             'version': model['cohort'].syllabus_version.version,
    #             'syllabus': model['cohort'].syllabus_version.syllabus.id,
    #             'duration_in_days': model.syllabus.duration_in_days,
    #             'duration_in_hours': model.syllabus.duration_in_hours,
    #             'github_url': model.syllabus.github_url,
    #             'logo': model.syllabus.logo,
    #             'private': model.syllabus.private,
    #             'week_hours': model.syllabus.week_hours,
    #         },
    #         'academy': {
    #             'id': model['cohort'].academy.id,
    #             'slug': model['cohort'].academy.slug,
    #             'name': model['cohort'].academy.name,
    #             'country': {
    #                 'code': model['cohort'].academy.country.code,
    #                 'name': model['cohort'].academy.country.name,
    #             },
    #             'city': {
    #                 'name': model['cohort'].academy.city.name,
    #             },
    #             'logo_url': model['cohort'].academy.logo_url,
    #         },
    #     } for model in models]

    #     self.assertEqual(json, expected)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(self.all_cohort_dict(), self.all_model_dict([x.cohort for x in models]))
    #     self.assertEqual(self.all_cohort_time_slot_dict(), [])
    #     self.assertEqual(cohort_saved.send.call_args_list, [])
    """
    🔽🔽🔽 Sort in querystring
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_me__with_data__with_sort(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        base = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability='read_single_cohort',
            role='potato',
            # cohort_user=1,
            skip_cohort=True)

        models = [
            self.generate_models(cohort=True,
                                 syllabus=True,
                                 cohort_user=1,
                                 syllabus_version=True,
                                 syllabus_schedule=True,
                                 models=base) for _ in range(0, 2)
        ]

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        ordened_models = sorted(models, key=lambda x: x['cohort'].slug, reverse=True)

        url = reverse_lazy('admissions:cohort_me') + '?sort=-slug'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort'].id,
            'slug': model['cohort'].slug,
            'name': model['cohort'].name,
            'current_day': model.cohort.current_day,
            'current_module': None,
            'never_ends': model['cohort'].never_ends,
            'private': model['cohort'].private,
            'kickoff_date': self.datetime_to_iso(model['cohort'].kickoff_date),
            'ending_date': model['cohort'].ending_date,
            'stage': model['cohort'].stage,
            'language': model['cohort'].language,
            'online_meeting_url': model['cohort'].online_meeting_url,
            'timezone': model['cohort'].timezone,
            'timeslots': [],
            'schedule': {
                'id': model['cohort'].schedule.id,
                'name': model['cohort'].schedule.name,
                'syllabus': model['cohort'].schedule.syllabus.id,
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
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_me_with_data__ignore_cohort_then_student_is_not_registered(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_single_cohort',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_schedule=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        model_dict = self.get_cohort_dict(1)
        base_url = reverse_lazy('admissions:cohort_me')
        url = f'{base_url}?location=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_me_with_data_with_location(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_single_cohort',
                                     role='potato',
                                     cohort_user=1,
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_schedule=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        model_dict = self.get_cohort_dict(1)
        base_url = reverse_lazy('admissions:cohort_me')
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
            'current_module': None,
            'online_meeting_url': model['cohort'].online_meeting_url,
            'timezone': model['cohort'].timezone,
            'timeslots': [],
            'schedule': {
                'id': model['cohort'].schedule.id,
                'name': model['cohort'].schedule.name,
                'syllabus': model['cohort'].schedule.syllabus.id,
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
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_me_with_data_with_location_with_comma(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_single_cohort',
                                     role='potato',
                                     cohort_user=1,
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_schedule=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        model_dict = self.get_cohort_dict(1)
        base_url = reverse_lazy('admissions:cohort_me')
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
            'current_module': None,
            'online_meeting_url': model['cohort'].online_meeting_url,
            'timezone': model['cohort'].timezone,
            'timeslots': [],
            'schedule': {
                'id': model['cohort'].schedule.id,
                'name': model['cohort'].schedule.name,
                'syllabus': model['cohort'].schedule.syllabus.id,
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
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_me_with_ten_datas(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=10,
                                     profile_academy=True,
                                     capability='read_single_cohort',
                                     role='potato',
                                     cohort_user=[{
                                         'cohort_id': id
                                     } for id in range(1, 11)],
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_schedule=True)

        cohorts = model.cohort
        cohorts.sort(key=lambda x: x.kickoff_date, reverse=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        self.client.force_authenticate(user=model['user'])
        url = reverse_lazy('admissions:cohort_me')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': cohort.id,
            'slug': cohort.slug,
            'name': cohort.name,
            'never_ends': cohort.never_ends,
            'private': cohort.private,
            'language': cohort.language,
            'kickoff_date': datetime_to_iso_format(cohort.kickoff_date),
            'ending_date': cohort.ending_date,
            'stage': cohort.stage,
            'current_day': cohort.current_day,
            'current_module': None,
            'online_meeting_url': cohort.online_meeting_url,
            'timezone': cohort.timezone,
            'timeslots': [],
            'schedule': {
                'id': cohort.schedule.id,
                'name': cohort.schedule.name,
                'syllabus': cohort.schedule.syllabus.id,
            },
            'syllabus_version': {
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'version': cohort.syllabus_version.version,
                'syllabus': cohort.syllabus_version.syllabus.id,
                'duration_in_days': model.syllabus.duration_in_days,
                'duration_in_hours': model.syllabus.duration_in_hours,
                'github_url': model.syllabus.github_url,
                'logo': model.syllabus.logo,
                'private': model.syllabus.private,
                'week_hours': model.syllabus.week_hours,
            },
            'academy': {
                'id': cohort.academy.id,
                'slug': cohort.academy.slug,
                'name': cohort.academy.name,
                'country': {
                    'code': cohort.academy.country.code,
                    'name': cohort.academy.country.name,
                },
                'city': {
                    'name': cohort.academy.city.name,
                },
                'logo_url': cohort.academy.logo_url,
            },
        } for cohort in cohorts]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), self.all_model_dict(cohorts))
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_me_with_ten_datas_just_get_100(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=105,
                                     profile_academy=True,
                                     capability='read_single_cohort',
                                     role='potato',
                                     cohort_user=[{
                                         'cohort_id': id
                                     } for id in range(1, 106)],
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_schedule=True)

        cohorts = model.cohort
        cohorts.sort(key=lambda x: x.kickoff_date, reverse=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        self.client.force_authenticate(user=model['user'])
        url = reverse_lazy('admissions:cohort_me')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': cohort.id,
            'slug': cohort.slug,
            'name': cohort.name,
            'never_ends': cohort.never_ends,
            'private': cohort.private,
            'language': cohort.language,
            'kickoff_date': datetime_to_iso_format(cohort.kickoff_date),
            'ending_date': cohort.ending_date,
            'stage': cohort.stage,
            'current_day': cohort.current_day,
            'current_module': None,
            'online_meeting_url': cohort.online_meeting_url,
            'timezone': cohort.timezone,
            'timeslots': [],
            'schedule': {
                'id': cohort.schedule.id,
                'name': cohort.schedule.name,
                'syllabus': cohort.schedule.syllabus.id,
            },
            'syllabus_version': {
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'version': cohort.syllabus_version.version,
                'syllabus': cohort.syllabus_version.syllabus.id,
                'duration_in_days': model.syllabus.duration_in_days,
                'duration_in_hours': model.syllabus.duration_in_hours,
                'github_url': model.syllabus.github_url,
                'logo': model.syllabus.logo,
                'private': model.syllabus.private,
                'week_hours': model.syllabus.week_hours,
            },
            'academy': {
                'id': cohort.academy.id,
                'slug': cohort.academy.slug,
                'name': cohort.academy.name,
                'country': {
                    'code': cohort.academy.country.code,
                    'name': cohort.academy.country.name,
                },
                'city': {
                    'name': cohort.academy.city.name,
                },
                'logo_url': cohort.academy.logo_url,
            },
        } for cohort in cohorts[:100]]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), self.all_model_dict(cohorts))
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_me_with_ten_datas_pagination_first_five(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=10,
                                     profile_academy=True,
                                     capability='read_single_cohort',
                                     role='potato',
                                     cohort_user=[{
                                         'cohort_id': id
                                     } for id in range(1, 11)],
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_schedule=True)

        cohorts = model.cohort
        cohorts.sort(key=lambda x: x.kickoff_date, reverse=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        self.client.force_authenticate(user=model['user'])
        base_url = reverse_lazy('admissions:cohort_me')
        url = f'{base_url}?limit=5&offset=0'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count':
            10,
            'first':
            None,
            'next':
            'http://testserver/v1/admissions/cohort/me?limit=5&offset=5',
            'previous':
            None,
            'last':
            'http://testserver/v1/admissions/cohort/me?limit=5&offset=5',
            'results': [{
                'id': cohort.id,
                'slug': cohort.slug,
                'name': cohort.name,
                'never_ends': cohort.never_ends,
                'private': cohort.private,
                'language': cohort.language,
                'kickoff_date': datetime_to_iso_format(cohort.kickoff_date),
                'ending_date': cohort.ending_date,
                'stage': cohort.stage,
                'current_day': cohort.current_day,
                'current_module': None,
                'online_meeting_url': cohort.online_meeting_url,
                'timezone': cohort.timezone,
                'timeslots': [],
                'schedule': {
                    'id': cohort.schedule.id,
                    'name': cohort.schedule.name,
                    'syllabus': cohort.schedule.syllabus.id,
                },
                'syllabus_version': {
                    'name': model.syllabus.name,
                    'slug': model.syllabus.slug,
                    'version': cohort.syllabus_version.version,
                    'syllabus': cohort.syllabus_version.syllabus.id,
                    'duration_in_days': model.syllabus.duration_in_days,
                    'duration_in_hours': model.syllabus.duration_in_hours,
                    'github_url': model.syllabus.github_url,
                    'logo': model.syllabus.logo,
                    'private': model.syllabus.private,
                    'week_hours': model.syllabus.week_hours,
                },
                'academy': {
                    'id': cohort.academy.id,
                    'slug': cohort.academy.slug,
                    'name': cohort.academy.name,
                    'country': {
                        'code': cohort.academy.country.code,
                        'name': cohort.academy.country.name,
                    },
                    'city': {
                        'name': cohort.academy.city.name,
                    },
                    'logo_url': cohort.academy.logo_url,
                },
            } for cohort in cohorts[:5]],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), self.all_model_dict(cohorts))
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_me_with_ten_datas_pagination_last_five(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=10,
                                     profile_academy=True,
                                     capability='read_single_cohort',
                                     role='potato',
                                     cohort_user=[{
                                         'cohort_id': id
                                     } for id in range(1, 11)],
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_schedule=True)

        cohorts = model.cohort
        cohorts.sort(key=lambda x: x.kickoff_date, reverse=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        self.client.force_authenticate(user=model['user'])
        base_url = reverse_lazy('admissions:cohort_me')
        url = f'{base_url}?limit=5&offset=5'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count':
            10,
            'first':
            'http://testserver/v1/admissions/cohort/me?limit=5',
            'next':
            None,
            'previous':
            'http://testserver/v1/admissions/cohort/me?limit=5',
            'last':
            None,
            'results': [{
                'id': cohort.id,
                'slug': cohort.slug,
                'name': cohort.name,
                'never_ends': cohort.never_ends,
                'private': cohort.private,
                'language': cohort.language,
                'kickoff_date': datetime_to_iso_format(cohort.kickoff_date),
                'ending_date': cohort.ending_date,
                'stage': cohort.stage,
                'current_day': cohort.current_day,
                'current_module': None,
                'online_meeting_url': cohort.online_meeting_url,
                'timezone': cohort.timezone,
                'timeslots': [],
                'schedule': {
                    'id': cohort.schedule.id,
                    'name': cohort.schedule.name,
                    'syllabus': cohort.schedule.syllabus.id,
                },
                'syllabus_version': {
                    'name': model.syllabus.name,
                    'slug': model.syllabus.slug,
                    'version': cohort.syllabus_version.version,
                    'syllabus': cohort.syllabus_version.syllabus.id,
                    'duration_in_days': model.syllabus.duration_in_days,
                    'duration_in_hours': model.syllabus.duration_in_hours,
                    'github_url': model.syllabus.github_url,
                    'logo': model.syllabus.logo,
                    'private': model.syllabus.private,
                    'week_hours': model.syllabus.week_hours,
                },
                'academy': {
                    'id': cohort.academy.id,
                    'slug': cohort.academy.slug,
                    'name': cohort.academy.name,
                    'country': {
                        'code': cohort.academy.country.code,
                        'name': cohort.academy.country.name,
                    },
                    'city': {
                        'name': cohort.academy.city.name,
                    },
                    'logo_url': cohort.academy.logo_url,
                },
            } for cohort in cohorts[5:]],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), self.all_model_dict(cohorts))
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_me_with_ten_datas_pagination_after_last_five(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=10,
                                     profile_academy=True,
                                     capability='read_single_cohort',
                                     role='potato',
                                     cohort_user=[{
                                         'cohort_id': id
                                     } for id in range(1, 11)],
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_schedule=True)

        cohorts = model.cohort

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        self.client.force_authenticate(user=model['user'])
        base_url = reverse_lazy('admissions:cohort_me')
        url = f'{base_url}?limit=5&offset=10'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count': 10,
            'first': 'http://testserver/v1/admissions/cohort/me?limit=5',
            'next': None,
            'previous': 'http://testserver/v1/admissions/cohort/me?limit=5&offset=5',
            'last': None,
            'results': [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), self.bc.format.to_dict(cohorts))
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_me_with_data_testing_cache(self):
        """Test /cohort without auth"""
        cache_keys = [
            'Cohort__resource=None&academy_id=1&upcoming=None&stage=None&academy='
            'None&location=None&like=None&limit=None&offset=None'
        ]

        self.assertEqual(self.cache.keys(), [])

        old_models = self.check_cohort_me__with_data()
        self.assertEqual(self.cache.keys(), cache_keys)

        self.check_cohort_me__with_data(old_models)
        self.assertEqual(self.cache.keys(), cache_keys)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
