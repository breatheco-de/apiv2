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
from ..mixins.new_certificate_test_case import CertificateTestCase


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
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True)

        url = reverse_lazy('certificate:root')
        data = [{
            'cohort_slug': model['cohort'].slug,
            'user_id': model['user'].id,
        }]
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'detail':
            "You (user: 1) don't have this capability: crud_certificate for academy 1",
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
                                     role="STUDENT",
                                     capability='crud_certificate')

        url = reverse_lazy('certificate:root')
        data = [{
            'cohort_slug': model['cohort'].slug,
            'user_id': model['user'].id,
        }]
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'detail': 'student-not-found-in-cohort',
            'status_code': 404
        }
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
                                     role="STUDENT",
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

        model = self.generate_models(
            authenticate=True,
            cohort=True,
            user=True,
            profile_academy=True,
            capability='crud_certificate',
            role='STUDENT',
            cohort_user=True,
            syllabus=True,
            specialty=True,
            layout_design=True,
            cohort_stage="ENDED",
            cohort_user_finantial_status='UP_TO_DATE',
            cohort_user_educational_status='GRADUATED',
            user_specialty=True,
            cohort_finished=True)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        teacher_model = self.generate_models(user=True,
                                             cohort_user=True,
                                             cohort_user_role='TEACHER',
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
                'name': model['cohort'].name,
                'slug': model['cohort'].slug,
                'syllabus': {
                    'certificate': {
                        'duration_in_hours':
                        model['certificate'].duration_in_hours
                    }
                }
            },
            'created_at':
            self.datetime_to_iso(model['user_specialty'].created_at),
            'expires_at':
            model['user_specialty'].expires_at,
            'id':
            1,
            'layout': {
                'name': model['layout_design'].name,
                'slug': model['layout_design'].slug
            },
            'preview_url':
            model['user_specialty'].preview_url,
            'signed_by_role':
            'Director',
            'specialty': {
                'created_at':
                self.datetime_to_iso(model['specialty'].created_at),
                'id': 1,
                'logo_url': None,
                'name': model['specialty'].name,
                'slug': model['specialty'].slug,
                'updated_at':
                self.datetime_to_iso(model['specialty'].updated_at),
            },
            'status':
            'PENDING',
            'status_text':
            None,
            'user': {
                'first_name': model['user'].first_name,
                'id': 1,
                'last_name': model['user'].last_name
            }
        }]
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_user_specialty_dict(), [{
            'academy_id':
            1,
            'cohort_id':
            1,
            'expires_at':
            None,
            'id':
            1,
            'layout_id':
            1,
            'preview_url':
            model['user_specialty'].preview_url,
            'signed_by':
            teacher_model['user'].first_name + " " +
            teacher_model['user'].last_name,
            'signed_by_role':
            'Director',
            'specialty_id':
            1,
            'status':
            'PERSISTED',
            'status_text':
            'Certificate successfully queued for PDF generation',
            'user_id':
            1,
            'token':
            "9e76a2ab3bd55454c384e0a5cdb5298d17285949"
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_re_attemps_two_certificates(self):
        """Test /root with auth"""
        """ Good Request """
        self.headers(academy=1)

        base = self.generate_models(authenticate=True,
                                    cohort=True,
                                    cohort_finished=True,
                                    capability='crud_certificate',
                                    role='STUDENT',
                                    profile_academy=True,
                                    syllabus=True,
                                    specialty=True,
                                    layout_design=True,
                                    cohort_stage="ENDED")

        del base['user']

        user_specialty_1_kwargs = {"token": "qwerrty"}
        user_specialty_2_kwargs = {"token": "huhuhuhuhu"}

        models = [
            self.generate_models(user=True,
                                 cohort_user=True,
                                 cohort_user_educational_status='GRADUATED',
                                 cohort_user_finantial_status='UP_TO_DATE',
                                 user_specialty=True,
                                 user_specialty_kwargs=user_specialty_2_kwargs,
                                 models=base),
            self.generate_models(user=True,
                                 cohort_user=True,
                                 cohort_user_educational_status='GRADUATED',
                                 cohort_user_finantial_status='UP_TO_DATE',
                                 user_specialty=True,
                                 user_specialty_kwargs=user_specialty_1_kwargs,
                                 models=base),
        ]

        teacher_model = self.generate_models(user=True,
                                             cohort_user=True,
                                             cohort_user_role='TEACHER',
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
                'name': models[0].cohort.name,
                'slug': models[0].cohort.slug,
                'syllabus': {
                    'certificate': {
                        'duration_in_hours':
                        models[0].certificate.duration_in_hours
                    }
                }
            },
            'created_at':
            self.datetime_to_iso(models[0].user_specialty.created_at),
            'expires_at':
            models[0].user_specialty.expires_at,
            'id':
            1,
            'layout': {
                'name': models[0].layout_design.name,
                'slug': models[0].layout_design.slug
            },
            'preview_url':
            models[0].user_specialty.preview_url,
            'signed_by_role':
            'Director',
            'specialty': {
                'created_at':
                self.datetime_to_iso(models[0].specialty.created_at),
                'id': 1,
                'logo_url': None,
                'name': models[0].specialty.name,
                'slug': models[0].specialty.slug,
                'updated_at':
                self.datetime_to_iso(models[0].specialty.updated_at),
            },
            'status':
            'PENDING',
            'status_text':
            None,
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
                'name': models[1].cohort.name,
                'slug': models[1].cohort.slug,
                'syllabus': {
                    'certificate': {
                        'duration_in_hours':
                        models[1].certificate.duration_in_hours
                    }
                }
            },
            'created_at':
            self.datetime_to_iso(models[1].user_specialty.created_at),
            'expires_at':
            models[1].user_specialty.expires_at,
            'id':
            2,
            'layout': {
                'name': models[1].layout_design.name,
                'slug': models[1].layout_design.slug
            },
            'preview_url':
            models[1].user_specialty.preview_url,
            'signed_by_role':
            'Director',
            'specialty': {
                'created_at':
                self.datetime_to_iso(models[1].specialty.created_at),
                'id': 1,
                'logo_url': None,
                'name': models[1].specialty.name,
                'slug': models[1].specialty.slug,
                'updated_at':
                self.datetime_to_iso(models[1].specialty.updated_at),
            },
            'status':
            'PENDING',
            'status_text':
            None,
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
                'academy_id':
                1,
                'cohort_id':
                1,
                'expires_at':
                None,
                'id':
                1,
                'layout_id':
                1,
                'preview_url':
                models[0].user_specialty.preview_url,
                'signed_by':
                teacher_model['user'].first_name + " " +
                teacher_model['user'].last_name,
                'signed_by_role':
                'Director',
                'specialty_id':
                1,
                'status':
                'PERSISTED',
                'status_text':
                'Certificate successfully queued for PDF generation',
                'user_id':
                2,
                'token':
                "huhuhuhuhu"
            },
            {
                'academy_id':
                1,
                'cohort_id':
                1,
                'expires_at':
                None,
                'id':
                2,
                'layout_id':
                1,
                'preview_url':
                models[1].user_specialty.preview_url,
                'signed_by':
                teacher_model['user'].first_name + " " +
                teacher_model['user'].last_name,
                'signed_by_role':
                'Director',
                'specialty_id':
                1,
                'status':
                'PERSISTED',
                'status_text':
                'Certificate successfully queued for PDF generation',
                'user_id':
                3,
                'token':
                "qwerrty"
            },
        ])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate__with_full_name_in_querystring(self):
        """Test /root """
        self.headers(academy=1)

        base = self.generate_models(authenticate=True,
                                    cohort=True,
                                    cohort_finished=True,
                                    capability='read_certificate',
                                    role='potato',
                                    academy=True,
                                    profile_academy=True,
                                    specialty=True)

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
        user_specialty_kwargs_1 = {"token": "123dfefef1123rerf346g"}
        user_specialty_kwargs_2 = {"token": "jojfsdknjbs1123rerf346g"}
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
                'name': models[0].cohort.name,
                'slug': models[0].cohort.slug,
                'syllabus': {}
            },
            'created_at':
            self.datetime_to_iso(models[0].user_specialty.created_at),
            'expires_at':
            models[0].user_specialty.expires_at,
            'id':
            1,
            'layout':
            None,
            'preview_url':
            models[0].user_specialty.preview_url,
            'signed_by':
            models[0].user_specialty.signed_by,
            'signed_by_role':
            'Director',
            'specialty': {
                'created_at':
                self.datetime_to_iso(models[0].specialty.created_at),
                'id': 1,
                'logo_url': None,
                'name': models[0].specialty.name,
                'slug': models[0].specialty.slug,
                'updated_at':
                self.datetime_to_iso(models[0].specialty.updated_at),
            },
            'status':
            'PENDING',
            'status_text':
            None,
            'updated_at':
            self.datetime_to_iso(models[0].user_specialty.updated_at),
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
        base = self.generate_models(authenticate=True,
                                    cohort=True,
                                    cohort_finished=True,
                                    capability='read_certificate',
                                    role='potato',
                                    academy=True,
                                    profile_academy=True,
                                    specialty=True)

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
        user_specialty_kwargs_1 = {"token": "123dfefef1123rerf346g"}
        user_specialty_kwargs_2 = {"token": "jojfsdknjbs1123rerf346g"}
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
                'name': models[0].cohort.name,
                'slug': models[0].cohort.slug,
                'syllabus': {}
            },
            'created_at':
            self.datetime_to_iso(models[0].user_specialty.created_at),
            'expires_at':
            models[0].user_specialty.expires_at,
            'id':
            1,
            'layout':
            None,
            'preview_url':
            models[0].user_specialty.preview_url,
            'signed_by':
            models[0].user_specialty.signed_by,
            'signed_by_role':
            'Director',
            'specialty': {
                'created_at':
                self.datetime_to_iso(models[0].specialty.created_at),
                'id': 1,
                'logo_url': None,
                'name': models[0].specialty.name,
                'slug': models[0].specialty.slug,
                'updated_at':
                self.datetime_to_iso(models[0].specialty.updated_at),
            },
            'status':
            'PENDING',
            'status_text':
            None,
            'updated_at':
            self.datetime_to_iso(models[0].user_specialty.updated_at),
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
        base = self.generate_models(authenticate=True,
                                    cohort=True,
                                    cohort_finished=True,
                                    capability='read_certificate',
                                    role='potato',
                                    academy=True,
                                    profile_academy=True,
                                    specialty=True)

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
        user_specialty_kwargs_1 = {"token": "123dfefef1123rerf346g"}
        user_specialty_kwargs_2 = {"token": "jojfsdknjbs1123rerf346g"}
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
                'name': models[0].cohort.name,
                'slug': models[0].cohort.slug,
                'syllabus': {}
            },
            'created_at':
            self.datetime_to_iso(models[0].user_specialty.created_at),
            'expires_at':
            models[0].user_specialty.expires_at,
            'id':
            1,
            'layout':
            None,
            'preview_url':
            models[0].user_specialty.preview_url,
            'signed_by':
            models[0].user_specialty.signed_by,
            'signed_by_role':
            'Director',
            'specialty': {
                'created_at':
                self.datetime_to_iso(models[0].specialty.created_at),
                'id': 1,
                'logo_url': None,
                'name': models[0].specialty.name,
                'slug': models[0].specialty.slug,
                'updated_at':
                self.datetime_to_iso(models[0].specialty.updated_at),
            },
            'status':
            'PENDING',
            'status_text':
            None,
            'updated_at':
            self.datetime_to_iso(models[0].user_specialty.updated_at),
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
        base = self.generate_models(authenticate=True,
                                    cohort=True,
                                    cohort_finished=True,
                                    capability='read_certificate',
                                    role='potato',
                                    academy=True,
                                    profile_academy=True,
                                    specialty=True)

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
        user_specialty_kwargs_1 = {"token": "123dfefef1123rerf346g"}
        user_specialty_kwargs_2 = {"token": "jojfsdknjbs1123rerf346g"}
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
                'name': models[0].cohort.name,
                'slug': models[0].cohort.slug,
                'syllabus': {}
            },
            'created_at':
            self.datetime_to_iso(models[0].user_specialty.created_at),
            'expires_at':
            models[0].user_specialty.expires_at,
            'id':
            1,
            'layout':
            None,
            'preview_url':
            models[0].user_specialty.preview_url,
            'signed_by':
            models[0].user_specialty.signed_by,
            'signed_by_role':
            'Director',
            'specialty': {
                'created_at':
                self.datetime_to_iso(models[0].specialty.created_at),
                'id': 1,
                'logo_url': None,
                'name': models[0].specialty.name,
                'slug': models[0].specialty.slug,
                'updated_at':
                self.datetime_to_iso(models[0].specialty.updated_at),
            },
            'status':
            'PENDING',
            'status_text':
            None,
            'updated_at':
            self.datetime_to_iso(models[0].user_specialty.updated_at),
            'user': {
                'first_name': models[0].user.first_name,
                'id': 2,
                'last_name': models[0].user.last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
