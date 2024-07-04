from datetime import timedelta
import random
from unittest.mock import MagicMock, call, patch
import breathecode.marketing.tasks as tasks
from breathecode.marketing.management.commands.retry_pending_leads import Command
from django.utils import timezone
from breathecode.marketing.tests.mixins import MarketingTestCase

UTC_NOW = timezone.now()


def serialize_form_entry(form_entry):
    return {
        "id": form_entry["id"],
        "first_name": form_entry["first_name"],
        "last_name": form_entry["last_name"],
        "phone": form_entry["phone"],
        "email": form_entry["email"],
        "location": form_entry["location"],
        "referral_key": form_entry["referral_key"],
        "course": form_entry["course"],
        "tags": form_entry["tags"],
        "automations": form_entry["automations"],
        "language": form_entry["language"],
        "city": form_entry["city"],
        "country": form_entry["country"],
        "utm_url": form_entry["utm_url"],
        "client_comments": form_entry["client_comments"],
        "current_download": form_entry["current_download"],
        "latitude": form_entry["latitude"],
        "longitude": form_entry["longitude"],
    }


class RetryPendingLeadsTestSuite(MarketingTestCase):
    """
    🔽🔽🔽 With no form entries
    """

    @patch("breathecode.marketing.tasks.persist_single_lead.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_without_formentries(self):
        command = Command()
        command.handle()

        self.assertEqual(self.bc.database.list_of("marketing.FormEntry"), [])
        self.assertEqual(tasks.persist_single_lead.delay.call_args_list, [])

    """
    🔽🔽🔽 With form entries not pending
    """

    @patch("breathecode.marketing.tasks.persist_single_lead.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_without_pending_formentries(self):
        model = self.bc.database.create(
            form_entry=[{"storage_status": "PERSISTED"}, {"storage_status": "PERSISTED"}],
        )
        command = Command()
        command.handle()

        self.assertEqual(self.bc.database.list_of("marketing.FormEntry"), self.bc.format.to_dict(model.form_entry))
        self.assertEqual(tasks.persist_single_lead.delay.call_args_list, [])

    """
    🔽🔽🔽 With form entries pending
    """

    @patch("breathecode.marketing.tasks.persist_single_lead.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_with_pending_formentries(self):
        model = self.bc.database.create(
            form_entry={"storage_status": "PENDING"},
        )
        command = Command()
        result = command.handle()

        model_dict = self.bc.format.to_dict(model.form_entry)

        self.assertEqual(self.bc.database.list_of("marketing.FormEntry"), self.bc.format.to_dict([model.form_entry]))
        self.assertEqual(tasks.persist_single_lead.delay.call_args_list, [call(serialize_form_entry(model_dict))])

    """
    🔽🔽🔽 With two form entries
    """

    @patch("breathecode.marketing.tasks.persist_single_lead.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_with_two_formentries(self):
        model = self.bc.database.create(
            form_entry=[{"storage_status": "PENDING"}, {"storage_status": "PERSISTED"}],
        )
        command = Command()
        result = command.handle()

        model_dict = self.bc.format.to_dict(model.form_entry)
        serialize_model = [serialize_form_entry(dict) for dict in model_dict]

        self.assertEqual(self.bc.database.list_of("marketing.FormEntry"), self.bc.format.to_dict(model.form_entry))
        self.assertEqual(tasks.persist_single_lead.delay.call_args_list, [call(serialize_form_entry(model_dict[0]))])
