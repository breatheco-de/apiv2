from datetime import timedelta
import random
from unittest.mock import MagicMock, call, patch
import breathecode.marketing.tasks as tasks
from breathecode.marketing.management.commands.retry_pending_leads import Command
from django.utils import timezone
from breathecode.marketing.tests.mixins import MarketingTestCase

UTC_NOW = timezone.now()


class RetryPendingLeadsTestSuite(MarketingTestCase):
    """
    🔽🔽🔽 With no form entries
    """

    def test_without_formentries(self):
        command = Command()
        command.handle()

        self.assertEqual(self.bc.database.list_of('marketing.FormEntry'), [])

    """
    🔽🔽🔽 With form entries not pending
    """

    def test_without_pending_formentries(self):
        model = self.bc.database.create(
            form_entry=2,
            form_entry_kwargs={'storage_status': 'PERSISTED'},
        )
        command = Command()
        command.handle()

        self.assertEqual(self.bc.database.list_of('marketing.FormEntry'),
                         self.bc.format.to_dict(model.form_entry))

    """
    🔽🔽🔽 With form entries pending
    """

    def test_with_pending_formentries(self):
        model = self.bc.database.create(
            form_entry=2,
            form_entry_kwargs={'storage_status': 'PENDING'},
        )
        command = Command()
        result = command.handle()

        print('result')
        for item in self.bc.format.to_dict(model.form_entry):
            print(item['id'])
            print(item['storage_status'])

        self.assertEqual(self.bc.database.list_of('marketing.FormEntry'),
                         self.bc.format.to_dict(model.form_entry))
