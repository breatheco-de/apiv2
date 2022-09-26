"""
Test /cohort
"""
from datetime import timedelta
import random
from django.utils import timezone
from breathecode.admissions.caches import CohortCache
from unittest.mock import MagicMock, call, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers

from breathecode.utils.datetime_interger import DatetimeInteger
from ..mixins import AdmissionsTestCase


def put_serializer(academy, country, city, data={}):
    return {
        'city': city.id,
        'country': country.code,
        'id': academy.id,
        'name': academy.name,
        'slug': academy.slug,
        'street_address': academy.street_address,
        **data,
    }


class AcademyCohortIdTestSuite(AdmissionsTestCase):
    """Test /cohort"""

    cache = CohortCache()
    """
    🔽🔽🔽 Auth
    """

    def test__without_auth(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_me')
        response = self.client.put(url, {})
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_put__without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_me')
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': "You (user: 1) don't have this capability: crud_my_academy for academy 1",
                'status_code': 403
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 Put without required fields
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test__put__without_required_fields(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_me')
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_my_academy',
                                     role='potato',
                                     skip_cohort=True,
                                     syllabus=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'name': ['This field is required.'],
            'slug': ['This field is required.'],
            'street_address': ['This field is required.'],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('admissions.Academy'), [
            self.bc.format.to_dict(model.academy),
        ])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Put with Academy, try to modify slug
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test__put__with_academy__try_to_modify_slug(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_me')
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_my_academy',
                                     role='potato',
                                     skip_cohort=True,
                                     syllabus=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        data = {
            'name': self.bc.fake.name(),
            'slug': self.bc.fake.slug(),
            'street_address': self.bc.fake.address(),
        }
        response = self.client.put(url, data)
        json = response.json()
        expected = {'detail': 'Academy slug cannot be updated', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('admissions.Academy'), [
            self.bc.format.to_dict(model.academy),
        ])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Put with Academy, passing all the fields
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test__put__with_academy__passing_all_the_fields(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_me')
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     country=3,
                                     city=3,
                                     capability='crud_my_academy',
                                     role='potato',
                                     skip_cohort=True,
                                     syllabus=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        country = random.choice(model.country)
        city = random.choice(model.city)
        data = {
            'name': self.bc.fake.name(),
            'slug': model.academy.slug,
            'street_address': self.bc.fake.address(),
            'country': country.code,
            'city': city.id,
        }
        response = self.client.put(url, data)
        json = response.json()
        expected = put_serializer(model.academy, country, city, data=data)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        fields = ['country', 'city']
        for field in fields:
            data[f'{field}_id'] = data.pop(field)

        self.assertEqual(self.bc.database.list_of('admissions.Academy'), [{
            **self.bc.format.to_dict(model.academy),
            **data,
        }])
        self.assertEqual(cohort_saved.send.call_args_list, [])

    """
    🔽🔽🔽 Put with Academy, passing all the wrong fields
    """

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def test__put__with_academy__passing_all_the_wrong_fields(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_me')
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     country=3,
                                     city=3,
                                     capability='crud_my_academy',
                                     role='potato',
                                     skip_cohort=True,
                                     syllabus=True)

        # reset because this call are coming from mixer
        cohort_saved.send.call_args_list = []

        country = random.choice(model.country)
        city = random.choice(model.city)
        data = {
            'name': self.bc.fake.name(),
            'slug': model.academy.slug,
            'street_address': self.bc.fake.address(),
            'country': country.code,
            'city': city.id,
        }

        incorrect_values = {
            'logo_url': self.bc.fake.url(),
            'icon_url': self.bc.fake.url(),
            'website_url': self.bc.fake.url(),
            'marketing_email': self.bc.fake.email(),
            'feedback_email': self.bc.fake.email(),
            'marketing_phone': self.bc.fake.phone_number(),
            'twitter_handle': self.bc.fake.user_name(),
            'facebook_handle': self.bc.fake.user_name(),
            'instagram_handle': self.bc.fake.user_name(),
            'github_handle': self.bc.fake.user_name(),
            'linkedin_url': self.bc.fake.url(),
            'youtube_url': self.bc.fake.url(),
            'latitude': random.random() * 90 * random.choice([1, -1]),  #
            'longitude': random.random() * 90 * random.choice([1, -1]),
            'zip_code': random.randint(1, 1000),
            'white_labeled': bool(random.randint(0, 1)),
            'active_campaign_slug': self.bc.fake.slug(),
            'available_as_saas': bool(random.randint(0, 1)),
            'status': random.choice(['INACTIVE', 'ACTIVE', 'DELETED']),
            'timezone': self.bc.fake.name(),
            'logistical_information': self.bc.fake.text()[:150]
        }

        to_send = data.copy()
        to_send |= incorrect_values

        response = self.client.put(url, to_send)
        json = response.json()
        expected = put_serializer(model.academy, country, city, data=data)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        fields = ['country', 'city']
        for field in fields:
            data[f'{field}_id'] = data.pop(field)

        self.assertEqual(self.bc.database.list_of('admissions.Academy'), [{
            **self.bc.format.to_dict(model.academy),
            **data,
        }])
        self.assertEqual(cohort_saved.send.call_args_list, [])
