import random

from breathecode.payments import signals
from breathecode.tests.mixins.legacy import LegacyAPITestCase


class TestSignal(LegacyAPITestCase):
    """
    🔽🔽🔽 With one Consumable and User
    """

    def test__with_consumable(self, enable_signals):
        enable_signals()

        how_many = -1
        consumable = {"how_many": how_many}
        model = self.bc.database.create(consumable=consumable)
        consumable_db = self.bc.format.to_dict(model.consumable)

        signals.lose_service_permissions.send(sender=model.consumable.__class__, instance=model.consumable)

        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                {
                    **consumable_db,
                    "how_many": how_many,
                },
            ],
        )
        self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])
        self.bc.check.queryset_with_pks(model.user.groups.all(), [])
        self.assertEqual(self.bc.database.list_of("auth.Group"), [])

    """
    🔽🔽🔽 With one Consumable, User and Group
    """

    def test__with_consumable__with_group(self, enable_signals):
        enable_signals()

        how_many = -1
        consumable = {"how_many": how_many}
        model = self.bc.database.create(consumable=consumable, group=1)
        consumable_db = self.bc.format.to_dict(model.consumable)

        signals.lose_service_permissions.send(sender=model.consumable.__class__, instance=model.consumable)

        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                {
                    **consumable_db,
                    "how_many": how_many,
                },
            ],
        )
        self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])
        self.bc.check.queryset_with_pks(model.user.groups.all(), [1])
        self.assertEqual(self.bc.database.list_of("auth.Group"), [self.bc.format.to_dict(model.group)])

    """
    🔽🔽🔽 With two Consumable(how_many=-1), User and Group
    """

    def test__with_two_consumables__with_group__how_many_minus_1(self, enable_signals):
        enable_signals()

        how_many = -1
        consumable = {"how_many": how_many}
        model = self.bc.database.create(consumable=(2, consumable), group=1)
        consumable_db = self.bc.format.to_dict(model.consumable)

        signals.lose_service_permissions.send(sender=model.consumable[0].__class__, instance=model.consumable[0])

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), consumable_db)
        self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])
        self.bc.check.queryset_with_pks(model.user.groups.all(), [1])
        self.assertEqual(self.bc.database.list_of("auth.Group"), [self.bc.format.to_dict(model.group)])

    """
    🔽🔽🔽 With two Consumable(how_many__gte=1), User and Group
    """

    def test__with_two_consumables__with_group__how_many_gte_1(self, enable_signals):
        enable_signals()

        how_many = random.randint(1, 100)
        consumable = {"how_many": how_many}
        model = self.bc.database.create(consumable=(2, consumable), group=1)
        consumable_db = self.bc.format.to_dict(model.consumable)

        signals.lose_service_permissions.send(sender=model.consumable[0].__class__, instance=model.consumable[0])

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), consumable_db)
        self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])
        self.bc.check.queryset_with_pks(model.user.groups.all(), [1])
        self.assertEqual(self.bc.database.list_of("auth.Group"), [self.bc.format.to_dict(model.group)])

    """
    🔽🔽🔽 With two Consumable(how_many=0), User and Group
    """

    def test__with_two_consumables__with_group__how_many_0(self, enable_signals):
        enable_signals()

        how_many = 0
        consumable = {"how_many": how_many}
        model = self.bc.database.create(consumable=(2, consumable), group=1)
        consumable_db = self.bc.format.to_dict(model.consumable)

        signals.lose_service_permissions.send(sender=model.consumable[0].__class__, instance=model.consumable[0])

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), consumable_db)
        self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])
        self.bc.check.queryset_with_pks(model.user.groups.all(), [])
        self.assertEqual(self.bc.database.list_of("auth.Group"), [self.bc.format.to_dict(model.group)])

    """
    🔽🔽🔽 With two Consumable[(how_many=0), (how_many__gte=1)], User and Group
    """

    def test__with_two_consumables__with_group__first_with_how_many_0__second_with_how_many_gte_1(self, enable_signals):
        enable_signals()

        first_how_many = 0
        second_how_many = random.randint(1, 100)
        consumables = [{"how_many": n} for n in [first_how_many, second_how_many]]
        model = self.bc.database.create(consumable=consumables, group=1)
        consumable_db = self.bc.format.to_dict(model.consumable)

        signals.lose_service_permissions.send(sender=model.consumable[0].__class__, instance=model.consumable[0])

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), consumable_db)
        self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])
        self.bc.check.queryset_with_pks(model.user.groups.all(), [1])
        self.assertEqual(self.bc.database.list_of("auth.Group"), [self.bc.format.to_dict(model.group)])

    """
    🔽🔽🔽 With two Consumable[(how_many=0), ...(how_many__gte=1)], User and Group
    """

    def test__with_two_consumables__with_group__first_with_how_many_0__rest_with_how_many_gte_1(self, enable_signals):
        enable_signals()

        length = random.randint(2, 5)
        consumables = [{"how_many": 0 if n == 0 else random.randint(1, 100)} for n in range(length)]
        model = self.bc.database.create(consumable=consumables, group=1)
        consumable_db = self.bc.format.to_dict(model.consumable)

        signals.lose_service_permissions.send(sender=model.consumable[0].__class__, instance=model.consumable[0])

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), consumable_db)
        self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])
        self.bc.check.queryset_with_pks(model.user.groups.all(), [1])
        self.assertEqual(self.bc.database.list_of("auth.Group"), [self.bc.format.to_dict(model.group)])

    """
    🔽🔽🔽 With two Consumable[(how_many=0), (how_many=-1)], User and Group
    """

    def test__with_two_consumables__with_group__first_with_how_many_0__second_with_how_many_minus_1(
        self, enable_signals
    ):
        enable_signals()

        first_how_many = 0
        second_how_many = -1
        consumables = [{"how_many": n} for n in [first_how_many, second_how_many]]
        model = self.bc.database.create(consumable=consumables, group=1)
        consumable_db = self.bc.format.to_dict(model.consumable)

        signals.lose_service_permissions.send(sender=model.consumable[0].__class__, instance=model.consumable[0])

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), consumable_db)
        self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])
        self.bc.check.queryset_with_pks(model.user.groups.all(), [1])
        self.assertEqual(self.bc.database.list_of("auth.Group"), [self.bc.format.to_dict(model.group)])

    """
    🔽🔽🔽 With two Consumable[(how_many=0), ...(how_many=-1)], User and Group
    """

    def test__with_two_consumables__with_group__first_with_how_many_0__rest_with_how_many_minus_1(self, enable_signals):
        enable_signals()

        length = random.randint(2, 5)
        consumables = [{"how_many": 0 if n == 0 else -1} for n in range(length)]
        model = self.bc.database.create(consumable=consumables, group=1)
        consumable_db = self.bc.format.to_dict(model.consumable)

        signals.lose_service_permissions.send(sender=model.consumable[0].__class__, instance=model.consumable[0])

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), consumable_db)
        self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])
        self.bc.check.queryset_with_pks(model.user.groups.all(), [1])
        self.assertEqual(self.bc.database.list_of("auth.Group"), [self.bc.format.to_dict(model.group)])

    """
    🔽🔽🔽 With two Consumable[(how_many=0), (how_many=-1)], User and Group
    """

    def test__with_two_consumables__with_group__first_with_how_many_0__second_with_how_many_0(self, enable_signals):
        enable_signals()

        first_how_many = 0
        second_how_many = 0
        consumables = [{"how_many": n} for n in [first_how_many, second_how_many]]
        model = self.bc.database.create(consumable=consumables, group=1)
        consumable_db = self.bc.format.to_dict(model.consumable)

        signals.lose_service_permissions.send(sender=model.consumable[0].__class__, instance=model.consumable[0])

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), consumable_db)
        self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])
        self.bc.check.queryset_with_pks(model.user.groups.all(), [])
        self.assertEqual(self.bc.database.list_of("auth.Group"), [self.bc.format.to_dict(model.group)])

    """
    🔽🔽🔽 With two Consumable[(how_many=0), ...(how_many=-1)], User and Group
    """

    def test__with_two_consumables__with_group__first_with_how_many_0__rest_with_how_many_0(self, enable_signals):
        enable_signals()

        length = random.randint(2, 5)
        consumables = [{"how_many": 0 if n == 0 else 0} for n in range(length)]
        model = self.bc.database.create(consumable=consumables, group=1)
        consumable_db = self.bc.format.to_dict(model.consumable)

        signals.lose_service_permissions.send(sender=model.consumable[0].__class__, instance=model.consumable[0])

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), consumable_db)
        self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])
        self.bc.check.queryset_with_pks(model.user.groups.all(), [])
        self.assertEqual(self.bc.database.list_of("auth.Group"), [self.bc.format.to_dict(model.group)])

    """
    🔽🔽🔽 With two Consumable[(how_many=0, service=1), ...(how_many=0, service=2)], one User, two
    Group and Service[(groups=[1]), (groups=[2])]
    """

    def test__with_two_consumables__with_two_group__first_with_how_many_0__rest_with_how_many_0(self, enable_signals):
        enable_signals()

        length = random.randint(2, 5)
        consumables = [
            {
                "how_many": 0 if n == 0 else 0,
                "service_item_id": 1 if n == 0 else 2,
            }
            for n in range(length)
        ]
        services = [
            {
                "groups": [1] if n == 0 else [2],
            }
            for n in range(length)
        ]
        service_items = [{"service_id": x} for x in range(1, 3)]
        model = self.bc.database.create(consumable=consumables, group=2, service=services, service_item=service_items)
        consumable_db = self.bc.format.to_dict(model.consumable)

        signals.lose_service_permissions.send(sender=model.consumable[0].__class__, instance=model.consumable[0])

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), consumable_db)
        self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])
        self.bc.check.queryset_with_pks(model.user.groups.all(), [2])
        self.assertEqual(self.bc.database.list_of("auth.Group"), self.bc.format.to_dict(model.group))

    """
    🔽🔽🔽 With two Consumable[(how_many=0, service=1), ...(how_many=-1, service=2)], one User, two
    Group and Service[(groups=[1]), (groups=[2])]
    """

    def test__with_two_consumables__with_two_group__first_with_how_many_0__rest_with_how_many_minus_1(
        self, enable_signals
    ):
        enable_signals()

        length = random.randint(2, 5)
        consumables = [
            {
                "how_many": 0 if n == 0 else -1,
                "service_item_id": 1 if n == 0 else 2,
            }
            for n in range(length)
        ]
        services = [
            {
                "groups": [1] if n == 0 else [2],
            }
            for n in range(length)
        ]
        service_items = [{"service_id": x} for x in range(1, 3)]
        model = self.bc.database.create(consumable=consumables, group=2, service=services, service_item=service_items)
        consumable_db = self.bc.format.to_dict(model.consumable)

        signals.lose_service_permissions.send(sender=model.consumable[0].__class__, instance=model.consumable[0])

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), consumable_db)
        self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])
        self.bc.check.queryset_with_pks(model.user.groups.all(), [2])
        self.assertEqual(self.bc.database.list_of("auth.Group"), self.bc.format.to_dict(model.group))

    """
    🔽🔽🔽 With two Consumable[(how_many=0, service=1), ...(how_many__gte=1, service=2)], one User, two
    Group and Service[(groups=[1]), (groups=[2])]
    """

    def test__with_two_consumables__with_two_group__first_with_how_many_0__rest_with_how_many_gte_1(
        self, enable_signals
    ):
        enable_signals()

        length = random.randint(2, 5)
        consumables = [
            {
                "how_many": 0 if n == 0 else random.randint(1, 100),
                "service_item_id": 1 if n == 0 else 2,
            }
            for n in range(length)
        ]
        services = [
            {
                "groups": [1] if n == 0 else [2],
            }
            for n in range(length)
        ]
        service_items = [{"service_id": x} for x in range(1, 3)]
        model = self.bc.database.create(consumable=consumables, group=2, service=services, service_item=service_items)
        consumable_db = self.bc.format.to_dict(model.consumable)

        signals.lose_service_permissions.send(sender=model.consumable[0].__class__, instance=model.consumable[0])

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), consumable_db)
        self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])
        self.bc.check.queryset_with_pks(model.user.groups.all(), [2])
        self.assertEqual(self.bc.database.list_of("auth.Group"), self.bc.format.to_dict(model.group))
