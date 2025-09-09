from unittest.mock import MagicMock, patch

import pytest

from capyc.rest_framework.exceptions import ValidationException

from ..mixins import PaymentsTestCase
from breathecode.payments import actions


class TestTeamActions(PaymentsTestCase):
    @patch("breathecode.payments.actions.notify_actions.send_email_message", MagicMock())
    def test_create_team_member_with_invite_capacity_and_duplicate(self):
        model = self.bc.database.create(user=1, academy=1)
        service = self.bc.database.create(service=1).service
        from django.contrib.auth.models import Group

        group = Group.objects.create(name="Team Group")

        plan = self.bc.database.create(plan={"owner": model.academy}).plan
        service_item = self.bc.database.create(
            service_item={
                "service": service,
                "is_team_allowed": True,
                "team_group": group,
                "max_team_members": 1,
                "team_consumables": {
                    "allowed": [{"service_slug": service.slug, "unit_type": "UNIT", "renew_at_unit": "MONTH"}]
                },
            }
        ).service_item
        plan.service_items.add(service_item)

        subscription = self.bc.database.create(subscription={"user": model.user, "academy": model.academy}).subscription

        # first invite ok
        inv = actions.create_team_member_with_invite(
            subscription=subscription,
            service_item=service_item,
            email="test@example.com",
            seats=1,
            author=model.user,
            lang="en",
        )
        assert inv.email == "test@example.com"

        # duplicate email blocked
        with pytest.raises(ValidationException):
            actions.create_team_member_with_invite(
                subscription=subscription,
                service_item=service_item,
                email="test@example.com",
                seats=1,
                author=model.user,
                lang="en",
            )

        # capacity full (1) -> another email blocked
        with pytest.raises(ValidationException):
            actions.create_team_member_with_invite(
                subscription=subscription,
                service_item=service_item,
                email="other@example.com",
                seats=1,
                author=model.user,
                lang="en",
            )

    def test_remove_team_member_revokes(self):
        model = self.bc.database.create(user=1, academy=1)
        service = self.bc.database.create(service=1).service
        from django.contrib.auth.models import Group

        group = Group.objects.create(name="Team Group")
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

        # add a team seat and consumable
        seat = self.bc.database.create(
            subscription_seat={"subscription": subscription, "service_item": service_item, "user": user2}
        ).subscription_seat
        consumable = self.bc.database.create(
            consumable={"subscription": subscription, "service_item": service_item, "user": user2}
        ).consumable
        assert consumable.how_many != 0

        actions.remove_team_member(
            subscription=subscription, service_item=service_item, user=user2, email=None, lang="en"
        )
        assert self.bc.database.get_model("payments.Consumable", consumable.id).how_many == 0
