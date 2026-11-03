"""Timeout retry must not treat an already-created AC contact as a full resend."""

from unittest.mock import patch

from requests.exceptions import Timeout

from breathecode.marketing.models import FormEntry
from breathecode.marketing.tasks import persist_single_lead
from breathecode.marketing.tests.tasks.tests_persist_single_lead import generate_form_entry_kwargs

from ..mixins import MarketingTestCase


class PersistSingleLeadTimeoutTestSuite(MarketingTestCase):
    def _run_timeout(self, form_entry):
        # task_manager swallows RetryTask and schedules a reattempt
        with patch("breathecode.marketing.tasks.register_new_lead", side_effect=Timeout("Read timed out")):
            persist_single_lead.delay({"id": form_entry.id})
        return FormEntry.objects.get(id=form_entry.id)

    def test_timeout_with_ac_contact_id_stays_pending_and_retries(self):
        model = self.generate_models(
            academy=True,
            form_entry=generate_form_entry_kwargs(
                {
                    "storage_status": "PENDING",
                    "ac_contact_id": "304357",
                    "course": "full-stack",
                }
            ),
        )

        entry = self._run_timeout(model.form_entry)

        self.assertEqual(entry.storage_status, "PENDING")
        self.assertEqual(entry.ac_contact_id, "304357")
        self.assertIn("timed out", entry.storage_status_text.lower())

    def test_timeout_without_ac_contact_id_stays_pending_and_retries(self):
        model = self.generate_models(
            academy=True,
            form_entry=generate_form_entry_kwargs(
                {
                    "storage_status": "PENDING",
                    "ac_contact_id": None,
                    "course": "full-stack",
                }
            ),
        )

        entry = self._run_timeout(model.form_entry)

        self.assertEqual(entry.storage_status, "PENDING")
        self.assertIsNone(entry.ac_contact_id)
        self.assertIn("timed out", entry.storage_status_text.lower())
