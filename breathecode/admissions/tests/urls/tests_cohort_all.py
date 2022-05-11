"""
Test /cohort/all
"""
from datetime import timedelta
import re
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status
from ..mixins import AdmissionsTestCase


class CohortAllTestSuite(AdmissionsTestCase):
    """Test /cohort/all"""
    def test_cohort_all_without_auth(self):
        """Test /cohort/all without auth"""
        url = reverse_lazy('admissions:cohort_all')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 0)

    def test_cohort_all_without_data(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True)
        url = reverse_lazy('admissions:cohort_all')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 0)

    def test_cohort_all_with_cohort_but_without_profile_academy(self):
        """Test /cohort/all without auth"""
        url = reverse_lazy('admissions:cohort_all')
        model = self.generate_models(authenticate=True, cohort=True)

        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{**self.model_to_dict(model, 'cohort')}])

    """
    🔽🔽🔽 Sort querystring
    """

    def test_cohort_all__with_data__with_sort(self):
        """Test /cohort/all without auth"""
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    skip_cohort=True,
                                    syllabus_version=True)

        models = [self.generate_models(cohort=True, syllabus=True, models=base) for _ in range(0, 2)]
        ordened_models = sorted(models, key=lambda x: x['cohort'].slug, reverse=True)

        url = reverse_lazy('admissions:cohort_all') + '?sort=-slug'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.cohort.id,
            'slug': model.cohort.slug,
            'name': model.cohort.name,
            'never_ends': model['cohort'].never_ends,
            'private': model['cohort'].private,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', model.cohort.kickoff_date.isoformat()),
            'ending_date': model.cohort.ending_date,
            'remote_available': model.cohort.remote_available,
            'language': model.cohort.language,
            'syllabus_version': {
                'status': model.syllabus_version.status,
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'syllabus': model.syllabus_version.syllabus.id,
                'version': model.cohort.syllabus_version.version,
                'duration_in_days': model.syllabus.duration_in_days,
                'duration_in_hours': model.syllabus.duration_in_hours,
                'github_url': model.syllabus.github_url,
                'logo': model.syllabus.logo,
                'private': model.syllabus.private,
                'week_hours': model.syllabus.week_hours,
            },
            'academy': {
                'id': model.cohort.academy.id,
                'slug': model.cohort.academy.slug,
                'name': model.cohort.academy.name,
                'country': {
                    'code': model.cohort.academy.country.code,
                    'name': model.cohort.academy.country.name,
                },
                'city': {
                    'name': model.cohort.academy.city.name,
                },
                'logo_url': model.cohort.academy.logo_url,
            },
            'schedule': None,
        } for model in ordened_models]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        } for model in models])

    def test_cohort_all_with_data_with_bad_get_academy(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True, cohort=True, profile_academy=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?academy=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{**self.model_to_dict(model, 'cohort')}])

    def test_cohort_all_with_data_with_get_academy(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     syllabus_version=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?academy={model.academy.slug}'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.cohort.id,
            'slug': model.cohort.slug,
            'name': model.cohort.name,
            'never_ends': model['cohort'].never_ends,
            'private': model['cohort'].private,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', model.cohort.kickoff_date.isoformat()),
            'ending_date': model.cohort.ending_date,
            'language': model.cohort.language,
            'remote_available': model.cohort.remote_available,
            'syllabus_version': {
                'status': model.syllabus_version.status,
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'syllabus': model.syllabus_version.syllabus.id,
                'version': model.cohort.syllabus_version.version,
                'duration_in_days': model.syllabus.duration_in_days,
                'duration_in_hours': model.syllabus.duration_in_hours,
                'github_url': model.syllabus.github_url,
                'logo': model.syllabus.logo,
                'private': model.syllabus.private,
                'week_hours': model.syllabus.week_hours,
            },
            'academy': {
                'id': model.cohort.academy.id,
                'slug': model.cohort.academy.slug,
                'name': model.cohort.academy.name,
                'country': {
                    'code': model.cohort.academy.country.code,
                    'name': model.cohort.academy.country.name,
                },
                'city': {
                    'name': model.cohort.academy.city.name,
                },
                'logo_url': model.cohort.academy.logo_url,
            },
            'schedule': None,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{**self.model_to_dict(model, 'cohort')}])

    def test_cohort_all_with_data_with_bad_get_location(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True, cohort=True, profile_academy=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?location=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{**self.model_to_dict(model, 'cohort')}])

    def test_cohort_all_with_data_with_get_location(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     syllabus_version=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?location={model.academy.slug}'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.cohort.id,
            'slug': model.cohort.slug,
            'name': model.cohort.name,
            'never_ends': model['cohort'].never_ends,
            'private': model['cohort'].private,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', model.cohort.kickoff_date.isoformat()),
            'ending_date': model.cohort.ending_date,
            'language': model.cohort.language,
            'remote_available': model.cohort.remote_available,
            'syllabus_version': {
                'status': model.syllabus_version.status,
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'syllabus': model.syllabus_version.syllabus.id,
                'version': model.cohort.syllabus_version.version,
                'duration_in_days': model.syllabus.duration_in_days,
                'duration_in_hours': model.syllabus.duration_in_hours,
                'github_url': model.syllabus.github_url,
                'logo': model.syllabus.logo,
                'private': model.syllabus.private,
                'week_hours': model.syllabus.week_hours,
            },
            'academy': {
                'id': model.cohort.academy.id,
                'slug': model.cohort.academy.slug,
                'name': model.cohort.academy.name,
                'country': {
                    'code': model.cohort.academy.country.code,
                    'name': model.cohort.academy.country.name,
                },
                'city': {
                    'name': model.cohort.academy.city.name,
                },
                'logo_url': model.cohort.academy.logo_url,
            },
            'schedule': None,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{**self.model_to_dict(model, 'cohort')}])

    def test_cohort_all_with_data_with_get_location_with_comma(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     syllabus_version=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?location={model.academy.slug},they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.cohort.id,
            'slug': model.cohort.slug,
            'name': model.cohort.name,
            'never_ends': model['cohort'].never_ends,
            'private': model['cohort'].private,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', model.cohort.kickoff_date.isoformat()),
            'ending_date': model.cohort.ending_date,
            'language': model.cohort.language,
            'remote_available': model.cohort.remote_available,
            'syllabus_version': {
                'status': model.syllabus_version.status,
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'syllabus': model.syllabus_version.syllabus.id,
                'version': model.cohort.syllabus_version.version,
                'duration_in_days': model.syllabus.duration_in_days,
                'duration_in_hours': model.syllabus.duration_in_hours,
                'github_url': model.syllabus.github_url,
                'logo': model.syllabus.logo,
                'private': model.syllabus.private,
                'week_hours': model.syllabus.week_hours,
            },
            'academy': {
                'id': model.cohort.academy.id,
                'slug': model.cohort.academy.slug,
                'name': model.cohort.academy.name,
                'country': {
                    'code': model.cohort.academy.country.code,
                    'name': model.cohort.academy.country.name,
                },
                'city': {
                    'name': model.cohort.academy.city.name,
                },
                'logo_url': model.cohort.academy.logo_url,
            },
            'schedule': None,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{**self.model_to_dict(model, 'cohort')}])

    def test_cohort_all_with_data_with_get_upcoming_false(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     syllabus_version=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?upcoming=false'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.cohort.id,
            'slug': model.cohort.slug,
            'name': model.cohort.name,
            'never_ends': model['cohort'].never_ends,
            'private': model['cohort'].private,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', model.cohort.kickoff_date.isoformat()),
            'ending_date': model.cohort.ending_date,
            'language': model.cohort.language,
            'remote_available': model.cohort.remote_available,
            'syllabus_version': {
                'status': model.syllabus_version.status,
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'syllabus': model.syllabus_version.syllabus.id,
                'version': model.cohort.syllabus_version.version,
                'duration_in_days': model.syllabus.duration_in_days,
                'duration_in_hours': model.syllabus.duration_in_hours,
                'github_url': model.syllabus.github_url,
                'logo': model.syllabus.logo,
                'private': model.syllabus.private,
                'week_hours': model.syllabus.week_hours,
            },
            'academy': {
                'id': model.cohort.academy.id,
                'slug': model.cohort.academy.slug,
                'name': model.cohort.academy.name,
                'country': {
                    'code': model.cohort.academy.country.code,
                    'name': model.cohort.academy.country.name,
                },
                'city': {
                    'name': model.cohort.academy.city.name,
                },
                'logo_url': model.cohort.academy.logo_url,
            },
            'schedule': None,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{**self.model_to_dict(model, 'cohort')}])

    def test_cohort_all_with_data_with_get_upcoming_true_without_current_data(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True, cohort=True, profile_academy=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?upcoming=true'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{**self.model_to_dict(model, 'cohort')}])

    def test_cohort_all_with_data_with_get_upcoming_true_with_current_data(self):
        """Test /cohort/all without auth"""
        cohort_kwargs = {'kickoff_date': timezone.now() + timedelta(days=365 * 2000)}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     syllabus_version=True,
                                     cohort_kwargs=cohort_kwargs)
        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?upcoming=true'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.cohort.id,
            'slug': model.cohort.slug,
            'name': model.cohort.name,
            'never_ends': model['cohort'].never_ends,
            'private': model['cohort'].private,
            'kickoff_date': self.datetime_to_iso(model['cohort'].kickoff_date),
            'ending_date': model.cohort.ending_date,
            'language': model.cohort.language,
            'remote_available': model.cohort.remote_available,
            'syllabus_version': {
                'status': model.syllabus_version.status,
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'syllabus': model.syllabus_version.syllabus.id,
                'version': model.cohort.syllabus_version.version,
                'duration_in_days': model.syllabus.duration_in_days,
                'duration_in_hours': model.syllabus.duration_in_hours,
                'github_url': model.syllabus.github_url,
                'logo': model.syllabus.logo,
                'private': model.syllabus.private,
                'week_hours': model.syllabus.week_hours,
            },
            'academy': {
                'id': model.cohort.academy.id,
                'slug': model.cohort.academy.slug,
                'name': model.cohort.academy.name,
                'country': {
                    'code': model.cohort.academy.country.code,
                    'name': model.cohort.academy.country.name,
                },
                'city': {
                    'name': model.cohort.academy.city.name,
                },
                'logo_url': model.cohort.academy.logo_url,
            },
            'schedule': None,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{**self.model_to_dict(model, 'cohort')}])

    def test_cohort_all_with_data(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     syllabus_version=True)

        url = reverse_lazy('admissions:cohort_all')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.cohort.id,
            'slug': model.cohort.slug,
            'name': model.cohort.name,
            'never_ends': model['cohort'].never_ends,
            'private': model['cohort'].private,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', model.cohort.kickoff_date.isoformat()),
            'ending_date': model.cohort.ending_date,
            'language': model.cohort.language,
            'remote_available': model.cohort.remote_available,
            'syllabus_version': {
                'status': model.syllabus_version.status,
                'name': model.syllabus.name,
                'slug': model.syllabus.slug,
                'syllabus': model.syllabus_version.syllabus.id,
                'version': model.cohort.syllabus_version.version,
                'duration_in_days': model.syllabus.duration_in_days,
                'duration_in_hours': model.syllabus.duration_in_hours,
                'github_url': model.syllabus.github_url,
                'logo': model.syllabus.logo,
                'private': model.syllabus.private,
                'week_hours': model.syllabus.week_hours,
            },
            'academy': {
                'id': model.cohort.academy.id,
                'slug': model.cohort.academy.slug,
                'name': model.cohort.academy.name,
                'country': {
                    'code': model.cohort.academy.country.code,
                    'name': model.cohort.academy.country.name,
                },
                'city': {
                    'name': model.cohort.academy.city.name,
                },
                'logo_url': model.cohort.academy.logo_url,
            },
            'schedule': None,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{**self.model_to_dict(model, 'cohort')}])

    def test_cohort_all_with_data_but_is_private(self):
        """Test /cohort/all without auth"""
        cohort_kwargs = {'private': True}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     syllabus=True,
                                     cohort_kwargs=cohort_kwargs)

        url = reverse_lazy('admissions:cohort_all')
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{**self.model_to_dict(model, 'cohort')}])
