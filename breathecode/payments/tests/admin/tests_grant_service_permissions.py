"""
Test /answer
"""

from django.utils import timezone

from breathecode.payments.admin import grant_service_permissions

from ..mixins import PaymentsTestCase

UTC_NOW = timezone.now()


class PaymentsTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 With Bag
    """

    def test_no_consumables(self):

        groups = [{"permissions": [1, 2]}, {"permissions": [3, 4]}]
        groups = [{"permissions": [1, 2]}, {"permissions": [3, 4]}]
        services = [{"groups": [1]}, {"groups": [2]}]
        service_items = [{"service_id": n + 1} for n in range(2)]
        model = self.bc.database.create(
            user=1, group=groups, permission=4, service_item=service_items, service=services
        )
        Consumable = self.bc.database.get_model("payments.Consumable")
        queryset = Consumable.objects.all()

        grant_service_permissions(None, None, queryset)

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])

    def test_with_consumables(self):
        groups = [{"permissions": [1, 2]}, {"permissions": [3, 4]}]
        services = [{"groups": [1]}, {"groups": [2]}]
        consumables = [{"service_item_id": 1}, {"service_item_id": 2}]
        service_items = [{"service_id": n + 1} for n in range(2)]
        model = self.bc.database.create(
            user=1, group=groups, permission=4, consumable=consumables, service_item=service_items, service=services
        )
        db = self.bc.format.to_dict(model.consumable)

        Consumable = self.bc.database.get_model("payments.Consumable")
        queryset = Consumable.objects.all()

        grant_service_permissions(None, None, queryset)

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), db)

        self.bc.check.queryset_with_pks(model.user.groups.all(), [1, 2])
