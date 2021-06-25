"""
Test /cohort
"""
from django.utils import timezone
from breathecode.admissions.caches import CohortCache
import re
from unittest.mock import patch
from django.urls.base import reverse_lazy
from breathecode.utils import Cache
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins.new_admissions_test_case import AdmissionsTestCase
from .tests_academy_cohort import AcademyCohortTestSuite


class AcademyCohortIdTestSuite(AdmissionsTestCase):
    """Test /cohort"""

    cache = CohortCache()
    """
    🔽🔽🔽 Auth
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id__without_auth(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id',
                           kwargs={'cohort_id': 1})
        response = self.client.put(url, {})
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_put__without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id',
                           kwargs={'cohort_id': 1})
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(
            json, {
                'detail':
                "You (user: 1) don't have this capability: crud_cohort for academy 1",
                'status_code': 403
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 Put without cohort
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id__put__without_cohort(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id',
                           kwargs={'cohort_id': 99999})
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus=True)
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(json, {
            'status_code': 400,
            'detail': 'Specified cohort not be found'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        }])

    """
    🔽🔽🔽 Put not have ending_date and never_ends
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id__put__without_ending_date_or_never_ends(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id',
                           kwargs={'cohort_id': 1})
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'detail': 'cohort-without-ending-date-and-never-ends',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        }])

    """
    🔽🔽🔽 Put with ending_date and never_ends=True
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id__put__with_ending_date_and_never_ends_true(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id',
                           kwargs={'cohort_id': 1})
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')
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
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        }])

    """
    🔽🔽🔽 Put with date
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id__put(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id',
                           kwargs={'cohort_id': 1})
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')
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
            'private': False,
            'kickoff_date': self.datetime_to_iso(model['cohort'].kickoff_date),
            'ending_date': model['cohort'].ending_date,
            'current_day': model['cohort'].current_day,
            'stage': model['cohort'].stage,
            'language': model['cohort'].language,
            'syllabus': None,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.all_cohort_dict(),
            [{
                **self.model_to_dict(model, 'cohort'),
                'never_ends': True,
            }])

    """
    🔽🔽🔽 Put syllabus with id instead of {slug}.v{id}
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id__put__with_id__with_bad_syllabus_version_malformed(
            self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus=True)
        url = reverse_lazy('admissions:academy_cohort_id',
                           kwargs={'cohort_id': model['cohort'].id})
        data = {
            'syllabus': 1,
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'current_day': model['cohort'].current_day + 1,
            'language': 'es',
        }
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'detail': 'syllabus-field-marformed',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        }])

    """
    🔽🔽🔽 Put syllabus but it doesn't exists
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id__put__with_id__with_bad_syllabus_version(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus=True)
        url = reverse_lazy('admissions:academy_cohort_id',
                           kwargs={'cohort_id': model['cohort'].id})
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
            'detail': 'syllabus-doesnt-exist',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        }])

    """
    🔽🔽🔽 Put syllabus with bad slug {slug}.v{id}
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id__put__with_id__with_bad_syllabus_version__with_bad_slug(
            self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus=True)
        url = reverse_lazy('admissions:academy_cohort_id',
                           kwargs={'cohort_id': model['cohort'].id})
        data = {
            'syllabus': 'they-killed-kenny.v' + str(model['syllabus'].version),
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'current_day': model['cohort'].current_day + 1,
            'language': 'es',
        }
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'detail': 'syllabus-doesnt-exist',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        }])

    """
    🔽🔽🔽 Put syllabus with bad version {slug}.v{id}
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id__put__with_id__with_bad_syllabus_version__with_bad_version(
            self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus=True)
        url = reverse_lazy('admissions:academy_cohort_id',
                           kwargs={'cohort_id': model['cohort'].id})
        data = {
            'syllabus': model['certificate'].slug + '.v1',
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'current_day': model['cohort'].current_day + 1,
            'language': 'es',
        }
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'detail': 'syllabus-doesnt-exist',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        }])

    # """
    # 🔽🔽🔽 Put without certificate timeslots
    # """
    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # def test_cohort_id__put__with_id__without_certificate_timeslots(self):
    #     """Test /cohort/:id without auth"""
    #     self.headers(academy=1)
    #     cohort_kwargs = {'ending_date': timezone.now()}
    #     model = self.generate_models(authenticate=True, cohort=True, profile_academy=True,
    #         capability='crud_cohort', role='potato', syllabus=True, cohort_kwargs=cohort_kwargs)
    #     url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': model['cohort'].id})
    #     data = {
    #         'syllabus': model['certificate'].slug + '.v' + str(model['syllabus'].version),
    #         'slug': 'they-killed-kenny',
    #         'name': 'They killed kenny',
    #         'current_day': model['cohort'].current_day + 1,
    #         'language': 'es',
    #     }
    #     response = self.client.put(url, data)
    #     json = response.json()
    #     expected = {
    #         'detail': 'certificate-not-have-time-slots',
    #         'status_code': 400,
    #     }

    #     self.assertEqual(json, expected)
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    #     self.assertEqual(self.all_cohort_dict(), [{
    #         'academy_id': 1,
    #         'current_day': model['cohort'].current_day,
    #         'ending_date': model['cohort'].ending_date,
    #         'id': model['cohort'].id,
    #         'kickoff_date': model['cohort'].kickoff_date,
    #         'language': model['cohort'].language,
    #         'name': model['cohort'].name,
    #         'never_ends': False,
    #         'private': False,
    #         'slug': model['cohort'].slug,
    #         'stage': model['cohort'].stage,
    #         'syllabus_id': model['cohort'].syllabus.id,
    #         'timezone': None,
    #     }])
    """
    🔽🔽🔽 Put with some data
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id__put__with_id__with_data_in_body(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        cohort_kwargs = {'ending_date': timezone.now()}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus=True,
                                     cohort_kwargs=cohort_kwargs,
                                     certificate_time_slot=True)
        url = reverse_lazy('admissions:academy_cohort_id',
                           kwargs={'cohort_id': model['cohort'].id})
        data = {
            'syllabus':
            model['certificate'].slug + '.v' + str(model['syllabus'].version),
            'slug':
            'they-killed-kenny',
            'name':
            'They killed kenny',
            'current_day':
            model['cohort'].current_day + 1,
            'language':
            'es',
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
            'private':
            False,
            'kickoff_date':
            self.datetime_to_iso(model['cohort'].kickoff_date),
            'ending_date':
            self.datetime_to_iso(model['cohort'].ending_date),
            'current_day':
            data['current_day'],
            'stage':
            model['cohort'].stage,
            'language':
            data['language'],
            'syllabus':
            model['cohort'].syllabus.certificate.slug + '.v' +
            str(model['cohort'].syllabus.version),
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(),
                         [{
                             'academy_id': 1,
                             'current_day': data['current_day'],
                             'ending_date': model['cohort'].ending_date,
                             'id': model['cohort'].id,
                             'kickoff_date': model['cohort'].kickoff_date,
                             'language': data['language'],
                             'name': data['name'],
                             'never_ends': False,
                             'private': False,
                             'slug': data['slug'],
                             'stage': model['cohort'].stage,
                             'syllabus_id': model['cohort'].syllabus.id,
                             'timezone': None,
                         }])

    """
    🔽🔽🔽 Get data
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id__get__with_id(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_cohort',
                                     role='potato',
                                     syllabus=True)
        model_dict = self.remove_dinamics_fields(model['cohort'].__dict__)
        url = reverse_lazy('admissions:academy_cohort_id',
                           kwargs={'cohort_id': model['cohort'].id})
        response = self.client.get(url)
        json = response.json()
        expected = {
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
            'syllabus': {
                'certificate': {
                    'id':
                    model['cohort'].syllabus.certificate.id,
                    'slug':
                    model['cohort'].syllabus.certificate.slug,
                    'name':
                    model['cohort'].syllabus.certificate.name,
                    'duration_in_days':
                    model['cohort'].syllabus.certificate.duration_in_days,
                },
                'version': model['cohort'].syllabus.version,
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

    """
    🔽🔽🔽 Get with bad slug
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id__get__with_bad_slug(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        self.generate_models(authenticate=True,
                             cohort=True,
                             profile_academy=True,
                             capability='read_cohort',
                             role='potato',
                             syllabus=True)
        url = reverse_lazy('admissions:academy_cohort_id',
                           kwargs={'cohort_id': 'they-killed-kenny'})
        response = self.client.get(url)

        self.assertEqual(response.data, None)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    """
    🔽🔽🔽 Get with slug
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id__get__with_slug(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_cohort',
                                     role='potato',
                                     syllabus=True)
        model_dict = self.remove_dinamics_fields(model['cohort'].__dict__)
        url = reverse_lazy('admissions:academy_cohort_id',
                           kwargs={'cohort_id': model['cohort'].slug})
        response = self.client.get(url)
        json = response.json()
        expected = {
            'id': model['cohort'].id,
            'slug': model['cohort'].slug,
            'name': model['cohort'].name,
            'never_ends': model['cohort'].never_ends,
            'private': model['cohort'].private,
            'kickoff_date': self.datetime_to_iso(model['cohort'].kickoff_date),
            'ending_date': model['cohort'].ending_date,
            'language': model['cohort'].language,
            'stage': model['cohort'].stage,
            'current_day': model['cohort'].current_day,
            'syllabus': {
                'certificate': {
                    'id':
                    model['cohort'].syllabus.certificate.id,
                    'slug':
                    model['cohort'].syllabus.certificate.slug,
                    'name':
                    model['cohort'].syllabus.certificate.name,
                    'duration_in_days':
                    model['cohort'].syllabus.certificate.duration_in_days,
                },
                'version': model['cohort'].syllabus.version,
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

    """
    🔽🔽🔽 Delete with bad id
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id__delete__with_bad_id(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     capability='read_cohort',
                                     role='potato',
                                     syllabus=True,
                                     cohort_user=True)
        url = reverse_lazy('admissions:academy_cohort_id',
                           kwargs={'cohort_id': 0})
        self.assertEqual(self.count_cohort_user(), 1)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.count_cohort_stage(model['cohort'].id),
                         'INACTIVE')

    """
    🔽🔽🔽 Delete with id
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id__delete__with_id(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     syllabus=True)
        url = reverse_lazy('admissions:academy_cohort_id',
                           kwargs={'cohort_id': model['cohort'].id})
        self.assertEqual(self.count_cohort_stage(model['cohort'].id),
                         'INACTIVE')
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.count_cohort_user(), 0)
        self.assertEqual(self.count_cohort_stage(model['cohort'].id),
                         'DELETED')

    """
    🔽🔽🔽 Cache
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_cohort_id__with_data__testing_cache_and_remove_in_delete__1(
            self):
        """Test /cohort without auth"""
        cache_keys = [
            'Cohort__resource=None&academy_id=1&upcoming=None&academy='
            'None&location=None&like=None&limit=None&offset=None'
        ]

        self.assertEqual(self.cache.keys(), [])

        old_models = AcademyCohortTestSuite.test_academy_cohort__with_data(
            self)
        self.assertEqual(self.cache.keys(), cache_keys)

        self.headers(academy=1)

        base = old_models[0].copy()

        del base['profile_academy']
        del base['capability']
        del base['role']
        del base['user']

        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato2',
                                     models=base)

        url = reverse_lazy('admissions:academy_cohort_id',
                           kwargs={'cohort_id': 1})
        data = {}
        response = self.client.delete(url, data)

        if response.status_code != 204:
            print(response.json())

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.cache.keys(), [])
        self.assertEqual(
            self.all_cohort_dict(),
            [{
                **self.model_to_dict(model, 'cohort'),
                'stage': 'DELETED',
            }])

        old_models[0]['cohort'].stage = 'DELETED'

        base = [
            self.generate_models(authenticate=True, models=old_models[0]),
        ]

        AcademyCohortTestSuite.test_academy_cohort__with_data(self, base)
        self.assertEqual(self.cache.keys(), cache_keys)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_cohort_id__with_data__testing_cache_and_remove_in_delete__2(
            self):
        """Test /cohort without auth"""
        cache_keys = [
            'Cohort__resource=None&academy_id=1&upcoming=None&academy='
            'None&location=None&like=None&limit=None&offset=None'
        ]

        self.assertEqual(self.cache.keys(), [])

        old_models = AcademyCohortTestSuite.test_academy_cohort__with_data(
            self)
        self.assertEqual(self.cache.keys(), cache_keys)

        self.headers(academy=1)

        base = old_models[0].copy()

        del base['profile_academy']
        del base['capability']
        del base['role']
        del base['user']

        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato2',
                                     models=base)

        url = reverse_lazy('admissions:academy_cohort_id',
                           kwargs={'cohort_id': 1})
        response = self.client.delete(url)

        if response.status_code != 204:
            print(response.json())

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.cache.keys(), [])
        self.assertEqual(
            self.all_cohort_dict(),
            [{
                **self.model_to_dict(model, 'cohort'), 'stage': 'DELETED'
            }])

        old_models[0]['cohort'].stage = 'DELETED'

        base = [
            self.generate_models(authenticate=True, models=old_models[0]),
        ]

        AcademyCohortTestSuite.test_academy_cohort__with_data(self, base)
        self.assertEqual(self.cache.keys(), cache_keys)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_cohort_id__delete__cohort_with_students(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato',
                                     cohort_user=True)
        url = reverse_lazy('admissions:academy_cohort_id',
                           kwargs={'cohort_id': 1})
        response = self.client.delete(url)
        json = response.json()
        expected = {
            'detail': 'cohort-has-students',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.all_cohort_dict(), [{
            **self.model_to_dict(model, 'cohort')
        }])
