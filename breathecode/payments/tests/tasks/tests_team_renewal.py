from unittest.mock import MagicMock, patch

from ..mixins import PaymentsTestCase
from breathecode.payments import tasks


class TestTeamRenewalTask(PaymentsTestCase):
    @patch("breathecode.payments.actions.create_team_member_consumables", MagicMock())
    @patch("breathecode.payments.actions.revoke_team_member_consumables", MagicMock())
    def test_renew_team_member_consumables_idempotent(self):
        model = self.bc.database.create(user=1, academy=1)
        service = self.bc.database.create(service=1).service
        group = self.bc.database.create(group=1).group
        user2 = self.bc.database.create(user=1).user

        service_item = self.bc.database.create(
            service_item={
                "service": service,
                "is_team_allowed": True,
                "team_group": group,
                "team_consumables": {
                    "allowed": [{"service_slug": service.slug, "unit_type": "UNIT", "renew_at_unit": "MONTH"}]
                },
            }
        ).service_item

        subscription = self.bc.database.create(subscription={"user": model.user, "academy": model.academy}).subscription
        seat = self.bc.database.create(
            subscription_seat={"subscription": subscription, "service_item": service_item, "user": user2}
        ).subscription_seat

        tasks.renew_team_member_consumables.delay(subscription.id)

        # called once per seat
        assert tasks.revoke_team_member_consumables.called
        assert tasks.create_team_member_consumables.called
