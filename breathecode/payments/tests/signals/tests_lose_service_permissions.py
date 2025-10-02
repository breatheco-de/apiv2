import random

from breathecode.payments import signals
from breathecode.tests.mixins.legacy import LegacyAPITestCase
from breathecode.payments.models import SubscriptionBillingTeam, SubscriptionSeat, Consumable


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

    def test__seat_consumable_zero__team_shared_consumable__keep_group(self, enable_signals):
        """Seat consumable hits 0, but team has a shared consumable (user=None) -> keep group."""
        services = [{"groups": [1]}]
        service_items = [{"service_id": 1}]

        # Base models
        model = self.bc.database.create(
            user=1,
            group=1,
            service=services,
            service_item=service_items,
            subscription=1,
        )

        team = SubscriptionBillingTeam.objects.create(
            subscription=model.subscription,
            name="Team 1",
            consumption_strategy=SubscriptionBillingTeam.ConsumptionStrategy.PER_TEAM,
        )
        seat = SubscriptionSeat.objects.create(billing_team=team, user=model.user, email=model.user.email)

        # Seat consumable that reached 0
        seat_consumable = self.bc.database.create(
            consumable={
                "how_many": 0,
                "user_id": model.user.id,
                "service_item_id": model.service_item.id,
                "subscription_seat_id": seat.id,
            }
        ).consumable

        # Create a team-level consumable and then remove the user to emulate shared team pool
        team_consumable = self.bc.database.create(
            consumable={
                "how_many": 4,
                "user_id": model.user.id,  # create with user to pass model validation
                "subscription_billing_team_id": team.id,
                "service_item_id": model.service_item.id,
            }
        ).consumable

        # Bypass validation to set user=None (shared by team)
        Consumable.objects.filter(id=team_consumable.id).update(user=None)

        # Initial group membership
        model.user.groups.add(model.group)

        enable_signals()
        # Act
        signals.lose_service_permissions.send(sender=seat_consumable.__class__, instance=seat_consumable)

        # Assert: group is kept because team shared consumable exists
        self.bc.check.queryset_with_pks(model.user.groups.all(), [1])

    def test__seat_consumable_zero__team_shared_consumable_per_seat__remove_group(self, enable_signals):
        """Seat consumable hits 0, team has a shared consumable but strategy PER_SEAT -> remove group."""
        services = [{"groups": [1]}]
        service_items = [{"service_id": 1}]

        model = self.bc.database.create(
            user=1,
            group=1,
            service=services,
            service_item=service_items,
            subscription=1,
        )

        # PER_SEAT strategy
        team = SubscriptionBillingTeam.objects.create(
            subscription=model.subscription,
            name="Team 1",
            consumption_strategy=SubscriptionBillingTeam.ConsumptionStrategy.PER_SEAT,
        )
        seat = SubscriptionSeat.objects.create(billing_team=team, user=model.user, email=model.user.email)

        # Seat consumable that reached 0
        seat_consumable = self.bc.database.create(
            consumable={
                "how_many": 0,
                "user_id": model.user.id,
                "service_item_id": model.service_item.id,
                "subscription_seat_id": seat.id,
            }
        ).consumable

        # Team shared consumable (user=None) which must be ignored for PER_SEAT
        team_consumable = self.bc.database.create(
            consumable={
                "how_many": 4,
                "user_id": model.user.id,
                "subscription_billing_team_id": team.id,
                "service_item_id": model.service_item.id,
            }
        ).consumable
        Consumable.objects.filter(id=team_consumable.id).update(user=None)

        # initial membership
        model.user.groups.add(model.group)

        enable_signals()
        signals.lose_service_permissions.send(sender=seat_consumable.__class__, instance=seat_consumable)

        # Since strategy is PER_SEAT, shared pool should be ignored and group removed
        self.bc.check.queryset_with_pks(model.user.groups.all(), [])

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
    🔽🔽🔽 Seats and Billing Teams interactions
    """

    def test__seat_consumable_zero__team_has_other_valid__keep_group(self, enable_signals):
        """When seat consumable reaches 0, but the team has a valid (non-zero) consumable for same service, keep group."""

        # Arrange (signals enabled later to avoid grant on creation for team/userless consumables)
        services = [{"groups": [1]}]
        service_items = [{"service_id": 1}]

        # Create base models
        model = self.bc.database.create(
            user=1,
            group=1,
            service=services,
            service_item=service_items,
            subscription=1,
        )

        # Create billing team and seat via ORM (generator doesn't support these keys yet)
        team = SubscriptionBillingTeam.objects.create(subscription=model.subscription, name="Team 1")
        seat = SubscriptionSeat.objects.create(billing_team=team, user=model.user, email=model.user.email)

        # Seat consumable that reached 0
        seat_consumable = self.bc.database.create(
            consumable={
                "how_many": 0,
                "user_id": model.user.id,
                "service_item_id": model.service_item.id,
                "subscription_seat_id": seat.id,
            }
        ).consumable

        # Team-level consumable still valid (non-zero) for the same service and same team
        _ = self.bc.database.create(
            consumable={
                "how_many": 5,
                "user_id": model.user.id,
                "subscription_billing_team_id": team.id,
                "service_item_id": model.service_item.id,
            }
        ).consumable

        # simulate that user already has the group (granted previously)
        model.user.groups.add(model.group)

        # Enable signals now and trigger lose permissions for the seat consumable
        enable_signals()
        # Act
        signals.lose_service_permissions.send(sender=seat_consumable.__class__, instance=seat_consumable)

        # Assert: user must keep the group because there is a valid team consumable
        self.bc.check.queryset_with_pks(model.user.groups.all(), [1])

    def test__seat_consumable_zero__other_team_has_valid__remove_group(self, enable_signals):
        """When seat consumable reaches 0, and other team (different billing team) has consumables, remove group."""
        services = [{"groups": [1]}]
        service_items = [{"service_id": 1}]

        # Base models
        model = self.bc.database.create(
            user=1,
            group=1,
            service=services,
            service_item=service_items,
            subscription=1,
        )

        # Two billing teams; seat belongs to team1
        team1 = SubscriptionBillingTeam.objects.create(subscription=model.subscription, name="Team 1")
        # create a second subscription to attach a different team (OneToOne with subscription)
        model2 = self.bc.database.create(subscription=1)
        team2 = SubscriptionBillingTeam.objects.create(subscription=model2.subscription, name="Team 2")
        seat = SubscriptionSeat.objects.create(billing_team=team1, user=model.user, email=model.user.email)

        # Seat consumable that reached 0
        seat_consumable = self.bc.database.create(
            consumable={
                "how_many": 0,
                "user_id": model.user.id,
                "service_item_id": model.service_item.id,
                "subscription_seat_id": seat.id,
            }
        ).consumable

        # Team-level consumable valid but for a different team (team 2) and different user
        other_user = self.bc.database.create(user=1).user
        _ = self.bc.database.create(
            consumable={
                "how_many": 3,
                "user_id": other_user.id,
                "subscription_billing_team_id": team2.id,  # other team
                "service_item_id": model.service_item.id,
            }
        ).consumable

        # user starts with the group
        model.user.groups.add(model.group)

        enable_signals()
        # Act
        signals.lose_service_permissions.send(sender=seat_consumable.__class__, instance=seat_consumable)

        # Assert: user must lose the group because team consumable is not from the same team
        self.bc.check.queryset_with_pks(model.user.groups.all(), [])

    def test__seat_consumable_zero__other_seat_has_valid__keep_group(self, enable_signals):
        """When seat consumable reaches 0, but another non-zero consumable for the same seat exists, keep group."""
        services = [{"groups": [1]}]
        service_items = [{"service_id": 1}]

        model = self.bc.database.create(
            user=1,
            group=1,
            service=services,
            service_item=service_items,
            subscription=1,
        )

        team = SubscriptionBillingTeam.objects.create(subscription=model.subscription, name="Team 1")
        seat = SubscriptionSeat.objects.create(billing_team=team, user=model.user, email=model.user.email)

        # Seat consumable that reached 0
        seat_consumable_zero = self.bc.database.create(
            consumable={
                "how_many": 0,
                "user_id": model.user.id,
                "service_item_id": model.service_item.id,
                "subscription_seat_id": seat.id,
            }
        ).consumable

        # Another seat consumable valid for same seat and service
        _ = self.bc.database.create(
            consumable={
                "how_many": 2,
                "user_id": model.user.id,
                "service_item_id": model.service_item.id,
                "subscription_seat_id": seat.id,
            }
        ).consumable

        # Initial group membership present
        model.user.groups.add(model.group)

        enable_signals()
        # Act
        signals.lose_service_permissions.send(sender=seat_consumable_zero.__class__, instance=seat_consumable_zero)

        # Assert: user must keep the group because there is another valid seat consumable
        self.bc.check.queryset_with_pks(model.user.groups.all(), [1])

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
