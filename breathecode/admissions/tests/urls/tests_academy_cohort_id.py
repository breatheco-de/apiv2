"""
Test /cohort
"""
from datetime import timedelta
from django.utils import timezone
from breathecode.admissions.caches import CohortCache
from unittest.mock import MagicMock, call, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers

from breathecode.utils.datetime_interger import DatetimeInteger
from ..mixins import AdmissionsTestCase


class AcademyCohortIdTestSuite(AdmissionsTestCase):
    """Test /cohort"""

    cache = CohortCache()
    """
    🔽🔽🔽 Auth
    """
    def test_cohort_id__without_auth(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': 1})
        response = self.client.put(url, {})
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cohort_id_put__without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': 1})
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: crud_cohort for academy 1",
            'status_code': 403
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 Put without cohort
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_id__put__without_cohort(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': 99999})
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(json, {'status_code': 400, 'detail': 'Specified cohort not be found'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])
        self.assertEqual(self.bc.database.list_of('admissions.CohortTimeSlot'), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Put not have ending_date and never_ends
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_id__put__without_ending_date_or_never_ends(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': 1})
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'detail': 'cohort-without-ending-date-and-never-ends',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])
        self.assertEqual(self.bc.database.list_of('admissions.CohortTimeSlot'), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Put with ending_date and never_ends=True
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_id__put__with_ending_date_and_never_ends_true(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': 1})
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        data = {
            'ending_date': timezone.now().isoformat(),
            'never_ends': True,
        }
        response = self.client.put(url, data)
        json = response.json()

        expected = {
            'detail': 'cohort-with-ending-date-and-never-ends',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])
        self.assertEqual(self.bc.database.list_of('admissions.CohortTimeSlot'), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Put with date
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_id__put(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': 1})
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        data = {
            'never_ends': True,
        }
        response = self.client.put(url, data)
        json = response.json()

        expected = {
            'id': model['cohort'].id,
            'slug': model['cohort'].slug,
            'name': model['cohort'].name,
            'never_ends': True,
            'remote_available': True,
            'private': False,
            'kickoff_date': self.datetime_to_iso(model['cohort'].kickoff_date),
            'ending_date': model['cohort'].ending_date,
            'current_day': model['cohort'].current_day,
            'current_module': model['cohort'].current_module,
            'stage': model['cohort'].stage,
            'language': model['cohort'].language,
            'syllabus_version': model['cohort'].syllabus_version,
            'schedule': model['cohort'].schedule,
            'online_meeting_url': model['cohort'].online_meeting_url,
            'timezone': model['cohort'].timezone,
            'timeslots': [],
            'academy': {
                'id': model.academy.id,
                'slug': model.academy.slug,
                'name': model.academy.name,
                'country': {
                    'code': model.academy.country.code,
                    'name': model.academy.country.name,
                },
                'city': {
                    'name': model.academy.city.name,
                },
                'logo_url': model.academy.logo_url,
            }
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'),
                         [{
                             **self.model_to_dict(model, 'cohort'),
                             'never_ends': True,
                         }])
        self.assertEqual(self.bc.database.list_of('admissions.CohortTimeSlot'), [])
        self.assertEqual(cohort_saved.send.call_args_list,
                         [call(instance=model.cohort, sender=model.cohort.__class__, created=False)])

    """
    🔽🔽🔽 Put with date, kickoff_date greater than ending_date
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_id__put__kickoff_date_greater_than_ending_date(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': 1})
        utc_now = timezone.now()
        cohort = {'kickoff_date': utc_now, 'ending_date': utc_now + timedelta(seconds=1)}
        model = self.generate_models(authenticate=True,
                                     cohort=cohort,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        cases = [
            {
                'kickoff_date': utc_now + timedelta(seconds=2),
            },
            {
                'ending_date': utc_now - timedelta(seconds=1),
            },
            {
                'kickoff_date': utc_now + timedelta(seconds=1),
                'ending_date': utc_now,
            },
        ]

        for data in cases:
            response = self.client.put(url, data)
            json = response.json()

            expected = {'detail': 'kickoff-date-greather-than-ending-date', 'status_code': 400}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [
                self.model_to_dict(model, 'cohort'),
            ])
            self.assertEqual(self.bc.database.list_of('admissions.CohortTimeSlot'), [])
            self.assertEqual(cohort_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Put syllabus with id instead of {slug}.v{id}
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_id__put__with_id__with_bad_syllabus_version_malformed(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'syllabus': 1,
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'current_day': model['cohort'].current_day + 1,
            'language': 'es',
        }
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {
            'detail': 'syllabus-field-marformed',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])
        self.assertEqual(self.bc.database.list_of('admissions.CohortTimeSlot'), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Put syllabus but it doesn't exists
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_id__put__with_id__with_bad_syllabus_version(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'syllabus': 'they-killed-kenny.v1',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'current_day': model['cohort'].current_day + 1,
            'language': 'es',
        }
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'detail': 'syllabus-version-not-found',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])
        self.assertEqual(self.bc.database.list_of('admissions.CohortTimeSlot'), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Put syllabus with bad slug {slug}.v{id}
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_id__put__with_id__with_bad_syllabus_version__with_bad_slug(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'x'}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus_schedule=True,
                                     syllabus_version=True,
                                     syllabus=True,
                                     syllabus_kwargs=syllabus_kwargs)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'syllabus': f'they-killed-kenny.v{model.syllabus_version.version}',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'current_day': model['cohort'].current_day + 1,
            'language': 'es',
        }
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'detail': 'syllabus-version-not-found',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])
        self.assertEqual(self.bc.database.list_of('admissions.CohortTimeSlot'), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Put syllabus with bad version {slug}.v{id}
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_id__put__with_id__with_bad_syllabus_version__with_bad_version(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        cohort_kwargs = {'never_ends': True}
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus_schedule=True,
                                     syllabus=True,
                                     syllabus_kwargs=syllabus_kwargs,
                                     cohort_kwargs=cohort_kwargs)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'syllabus': model['syllabus'].slug + '.v999',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'current_day': model['cohort'].current_day + 1,
            'language': 'es',
        }
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {
            'detail': 'syllabus-version-not-found',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])
        self.assertEqual(self.bc.database.list_of('admissions.CohortTimeSlot'), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Put assigning the syllabus version 1
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_id__put__with_id__assigning_syllabus_version_1(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        cohort_kwargs = {'ending_date': timezone.now()}
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        academy = {'timezone': 'Pacific/Pago_Pago'}
        timeslot = {'timezone': 'Pacific/Pago_Pago'}
        syllabus_version = {'version': 1}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     academy=academy,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=syllabus_version,
                                     syllabus_schedule=True,
                                     cohort_kwargs=cohort_kwargs,
                                     syllabus_schedule_time_slot=True,
                                     cohort_time_slot=True,
                                     syllabus_kwargs=syllabus_kwargs)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        model2 = self.generate_models(academy=model.academy,
                                      skip_cohort=True,
                                      syllabus_schedule=True,
                                      syllabus=model.syllabus,
                                      syllabus_schedule_time_slot=(2, timeslot))
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'syllabus': f'{model.syllabus.slug}.v{model.syllabus_version.version}',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'schedule': 2,
            'current_day': model['cohort'].current_day + 1,
            'language': 'es',
        }
        response = self.client.put(url, data)
        json = response.json()

        expected = {'detail': 'assigning-a-syllabus-version-1', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [
            self.bc.format.to_dict(model.cohort),
        ])

        self.assertEqual(self.bc.database.list_of('admissions.CohortTimeSlot'), [
            self.bc.format.to_dict(model.cohort_time_slot),
        ])

        self.assertEqual(cohort_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Put with some data
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_id__put__with_id__with_data_in_body(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        cohort_kwargs = {'ending_date': timezone.now()}
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        academy = {'timezone': 'Pacific/Pago_Pago'}
        timeslot = {'timezone': 'Europe/Amsterdam'}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     academy=academy,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_schedule=True,
                                     cohort_kwargs=cohort_kwargs,
                                     syllabus_schedule_time_slot=True,
                                     cohort_time_slot=True,
                                     syllabus_kwargs=syllabus_kwargs)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        model2 = self.generate_models(academy=model.academy,
                                      skip_cohort=True,
                                      syllabus_schedule=True,
                                      syllabus=model.syllabus,
                                      syllabus_schedule_time_slot=(2, timeslot))
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'syllabus': f'{model.syllabus.slug}.v{model.syllabus_version.version}',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'schedule': 2,
            'current_day': model['cohort'].current_day + 1,
            'language': 'es',
        }
        response = self.client.put(url, data)
        json = response.json()

        expected = {
            'id':
            model['cohort'].id,
            'slug':
            data['slug'],
            'name':
            data['name'],
            'never_ends':
            False,
            'remote_available':
            True,
            'private':
            False,
            'language':
            data['language'],
            'kickoff_date':
            self.datetime_to_iso(model['cohort'].kickoff_date),
            'ending_date':
            self.datetime_to_iso(model['cohort'].ending_date),
            'current_day':
            data['current_day'],
            'current_module':
            None,
            'stage':
            model['cohort'].stage,
            'online_meeting_url':
            model['cohort'].online_meeting_url,
            'timezone':
            model['cohort'].timezone,
            'timeslots': [{
                'ending_at':
                DatetimeInteger.to_iso_string(model.academy.timezone, syllabus_schedule_time_slot.ending_at),
                'id':
                syllabus_schedule_time_slot.id,
                'recurrency_type':
                syllabus_schedule_time_slot.recurrency_type,
                'recurrent':
                syllabus_schedule_time_slot.recurrent,
                'starting_at':
                DatetimeInteger.to_iso_string(model.academy.timezone,
                                              syllabus_schedule_time_slot.starting_at),
            } for syllabus_schedule_time_slot in model2.syllabus_schedule_time_slot],
            'schedule': {
                'id': model2.syllabus_schedule.id,
                'name': model2.syllabus_schedule.name,
                'syllabus': model2.syllabus_schedule.syllabus.id,
            },
            'syllabus_version': {
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'status': model['cohort'].syllabus_version.status,
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
                'id': model.academy.id,
                'slug': model.academy.slug,
                'name': model.academy.name,
                'country': {
                    'code': model.academy.country.code,
                    'name': model.academy.country.name,
                },
                'city': {
                    'name': model.academy.city.name,
                },
                'logo_url': model.academy.logo_url,
            }
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'),
                         [{
                             'academy_id': 1,
                             'current_day': data['current_day'],
                             'current_module': None,
                             'ending_date': model['cohort'].ending_date,
                             'id': model['cohort'].id,
                             'kickoff_date': model['cohort'].kickoff_date,
                             'remote_available': model['cohort'].remote_available,
                             'online_meeting_url': model['cohort'].online_meeting_url,
                             'language': data['language'],
                             'name': data['name'],
                             'never_ends': False,
                             'private': False,
                             'slug': data['slug'],
                             'stage': model['cohort'].stage,
                             'syllabus_version_id': model['cohort'].syllabus_version.id,
                             'schedule_id': model2.syllabus_schedule.id,
                             'timezone': None,
                         }])

        self.assertEqual(self.bc.database.list_of('admissions.CohortTimeSlot'),
                         [{
                             'cohort_id': 1,
                             'ending_at': syllabus_schedule_time_slot.ending_at,
                             'id': syllabus_schedule_time_slot.id,
                             'timezone': model.academy.timezone,
                             'recurrency_type': syllabus_schedule_time_slot.recurrency_type,
                             'recurrent': syllabus_schedule_time_slot.recurrent,
                             'starting_at': syllabus_schedule_time_slot.starting_at,
                         } for syllabus_schedule_time_slot in model2.syllabus_schedule_time_slot])

        self.assertEqual(cohort_saved.send.call_args_list,
                         [call(instance=model.cohort, sender=model.cohort.__class__, created=False)])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_id__put__with_id__with_data_in_body__cohort_with_timezone(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        cohort_kwargs = {'ending_date': timezone.now(), 'timezone': 'Europe/Monaco'}
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        academy = {'timezone': 'Pacific/Pago_Pago'}
        timeslot = {'timezone': 'Europe/Amsterdam'}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     academy=academy,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_schedule=True,
                                     cohort_kwargs=cohort_kwargs,
                                     syllabus_schedule_time_slot=True,
                                     cohort_time_slot=True,
                                     syllabus_kwargs=syllabus_kwargs)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        model2 = self.generate_models(academy=model.academy,
                                      skip_cohort=True,
                                      syllabus_schedule=True,
                                      syllabus=model.syllabus,
                                      syllabus_schedule_time_slot=(2, timeslot))
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'syllabus': f'{model.syllabus.slug}.v{model.syllabus_version.version}',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'schedule': 2,
            'current_day': model['cohort'].current_day + 1,
            'language': 'es',
        }
        response = self.client.put(url, data)
        json = response.json()

        expected = {
            'id':
            model['cohort'].id,
            'slug':
            data['slug'],
            'name':
            data['name'],
            'never_ends':
            False,
            'remote_available':
            True,
            'private':
            False,
            'language':
            data['language'],
            'kickoff_date':
            self.datetime_to_iso(model['cohort'].kickoff_date),
            'ending_date':
            self.datetime_to_iso(model['cohort'].ending_date),
            'current_day':
            data['current_day'],
            'current_module':
            None,
            'stage':
            model['cohort'].stage,
            'online_meeting_url':
            model['cohort'].online_meeting_url,
            'timezone':
            model['cohort'].timezone,
            'timeslots': [{
                'ending_at':
                DatetimeInteger.to_iso_string(model.cohort.timezone, syllabus_schedule_time_slot.ending_at),
                'id':
                syllabus_schedule_time_slot.id,
                'recurrency_type':
                syllabus_schedule_time_slot.recurrency_type,
                'recurrent':
                syllabus_schedule_time_slot.recurrent,
                'starting_at':
                DatetimeInteger.to_iso_string(model.cohort.timezone, syllabus_schedule_time_slot.starting_at),
            } for syllabus_schedule_time_slot in model2.syllabus_schedule_time_slot],
            'schedule': {
                'id': model2.syllabus_schedule.id,
                'name': model2.syllabus_schedule.name,
                'syllabus': model2.syllabus_schedule.syllabus.id,
            },
            'syllabus_version': {
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'status': model['cohort'].syllabus_version.status,
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
                'id': model.academy.id,
                'slug': model.academy.slug,
                'name': model.academy.name,
                'country': {
                    'code': model.academy.country.code,
                    'name': model.academy.country.name,
                },
                'city': {
                    'name': model.academy.city.name,
                },
                'logo_url': model.academy.logo_url,
            }
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'),
                         [{
                             'academy_id': 1,
                             'current_day': data['current_day'],
                             'current_module': None,
                             'ending_date': model['cohort'].ending_date,
                             'id': model['cohort'].id,
                             'kickoff_date': model['cohort'].kickoff_date,
                             'remote_available': model['cohort'].remote_available,
                             'online_meeting_url': model['cohort'].online_meeting_url,
                             'language': data['language'],
                             'name': data['name'],
                             'never_ends': False,
                             'private': False,
                             'slug': data['slug'],
                             'stage': model['cohort'].stage,
                             'syllabus_version_id': model['cohort'].syllabus_version.id,
                             'schedule_id': model2.syllabus_schedule.id,
                             'timezone': 'Europe/Monaco',
                         }])

        self.assertEqual(self.bc.database.list_of('admissions.CohortTimeSlot'),
                         [{
                             'cohort_id': 1,
                             'ending_at': syllabus_schedule_time_slot.ending_at,
                             'id': syllabus_schedule_time_slot.id,
                             'timezone': model.cohort.timezone,
                             'recurrency_type': syllabus_schedule_time_slot.recurrency_type,
                             'recurrent': syllabus_schedule_time_slot.recurrent,
                             'starting_at': syllabus_schedule_time_slot.starting_at,
                         } for syllabus_schedule_time_slot in model2.syllabus_schedule_time_slot])

        self.assertEqual(cohort_saved.send.call_args_list,
                         [call(instance=model.cohort, sender=model.cohort.__class__, created=False)])

    """
    🔽🔽🔽 Put with some data, of other academy, syllabus public
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_id__put__with_id__schedule_related_to_syllabus_of_other_academy_public(self):
        """Test /cohort/:id without auth"""

        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        cohort_kwargs = {'ending_date': timezone.now()}
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        academy = {'timezone': 'Pacific/Pago_Pago'}
        timeslot = {'timezone': 'Europe/Amsterdam'}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     academy=academy,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_schedule=True,
                                     cohort_kwargs=cohort_kwargs,
                                     syllabus_schedule_time_slot=True,
                                     cohort_time_slot=True,
                                     syllabus_kwargs=syllabus_kwargs)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        syllabus = {'private': False}
        model2 = self.generate_models(academy=1,
                                      skip_cohort=True,
                                      syllabus=syllabus,
                                      syllabus_schedule=True,
                                      syllabus_schedule_time_slot=(2, timeslot))
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'syllabus': f'{model.syllabus.slug}.v{model.syllabus_version.version}',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'schedule': 2,
            'current_day': model['cohort'].current_day + 1,
            'language': 'es',
        }
        response = self.client.put(url, data)
        json = response.json()

        expected = {
            'id':
            model['cohort'].id,
            'slug':
            data['slug'],
            'name':
            data['name'],
            'never_ends':
            False,
            'remote_available':
            True,
            'private':
            False,
            'language':
            data['language'],
            'kickoff_date':
            self.datetime_to_iso(model['cohort'].kickoff_date),
            'ending_date':
            self.datetime_to_iso(model['cohort'].ending_date),
            'current_day':
            data['current_day'],
            'current_module':
            None,
            'stage':
            model['cohort'].stage,
            'online_meeting_url':
            model['cohort'].online_meeting_url,
            'timezone':
            model['cohort'].timezone,
            'timeslots': [{
                'ending_at':
                DatetimeInteger.to_iso_string(model.academy.timezone, syllabus_schedule_time_slot.ending_at),
                'id':
                syllabus_schedule_time_slot.id,
                'recurrency_type':
                syllabus_schedule_time_slot.recurrency_type,
                'recurrent':
                syllabus_schedule_time_slot.recurrent,
                'starting_at':
                DatetimeInteger.to_iso_string(model.academy.timezone,
                                              syllabus_schedule_time_slot.starting_at),
            } for syllabus_schedule_time_slot in model2.syllabus_schedule_time_slot],
            'schedule': {
                'id': model2.syllabus_schedule.id,
                'name': model2.syllabus_schedule.name,
                'syllabus': model2.syllabus_schedule.syllabus.id,
            },
            'syllabus_version': {
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'status': model['cohort'].syllabus_version.status,
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
                'id': model.academy.id,
                'slug': model.academy.slug,
                'name': model.academy.name,
                'country': {
                    'code': model.academy.country.code,
                    'name': model.academy.country.name,
                },
                'city': {
                    'name': model.academy.city.name,
                },
                'logo_url': model.academy.logo_url,
            }
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'),
                         [{
                             'academy_id': 1,
                             'current_day': data['current_day'],
                             'current_module': None,
                             'ending_date': model['cohort'].ending_date,
                             'id': model['cohort'].id,
                             'kickoff_date': model['cohort'].kickoff_date,
                             'remote_available': model['cohort'].remote_available,
                             'online_meeting_url': model['cohort'].online_meeting_url,
                             'language': data['language'],
                             'name': data['name'],
                             'never_ends': False,
                             'private': False,
                             'slug': data['slug'],
                             'stage': model['cohort'].stage,
                             'syllabus_version_id': model['cohort'].syllabus_version.id,
                             'schedule_id': model2.syllabus_schedule.id,
                             'timezone': None,
                         }])

        self.assertEqual(self.bc.database.list_of('admissions.CohortTimeSlot'),
                         [{
                             'cohort_id': 1,
                             'ending_at': syllabus_schedule_time_slot.ending_at,
                             'id': syllabus_schedule_time_slot.id,
                             'timezone': model.academy.timezone,
                             'recurrency_type': syllabus_schedule_time_slot.recurrency_type,
                             'recurrent': syllabus_schedule_time_slot.recurrent,
                             'starting_at': syllabus_schedule_time_slot.starting_at,
                         } for syllabus_schedule_time_slot in model2.syllabus_schedule_time_slot])

        self.assertEqual(cohort_saved.send.call_args_list,
                         [call(instance=model.cohort, sender=model.cohort.__class__, created=False)])

    """
    🔽🔽🔽 Put with some data, of other academy, syllabus private
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_id__put__with_id__schedule_related_to_syllabus_of_other_academy_private(self):
        """Test /cohort/:id without auth"""

        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        cohort_kwargs = {'ending_date': timezone.now()}
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        academy = {'timezone': 'Pacific/Pago_Pago'}
        timeslot = {'timezone': 'Europe/Amsterdam'}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     academy=academy,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_schedule=True,
                                     cohort_kwargs=cohort_kwargs,
                                     syllabus_schedule_time_slot=True,
                                     cohort_time_slot=True,
                                     syllabus_kwargs=syllabus_kwargs)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        syllabus = {'private': True}
        model2 = self.generate_models(academy=1,
                                      skip_cohort=True,
                                      syllabus=syllabus,
                                      syllabus_schedule=True,
                                      syllabus_schedule_time_slot=(2, timeslot))
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'syllabus': f'{model.syllabus.slug}.v{model.syllabus_version.version}',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'schedule': 2,
            'current_day': model['cohort'].current_day + 1,
            'language': 'es',
        }
        response = self.client.put(url, data)
        json = response.json()

        expected = {
            'id': model['cohort'].id,
            'slug': data['slug'],
            'name': data['name'],
            'never_ends': False,
            'remote_available': True,
            'private': False,
            'language': data['language'],
            'kickoff_date': self.datetime_to_iso(model['cohort'].kickoff_date),
            'ending_date': self.datetime_to_iso(model['cohort'].ending_date),
            'current_day': data['current_day'],
            'current_module': None,
            'stage': model['cohort'].stage,
            'online_meeting_url': model['cohort'].online_meeting_url,
            'timezone': model['cohort'].timezone,
            'timeslots': [],
            'schedule': {
                'id': model2.syllabus_schedule.id,
                'name': model2.syllabus_schedule.name,
                'syllabus': model2.syllabus_schedule.syllabus.id,
            },
            'syllabus_version': {
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'status': model['cohort'].syllabus_version.status,
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
                'id': model.academy.id,
                'slug': model.academy.slug,
                'name': model.academy.name,
                'country': {
                    'code': model.academy.country.code,
                    'name': model.academy.country.name,
                },
                'city': {
                    'name': model.academy.city.name,
                },
                'logo_url': model.academy.logo_url,
            }
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'),
                         [{
                             'academy_id': 1,
                             'current_day': data['current_day'],
                             'current_module': None,
                             'ending_date': model['cohort'].ending_date,
                             'id': model['cohort'].id,
                             'kickoff_date': model['cohort'].kickoff_date,
                             'remote_available': model['cohort'].remote_available,
                             'online_meeting_url': model['cohort'].online_meeting_url,
                             'language': data['language'],
                             'name': data['name'],
                             'never_ends': False,
                             'private': False,
                             'slug': data['slug'],
                             'stage': model['cohort'].stage,
                             'syllabus_version_id': model['cohort'].syllabus_version.id,
                             'schedule_id': model2.syllabus_schedule.id,
                             'timezone': None,
                         }])

        self.assertEqual(self.bc.database.list_of('admissions.CohortTimeSlot'), [])
        self.assertEqual(cohort_saved.send.call_args_list,
                         [call(instance=model.cohort, sender=model.cohort.__class__, created=False)])

    """
    🔽🔽🔽 Get data
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_id__get__with_id(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato',
                                     syllabus_schedule=True,
                                     syllabus=True,
                                     syllabus_version=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        model_dict = self.remove_dinamics_fields(model['cohort'].__dict__)
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': model['cohort'].id})
        response = self.client.get(url)
        json = response.json()
        expected = {
            'id': model['cohort'].id,
            'slug': model['cohort'].slug,
            'name': model['cohort'].name,
            'never_ends': model['cohort'].never_ends,
            'remote_available': model['cohort'].remote_available,
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
                'status': model['cohort'].syllabus_version.status,
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
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)
        self.assertEqual(cohort_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Get with bad slug
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_id__get__with_bad_slug(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        self.generate_models(authenticate=True,
                             cohort=True,
                             profile_academy=True,
                             capability='read_all_cohort',
                             role='potato',
                             syllabus=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': 'they-killed-kenny'})
        response = self.client.get(url)

        self.assertEqual(response.data, None)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(cohort_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Get with slug
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_id__get__with_slug(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato',
                                     syllabus_schedule=True,
                                     syllabus=True,
                                     syllabus_version=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        model_dict = self.remove_dinamics_fields(model['cohort'].__dict__)
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': model['cohort'].slug})
        response = self.client.get(url)
        json = response.json()
        expected = {
            'id': model['cohort'].id,
            'slug': model['cohort'].slug,
            'name': model['cohort'].name,
            'never_ends': model['cohort'].never_ends,
            'remote_available': model['cohort'].remote_available,
            'private': model['cohort'].private,
            'kickoff_date': self.datetime_to_iso(model['cohort'].kickoff_date),
            'ending_date': model['cohort'].ending_date,
            'language': model['cohort'].language,
            'stage': model['cohort'].stage,
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
                'status': model['cohort'].syllabus_version.status,
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
                'country': model['cohort'].academy.country,
                'city': model['cohort'].academy.city,
                'logo_url': model['cohort'].academy.logo_url,
                'country': {
                    'code': model['cohort'].academy.country.code,
                    'name': model['cohort'].academy.country.name,
                },
                'city': {
                    'name': model['cohort'].academy.city.name,
                },
            },
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)
        self.assertEqual(cohort_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Delete with bad id
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_id__delete__with_bad_id(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato',
                                     syllabus=True,
                                     cohort_user=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': 0})
        self.assertEqual(self.count_cohort_user(), 1)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.count_cohort_stage(model['cohort'].id), 'INACTIVE')
        self.assertEqual(cohort_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Delete with id
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_cohort_id__delete__with_id(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': model['cohort'].id})
        self.assertEqual(self.count_cohort_stage(model['cohort'].id), 'INACTIVE')
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.count_cohort_user(), 0)
        self.assertEqual(self.count_cohort_stage(model['cohort'].id), 'DELETED')
        self.assertEqual(cohort_saved.send.call_args_list,
                         [call(instance=model.cohort, sender=model.cohort.__class__, created=False)])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort_id__delete__cohort_with_students(self):
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     cohort_user=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': 1})
        response = self.client.delete(url)
        json = response.json()
        expected = {
            'detail': 'cohort-has-students',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Spy the extensions
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    @patch.object(APIViewExtensionHandlers, '_spy_extensions', MagicMock())
    def test_cohort_id__get__spy_extensions(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato',
                                     syllabus_schedule=True,
                                     syllabus=True,
                                     syllabus_version=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': model['cohort'].id})
        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extensions.call_args_list, [
            call(['CacheExtension', 'PaginationExtension', 'SortExtension']),
        ])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    @patch.object(APIViewExtensionHandlers, '_spy_extension_arguments', MagicMock())
    def test_cohort_id__get__spy_extension_arguments(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato',
                                     syllabus_schedule=True,
                                     syllabus=True,
                                     syllabus_version=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': model['cohort'].id})
        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extension_arguments.call_args_list, [
            call(cache=CohortCache, sort='-kickoff_date', paginate=True),
        ])
