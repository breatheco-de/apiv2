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

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
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
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort__without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort')
        self.bc.database.create(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': "You (user: 1) don't have this capability: read_all_cohort for academy 1",
                'status_code': 403
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 Post
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort__post__without_profile_academy(self):
        """Test /academy/cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        cohort=True,
                                        user=True,
                                        profile_academy=True,
                                        capability='crud_cohort',
                                        role='potato',
                                        syllabus=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

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
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort__post__with_bad_fields(self):
        """Test /academy/cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        model = self.bc.database.create(authenticate=True,
                                        cohort=True,
                                        user=True,
                                        profile_academy=True,
                                        capability='crud_cohort',
                                        role='potato',
                                        syllabus_schedule=True,
                                        syllabus=True,
                                        syllabus_kwargs=syllabus_kwargs)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'syllabus': model['syllabus'].id,
            'schedule': 1,
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
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort__post__with_bad_current_day(self):
        """Test /academy/cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        model = self.bc.database.create(authenticate=True,
                                        cohort=True,
                                        user=True,
                                        profile_academy=True,
                                        capability='crud_cohort',
                                        role='potato',
                                        syllabus=True,
                                        syllabus_schedule=True,
                                        syllabus_kwargs=syllabus_kwargs)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'syllabus': model['syllabus'].id,
            'current_day': 999,
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'kickoff_date': datetime.today().isoformat(),
            'schedule': 1,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'current-day-not-allowed', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    # @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    # def test_academy_cohort__post__without_schedule(self):
    #     """Test /academy/cohort without auth"""
    #     from breathecode.admissions.signals import cohort_saved
    #
    #     self.headers(academy=1)
    #     model = self.bc.database.create(authenticate=True,
    #                                  user=True,
    #                                  profile_academy=True,
    #                                  capability='crud_cohort',
    #                                  role='potato',
    #                                  syllabus_schedule=True,
    #                                  syllabus=True,
    #                                  syllabus_version=True,
    #                                  skip_cohort=True,
    #                                  syllabus_schedule_time_slot=True)
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

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort__post__without_ending_date_or_never_ends(self):
        """Test /academy/cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        model = self.bc.database.create(authenticate=True,
                                        user=True,
                                        profile_academy=True,
                                        capability='crud_cohort',
                                        role='potato',
                                        syllabus_schedule=True,
                                        syllabus=True,
                                        syllabus_version=True,
                                        skip_cohort=True,
                                        syllabus_schedule_time_slot=True,
                                        syllabus_kwargs=syllabus_kwargs)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'syllabus': f'{model.syllabus.slug}.v{model.syllabus_version.version}',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'kickoff_date': datetime.today().isoformat(),
            'schedule': 1,
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
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort__post__with_ending_date_and_never_ends_true(self):
        """Test /academy/cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        model = self.bc.database.create(authenticate=True,
                                        user=True,
                                        profile_academy=True,
                                        capability='crud_cohort',
                                        role='potato',
                                        syllabus_schedule=True,
                                        syllabus=True,
                                        syllabus_version=True,
                                        skip_cohort=True,
                                        syllabus_schedule_time_slot=True,
                                        syllabus_kwargs=syllabus_kwargs)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'syllabus': f'{model.syllabus.slug}.v{model.syllabus_version.version}',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'kickoff_date': datetime.today().isoformat(),
            'ending_date': datetime.today().isoformat(),
            'never_ends': True,
            'schedule': 1,
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
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort__post__without_ending_date_and_never_ends_false(self):
        """Test /academy/cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        model = self.bc.database.create(authenticate=True,
                                        user=True,
                                        profile_academy=True,
                                        capability='crud_cohort',
                                        role='potato',
                                        syllabus_schedule=True,
                                        syllabus=True,
                                        syllabus_version=True,
                                        skip_cohort=True,
                                        syllabus_schedule_time_slot=True,
                                        syllabus_kwargs=syllabus_kwargs)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'syllabus': f'{model.syllabus.slug}.v{model.syllabus_version.version}',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'kickoff_date': datetime.today().isoformat(),
            'never_ends': False,
            'schedule': 1,
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
        self.assertEqual(cohort_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Put assigning the syllabus version 1
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort__post__assigning_syllabus_version_1(self):
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        syllabus_version = {'version': 1}
        model = self.bc.database.create(authenticate=True,
                                        user=True,
                                        profile_academy=True,
                                        capability='crud_cohort',
                                        role='potato',
                                        syllabus_schedule=True,
                                        syllabus=True,
                                        syllabus_version=syllabus_version,
                                        skip_cohort=True,
                                        syllabus_schedule_time_slot=True,
                                        syllabus_kwargs=syllabus_kwargs)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        models_dict = self.all_cohort_dict()
        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'syllabus': f'{model.syllabus.slug}.v{model.syllabus_version.version}',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'kickoff_date': datetime.today().isoformat(),
            'never_ends': True,
            'schedule': 1,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'assigning-a-syllabus-version-1', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort__post__without_timezone(self):
        """Test /academy/cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        model = self.bc.database.create(authenticate=True,
                                        user=True,
                                        profile_academy=True,
                                        capability='crud_cohort',
                                        role='potato',
                                        syllabus_schedule=True,
                                        syllabus=True,
                                        syllabus_version=True,
                                        skip_cohort=True,
                                        syllabus_schedule_time_slot=True,
                                        syllabus_kwargs=syllabus_kwargs)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        models_dict = self.all_cohort_dict()
        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'syllabus': f'{model.syllabus.slug}.v{model.syllabus_version.version}',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'kickoff_date': datetime.today().isoformat(),
            'never_ends': True,
            'remote_available': True,
            'schedule': 1,
        }
        response = self.client.post(url, data)
        json = response.json()
        cohort = self.get_cohort(1)
        expected = {
            'id': cohort.id,
            'slug': cohort.slug,
            'name': cohort.name,
            'never_ends': True,
            'remote_available': True,
            'kickoff_date': self.datetime_to_iso(cohort.kickoff_date),
            'current_day': cohort.current_day,
            'schedule': cohort.schedule.id,
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
        del cohort_two['schedule']

        models_dict.append(self.remove_dinamics_fields({**cohort_two}))

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_cohort_dict(), models_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
        self.assertEqual(cohort_saved.send.call_args_list,
                         [call(instance=cohort, sender=cohort.__class__, created=True)])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort__post__kickoff_date_greater_than_ending_date(self):
        """Test /academy/cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        model = self.generate_models(authenticate=True,
                                     user=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus_schedule=True,
                                     syllabus=True,
                                     syllabus_version=True,
                                     skip_cohort=True,
                                     syllabus_schedule_time_slot=True,
                                     syllabus_kwargs=syllabus_kwargs)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        url = reverse_lazy('admissions:academy_cohort')
        utc_now = timezone.now()
        data = {
            'syllabus': f'{model.syllabus.slug}.v{model.syllabus_version.version}',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'kickoff_date': datetime.today().isoformat(),
            'schedule': 1,
            'kickoff_date': utc_now + timedelta(seconds=1),
            'ending_date': utc_now,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'kickoff-date-greather-than-ending-date', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_dict(), [])
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort__post__with_timezone(self):
        """Test /academy/cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        academy_kwargs = {'timezone': 'America/Caracas'}
        model = self.bc.database.create(authenticate=True,
                                        user=True,
                                        profile_academy=True,
                                        capability='crud_cohort',
                                        role='potato',
                                        syllabus_schedule=True,
                                        syllabus=True,
                                        syllabus_version=True,
                                        skip_cohort=True,
                                        syllabus_schedule_time_slot=True,
                                        syllabus_kwargs=syllabus_kwargs,
                                        academy_kwargs=academy_kwargs)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        models_dict = self.all_cohort_dict()
        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'syllabus': f'{model.syllabus.slug}.v{model.syllabus_version.version}',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'kickoff_date': datetime.today().isoformat(),
            'never_ends': True,
            'remote_available': True,
            'schedule': 1,
        }
        response = self.client.post(url, data)
        json = response.json()
        cohort = self.get_cohort(1)
        expected = {
            'id': cohort.id,
            'slug': cohort.slug,
            'name': cohort.name,
            'never_ends': True,
            'remote_available': True,
            'kickoff_date': self.datetime_to_iso(cohort.kickoff_date),
            'current_day': cohort.current_day,
            'schedule': cohort.schedule.id,
            'online_meeting_url': cohort.online_meeting_url,
            'timezone': model.academy.timezone,
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
        del cohort_two['schedule']

        models_dict.append(self.remove_dinamics_fields({**cohort_two}))

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_cohort_dict(), models_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(),
                         [{
                             'id': 1,
                             'cohort_id': 1,
                             'starting_at': model.syllabus_schedule_time_slot.starting_at,
                             'ending_at': model.syllabus_schedule_time_slot.ending_at,
                             'recurrent': model.syllabus_schedule_time_slot.recurrent,
                             'recurrency_type': model.syllabus_schedule_time_slot.recurrency_type,
                             'timezone': model.academy.timezone,
                         }])
        self.assertEqual(cohort_saved.send.call_args_list,
                         [call(instance=cohort, sender=cohort.__class__, created=True)])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort__post__with_timezone__passing_custom_timezone(self):
        """Test /academy/cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        academy_kwargs = {'timezone': 'America/Caracas'}
        model = self.bc.database.create(authenticate=True,
                                        user=True,
                                        profile_academy=True,
                                        capability='crud_cohort',
                                        role='potato',
                                        syllabus_schedule=True,
                                        syllabus=True,
                                        syllabus_version=True,
                                        skip_cohort=True,
                                        syllabus_schedule_time_slot=True,
                                        syllabus_kwargs=syllabus_kwargs,
                                        academy_kwargs=academy_kwargs)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        models_dict = self.all_cohort_dict()
        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'syllabus': f'{model.syllabus.slug}.v{model.syllabus_version.version}',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'kickoff_date': datetime.today().isoformat(),
            'never_ends': True,
            'remote_available': True,
            'schedule': 1,
            'timezone': 'Pacific/Pago_Pago',
        }
        response = self.client.post(url, data)
        json = response.json()
        cohort = self.get_cohort(1)
        expected = {
            'id': cohort.id,
            'slug': cohort.slug,
            'name': cohort.name,
            'never_ends': True,
            'remote_available': True,
            'kickoff_date': self.datetime_to_iso(cohort.kickoff_date),
            'current_day': cohort.current_day,
            'schedule': cohort.schedule.id,
            'online_meeting_url': cohort.online_meeting_url,
            'timezone': 'Pacific/Pago_Pago',
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
        del cohort_two['schedule']

        models_dict.append(self.remove_dinamics_fields({**cohort_two}))

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_cohort_dict(), models_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(),
                         [{
                             'id': 1,
                             'cohort_id': 1,
                             'starting_at': model.syllabus_schedule_time_slot.starting_at,
                             'ending_at': model.syllabus_schedule_time_slot.ending_at,
                             'recurrent': model.syllabus_schedule_time_slot.recurrent,
                             'recurrency_type': model.syllabus_schedule_time_slot.recurrency_type,
                             'timezone': 'Pacific/Pago_Pago',
                         }])
        self.assertEqual(cohort_saved.send.call_args_list,
                         [call(instance=cohort, sender=cohort.__class__, created=True)])

    # """

    # NEW TESTS HERE!!!
    """
    🔽🔽🔽 Without data
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort_without_data(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort')
        model = self.bc.database.create(authenticate=True,
                                        profile_academy=True,
                                        capability='read_all_cohort',
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
    def test_academy_cohort__with_data(self):
        """Test /cohort without auth"""
        self.check_academy_cohort__with_data()

    """
    🔽🔽🔽 Put
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort__put__without_id(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort')
        model = self.bc.database.create(authenticate=True,
                                        profile_academy=True,
                                        capability='crud_cohort',
                                        role='potato',
                                        syllabus=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(json, {'detail': 'Missing cohort_id', 'status_code': 400})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Get
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort__with_data__with_upcoming_false(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        cohort=True,
                                        profile_academy=True,
                                        capability='read_all_cohort',
                                        role='potato',
                                        syllabus=True,
                                        syllabus_version=True,
                                        syllabus_schedule=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

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
            'remote_available': model['cohort'].remote_available,
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
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort__with_data__with_upcoming_true__without_data(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        self.clear_cache()
        model = self.bc.database.create(authenticate=True,
                                        cohort=True,
                                        profile_academy=True,
                                        capability='read_all_cohort',
                                        role='potato',
                                        syllabus=True,
                                        syllabus_version=True,
                                        syllabus_schedule=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

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
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort__with_data__with_upcoming_true(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        cohort_kwargs = {
            'kickoff_date': timezone.now() + timedelta(days=1),
        }
        model = self.bc.database.create(authenticate=True,
                                        cohort=True,
                                        profile_academy=True,
                                        capability='read_all_cohort',
                                        role='potato',
                                        syllabus=True,
                                        syllabus_version=True,
                                        syllabus_schedule=True,
                                        cohort_kwargs=cohort_kwargs)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

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
            'remote_available': model['cohort'].remote_available,
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
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort__with_data__with_bad_academy(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        cohort=True,
                                        impossible_kickoff_date=True,
                                        profile_academy=True,
                                        capability='read_all_cohort',
                                        role='potato',
                                        syllabus=True,
                                        syllabus_version=True,
                                        syllabus_schedule=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

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
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort_with_data_with_academy(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        cohort=True,
                                        profile_academy=True,
                                        capability='read_all_cohort',
                                        role='potato',
                                        syllabus=True,
                                        syllabus_version=True,
                                        syllabus_schedule=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

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
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort_with_data_with_academy_with_comma(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        cohort=True,
                                        profile_academy=True,
                                        capability='read_all_cohort',
                                        role='potato',
                                        syllabus=True,
                                        syllabus_version=True,
                                        syllabus_schedule=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

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
            'remote_available': model['cohort'].remote_available,
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
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort_with_ten_datas_with_academy_with_comma(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        models = [
            self.bc.database.create(authenticate=True,
                                    cohort=True,
                                    profile_academy=True,
                                    capability='read_all_cohort',
                                    role='potato',
                                    syllabus=True,
                                    syllabus_version=True,
                                    syllabus_schedule=True)
        ]

        base = models[0].copy()
        del base['cohort']

        models = models + [self.bc.database.create(cohort=True, models=base) for index in range(0, 9)]
        models.sort(key=lambda x: x.cohort.kickoff_date, reverse=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

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
            'remote_available': model['cohort'].remote_available,
            'private': model['cohort'].private,
            'language': model['cohort'].language,
            'kickoff_date': datetime_to_iso_format(model['cohort'].kickoff_date),
            'ending_date': model['cohort'].ending_date,
            'stage': model['cohort'].stage,
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
        } for model in models]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), self.all_model_dict([x.cohort for x in models]))
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Sort in querystring
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort__with_data__with_sort(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        base = self.bc.database.create(authenticate=True,
                                       profile_academy=True,
                                       capability='read_all_cohort',
                                       role='potato',
                                       skip_cohort=True)

        models = [
            self.bc.database.create(cohort=True,
                                    syllabus=True,
                                    syllabus_version=True,
                                    syllabus_schedule=True,
                                    models=base) for _ in range(0, 2)
        ]

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        ordened_models = sorted(models, key=lambda x: x['cohort'].slug, reverse=True)

        url = reverse_lazy('admissions:academy_cohort') + '?sort=-slug'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort'].id,
            'slug': model['cohort'].slug,
            'name': model['cohort'].name,
            'current_day': model.cohort.current_day,
            'current_module': None,
            'never_ends': model['cohort'].never_ends,
            'remote_available': model['cohort'].remote_available,
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
        } for model in ordened_models]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        } for model in models])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort_with_data_with_bad_location(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        cohort=True,
                                        profile_academy=True,
                                        capability='read_all_cohort',
                                        role='potato',
                                        syllabus=True,
                                        syllabus_version=True,
                                        syllabus_schedule=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

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
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort_with_data_with_location(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        cohort=True,
                                        profile_academy=True,
                                        capability='read_all_cohort',
                                        role='potato',
                                        syllabus=True,
                                        syllabus_version=True,
                                        syllabus_schedule=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

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
            'remote_available': model['cohort'].remote_available,
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
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort_with_data_with_location_with_comma(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        cohort=True,
                                        profile_academy=True,
                                        capability='read_all_cohort',
                                        role='potato',
                                        syllabus=True,
                                        syllabus_version=True,
                                        syllabus_schedule=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

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
            'remote_available': model['cohort'].remote_available,
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
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort_with_ten_datas_with_location_with_comma(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        models = [
            self.bc.database.create(authenticate=True,
                                    cohort=True,
                                    profile_academy=True,
                                    capability='read_all_cohort',
                                    role='potato',
                                    syllabus=True,
                                    syllabus_version=True,
                                    syllabus_schedule=True)
        ]

        base = models[0].copy()
        del base['cohort']

        models = models + [self.bc.database.create(cohort=True, models=base) for index in range(0, 9)]
        models.sort(key=lambda x: x.cohort.kickoff_date, reverse=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

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
            'remote_available': model['cohort'].remote_available,
            'private': model['cohort'].private,
            'language': model['cohort'].language,
            'kickoff_date': datetime_to_iso_format(model['cohort'].kickoff_date),
            'ending_date': model['cohort'].ending_date,
            'stage': model['cohort'].stage,
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
        } for model in models]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), self.all_model_dict([x.cohort for x in models]))
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort_delete_without_args_in_url_or_bulk(self):
        """Test /cohort/:id/user without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        profile_academy=True,
                                        capability='crud_cohort',
                                        role='potato')

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

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
        self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort_delete_in_bulk_with_students(self):
        """Test /cohort/:id/user without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        many_fields = ['id']

        base = self.bc.database.create(academy=True, capability='crud_cohort', role='potato')

        expected = {
            'detail': 'cohort-has-students',
            'status_code': 400,
        }

        for field in many_fields:
            model = self.bc.database.create(authenticate=True,
                                            profile_academy=True,
                                            cohort_user=True,
                                            models=base)

            # reset because this call are coming from mixer
            cohort_saved.send.call_args_list = []

            value = getattr(model['cohort'], field)

            url = (reverse_lazy('admissions:academy_cohort') + f'?{field}=' + str(value))
            response = self.client.delete(url)
            json = response.json()

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

            self.assertEqual(self.all_cohort_dict(), [{**self.model_to_dict(model, 'cohort')}])
            self.assertEqual(cohort_saved.send.call_args_list, [])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort_delete_in_bulk_with_one(self):
        """Test /cohort/:id/user without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)

        many_fields = ['id']
        base = self.bc.database.create(academy=True, capability='crud_cohort', role='potato')

        for field in many_fields:
            cohort_kwargs = {
                'kickoff_date': datetime.now(),
                'ending_date': datetime.now(),
                'timezone': choice(['-1', '-2', '-3', '-4', '-5']),
            }
            model = self.bc.database.create(authenticate=True,
                                            profile_academy=True,
                                            cohort_kwargs=cohort_kwargs,
                                            models=base)

            # reset because this call are coming from mixer
            cohort_saved.send.call_args_list = []

            value = getattr(model['cohort'], field)

            url = (reverse_lazy('admissions:academy_cohort') + f'?{field}=' + str(value))
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.count_cohort_user(), 0)
            self.assertEqual(self.count_cohort_stage(model['cohort'].id), 'DELETED')
            self.assertEqual(cohort_saved.send.call_args_list,
                             [call(instance=model.cohort, sender=model.cohort.__class__, created=False)])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test_academy_cohort_delete_in_bulk_with_two(self):
        """Test /cohort/:id/user without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        many_fields = ['id']

        base = self.bc.database.create(academy=True, capability='crud_cohort', role='potato')

        for field in many_fields:
            cohort_kwargs = {
                'kickoff_date': datetime.now(),
                'ending_date': datetime.now(),
                'timezone': choice(['-1', '-2', '-3', '-4', '-5']),
            }
            model1 = self.bc.database.create(authenticate=True,
                                             profile_academy=True,
                                             syllabus=True,
                                             cohort_kwargs=cohort_kwargs,
                                             models=base)

            cohort_kwargs = {
                'kickoff_date': datetime.now(),
                'ending_date': datetime.now(),
                'timezone': choice(['-1', '-2', '-3', '-4', '-5']),
            }
            model2 = self.bc.database.create(profile_academy=True,
                                             syllabus=True,
                                             cohort_kwargs=cohort_kwargs,
                                             models=base)

            # reset because this call are coming from mixer
            cohort_saved.send.call_args_list = []

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
            self.assertEqual(cohort_saved.send.call_args_list,
                             [call(instance=model1.cohort, sender=model1.cohort.__class__, created=False)])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    @patch.object(APIViewExtensionHandlers, '_spy_extensions', MagicMock())
    def test_academy_cohort__spy_extensions(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort')
        model = self.bc.database.create(authenticate=True,
                                        profile_academy=True,
                                        capability='read_all_cohort',
                                        role='potato',
                                        syllabus=True,
                                        skip_cohort=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extensions.call_args_list, [
            call(['CacheExtension', 'PaginationExtension', 'SortExtension']),
        ])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    @patch.object(APIViewExtensionHandlers, '_spy_extension_arguments', MagicMock())
    def test_academy_cohort__spy_extension_arguments(self):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort')
        model = self.bc.database.create(authenticate=True,
                                        profile_academy=True,
                                        capability='read_all_cohort',
                                        role='potato',
                                        syllabus=True,
                                        skip_cohort=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extension_arguments.call_args_list, [
            call(cache=CohortCache, sort='-kickoff_date', paginate=True),
        ])
