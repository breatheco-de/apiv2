"""
Test /academy/lead/process
"""

from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from ..mixins import MarketingTestCase
from .tests_academy_lead import generate_form_entry_kwargs


class AcademyProcessLeadTestSuite(MarketingTestCase):
    """Test /academy/lead/process"""

    def test_academy_process_lead__without_auth(self):
        url = reverse_lazy("marketing:academy_process_lead") + "?id=1"
        response = self.client.put(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_academy_process_lead__without_capability(self):
        self.headers(academy=1)
        url = reverse_lazy("marketing:academy_process_lead") + "?id=1"
        self.generate_models(authenticate=True)

        response = self.client.put(url)
        json = response.json()
        expected = {"detail": "You (user: 1) don't have this capability: crud_lead for academy 1", "status_code": 403}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_academy_process_lead__without_id(self):
        self.headers(academy=1)
        url = reverse_lazy("marketing:academy_process_lead")
        self.generate_models(authenticate=True, profile_academy=True, capability="crud_lead", role="potato")

        response = self.client.put(url)
        json = response.json()
        expected = {"detail": "Missing id parameters in the querystring", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("breathecode.marketing.views.persist_single_lead.delay", MagicMock())
    def test_academy_process_lead__async(self, mock_delay):
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_lead",
            role="potato",
            academy=True,
            form_entry=True,
            form_entry_kwargs=generate_form_entry_kwargs(),
        )

        url = reverse_lazy("marketing:academy_process_lead") + f"?id={model.form_entry.id}"
        response = self.client.put(url)
        json = response.json()

        self.assertEqual(json, {"details": "1 leads added to the processing queue"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            mock_delay.call_args_list,
            [call(model.form_entry.to_form_data())],
        )

    @patch("breathecode.marketing.views.persist_single_lead", MagicMock())
    def test_academy_process_lead__sync(self, mock_persist_single_lead):
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_lead",
            role="potato",
            academy=True,
            form_entry=True,
            form_entry_kwargs=generate_form_entry_kwargs(),
        )

        url = reverse_lazy("marketing:academy_process_lead") + f"?id={model.form_entry.id}&sync=true"
        response = self.client.put(url)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json["details"], "1 leads processed")
        self.assertEqual(
            json["results"],
            [
                {
                    "id": model.form_entry.id,
                    "storage_status": model.form_entry.storage_status,
                    "storage_status_text": model.form_entry.storage_status_text,
                }
            ],
        )
        self.assertEqual(
            mock_persist_single_lead.call_args_list,
            [call(model.form_entry.to_form_data())],
        )
