import os

from django.urls.base import reverse_lazy
from rest_framework import status

from ..mixins import CypressTestCase


class AcademyEventTestSuite(CypressTestCase):

    def test_clean_model__bad_environment__not_exits(self):
        if "ALLOW_UNSAFE_CYPRESS_APP" in os.environ:
            del os.environ["ALLOW_UNSAFE_CYPRESS_APP"]

        url = reverse_lazy("cypress:clean_model", kwargs={"model_name": "TheyKilledKenny"})
        response = self.client.delete(url)
        json = response.json()
        expected = {"detail": "is-not-allowed", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_academy_dict(), [])
        self.assertEqual(self.all_form_entry_dict(), [])

    def test_clean_model__bad_environment__empty_string(self):
        os.environ["ALLOW_UNSAFE_CYPRESS_APP"] = ""

        url = reverse_lazy("cypress:clean_model", kwargs={"model_name": "TheyKilledKenny"})
        response = self.client.delete(url)
        json = response.json()
        expected = {"detail": "is-not-allowed", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_academy_dict(), [])
        self.assertEqual(self.all_form_entry_dict(), [])

    def test_clean_model__invalid_model(self):
        os.environ["ALLOW_UNSAFE_CYPRESS_APP"] = "True"
        url = reverse_lazy("cypress:clean_model", kwargs={"model_name": "TheyKilledKenny"})
        self.generate_models(academy=True, form_entry=True)

        response = self.client.delete(url)
        json = response.json()
        expected = {"detail": "model-not-exits", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_clean_model__delete_academy__model_name_in_many_apps(self):
        os.environ["ALLOW_UNSAFE_CYPRESS_APP"] = "True"
        url = reverse_lazy("cypress:clean_model", kwargs={"model_name": "Academy"})
        model = self.generate_models(academy=True)

        response = self.client.delete(url)
        json = response.json()
        expected = {"detail": "many-models-with-the-same-name", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_academy_dict(), [{**self.model_to_dict(model, "academy")}])

    def test_clean_model__delete_academy__bad_format(self):
        os.environ["ALLOW_UNSAFE_CYPRESS_APP"] = "True"
        url = reverse_lazy("cypress:clean_model", kwargs={"model_name": "breathecode.admissions.Academy"})
        model = self.generate_models(academy=True)

        response = self.client.delete(url)
        json = response.json()
        expected = {"detail": "bad-model-name-format", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_academy_dict(), [{**self.model_to_dict(model, "academy")}])

    def test_clean_model__delete_academy(self):
        os.environ["ALLOW_UNSAFE_CYPRESS_APP"] = "True"
        url = reverse_lazy("cypress:clean_model", kwargs={"model_name": "admissions.Academy"})
        self.generate_models(academy=True)

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_academy_dict(), [])

    def test_clean_model__delete_user(self):
        os.environ["ALLOW_UNSAFE_CYPRESS_APP"] = "True"
        url = reverse_lazy("cypress:clean_model", kwargs={"model_name": "User"})
        self.generate_models(user=True)

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_user_dict(), [])
