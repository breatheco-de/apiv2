"""
Test /cohort/:id/user/:id
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
from ..mixins import AdmissionsTestCase


class CohortIdUserIdTestSuite(AdmissionsTestCase):
    """Test /cohort/:id/user/:id"""
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_id_without_auth(self):
        """Test /cohort/:id/user/:id without auth"""
        url = reverse_lazy('admissions:cohort_id_user_id', kwargs={'cohort_id': 1, 'user_id': 1})
        response = self.client.get(url)
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
    def test_cohort_id_user_id_put_with_bad_cohort_id(self):
        """Test /cohort/:id/user/:id without auth"""
        model = self.generate_models(authenticate=True)
        url = reverse_lazy('admissions:cohort_id_user_id', kwargs={'cohort_id': 1, 'user_id': 1})
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {'status_code': 400, 'detail': 'invalid cohort_id'}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_id_put_with_bad_user_id(self):
        """Test /cohort/:id/user/:id without auth"""
        model = self.generate_models(authenticate=True, cohort=True)
        url = reverse_lazy('admissions:cohort_id_user_id',
                           kwargs={
                               'cohort_id': model.cohort.id,
                               'user_id': 999
                           })
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {'status_code': 400, 'detail': 'invalid user_id'}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_id_put_with_bad_id(self):
        """Test /cohort/:id/user/:id without auth"""
        model = self.generate_models(authenticate=True, cohort=True, user=True)
        url = reverse_lazy('admissions:cohort_id_user_id',
                           kwargs={
                               'cohort_id': model.cohort.id,
                               'user_id': model.user.id
                           })
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {'status_code': 400, 'detail': 'Specified cohort not be found'}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_id_put_with_id_but_without_user(self):
        """Test /cohort/:id/user/:id without auth"""
        model = self.generate_models(authenticate=True, cohort=True)
        url = reverse_lazy('admissions:cohort_id_user_id',
                           kwargs={
                               'cohort_id': model.cohort.id,
                               'user_id': model.user.id
                           })
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {'status_code': 400, 'detail': 'Specified cohort not be found'}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_id_put_with_id_but_with_user(self):
        """Test /cohort/:id/user/:id without auth"""
        model = self.generate_models(authenticate=True, cohort=True, user=True)
        url = reverse_lazy('admissions:cohort_id_user_id',
                           kwargs={
                               'cohort_id': model.cohort.id,
                               'user_id': model.user.id
                           })
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {'status_code': 400, 'detail': 'Specified cohort not be found'}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_id_put_with_id(self):
        """Test /cohort/:id/user/:id without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     syllabus_schedule=True,
                                     profile_academy=True,
                                     cohort_user=True)
        model_dict = self.get_cohort_user_dict(1)
        url = reverse_lazy('admissions:cohort_id_user_id',
                           kwargs={
                               'cohort_id': model.cohort.id,
                               'user_id': model.user.id
                           })
        data = {'schedule': model.syllabus_schedule.id}
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'id': model.cohort_user.id,
            'role': model.cohort_user.role,
            'educational_status': model.cohort_user.educational_status,
            'finantial_status': model.cohort_user.finantial_status,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_id_delete_with_id_with_bad_user_id(self):
        """Test /cohort/:id/user/:id without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     syllabus_schedule=True,
                                     profile_academy=True,
                                     cohort_user=True)
        url = reverse_lazy('admissions:cohort_id_user_id',
                           kwargs={
                               'cohort_id': model.cohort.id,
                               'user_id': 9999
                           })
        data = {'schedule': model.syllabus_schedule.id}
        response = self.client.delete(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_id_delete_with_id_with_bad_cohort_id(self):
        """Test /cohort/:id/user/:id without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     syllabus_schedule=True,
                                     profile_academy=True,
                                     cohort_user=True)
        url = reverse_lazy('admissions:cohort_id_user_id',
                           kwargs={
                               'cohort_id': 9999,
                               'user_id': model.user.id
                           })
        data = {'schedule': model.syllabus_schedule.id}
        response = self.client.delete(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_id_delete_with_id(self):
        """Test /cohort/:id/user/:id without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     syllabus_schedule=True,
                                     profile_academy=True,
                                     cohort_user=True)
        url = reverse_lazy('admissions:cohort_id_user_id',
                           kwargs={
                               'cohort_id': model.cohort.id,
                               'user_id': model.user.id
                           })
        data = {'schedule': model.syllabus_schedule.id}
        response = self.client.delete(url, data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.count_cohort_user(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_id_put_with_unsuccess_task(self):
        """Test /cohort/:id/user/:id without auth"""
        task = {'task_status': 'PENDING', 'task_type': 'PROJECT'}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     cohort_user=True,
                                     task=task)
        url = reverse_lazy('admissions:cohort_id_user_id',
                           kwargs={
                               'cohort_id': model.cohort.id,
                               'user_id': model.user.id
                           })
        data = {
            'educational_status': 'GRADUATED',
        }
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'status_code': 400,
            'detail': 'User has tasks with status pending the educational status cannot be GRADUATED',
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_id_put_with_unsuccess_finantial_status(self):
        """Test /cohort/:id/user/:id without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     cohort_user=True)
        url = reverse_lazy('admissions:cohort_id_user_id',
                           kwargs={
                               'cohort_id': model.cohort.id,
                               'user_id': model.user.id
                           })
        data = {
            'educational_status': 'GRADUATED',
            'finantial_status': 'LATE',
        }
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'status_code': 400,
            'detail': 'Cannot be marked as `GRADUATED` if its financial status is `LATE`',
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cohort_id_user_id_put_with_stage_delete(self):
        """Test /cohort/:id/user/:id without auth"""
        cohort_kwargs = {'stage': 'DELETED'}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     cohort_user=True,
                                     cohort_kwargs=cohort_kwargs)

        url = reverse_lazy('admissions:cohort_id_user_id',
                           kwargs={
                               'cohort_id': model.cohort.id,
                               'user_id': model.user.id
                           })
        data = {
            'educational_status': 'GRADUATED',
            'finantial_status': 'LATE',
        }
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'status_code': 400,
            'detail': 'cohort-with-stage-deleted',
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
