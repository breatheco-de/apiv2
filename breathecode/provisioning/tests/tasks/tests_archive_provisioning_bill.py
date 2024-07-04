import random
from logging import Logger
from unittest.mock import MagicMock, call, patch

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.provisioning.tasks import archive_provisioning_bill

from ..mixins.provisioning_test_case import ProvisioningTestCase

UTC_NOW = timezone.now()


class AcademyCohortTestSuite(ProvisioningTestCase):
    """
    🔽🔽🔽 With zero Profile
    """

    # When: No invites
    # Then: Shouldn't do anything
    @patch("logging.Logger.error", MagicMock())
    def test_0_bills(self):
        archive_provisioning_bill.delay(1)

        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningBill"), [])
        self.bc.check.calls(
            Logger.error.call_args_list,
            [
                call("Bill 1 not found or requirements not met", exc_info=True),
            ],
        )

    # Given: 2 UserInvite, 1 Academy
    # When: email is not validated and academy is not available as saas
    # Then: validate all emails
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.error", MagicMock())
    def test_2_bills__requirements_not_meet(self):
        hash = self.bc.fake.slug()
        provisioning_bill = {
            "status": "PAID",
            "paid_at": self.bc.datetime.now() - relativedelta(months=1) + relativedelta(days=random.randint(1, 28)),
            "archived_at": None,
            "hash": hash,
        }

        provisioning_user_consumption = {
            "hash": hash,
        }

        model = self.bc.database.create(
            provisioning_bill=provisioning_bill,
            provisioning_user_consumption=provisioning_user_consumption,
            provisioning_consumption_event=10,
        )

        # with self.assertRaisesMessage(AbortTask, 'Bill 1 not found or requirements not met'):
        archive_provisioning_bill.delay(1)

        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                self.bc.format.to_dict(model.provisioning_bill),
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"),
            self.bc.format.to_dict(model.provisioning_consumption_event),
        )

        self.bc.check.calls(
            Logger.error.call_args_list,
            [
                call("Bill 1 not found or requirements not met", exc_info=True),
            ],
        )

    # Given: 2 UserInvite, 1 Academy, 1 Cohort
    # When: email is not validated and cohort from an academy is not available as saas
    # Then: validate all emails
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.error", MagicMock())
    def test_2_bills__requirements_meet(self):
        hash = self.bc.fake.slug()
        provisioning_bill = {
            "status": "PAID",
            "paid_at": self.bc.datetime.now() - relativedelta(months=1, days=1),
            "archived_at": None,
            "hash": hash,
        }

        provisioning_user_consumption = {
            "hash": hash,
        }

        model = self.bc.database.create(
            provisioning_bill=provisioning_bill,
            provisioning_user_consumption=provisioning_user_consumption,
            provisioning_consumption_event=10,
        )

        archive_provisioning_bill.delay(1)

        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                {
                    **self.bc.format.to_dict(model.provisioning_bill),
                    "archived_at": UTC_NOW,
                },
            ],
        )

        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningConsumptionEvent"), [])

        self.bc.check.calls(Logger.error.call_args_list, [])
