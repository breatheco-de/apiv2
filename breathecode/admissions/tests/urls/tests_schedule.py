"""
Test /certificate
"""
from unittest.mock import MagicMock, call, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from random import choice, randint

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from ..mixins import AdmissionsTestCase


class CertificateTestSuite(AdmissionsTestCase):
    """Test /certificate"""
    def test_certificate_without_auth(self):
        """Test /certificate without auth"""
        url = reverse_lazy('admissions:schedule')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_certificate_without_data(self):
        """Test /certificate without auth"""
        url = reverse_lazy('admissions:schedule')
        self.bc.database.create(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_syllabus_schedule(), 0)

    def test_certificate_with_data(self):
        """Test /certificate without auth"""
        model = self.bc.database.create(authenticate=True, syllabus=True, syllabus_schedule=True)
        url = reverse_lazy('admissions:schedule')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'id': model['syllabus_schedule'].id,
            'name': model['syllabus_schedule'].name,
            'description': model['syllabus_schedule'].description,
            'syllabus': model['syllabus_schedule'].syllabus.id,
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.all_syllabus_schedule_dict(), [{
            **self.model_to_dict(model, 'syllabus_schedule'),
        }])

    """
    🔽🔽🔽 Syllabus id in querystring
    """

    def test_academy_schedule__syllabus_id_in_querystring__bad_id(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        syllabus_schedule=True,
                                        profile_academy=True,
                                        capability='read_certificate',
                                        role='potato',
                                        syllabus=True)
        url = reverse_lazy('admissions:schedule') + '?syllabus_id=9999'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])

    def test_academy_schedule__syllabus_id_in_querystring(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        syllabus_schedule=True,
                                        profile_academy=True,
                                        capability='read_certificate',
                                        role='potato',
                                        syllabus=True)
        url = reverse_lazy('admissions:schedule') + '?syllabus_id=1'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.syllabus_schedule.id,
            'name': model.syllabus_schedule.name,
            'description': model.syllabus_schedule.description,
            'syllabus': model.syllabus_schedule.syllabus.id,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])

    """
    🔽🔽🔽 Syllabus slug in querystring
    """

    def test_academy_schedule__syllabus_slug_in_querystring__bad_id(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        syllabus_schedule=True,
                                        profile_academy=True,
                                        capability='read_certificate',
                                        role='potato',
                                        syllabus=True)
        url = reverse_lazy('admissions:schedule') + '?syllabus_slug=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])

    def test_academy_schedule__syllabus_slug_in_querystring(self):
        """Test /certificate without auth"""
        self.headers(academy=1)

        syllabus_kwargs = {'slug': 'they-killed-kenny'}
        model = self.bc.database.create(authenticate=True,
                                        syllabus_schedule=True,
                                        profile_academy=True,
                                        capability='read_certificate',
                                        role='potato',
                                        syllabus=True,
                                        syllabus_kwargs=syllabus_kwargs)
        url = reverse_lazy('admissions:schedule') + '?syllabus_slug=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.syllabus_schedule.id,
            'name': model.syllabus_schedule.name,
            'description': model.syllabus_schedule.description,
            'syllabus': model.syllabus_schedule.syllabus.id,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])

    """
    🔽🔽🔽 Academy id in querystring
    """

    def test_academy_schedule__academy_id_in_querystring__bad_id(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        syllabus_schedule=True,
                                        profile_academy=True,
                                        capability='read_certificate',
                                        role='potato',
                                        syllabus=True)
        url = reverse_lazy('admissions:schedule') + '?academy_id=9999'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])

    def test_academy_schedule__academy_id_in_querystring(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        syllabus_schedule=True,
                                        profile_academy=True,
                                        capability='read_certificate',
                                        role='potato',
                                        syllabus=True)
        url = reverse_lazy('admissions:schedule') + '?academy_id=1'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.syllabus_schedule.id,
            'name': model.syllabus_schedule.name,
            'description': model.syllabus_schedule.description,
            'syllabus': model.syllabus_schedule.syllabus.id,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])

    """
    🔽🔽🔽 Academy slug in querystring
    """

    def test_academy_schedule__academy_slug_in_querystring__bad_id(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.bc.database.create(authenticate=True,
                                        syllabus_schedule=True,
                                        profile_academy=True,
                                        capability='read_certificate',
                                        role='potato',
                                        syllabus=True)
        url = reverse_lazy('admissions:schedule') + '?academy_slug=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])

    def test_academy_schedule__academy_slug_in_querystring(self):
        """Test /certificate without auth"""
        self.headers(academy=1)

        academy = {'slug': 'they-killed-kenny'}
        model = self.bc.database.create(authenticate=True,
                                        syllabus_schedule=True,
                                        profile_academy=True,
                                        capability='read_certificate',
                                        role='potato',
                                        syllabus=True,
                                        academy=academy)
        url = reverse_lazy('admissions:schedule') + '?academy_slug=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.syllabus_schedule.id,
            'name': model.syllabus_schedule.name,
            'description': model.syllabus_schedule.description,
            'syllabus': model.syllabus_schedule.syllabus.id,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, 'syllabus')}])

    """
    🔽🔽🔽 Spy the extensions
    """

    @patch.object(APIViewExtensionHandlers, '_spy_extensions', MagicMock())
    def test_certificate__spy_extensions(self):
        """Test /certificate without auth"""

        url = reverse_lazy('admissions:schedule')
        self.bc.database.create(authenticate=True)
        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extensions.call_args_list, [
            call(['PaginationExtension']),
        ])

    @patch.object(APIViewExtensionHandlers, '_spy_extension_arguments', MagicMock())
    def test_certificate__spy_extension_arguments(self):
        """Test /certificate without auth"""

        url = reverse_lazy('admissions:schedule')
        self.bc.database.create(authenticate=True)
        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extension_arguments.call_args_list, [
            call(paginate=True),
        ])
