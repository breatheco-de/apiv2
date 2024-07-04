import random
from unittest.mock import MagicMock, patch, call
from ...mixins.provisioning_test_case import ProvisioningTestCase
from ....management.commands.archive_provisioning_bills import Command
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from breathecode.provisioning.tasks import archive_provisioning_bill

from django.core.management.base import OutputWrapper

UTC_NOW = timezone.now()


class AcademyCohortTestSuite(ProvisioningTestCase):
    """
    🔽🔽🔽 With zero Profile
    """

    # When: No bills
    # Then: doesn't do anything
    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    @patch("breathecode.provisioning.tasks.archive_provisioning_bill.delay", MagicMock())
    def test_0_ibills(self):
        command = Command()
        result = command.handle()

        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningBill"), [])
        self.assertEqual(
            OutputWrapper.write.call_args_list,
            [
                call("No provisioning bills to clean"),
            ],
        )
        self.bc.check.calls(archive_provisioning_bill.delay.call_args_list, [])

    # Given: 1 ProvisioningBill
    # When: it's paid, not archived but paid_at is less than 1 month ago
    # Then: doesn't do anything
    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.provisioning.tasks.archive_provisioning_bill.delay", MagicMock())
    def test__bill__requirements_not_meet(self):
        provisioning_bills = [
            {
                "status": "PAID",
                "paid_at": self.bc.datetime.now() - relativedelta(months=1) + relativedelta(days=random.randint(1, 28)),
                "archived_at": None,
            }
            for _ in range(2)
        ]
        model = self.bc.database.create(provisioning_bill=provisioning_bills)

        command = Command()
        result = command.handle()

        self.assertEqual(result, None)
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"), self.bc.format.to_dict(model.provisioning_bill)
        )

        self.assertEqual(
            OutputWrapper.write.call_args_list,
            [
                call("No provisioning bills to clean"),
            ],
        )
        self.bc.check.calls(archive_provisioning_bill.delay.call_args_list, [])

    # Given: 1 ProvisioningBill
    # When: it's paid, not archived and paid_at is more than 1 month ago
    # Then: archive it
    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.provisioning.tasks.archive_provisioning_bill.delay", MagicMock())
    def test_1_bill__requirements_meet(self):
        provisioning_bills = [
            {
                "status": "PAID",
                "paid_at": self.bc.datetime.now() - relativedelta(months=1, days=1),
                "archived_at": None,
            }
            for _ in range(2)
        ]
        model = self.bc.database.create(provisioning_bill=provisioning_bills)

        command = Command()
        result = command.handle()

        self.assertEqual(result, None)
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                {
                    **self.bc.format.to_dict(model.provisioning_bill[0]),
                },
                {
                    **self.bc.format.to_dict(model.provisioning_bill[1]),
                },
            ],
        )
        self.assertEqual(
            OutputWrapper.write.call_args_list,
            [
                call("Cleaning 1, 2 provisioning bills"),
            ],
        )

        self.bc.check.calls(archive_provisioning_bill.delay.call_args_list, [call(1), call(2)])
