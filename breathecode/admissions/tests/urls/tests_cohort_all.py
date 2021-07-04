"""
Test /cohort/all
"""
import re
from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins.new_admissions_test_case import AdmissionsTestCase


class CohortAllTestSuite(AdmissionsTestCase):
    """Test /cohort/all"""
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_without_auth(self):
        """Test /cohort/all without auth"""
        url = reverse_lazy('admissions:cohort_all')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_without_data(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True)
        url = reverse_lazy('admissions:cohort_all')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_cohort_but_without_profile_academy(self):
        """Test /cohort/all without auth"""
        url = reverse_lazy('admissions:cohort_all')
        model = self.generate_models(authenticate=True, cohort=True)

        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        }])

    """
    🔽🔽🔽 Sort querystring
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all__with_data__with_sort(self):
        """Test /cohort/all without auth"""
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    skip_cohort=True)

        models = [
            self.generate_models(cohort=True, syllabus=True, models=base)
            for _ in range(0, 2)
        ]
        ordened_models = sorted(models,
                                key=lambda x: x['cohort'].slug,
                                reverse=True)

        url = reverse_lazy('admissions:cohort_all') + '?sort=-slug'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id':
            model.cohort.id,
            'slug':
            model.cohort.slug,
            'name':
            model.cohort.name,
            'current_day':
            model.cohort.current_day,
            'never_ends':
            model['cohort'].never_ends,
            'private':
            model['cohort'].private,
            'kickoff_date':
            re.sub(r'\+00:00$', 'Z', model.cohort.kickoff_date.isoformat()),
            'ending_date':
            model.cohort.ending_date,
            'stage':
            model.cohort.stage,
            'language':
            model.cohort.language,
            'syllabus': {
                'version': model.cohort.syllabus.version,
                'certificate': {
                    'id':
                    model.cohort.syllabus.certificate.id,
                    'slug':
                    model.cohort.syllabus.certificate.slug,
                    'name':
                    model.cohort.syllabus.certificate.name,
                    'duration_in_days':
                    model.cohort.syllabus.certificate.duration_in_days,
                }
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
        } for model in ordened_models]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        } for model in models])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_bad_get_academy(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?academy=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_get_academy(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     syllabus=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?academy={model.academy.slug}'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id':
            model.cohort.id,
            'slug':
            model.cohort.slug,
            'name':
            model.cohort.name,
            'never_ends':
            model['cohort'].never_ends,
            'private':
            model['cohort'].private,
            'kickoff_date':
            re.sub(r'\+00:00$', 'Z', model.cohort.kickoff_date.isoformat()),
            'ending_date':
            model.cohort.ending_date,
            'stage':
            model.cohort.stage,
            'language':
            model.cohort.language,
            'current_day':
            model.cohort.current_day,
            'syllabus': {
                'version': model.cohort.syllabus.version,
                'certificate': {
                    'id':
                    model.cohort.syllabus.certificate.id,
                    'slug':
                    model.cohort.syllabus.certificate.slug,
                    'name':
                    model.cohort.syllabus.certificate.name,
                    'duration_in_days':
                    model.cohort.syllabus.certificate.duration_in_days,
                }
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
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_bad_get_location(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?location=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_get_location(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     syllabus=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?location={model.academy.slug}'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id':
            model.cohort.id,
            'slug':
            model.cohort.slug,
            'name':
            model.cohort.name,
            'never_ends':
            model['cohort'].never_ends,
            'private':
            model['cohort'].private,
            'kickoff_date':
            re.sub(r'\+00:00$', 'Z', model.cohort.kickoff_date.isoformat()),
            'ending_date':
            model.cohort.ending_date,
            'stage':
            model.cohort.stage,
            'language':
            model.cohort.language,
            'current_day':
            model.cohort.current_day,
            'syllabus': {
                'version': model.cohort.syllabus.version,
                'certificate': {
                    'id':
                    model.cohort.syllabus.certificate.id,
                    'slug':
                    model.cohort.syllabus.certificate.slug,
                    'name':
                    model.cohort.syllabus.certificate.name,
                    'duration_in_days':
                    model.cohort.syllabus.certificate.duration_in_days,
                }
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
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_get_location_with_comma(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     syllabus=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?location={model.academy.slug},they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id':
            model.cohort.id,
            'slug':
            model.cohort.slug,
            'name':
            model.cohort.name,
            'never_ends':
            model['cohort'].never_ends,
            'private':
            model['cohort'].private,
            'kickoff_date':
            re.sub(r'\+00:00$', 'Z', model.cohort.kickoff_date.isoformat()),
            'ending_date':
            model.cohort.ending_date,
            'stage':
            model.cohort.stage,
            'language':
            model.cohort.language,
            'current_day':
            model.cohort.current_day,
            'syllabus': {
                'version': model.cohort.syllabus.version,
                'certificate': {
                    'id':
                    model.cohort.syllabus.certificate.id,
                    'slug':
                    model.cohort.syllabus.certificate.slug,
                    'name':
                    model.cohort.syllabus.certificate.name,
                    'duration_in_days':
                    model.cohort.syllabus.certificate.duration_in_days,
                }
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
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_get_upcoming_false(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     syllabus=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?upcoming=false'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id':
            model.cohort.id,
            'slug':
            model.cohort.slug,
            'name':
            model.cohort.name,
            'never_ends':
            model['cohort'].never_ends,
            'private':
            model['cohort'].private,
            'kickoff_date':
            re.sub(r'\+00:00$', 'Z', model.cohort.kickoff_date.isoformat()),
            'ending_date':
            model.cohort.ending_date,
            'stage':
            model.cohort.stage,
            'language':
            model.cohort.language,
            'current_day':
            model.cohort.current_day,
            'syllabus': {
                'version': model.cohort.syllabus.version,
                'certificate': {
                    'id':
                    model.cohort.syllabus.certificate.id,
                    'slug':
                    model.cohort.syllabus.certificate.slug,
                    'name':
                    model.cohort.syllabus.certificate.name,
                    'duration_in_days':
                    model.cohort.syllabus.certificate.duration_in_days,
                }
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
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_get_upcoming_true_without_current_data(
            self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?upcoming=true'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_get_upcoming_true_with_current_data(
            self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     impossible_kickoff_date=True,
                                     syllabus=True)
        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?upcoming=true'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id':
            model.cohort.id,
            'slug':
            model.cohort.slug,
            'name':
            model.cohort.name,
            'never_ends':
            model['cohort'].never_ends,
            'private':
            model['cohort'].private,
            'kickoff_date':
            self.datetime_to_iso(model['cohort'].kickoff_date),
            'ending_date':
            model.cohort.ending_date,
            'stage':
            model.cohort.stage,
            'language':
            model.cohort.language,
            'current_day':
            model.cohort.current_day,
            'syllabus': {
                'version': model.cohort.syllabus.version,
                'certificate': {
                    'id':
                    model.cohort.syllabus.certificate.id,
                    'slug':
                    model.cohort.syllabus.certificate.slug,
                    'name':
                    model.cohort.syllabus.certificate.name,
                    'duration_in_days':
                    model.cohort.syllabus.certificate.duration_in_days,
                }
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
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     syllabus=True)

        url = reverse_lazy('admissions:cohort_all')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id':
            model.cohort.id,
            'slug':
            model.cohort.slug,
            'name':
            model.cohort.name,
            'never_ends':
            model['cohort'].never_ends,
            'private':
            model['cohort'].private,
            'kickoff_date':
            re.sub(r'\+00:00$', 'Z', model.cohort.kickoff_date.isoformat()),
            'ending_date':
            model.cohort.ending_date,
            'stage':
            model.cohort.stage,
            'language':
            model.cohort.language,
            'current_day':
            model.cohort.current_day,
            'syllabus': {
                'version': model.cohort.syllabus.version,
                'certificate': {
                    'id':
                    model.cohort.syllabus.certificate.id,
                    'slug':
                    model.cohort.syllabus.certificate.slug,
                    'name':
                    model.cohort.syllabus.certificate.name,
                    'duration_in_days':
                    model.cohort.syllabus.certificate.duration_in_days,
                }
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
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
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
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        }])
