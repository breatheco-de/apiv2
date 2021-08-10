"""
Test /academy
"""
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AdmissionsTestCase


class academyTestSuite(AdmissionsTestCase):
    """Test /academy"""
    def test_academy_without_auth(self):
        """Test /academy without auth"""
        url = reverse_lazy('admissions:academy')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_academy_without_data(self):
        """Test /academy without auth"""
        url = reverse_lazy('admissions:academy')
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_academy(), 0)

    def test_academy_with_data(self):
        """Test /academy without auth"""
        model = self.generate_models(authenticate=True, academy=True)
        url = reverse_lazy('admissions:academy')
        model_dict = self.remove_dinamics_fields(model.academy.__dict__)

        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'id': model.academy.id,
            'name': model.academy.name,
            'slug': model.academy.slug,
            'street_address': model.academy.street_address,
            'country': model.academy.country.code,
            'city': model.academy.city.id,
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_academy(), 1)
        self.assertEqual(self.get_academy_dict(1), model_dict)

    # def test_academy_new_without_require_fields(self):
    #     """Test /academy without auth"""
    #     url = reverse_lazy('admissions:academy_me')
    #     self.generate_models(authenticate=True, academy=True)
    #     data = {}
    #     response = self.client.post(url, data)
    #     json = response.json()

    #     self.assertEqual(
    #         json,
    #         {
    #             # 'city': ['This field is required.'],
    #             # 'country': ['This field is required.'],
    #             'slug': ['This field is required.'],
    #             'name': ['This field is required.'],
    #             'street_address': ['This field is required.']
    #         })
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # def test_academy_new_element(self):
    #     """Test /academy without auth"""
    #     url = reverse_lazy('admissions:academy_me')
    #     self.generate_models(authenticate=True, country=True)
    #     data = {
    #         'slug': 'oh-my-god',
    #         'name': 'they killed kenny',
    #         'street_address': 'you bastards',
    #         'country': self.country.code,
    #         'city': self.city.id,
    #     }
    #     response = self.client.post(url, data)
    #     json = response.json()

    #     expected = {
    #         'id': 1,
    #     }
    #     expected.update(data)
    #     self.assertEqual(json, expected)
    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    #     model_dict = self.get_academy_dict(1)
    #     data['country_id'] = data['country']
    #     data['city_id'] = data['city']
    #     del data['country']
    #     del data['city']
    #     model_dict.update(data)

    #     self.assertEqual(self.count_academy(), 1)
    #     self.assertEqual(self.get_academy_dict(1), model_dict)
