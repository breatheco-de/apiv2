import pytest
from django.contrib.auth.models import Group

from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException

from ..mixins import PaymentsTestCase


class TestTeamModels(PaymentsTestCase):
    def test_serviceitem_clean_requires_team_group_when_enabled(self):
        service = self.bc.database.create(service=1).service

        # is_team_allowed without team_group -> invalid
        with pytest.raises(Exception):
            self.bc.database.create(
                service_item={
                    "service": service,
                    "is_team_allowed": True,
                    "team_group": None,
                    "team_consumables": {"allowed": []},
                },
            )

        # valid with team_group and allowed entries
        group = Group.objects.create(name="Team Group")
        self.bc.database.create(
            service_item={
                "service": service,
                "is_team_allowed": True,
                "team_group": group,
                "team_consumables": {
                    "allowed": [{"service_slug": service.slug, "unit_type": "UNIT", "renew_at_unit": "MONTH"}]
                },
            },
        )

    def test_consumable_clean_team_checks(self):
        # setup user, group, service and service_item with team enabled
        model = self.bc.database.create(user=1)
        group = Group.objects.create(name="Team Group")
        service = self.bc.database.create(service=1).service
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

        # user not in group -> adding team_member consumable must error
        with pytest.raises(Exception):
            self.bc.database.create(
                consumable={"service_item": service_item, "user": model.user, "team_member": None},
            )

        # add user to group -> valid
        model.user.groups.add(group)
        self.bc.database.create(consumable={"service_item": service_item, "user": model.user})
