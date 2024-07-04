import os

from django.urls.base import reverse_lazy
from rest_framework import status

from ..mixins import CypressTestCase


class AcademyEventTestSuite(CypressTestCase):

    def test_clean__bad_environment__not_exits(self):
        if "ALLOW_UNSAFE_CYPRESS_APP" in os.environ:
            del os.environ["ALLOW_UNSAFE_CYPRESS_APP"]

        url = reverse_lazy("cypress:clean")
        response = self.client.delete(url)
        json = response.json()
        expected = {"detail": "is-not-allowed", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_academy_dict(), [])
        self.assertEqual(self.all_form_entry_dict(), [])

    def test_clean__bad_environment__empty_string(self):
        os.environ["ALLOW_UNSAFE_CYPRESS_APP"] = ""

        url = reverse_lazy("cypress:clean")
        response = self.client.delete(url)
        json = response.json()
        expected = {"detail": "is-not-allowed", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_academy_dict(), [])
        self.assertEqual(self.all_form_entry_dict(), [])

    def test_clean(self):
        os.environ["ALLOW_UNSAFE_CYPRESS_APP"] = "True"
        url = reverse_lazy("cypress:clean")
        self.generate_models(academy=True, form_entry=True)

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_academy_dict(), [])
        self.assertEqual(self.all_form_entry_dict(), [])
