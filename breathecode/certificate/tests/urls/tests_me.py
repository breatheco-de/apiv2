"""
Test /certificate
"""
from unittest.mock import MagicMock, call, patch
from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from ..mixins import CertificateTestCase
import breathecode.certificate.signals as signals


def get_serializer(self, user_specialty, academy, specialty, user):
    return {
        'academy': {
            'id': academy.id,
            'logo_url': academy.logo_url,
            'name': academy.name,
            'slug': academy.slug,
            'website_url': academy.website_url,
        },
        'cohort': user_specialty.cohort,
        'created_at': self.bc.datetime.to_iso_string(user_specialty.created_at),
        'expires_at': user_specialty.expires_at,
        'id': user_specialty.id,
        'issued_at': user_specialty.issued_at,
        'layout': user_specialty.layout,
        'preview_url': user_specialty.preview_url,
        'signed_by': user_specialty.signed_by,
        'signed_by_role': user_specialty.signed_by_role,
        'specialty': {
            'created_at': self.bc.datetime.to_iso_string(specialty.created_at),
            'description': specialty.description,
            'id': specialty.id,
            'logo_url': specialty.logo_url,
            'name': specialty.name,
            'slug': specialty.slug,
            'updated_at': self.bc.datetime.to_iso_string(specialty.updated_at),
        },
        'status': user_specialty.status,
        'status_text': user_specialty.status_text,
        'updated_at': self.bc.datetime.to_iso_string(user_specialty.updated_at),
        'user': {
            'first_name': user.first_name,
            'id': user.id,
            'last_name': user.last_name,
        },
        'profile_academy': None
    }


class CertificateTestSuite(CertificateTestCase):
    """Test /me"""
    """
    🔽🔽🔽 Auth
    """

    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_without_auth(self):
        url = reverse_lazy('certificate:me')
        response = self.client.get(url)

        json = response.json()
        expected = {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    """
    🔽🔽🔽 GET without permission
    """

    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test__get__without_permission(self):
        model = self.bc.database.create(user=1)

        self.bc.request.authenticate(model.user)
        url = reverse_lazy('certificate:me')
        response = self.client.get(url)

        json = response.json()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET with zero UserSpecialty
    """

    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test__get__with_zero_user_specialties(self):
        permission = {'codename': 'get_my_certificate'}
        model = self.bc.database.create(user=1, permission=permission)

        self.bc.request.authenticate(model.user)
        url = reverse_lazy('certificate:me')
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 GET with one UserSpecialty and status 'PENDING'
    """

    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test__get__with_one_user_specialty_status_pending(self):
        permission = {'codename': 'get_my_certificate'}
        model = self.bc.database.create(user=1, permission=permission, user_specialty=1)

        self.bc.request.authenticate(model.user)
        url = reverse_lazy('certificate:me')
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, model.user_specialty, model.academy, model.specialty, model.user)
                    ] if model.user_specialty.status == 'PERSISTED' else []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 GET with one UserSpecialty and status 'PERSISTED'
    """

    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test__get__with_one_user_specialty_status_persisted(self):
        permission = {'codename': 'get_my_certificate'}
        model = self.bc.database.create(user=1,
                                        permission=permission,
                                        user_specialty={
                                            'token': 'xyz1',
                                            'status': 'PERSISTED'
                                        })

        self.bc.request.authenticate(model.user)
        url = reverse_lazy('certificate:me')
        response = self.client.get(url)

        json = response.json()
        expected = [get_serializer(self, model.user_specialty, model.academy, model.specialty, model.user)
                    ] if model.user_specialty.status == 'PERSISTED' else []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 GET with two UserSpecialty
    """

    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test__get__with_two_user_specialty(self):
        permission = {'codename': 'get_my_certificate'}
        user_specialties = [{'token': 'xyz1', 'status': 'PERSISTED'}, {'token': 'xyz2'}]
        model = self.bc.database.create(user=1, permission=permission, user_specialty=user_specialties)

        self.bc.request.authenticate(model.user)
        url = reverse_lazy('certificate:me')
        response = self.client.get(url)

        json = response.json()
        user_specialties = sorted(model.user_specialty, key=lambda x: x.created_at, reverse=True)
        expected = [
            get_serializer(self, user_specialty, model.academy, model.specialty, model.user)
            for user_specialty in user_specialties if user_specialty.status == 'PERSISTED'
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 GET with two UserSpecialty from another user
    """

    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test__get__with_two_user_specialty__from_another_user(self):
        permission = {'codename': 'get_my_certificate'}
        user_specialties = [{'token': 'xyz1', 'user_id': 2}, {'token': 'xyz2', 'user_id': 2}]
        model = self.bc.database.create(user=2, permission=permission, user_specialty=user_specialties)

        self.bc.request.authenticate(model.user[0])
        url = reverse_lazy('certificate:me')
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 Spy the extensions
    """

    @patch.object(APIViewExtensionHandlers, '_spy_extensions', MagicMock())
    @patch.object(APIViewExtensionHandlers, '_spy_extension_arguments', MagicMock())
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test__get__spy_the_extensions(self):
        permission = {'codename': 'get_my_certificate'}
        model = self.bc.database.create(user=1, permission=permission, user_specialty=1)

        self.bc.request.authenticate(model.user)
        url = reverse_lazy('certificate:me')
        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extensions.call_args_list, [
            call(['PaginationExtension', 'SortExtension']),
        ])

        self.assertEqual(APIViewExtensionHandlers._spy_extension_arguments.call_args_list, [
            call(sort='-created_at', paginate=True),
        ])
