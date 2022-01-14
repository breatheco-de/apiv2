"""
Test /certificate
"""
from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import CertificateTestCase


class CertificateTestSuite(CertificateTestCase):
    """Test /certificate"""
    """
    🔽🔽🔽 Auth
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_cohort_user__without_auth(self):
        """Test /root without auth"""
        self.headers(academy=1)
        url = reverse_lazy('certificate:root')
        response = self.client.post(url, {})
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    """
    🔽🔽🔽 Post method
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_re_attemps_without_capability(self):
        """Test /root with auth"""
        """ No capability for the request"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True)

        url = reverse_lazy('certificate:root')
        data = [{
            'cohort_slug': model['cohort'].slug,
            'user_id': model['user'].id,
        }]
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: crud_certificate for academy 1",
            'status_code': 403
        }
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.all_user_specialty_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_re_attemps_without_cohort_user(self):
        """Test /root with auth"""
        """ No cohort_user for the request"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     role='STUDENT',
                                     capability='crud_certificate')

        url = reverse_lazy('certificate:root')
        data = [{
            'cohort_slug': model['cohort'].slug,
            'user_id': model['user'].id,
        }]
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'student-not-found-in-cohort', 'status_code': 404}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.all_user_specialty_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_re_attemps_without_user_specialty(self):
        """Test /root with auth"""
        """ No user_specialty for the request"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     role='STUDENT',
                                     capability='crud_certificate',
                                     cohort_user=True)

        url = reverse_lazy('certificate:root')
        data = [{
            'cohort_slug': model['cohort'].slug,
            'user_id': model['user'].id,
        }]
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'no-user-specialty', 'status_code': 404}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.all_user_specialty_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_re_attemps(self):
        """Test /root with auth"""
        """ Good Request """
        self.headers(academy=1)

        syllabus_kwargs = {'duration_in_days': 543665478761}
        cohort_kwargs = {
            'current_day': 543665478761,
            'stage': 'ENDED',
        }
        cohort_user_kwargs = {
            'finantial_status': 'UP_TO_DATE',
            'educational_status': 'GRADUATED',
        }
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     capability='crud_certificate',
                                     role='STUDENT',
                                     cohort_user=True,
                                     syllabus=True,
                                     syllabus_version=True,
                                     specialty=True,
                                     layout_design=True,
                                     user_specialty=True,
                                     specialty_mode=True,
                                     cohort_kwargs=cohort_kwargs,
                                     cohort_user_kwargs=cohort_user_kwargs,
                                     syllabus_kwargs=syllabus_kwargs)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        cohort_user_kwargs = {'role': 'TEACHER'}
        teacher_model = self.generate_models(user=True,
                                             cohort_user=True,
                                             cohort_user_kwargs=cohort_user_kwargs,
                                             models=base)

        url = reverse_lazy('certificate:root')
        data = [{
            'cohort_slug': model['cohort'].slug,
            'user_id': model['user'].id,
        }]
        response = self.client.post(url, data, format='json')
        json = response.json()

        self.assertDatetime(json[0]['updated_at'])
        del json[0]['updated_at']
        del json[0]['signed_by']

        expected = [{
            'academy': {
                'id': 1,
                'logo_url': model['academy'].logo_url,
                'name': model['academy'].name,
                'slug': model['academy'].slug,
                'website_url': None
            },
            'cohort': {
                'id': 1,
                'kickoff_date': self.datetime_to_iso(model.cohort.kickoff_date),
                'ending_date': None,
                'name': model['cohort'].name,
                'slug': model['cohort'].slug,
                'specialty_mode': {
                    'id': model['specialty_mode'].id,
                    'name': model['specialty_mode'].name,
                    'syllabus': model['specialty_mode'].syllabus.id,
                },
                'syllabus_version': {
                    'version': model['syllabus_version'].version,
                    'name': model['syllabus_version'].syllabus.name,
                    'slug': model['syllabus_version'].syllabus.slug,
                    'syllabus': model['syllabus_version'].syllabus.id,
                    'duration_in_days': model['syllabus_version'].syllabus.duration_in_days,
                    'duration_in_hours': model['syllabus_version'].syllabus.duration_in_hours,
                    'week_hours': model['syllabus_version'].syllabus.week_hours,
                },
            },
            'created_at': self.datetime_to_iso(model['user_specialty'].created_at),
            'expires_at': model['user_specialty'].expires_at,
            'id': 1,
            'layout': {
                'name': model['layout_design'].name,
                'slug': model['layout_design'].slug,
                'background_url': model['layout_design'].background_url
            },
            'preview_url': model['user_specialty'].preview_url,
            'signed_by_role': 'Director',
            'specialty': {
                'created_at': self.datetime_to_iso(model['specialty'].created_at),
                'description': model.specialty.description,
                'id': 1,
                'logo_url': None,
                'name': model['specialty'].name,
                'slug': model['specialty'].slug,
                'updated_at': self.datetime_to_iso(model['specialty'].updated_at),
            },
            'status': 'PENDING',
            'status_text': None,
            'user': {
                'first_name': model['user'].first_name,
                'id': 1,
                'last_name': model['user'].last_name
            }
        }]
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.all_user_specialty_dict(),
            [{
                'academy_id': 1,
                'cohort_id': 1,
                'expires_at': None,
                'id': 1,
                'layout_id': 1,
                'preview_url': model['user_specialty'].preview_url,
                'signed_by': teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name,
                'signed_by_role': 'Director',
                'specialty_id': 1,
                'status': 'PERSISTED',
                'status_text': 'Certificate successfully queued for PDF generation',
                'user_id': 1,
                'token': '9e76a2ab3bd55454c384e0a5cdb5298d17285949'
            }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_re_attemps_two_certificates(self):
        """Test /root with auth"""
        """ Good Request """
        self.headers(academy=1)

        syllabus_kwargs = {'duration_in_days': 543665478761}
        cohort_kwargs = {
            'current_day': 543665478761,
            'stage': 'ENDED',
        }
        cohort_user_kwargs = {
            'finantial_status': 'UP_TO_DATE',
            'educational_status': 'GRADUATED',
        }
        base = self.generate_models(authenticate=True,
                                    cohort=True,
                                    capability='crud_certificate',
                                    role='STUDENT',
                                    profile_academy=True,
                                    syllabus=True,
                                    syllabus_version=True,
                                    specialty=True,
                                    specialty_mode=True,
                                    layout_design=True,
                                    syllabus_kwargs=syllabus_kwargs,
                                    cohort_kwargs=cohort_kwargs)

        del base['user']

        user_specialty_1_kwargs = {'token': 'qwerrty'}
        user_specialty_2_kwargs = {'token': 'huhuhuhuhu'}

        models = [
            self.generate_models(user=True,
                                 cohort_user=True,
                                 user_specialty=True,
                                 user_specialty_kwargs=user_specialty_2_kwargs,
                                 cohort_user_kwargs=cohort_user_kwargs,
                                 models=base),
            self.generate_models(user=True,
                                 cohort_user=True,
                                 user_specialty=True,
                                 user_specialty_kwargs=user_specialty_1_kwargs,
                                 cohort_user_kwargs=cohort_user_kwargs,
                                 models=base),
        ]

        cohort_user_kwargs = {'role': 'TEACHER'}
        teacher_model = self.generate_models(user=True,
                                             cohort_user=True,
                                             cohort_user_kwargs=cohort_user_kwargs,
                                             models=base)

        url = reverse_lazy('certificate:root')
        data = [
            {
                'cohort_slug': models[0].cohort.slug,
                'user_id': models[0].user.id,
            },
            {
                'cohort_slug': models[1].cohort.slug,
                'user_id': models[1].user.id,
            },
        ]
        response = self.client.post(url, data, format='json')
        json = response.json()

        self.assertDatetime(json[0]['updated_at'])
        del json[0]['updated_at']
        del json[0]['signed_by']

        self.assertDatetime(json[1]['updated_at'])
        del json[1]['updated_at']
        del json[1]['signed_by']

        expected = [{
            'academy': {
                'id': 1,
                'logo_url': models[0].academy.logo_url,
                'name': models[0].academy.name,
                'slug': models[0].academy.slug,
                'website_url': None
            },
            'cohort': {
                'id': 1,
                'kickoff_date': self.datetime_to_iso(models[1].cohort.kickoff_date),
                'ending_date': None,
                'name': models[0].cohort.name,
                'slug': models[0].cohort.slug,
                'specialty_mode': {
                    'id': models[0]['specialty_mode'].id,
                    'name': models[0]['specialty_mode'].name,
                    'syllabus': models[0]['specialty_mode'].syllabus.id,
                },
                'syllabus_version': {
                    'version': models[0]['syllabus_version'].version,
                    'name': models[0]['syllabus_version'].syllabus.name,
                    'slug': models[0]['syllabus_version'].syllabus.slug,
                    'syllabus': models[0]['syllabus_version'].syllabus.id,
                    'duration_in_days': models[0]['syllabus_version'].syllabus.duration_in_days,
                    'duration_in_hours': models[0]['syllabus_version'].syllabus.duration_in_hours,
                    'week_hours': models[0]['syllabus_version'].syllabus.week_hours,
                },
            },
            'created_at': self.datetime_to_iso(models[0].user_specialty.created_at),
            'expires_at': models[0].user_specialty.expires_at,
            'id': 1,
            'layout': {
                'name': models[0].layout_design.name,
                'background_url': models[0].layout_design.background_url,
                'slug': models[0].layout_design.slug,
            },
            'preview_url': models[0].user_specialty.preview_url,
            'signed_by_role': 'Director',
            'specialty': {
                'created_at': self.datetime_to_iso(models[0].specialty.created_at),
                'description': models[0].specialty.description,
                'id': 1,
                'logo_url': None,
                'name': models[0].specialty.name,
                'slug': models[0].specialty.slug,
                'updated_at': self.datetime_to_iso(models[0].specialty.updated_at),
            },
            'status': 'PENDING',
            'status_text': None,
            'user': {
                'first_name': models[0].user.first_name,
                'id': 2,
                'last_name': models[0].user.last_name
            }
        }, {
            'academy': {
                'id': 1,
                'logo_url': models[1].academy.logo_url,
                'name': models[1].academy.name,
                'slug': models[1].academy.slug,
                'website_url': None
            },
            'cohort': {
                'id': 1,
                'kickoff_date': self.datetime_to_iso(models[1].cohort.kickoff_date),
                'ending_date': None,
                'name': models[1].cohort.name,
                'slug': models[1].cohort.slug,
                'specialty_mode': {
                    'id': models[0]['specialty_mode'].id,
                    'name': models[0]['specialty_mode'].name,
                    'syllabus': models[0]['specialty_mode'].syllabus.id,
                },
                'syllabus_version': {
                    'version': models[0]['syllabus_version'].version,
                    'name': models[0]['syllabus_version'].syllabus.name,
                    'slug': models[0]['syllabus_version'].syllabus.slug,
                    'syllabus': models[0]['syllabus_version'].syllabus.id,
                    'duration_in_days': models[0]['syllabus_version'].syllabus.duration_in_days,
                    'duration_in_hours': models[0]['syllabus_version'].syllabus.duration_in_hours,
                    'week_hours': models[0]['syllabus_version'].syllabus.week_hours,
                },
            },
            'created_at': self.datetime_to_iso(models[1].user_specialty.created_at),
            'expires_at': models[1].user_specialty.expires_at,
            'id': 2,
            'layout': {
                'name': models[1].layout_design.name,
                'slug': models[1].layout_design.slug,
                'background_url': models[1].layout_design.background_url
            },
            'preview_url': models[1].user_specialty.preview_url,
            'signed_by_role': 'Director',
            'specialty': {
                'created_at': self.datetime_to_iso(models[1].specialty.created_at),
                'description': models[1].specialty.description,
                'id': 1,
                'logo_url': None,
                'name': models[1].specialty.name,
                'slug': models[1].specialty.slug,
                'updated_at': self.datetime_to_iso(models[1].specialty.updated_at),
            },
            'status': 'PENDING',
            'status_text': None,
            'user': {
                'first_name': models[1].user.first_name,
                'id': 3,
                'last_name': models[1].user.last_name
            }
        }]
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_user_specialty_dict(), [
            {
                'academy_id': 1,
                'cohort_id': 1,
                'expires_at': None,
                'id': 1,
                'layout_id': 1,
                'preview_url': models[0].user_specialty.preview_url,
                'signed_by': teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name,
                'signed_by_role': 'Director',
                'specialty_id': 1,
                'status': 'PERSISTED',
                'status_text': 'Certificate successfully queued for PDF generation',
                'user_id': 2,
                'token': 'huhuhuhuhu'
            },
            {
                'academy_id': 1,
                'cohort_id': 1,
                'expires_at': None,
                'id': 2,
                'layout_id': 1,
                'preview_url': models[1].user_specialty.preview_url,
                'signed_by': teacher_model['user'].first_name + ' ' + teacher_model['user'].last_name,
                'signed_by_role': 'Director',
                'specialty_id': 1,
                'status': 'PERSISTED',
                'status_text': 'Certificate successfully queued for PDF generation',
                'user_id': 3,
                'token': 'qwerrty'
            },
        ])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate__with_full_name_in_querystring(self):
        """Test /root """
        self.headers(academy=1)

        specialty_mode_kwargs = {'duration_in_days': 543665478761}
        cohort_kwargs = {
            'current_day': 543665478761,
            'stage': 'ENDED',
        }
        base = self.generate_models(authenticate=True,
                                    cohort=True,
                                    capability='read_certificate',
                                    role='potato',
                                    academy=True,
                                    profile_academy=True,
                                    specialty=True,
                                    specialty_mode=True,
                                    specialty_mode_kwargs=specialty_mode_kwargs,
                                    syllabus=True,
                                    cohort_kwargs=cohort_kwargs)

        del base['user']

        user_kwargs = {
            'email': 'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
        }
        user_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Michael',
            'last_name': 'Jordan',
        }
        user_specialty_kwargs_1 = {'token': '123dfefef1123rerf346g'}
        user_specialty_kwargs_2 = {'token': 'jojfsdknjbs1123rerf346g'}
        models = [
            self.generate_models(user=True,
                                 user_specialty=True,
                                 cohort_user=True,
                                 user_kwargs=user_kwargs,
                                 user_specialty_kwargs=user_specialty_kwargs_1,
                                 models=base),
            self.generate_models(user=True,
                                 user_specialty=True,
                                 cohort_user=True,
                                 user_kwargs=user_kwargs_2,
                                 user_specialty_kwargs=user_specialty_kwargs_2,
                                 models=base)
        ]

        base_url = reverse_lazy('certificate:root')
        url = f'{base_url}?like=Rene Descartes'

        response = self.client.get(url)
        json = response.json()

        expected = [{
            'academy': {
                'id': 1,
                'logo_url': models[0].academy.logo_url,
                'name': models[0].academy.name,
                'slug': models[0].academy.slug,
                'website_url': None
            },
            'cohort': {
                'id': 1,
                'kickoff_date': self.datetime_to_iso(models[0].cohort.kickoff_date),
                'ending_date': None,
                'name': models[0].cohort.name,
                'slug': models[0].cohort.slug,
                'specialty_mode': {
                    'id': models[0]['specialty_mode'].id,
                    'name': models[0]['specialty_mode'].name,
                    'syllabus': models[0]['specialty_mode'].syllabus.id,
                },
                'syllabus_version': None,
            },
            'created_at': self.datetime_to_iso(models[0].user_specialty.created_at),
            'expires_at': models[0].user_specialty.expires_at,
            'id': 1,
            'layout': None,
            'preview_url': models[0].user_specialty.preview_url,
            'signed_by': models[0].user_specialty.signed_by,
            'signed_by_role': 'Director',
            'specialty': {
                'created_at': self.datetime_to_iso(models[0].specialty.created_at),
                'description': models[0].specialty.description,
                'id': 1,
                'logo_url': None,
                'name': models[0].specialty.name,
                'slug': models[0].specialty.slug,
                'updated_at': self.datetime_to_iso(models[0].specialty.updated_at),
            },
            'status': 'PENDING',
            'status_text': None,
            'updated_at': self.datetime_to_iso(models[0].user_specialty.updated_at),
            'user': {
                'first_name': models[0].user.first_name,
                'id': 2,
                'last_name': models[0].user.last_name
            }
        }]
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 With full like querystring
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate__with_first_name_in_querystring(self):
        """Test /root """
        self.headers(academy=1)
        specialty_mode_kwargs = {'duration_in_days': 543665478761}
        cohort_kwargs = {
            'current_day': 543665478761,
            'stage': 'ENDED',
        }
        base = self.generate_models(authenticate=True,
                                    cohort=True,
                                    capability='read_certificate',
                                    role='potato',
                                    academy=True,
                                    profile_academy=True,
                                    specialty=True,
                                    specialty_mode=True,
                                    specialty_mode_kwargs=specialty_mode_kwargs,
                                    syllabus=True,
                                    cohort_kwargs=cohort_kwargs)

        del base['user']

        user_kwargs = {
            'email': 'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
        }
        user_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Michael',
            'last_name': 'Jordan',
        }
        user_specialty_kwargs_1 = {'token': '123dfefef1123rerf346g'}
        user_specialty_kwargs_2 = {'token': 'jojfsdknjbs1123rerf346g'}
        models = [
            self.generate_models(user=True,
                                 user_specialty=True,
                                 cohort_user=True,
                                 user_kwargs=user_kwargs,
                                 user_specialty_kwargs=user_specialty_kwargs_1,
                                 models=base),
            self.generate_models(user=True,
                                 user_specialty=True,
                                 cohort_user=True,
                                 user_kwargs=user_kwargs_2,
                                 user_specialty_kwargs=user_specialty_kwargs_2,
                                 models=base)
        ]

        base_url = reverse_lazy('certificate:root')
        url = f'{base_url}?like=Rene'

        response = self.client.get(url)
        json = response.json()

        expected = [{
            'academy': {
                'id': 1,
                'logo_url': models[0].academy.logo_url,
                'name': models[0].academy.name,
                'slug': models[0].academy.slug,
                'website_url': None
            },
            'cohort': {
                'id': 1,
                'kickoff_date': self.datetime_to_iso(models[0].cohort.kickoff_date),
                'ending_date': None,
                'name': models[0].cohort.name,
                'slug': models[0].cohort.slug,
                'specialty_mode': {
                    'id': models[0]['specialty_mode'].id,
                    'name': models[0]['specialty_mode'].name,
                    'syllabus': models[0]['specialty_mode'].syllabus.id,
                },
                'syllabus_version': None,
            },
            'created_at': self.datetime_to_iso(models[0].user_specialty.created_at),
            'expires_at': models[0].user_specialty.expires_at,
            'id': 1,
            'layout': None,
            'preview_url': models[0].user_specialty.preview_url,
            'signed_by': models[0].user_specialty.signed_by,
            'signed_by_role': 'Director',
            'specialty': {
                'created_at': self.datetime_to_iso(models[0].specialty.created_at),
                'description': models[0].specialty.description,
                'id': 1,
                'logo_url': None,
                'name': models[0].specialty.name,
                'slug': models[0].specialty.slug,
                'updated_at': self.datetime_to_iso(models[0].specialty.updated_at),
            },
            'status': 'PENDING',
            'status_text': None,
            'updated_at': self.datetime_to_iso(models[0].user_specialty.updated_at),
            'user': {
                'first_name': models[0].user.first_name,
                'id': 2,
                'last_name': models[0].user.last_name
            }
        }]
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate__with_last_name_in_querystring(self):
        """Test /root """
        self.headers(academy=1)
        specialty_mode_kwargs = {'duration_in_days': 543665478761}
        cohort_kwargs = {
            'current_day': 543665478761,
            'stage': 'ENDED',
        }
        base = self.generate_models(authenticate=True,
                                    cohort=True,
                                    capability='read_certificate',
                                    role='potato',
                                    academy=True,
                                    profile_academy=True,
                                    specialty=True,
                                    specialty_mode=True,
                                    specialty_mode_kwargs=specialty_mode_kwargs,
                                    syllabus=True,
                                    cohort_kwargs=cohort_kwargs)

        del base['user']

        user_kwargs = {
            'email': 'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
        }
        user_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Michael',
            'last_name': 'Jordan',
        }
        user_specialty_kwargs_1 = {'token': '123dfefef1123rerf346g'}
        user_specialty_kwargs_2 = {'token': 'jojfsdknjbs1123rerf346g'}
        models = [
            self.generate_models(user=True,
                                 user_specialty=True,
                                 cohort_user=True,
                                 user_kwargs=user_kwargs,
                                 user_specialty_kwargs=user_specialty_kwargs_1,
                                 models=base),
            self.generate_models(user=True,
                                 user_specialty=True,
                                 cohort_user=True,
                                 user_kwargs=user_kwargs_2,
                                 user_specialty_kwargs=user_specialty_kwargs_2,
                                 models=base)
        ]

        base_url = reverse_lazy('certificate:root')
        url = f'{base_url}?like=Descartes'

        response = self.client.get(url)
        json = response.json()

        expected = [{
            'academy': {
                'id': 1,
                'logo_url': models[0].academy.logo_url,
                'name': models[0].academy.name,
                'slug': models[0].academy.slug,
                'website_url': None
            },
            'cohort': {
                'id': 1,
                'kickoff_date': self.datetime_to_iso(models[0].cohort.kickoff_date),
                'ending_date': None,
                'name': models[0].cohort.name,
                'slug': models[0].cohort.slug,
                'specialty_mode': {
                    'id': models[0]['specialty_mode'].id,
                    'name': models[0]['specialty_mode'].name,
                    'syllabus': models[0]['specialty_mode'].syllabus.id,
                },
                'syllabus_version': None,
            },
            'created_at': self.datetime_to_iso(models[0].user_specialty.created_at),
            'expires_at': models[0].user_specialty.expires_at,
            'id': 1,
            'layout': None,
            'preview_url': models[0].user_specialty.preview_url,
            'signed_by': models[0].user_specialty.signed_by,
            'signed_by_role': 'Director',
            'specialty': {
                'created_at': self.datetime_to_iso(models[0].specialty.created_at),
                'description': models[0].specialty.description,
                'id': 1,
                'logo_url': None,
                'name': models[0].specialty.name,
                'slug': models[0].specialty.slug,
                'updated_at': self.datetime_to_iso(models[0].specialty.updated_at),
            },
            'status': 'PENDING',
            'status_text': None,
            'updated_at': self.datetime_to_iso(models[0].user_specialty.updated_at),
            'user': {
                'first_name': models[0].user.first_name,
                'id': 2,
                'last_name': models[0].user.last_name
            }
        }]
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate__with_email_in_querystring(self):
        """Test /root """
        self.headers(academy=1)
        specialty_mode_kwargs = {'duration_in_days': 543665478761}
        cohort_kwargs = {
            'current_day': 543665478761,
            'stage': 'ENDED',
        }
        base = self.generate_models(authenticate=True,
                                    cohort=True,
                                    cohort_finished=True,
                                    capability='read_certificate',
                                    role='potato',
                                    academy=True,
                                    profile_academy=True,
                                    specialty=True,
                                    specialty_mode=True,
                                    specialty_mode_kwargs=specialty_mode_kwargs,
                                    syllabus=True,
                                    cohort_kwargs=cohort_kwargs)

        del base['user']

        user_kwargs = {
            'email': 'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
        }
        user_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Michael',
            'last_name': 'Jordan',
        }
        user_specialty_kwargs_1 = {'token': '123dfefef1123rerf346g'}
        user_specialty_kwargs_2 = {'token': 'jojfsdknjbs1123rerf346g'}
        models = [
            self.generate_models(user=True,
                                 user_specialty=True,
                                 cohort_user=True,
                                 user_kwargs=user_kwargs,
                                 user_specialty_kwargs=user_specialty_kwargs_1,
                                 models=base),
            self.generate_models(user=True,
                                 user_specialty=True,
                                 cohort_user=True,
                                 user_kwargs=user_kwargs_2,
                                 user_specialty_kwargs=user_specialty_kwargs_2,
                                 models=base)
        ]

        base_url = reverse_lazy('certificate:root')
        url = f'{base_url}?like=b@b.com'

        response = self.client.get(url)
        json = response.json()

        expected = [{
            'academy': {
                'id': 1,
                'logo_url': models[0].academy.logo_url,
                'name': models[0].academy.name,
                'slug': models[0].academy.slug,
                'website_url': None
            },
            'cohort': {
                'id': 1,
                'kickoff_date': self.datetime_to_iso(models[0].cohort.kickoff_date),
                'ending_date': None,
                'name': models[0].cohort.name,
                'slug': models[0].cohort.slug,
                'specialty_mode': {
                    'id': models[0]['specialty_mode'].id,
                    'name': models[0]['specialty_mode'].name,
                    'syllabus': models[0]['specialty_mode'].syllabus.id,
                },
                'syllabus_version': None,
            },
            'created_at': self.datetime_to_iso(models[0].user_specialty.created_at),
            'expires_at': models[0].user_specialty.expires_at,
            'id': 1,
            'layout': None,
            'preview_url': models[0].user_specialty.preview_url,
            'signed_by': models[0].user_specialty.signed_by,
            'signed_by_role': 'Director',
            'specialty': {
                'created_at': self.datetime_to_iso(models[0].specialty.created_at),
                'description': models[0].specialty.description,
                'id': 1,
                'logo_url': None,
                'name': models[0].specialty.name,
                'slug': models[0].specialty.slug,
                'updated_at': self.datetime_to_iso(models[0].specialty.updated_at),
            },
            'status': 'PENDING',
            'status_text': None,
            'updated_at': self.datetime_to_iso(models[0].user_specialty.updated_at),
            'user': {
                'first_name': models[0].user.first_name,
                'id': 2,
                'last_name': models[0].user.last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 Delete
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_delete_certificate_in_bulk_with_two_ids(self):
        """Test / with two certificates"""
        self.headers(academy=1)

        base = self.generate_models(authenticate=True,
                                    cohort=True,
                                    user=True,
                                    profile_academy=True,
                                    syllabus=True,
                                    capability='crud_certificate',
                                    cohort_user=True,
                                    specialty=True,
                                    role='potato')
        del base['user']

        model1 = self.generate_models(user=True,
                                      profile_academy=True,
                                      user_specialty=True,
                                      user_specialty_kwargs={'token': 'hitman3000'},
                                      models=base)

        model2 = self.generate_models(user=True,
                                      profile_academy=True,
                                      user_specialty=True,
                                      user_specialty_kwargs={'token': 'batman2000'},
                                      models=base)

        url = reverse_lazy('certificate:root') + '?id=1,2'
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_user_invite_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_delete_certificate_in_bulk_not_found(self):
        """Test / with two certificates"""
        self.headers(academy=1)

        base = self.generate_models(authenticate=True,
                                    cohort=True,
                                    user=True,
                                    profile_academy=True,
                                    syllabus=True,
                                    capability='crud_certificate',
                                    cohort_user=True,
                                    specialty=True,
                                    role='potato')
        del base['user']

        model1 = self.generate_models(user=True,
                                      user_specialty=True,
                                      user_specialty_kwargs={'token': 'hitman3000'},
                                      models=base)

        model2 = self.generate_models(user=True,
                                      user_specialty=True,
                                      user_specialty_kwargs={'token': 'batman2000'},
                                      models=base)

        url = reverse_lazy('certificate:root') + '?id=3,4'
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {'detail': 'specialties_not_found', 'status_code': 404})
        self.assertEqual(self.all_user_invite_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_delete_certificate_in_bulk_without_passing_ids(self):
        """Test / with two certificates"""
        self.headers(academy=1)

        base = self.generate_models(authenticate=True,
                                    cohort=True,
                                    user=True,
                                    profile_academy=True,
                                    syllabus=True,
                                    capability='crud_certificate',
                                    cohort_user=True,
                                    specialty=True,
                                    role='potato')
        del base['user']

        model1 = self.generate_models(user=True,
                                      user_specialty=True,
                                      user_specialty_kwargs={'token': 'hitman3000'},
                                      models=base)

        model2 = self.generate_models(user=True,
                                      user_specialty=True,
                                      user_specialty_kwargs={'token': 'batman2000'},
                                      models=base)

        url = reverse_lazy('certificate:root')
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {'detail': 'missing_ids', 'status_code': 404})
        self.assertEqual(self.all_user_invite_dict(), [])
