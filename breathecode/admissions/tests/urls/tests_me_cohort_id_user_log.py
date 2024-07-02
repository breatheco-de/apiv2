"""
Test /cohort/:id/user/:id
"""
import re
from unittest.mock import MagicMock, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_blob_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_client_mock,
)

from ..mixins import AdmissionsTestCase


def get_serializer(cohort_user, cohort, data={}):
    return {
        'cohort': {
            'id': cohort.id,
            'slug': cohort.slug,
        },
        'history_log': cohort_user.history_log,
    }


class CohortIdUserIdTestSuite(AdmissionsTestCase):
    """Test /cohort/:id/user/:id"""

    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test_no_auth(self):
        """Test /cohort/:id/user/:id without auth"""
        url = reverse_lazy('admissions:me_cohort_id_user_log', kwargs={'cohort_id': 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test_zero_items(self):
        """Test /cohort/:id/user/:id without auth"""
        model = self.generate_models(user=1)
        self.bc.request.authenticate(model['user'])
        url = reverse_lazy('admissions:me_cohort_id_user_log', kwargs={'cohort_id': 1})
        response = self.client.get(url, format='json')
        json = response.json()
        expected = {'detail': 'cohort-user-not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

    @patch('django.db.models.signals.pre_delete.send_robust', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send_robust', MagicMock(return_value=None))
    def test_two_items(self):
        """Test /cohort/:id/user/:id without auth"""

        history_log = {
            self.bc.fake.slug(): self.bc.fake.slug(),
            self.bc.fake.slug(): self.bc.fake.slug(),
            self.bc.fake.slug(): self.bc.fake.slug(),
        }
        cohort_user = {'history_log': history_log}
        model = self.generate_models(user=1, cohort_user=cohort_user)
        self.bc.request.authenticate(model['user'])
        url = reverse_lazy('admissions:me_cohort_id_user_log', kwargs={'cohort_id': 1})
        response = self.client.get(url, format='json')
        json = response.json()
        expected = get_serializer(model.cohort_user, model.cohort)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [
            self.bc.format.to_dict(model.cohort_user),
        ])
