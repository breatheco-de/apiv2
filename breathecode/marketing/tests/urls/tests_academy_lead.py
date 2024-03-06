"""
Test /academy/lead
"""
from unittest.mock import MagicMock, call, patch
from django.utils import timezone
from datetime import timedelta
import string
from random import choice, choices, randint
from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from ..mixins import MarketingTestCase


def random_string():
    return ''.join(choices(string.ascii_letters, k=10))


def generate_form_entry_kwargs():
    """That random values is too long that i prefer have it in one function"""
    return {
        'fb_leadgen_id': randint(0, 9999),
        'fb_page_id': randint(0, 9999),
        'fb_form_id': randint(0, 9999),
        'fb_adgroup_id': randint(0, 9999),
        'fb_ad_id': randint(0, 9999),
        'gclid': random_string(),
        'first_name': choice(['Rene', 'Albert', 'Immanuel']),
        'last_name': choice(['Descartes', 'Camus', 'Kant']),
        'email': choice(['a@a.com', 'b@b.com', 'c@c.com']),
        'phone': choice(['123', '456', '789']),
        'course': random_string(),
        'client_comments': random_string(),
        'location': random_string(),
        'language': random_string(),
        'utm_url': random_string(),
        'utm_medium': random_string(),
        'utm_campaign': random_string(),
        'utm_source': random_string(),
        'utm_placement': random_string(),
        'utm_term': random_string(),
        'utm_plan': random_string(),
        'sex': random_string(),
        'custom_fields': None,
        'referral_key': random_string(),
        'gclid': random_string(),
        'tags': random_string(),
        'automations': random_string(),
        'street_address': random_string(),
        'country': random_string(),
        'city': random_string(),
        'latitude': randint(0, 9999),
        'longitude': randint(0, 9999),
        'state': random_string(),
        'zip_code': str(randint(0, 9999)),
        'browser_lang': random_string(),
        'storage_status': choice(['PENDING', 'PERSISTED']),
        'lead_type': choice(['STRONG', 'SOFT', 'DISCOVERY']),
        'deal_status': choice(['WON', 'LOST']),
        'sentiment': choice(['GOOD', 'BAD']),
    }


def get_serializer(self, form_entry):
    return {
        'country': form_entry.country,
        'course': form_entry.course,
        'email': form_entry.email,
        'first_name': form_entry.first_name,
        'gclid': form_entry.gclid,
        'id': form_entry.id,
        'language': form_entry.language,
        'last_name': form_entry.last_name,
        'lead_type': form_entry.lead_type,
        'location': form_entry.location,
        'storage_status': form_entry.storage_status,
        'tags': form_entry.tags,
        'utm_campaign': form_entry.utm_campaign,
        'utm_medium': form_entry.utm_medium,
        'utm_source': form_entry.utm_source,
        'utm_content': form_entry.utm_content,
        'utm_placement': form_entry.utm_placement,
        'utm_term': form_entry.utm_term,
        'utm_plan': form_entry.utm_plan,
        'sex': form_entry.sex,
        'custom_fields': form_entry.custom_fields,
        'utm_url': form_entry.utm_url,
        'ac_expected_cohort': form_entry.ac_expected_cohort,
        'user': None,
        'phone': form_entry.phone,
        'created_at': self.bc.datetime.to_iso_string(form_entry.created_at),
        'storage_status_text': form_entry.storage_status_text,
    }


class CohortUserTestSuite(MarketingTestCase):
    """Test /academy/lead"""
    """
    🔽🔽🔽 Auth
    """

    def test_academy_lead__without_auth(self):
        """Test /cohort/:id/user without auth"""
        url = reverse_lazy('marketing:academy_lead')
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_form_entry_dict(), [])

    def test_academy_lead__without_academy_header(self):
        """Test /cohort/:id/user without auth"""
        url = reverse_lazy('marketing:academy_lead')
        model = self.generate_models(authenticate=True, profile_academy=True, capability='read_lead', role='potato')

        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': 'Missing academy_id parameter expected for the endpoint url or '
            "'Academy' header",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_form_entry_dict(), [])

    """
    🔽🔽🔽 Without data
    """

    def test_academy_lead__without_data(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('marketing:academy_lead')
        model = self.generate_models(authenticate=True, profile_academy=True, capability='read_lead', role='potato')

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [])

    """
    🔽🔽🔽 With data
    """

    def test_academy_lead(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato',
                                     form_entry=True,
                                     form_entry_kwargs=generate_form_entry_kwargs())

        url = reverse_lazy('marketing:academy_lead')
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(self, model.form_entry)
        del expected['custom_fields']
        expected = [expected]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, 'form_entry')}])

    """
    🔽🔽🔽 Storage status in querystring
    """

    def test_academy_lead__with_bad_storage_status_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato',
                                     form_entry=True,
                                     form_entry_kwargs=generate_form_entry_kwargs())

        url = reverse_lazy('marketing:academy_lead') + '?storage_status=freyja'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, 'form_entry')}])

    def test_academy_lead__with_storage_status_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato',
                                     form_entry=True,
                                     form_entry_kwargs=generate_form_entry_kwargs())

        url = reverse_lazy('marketing:academy_lead') + f'?storage_status={model.form_entry.storage_status}'
        response = self.client.get(url)

        json = response.json()

        expected = get_serializer(self, model.form_entry)
        del expected['custom_fields']
        expected = [expected]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, 'form_entry')}])

    """
    🔽🔽🔽 Course in querystring
    """

    def test_academy_lead__with_bad_course_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato',
                                     form_entry=True,
                                     form_entry_kwargs=generate_form_entry_kwargs())

        url = reverse_lazy('marketing:academy_lead') + '?course=freyja'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, 'form_entry')}])

    def test_academy_lead__with_course_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato',
                                     form_entry=True,
                                     form_entry_kwargs=generate_form_entry_kwargs())

        url = reverse_lazy('marketing:academy_lead') + f'?course={model.form_entry.course}'
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(self, model.form_entry)
        del expected['custom_fields']
        expected = [expected]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, 'form_entry')}])

    """
    🔽🔽🔽 Location in querystring
    """

    def test_academy_lead__with_bad_location_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato',
                                     form_entry=True,
                                     form_entry_kwargs=generate_form_entry_kwargs())

        url = reverse_lazy('marketing:academy_lead') + '?location=freyja'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, 'form_entry')}])

    def test_academy_lead__with_location_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato',
                                     form_entry=True,
                                     form_entry_kwargs=generate_form_entry_kwargs())

        url = reverse_lazy('marketing:academy_lead') + f'?location={model.form_entry.location}'
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(self, model.form_entry)
        del expected['custom_fields']
        expected = [expected]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, 'form_entry')}])

    def test_academy_lead__with_location_alias_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato',
                                     form_entry=True,
                                     form_entry_kwargs=generate_form_entry_kwargs())

        url = reverse_lazy('marketing:academy_lead') + f'?location_alias={model.form_entry.location}'
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(self, model.form_entry)
        del expected['custom_fields']
        expected = [expected]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, 'form_entry')}])

    """
    🔽🔽🔽 utm_term in querystring
    """

    def test_academy_lead__with_bad_utm_term_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato',
                                     form_entry=True,
                                     form_entry_kwargs=generate_form_entry_kwargs())

        url = reverse_lazy('marketing:academy_lead') + '?utm_term=freyja'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, 'form_entry')}])

    def test_academy_lead__with_utm_term_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato',
                                     form_entry=True,
                                     form_entry_kwargs=generate_form_entry_kwargs())

        url = reverse_lazy('marketing:academy_lead') + f'?utm_term={model.form_entry.utm_term}'
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(self, model.form_entry)
        del expected['custom_fields']
        expected = [expected]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, 'form_entry')}])

    """
    🔽🔽🔽 utm_source in querystring
    """

    def test_academy_lead__with_bad_utm_source_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato',
                                     form_entry=True,
                                     form_entry_kwargs=generate_form_entry_kwargs())

        url = reverse_lazy('marketing:academy_lead') + '?utm_source=freyja'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, 'form_entry')}])

    def test_academy_lead__with_utm_source_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato',
                                     form_entry=True,
                                     form_entry_kwargs=generate_form_entry_kwargs())

        url = reverse_lazy('marketing:academy_lead') + f'?utm_source={model.form_entry.utm_source}'
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(self, model.form_entry)
        del expected['custom_fields']
        expected = [expected]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, 'form_entry')}])

    """
    🔽🔽🔽 Start in querystring
    """

    def test_academy_lead__with_bad_start_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('marketing:academy_lead') + '?start=2100-01-01'
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato',
                                     form_entry=True)

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, 'form_entry')}])

    def test_academy_lead__with_start_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        query_date = (timezone.now() - timedelta(hours=48)).strftime('%Y-%m-%d')
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato',
                                     form_entry=True)

        url = reverse_lazy('marketing:academy_lead') + f'?start={query_date}'
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(self, model.form_entry)
        del expected['custom_fields']
        expected = [expected]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, 'form_entry')}])

    """
    🔽🔽🔽 End in querystring
    """

    def test_academy_lead__with_bad_end_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('marketing:academy_lead') + '?end=1900-01-01'
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato',
                                     form_entry=True)

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, 'form_entry')}])

    def test_academy_lead__with_end_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        query_date = (timezone.now() + timedelta(hours=48)).strftime('%Y-%m-%d')
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato',
                                     form_entry=True)

        url = reverse_lazy('marketing:academy_lead') + f'?end={query_date}'
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(self, model.form_entry)
        del expected['custom_fields']
        expected = [expected]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, 'form_entry')}])

    """
    🔽🔽🔽 Bulk delete
    """

    def test_academy_lead__delete__in_bulk_with_one(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields = ['id']

        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='crud_lead',
                                    role='potato',
                                    academy=True,
                                    active_campaign_academy=True)

        for field in many_fields:
            form_entry_kwargs = generate_form_entry_kwargs()
            model = self.generate_models(form_entry=True,
                                         contact=True,
                                         automation=True,
                                         form_entry_kwargs=form_entry_kwargs,
                                         models=base)

            url = (reverse_lazy('marketing:academy_lead') + f'?{field}=' + str(getattr(model['form_entry'], field)))
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.all_form_entry_dict(), [])

    def test_academy_lead__delete__in_bulk_with_two(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields = ['id']

        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='crud_lead',
                                    role='potato',
                                    academy=True,
                                    active_campaign_academy=True)

        for field in many_fields:
            form_entry_kwargs = generate_form_entry_kwargs()
            model1 = self.generate_models(form_entry=True,
                                          contact=True,
                                          automation=True,
                                          form_entry_kwargs=form_entry_kwargs,
                                          models=base)

            form_entry_kwargs = generate_form_entry_kwargs()
            model2 = self.generate_models(form_entry=True,
                                          contact=True,
                                          automation=True,
                                          form_entry_kwargs=form_entry_kwargs,
                                          models=base)

            url = (reverse_lazy('marketing:academy_lead') + f'?{field}=' + str(getattr(model1['form_entry'], field)) +
                   ',' + str(getattr(model2['form_entry'], field)))
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.all_form_entry_dict(), [])

    """
    🔽🔽🔽 With full like in querystring
    """

    def test_academy_lead__with_full_name_in_querystring(self):
        """Test /academy/lead """
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    academy=True,
                                    capability='read_lead',
                                    role='potato')

        form_entry_kwargs_1 = generate_form_entry_kwargs()
        form_entry_kwargs_2 = generate_form_entry_kwargs()

        form_entry_kwargs_1['first_name'] = 'Michael'
        form_entry_kwargs_1['last_name'] = 'Jordan'

        models = [
            self.generate_models(form_entry_kwargs=form_entry_kwargs_1, form_entry=True, models=base),
            self.generate_models(form_entry_kwargs=form_entry_kwargs_2, form_entry=True, models=base)
        ]

        base_url = reverse_lazy('marketing:academy_lead')
        url = f'{base_url}?like={models[0].form_entry.first_name} {models[0].form_entry.last_name}'
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(self, models[0].form_entry)
        del expected['custom_fields']
        expected = [expected]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, 'form_entry')} for model in models])

    def test_academy_lead__with_first_name_in_querystring(self):
        """Test /academy/lead """
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    academy=True,
                                    capability='read_lead',
                                    role='potato')

        form_entry_kwargs_1 = generate_form_entry_kwargs()
        form_entry_kwargs_2 = generate_form_entry_kwargs()

        form_entry_kwargs_1['first_name'] = 'Michael'
        form_entry_kwargs_1['last_name'] = 'Jordan'

        models = [
            self.generate_models(form_entry_kwargs=form_entry_kwargs_1, form_entry=True, models=base),
            self.generate_models(form_entry_kwargs=form_entry_kwargs_2, form_entry=True, models=base)
        ]
        base_url = reverse_lazy('marketing:academy_lead')
        url = f'{base_url}?like={models[0].form_entry.first_name}'
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(self, models[0].form_entry)
        del expected['custom_fields']
        expected = [expected]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, 'form_entry')} for model in models])

    def test_academy_lead__with_last_name_in_querystring(self):
        """Test /academy/lead """
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    academy=True,
                                    capability='read_lead',
                                    role='potato')

        form_entry_kwargs_1 = generate_form_entry_kwargs()
        form_entry_kwargs_2 = generate_form_entry_kwargs()

        form_entry_kwargs_1['first_name'] = 'Michael'
        form_entry_kwargs_1['last_name'] = 'Jordan'

        models = [
            self.generate_models(form_entry_kwargs=form_entry_kwargs_1, form_entry=True, models=base),
            self.generate_models(form_entry_kwargs=form_entry_kwargs_2, form_entry=True, models=base)
        ]

        base_url = reverse_lazy('marketing:academy_lead')
        url = f'{base_url}?like={models[0].form_entry.last_name}'
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(self, models[0].form_entry)
        del expected['custom_fields']
        expected = [expected]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, 'form_entry')} for model in models])

    def test_academy_lead__with_email_in_querystring(self):
        """Test /academy/lead """
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    academy=True,
                                    capability='read_lead',
                                    role='potato')

        form_entry_kwargs_1 = generate_form_entry_kwargs()
        form_entry_kwargs_2 = generate_form_entry_kwargs()

        form_entry_kwargs_1['email'] = 'michael@jordan.com'
        models = [
            self.generate_models(form_entry_kwargs=form_entry_kwargs_1, form_entry=True, models=base),
            self.generate_models(form_entry_kwargs=form_entry_kwargs_2, form_entry=True, models=base)
        ]

        base_url = reverse_lazy('marketing:academy_lead')
        url = f'{base_url}?like={models[0].form_entry.email}'
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(self, models[0].form_entry)
        del expected['custom_fields']
        expected = [expected]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, 'form_entry')} for model in models])

    """
    🔽🔽🔽 Spy extensions
    """

    @patch.object(APIViewExtensionHandlers, '_spy_extensions', MagicMock())
    def test_academy_lead__spy_extensions(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('marketing:academy_lead')
        model = self.generate_models(authenticate=True, profile_academy=True, capability='read_lead', role='potato')

        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extensions.call_args_list, [
            call(['LanguageExtension', 'LookupExtension', 'PaginationExtension', 'SortExtension']),
        ])

    @patch.object(APIViewExtensionHandlers, '_spy_extension_arguments', MagicMock())
    def test_academy_lead__spy_extension_arguments(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('marketing:academy_lead')
        model = self.generate_models(authenticate=True, profile_academy=True, capability='read_lead', role='potato')

        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extension_arguments.call_args_list, [
            call(sort='-created_at', paginate=True),
        ])
