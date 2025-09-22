from unittest.mock import MagicMock, patch


def make_group(name, pk=1):
    """Build a fake Django Group-like object with name and pk."""
    g = MagicMock()
    g.name = name
    g.pk = pk
    return g


def make_instance(how_many=1, user=True, groups=None, subscription_seat=False, subscription_billing_team=None):
    """Build a minimal fake Consumable instance for the receiver."""
    if groups is None:
        groups = [make_group("g1", 1), make_group("g2", 2)]

    inst = MagicMock()
    inst.how_many = how_many

    # service groups
    service = MagicMock()
    service.groups.all.return_value = groups
    service_item = MagicMock()
    service_item.service = service
    inst.service_item = service_item

    # user or team
    inst.user = MagicMock() if user else None
    if inst.user:
        # user.groups.filter(name=...).exists() => False by default
        inst.user.groups.filter.return_value.exists.return_value = False
    if subscription_seat:
        seat = MagicMock()
        # when seat exists, receiver resolves user from seat.user
        seat.user = inst.user
        # allow access to billing_team via seat
        seat.billing_team = MagicMock()
        inst.subscription_seat = seat
    else:
        inst.subscription_seat = None

    inst.subscription_billing_team = subscription_billing_team
    return inst


@patch("breathecode.payments.receivers.SubscriptionSeat")
def test_ignore_when_how_many_not_positive(mock_seat):
    """Does nothing when instance.how_many <= 0 (no grants, no seat queries)."""
    from breathecode.payments.receivers import grant_service_permissions_receiver

    inst = make_instance(how_many=0, user=True)

    grant_service_permissions_receiver(sender=type(inst), instance=inst)

    # No grants and no seat queries
    assert not inst.user.groups.add.called
    assert not mock_seat.objects.filter.called


def test_grant_user_when_how_many_positive():
    """Grants all service groups to the resolved user when how_many > 0."""
    from breathecode.payments.receivers import grant_service_permissions_receiver

    inst = make_instance(how_many=2, user=True)

    grant_service_permissions_receiver(sender=type(inst), instance=inst)

    # Should add both groups to user
    assert inst.user.groups.add.call_count == 2


@patch("breathecode.payments.receivers.SubscriptionSeat")
def test_team_shared_per_team_grants_all_seat_users(mock_seat):
    """With team-shared consumable and PER_TEAM strategy, grant to all seat users in the team."""
    from breathecode.payments.receivers import grant_service_permissions_receiver
    from breathecode.payments.models import SubscriptionBillingTeam

    team = MagicMock()
    team.consumption_strategy = SubscriptionBillingTeam.ConsumptionStrategy.PER_TEAM

    # shared: user=None (instance.user is None), team set
    inst = make_instance(how_many=3, user=False, subscription_billing_team=team)

    # Prepare seats with users
    u1, u2 = MagicMock(), MagicMock()
    u1.groups.filter.return_value.exists.return_value = False
    u2.groups.filter.return_value.exists.return_value = False
    s1, s2 = MagicMock(), MagicMock()
    s1.user, s2.user = u1, u2

    q = MagicMock()
    q.select_related.return_value = [s1, s2]
    mock_seat.objects.filter.return_value = q

    grant_service_permissions_receiver(sender=type(inst), instance=inst)

    # Both users should receive the groups
    assert u1.groups.add.called
    assert u2.groups.add.called
    # Ensure we filtered by billing_team
    mock_seat.objects.filter.assert_called_once()
    kwargs = mock_seat.objects.filter.call_args.kwargs
    assert "billing_team" in kwargs
    assert kwargs["billing_team"] is team


@patch("breathecode.payments.receivers.SubscriptionSeat")
def test_team_shared_per_seat_ignored(mock_seat):
    """With team-shared consumable and PER_SEAT strategy, ignore (no grants, no seat lookup)."""
    from breathecode.payments.receivers import grant_service_permissions_receiver
    from breathecode.payments.models import SubscriptionBillingTeam

    team = MagicMock()
    team.consumption_strategy = SubscriptionBillingTeam.ConsumptionStrategy.PER_SEAT

    inst = make_instance(how_many=3, user=False, subscription_billing_team=team)

    grant_service_permissions_receiver(sender=type(inst), instance=inst)

    # No seat lookup performed and no grants
    assert not mock_seat.objects.filter.called


@patch("breathecode.payments.receivers.SubscriptionSeat")
def test_prefers_subscription_billing_team_over_seat_team(mock_seat):
    """Prefer instance.subscription_billing_team over seat.billing_team when both are present."""
    from breathecode.payments.receivers import grant_service_permissions_receiver
    from breathecode.payments.models import SubscriptionBillingTeam

    # Both seat and team are present, should prefer subscription_billing_team
    team_preferred = MagicMock()
    team_preferred.consumption_strategy = SubscriptionBillingTeam.ConsumptionStrategy.PER_TEAM

    inst = make_instance(how_many=3, user=False, subscription_seat=True, subscription_billing_team=team_preferred)

    q = MagicMock()
    q.select_related.return_value = []
    mock_seat.objects.filter.return_value = q

    grant_service_permissions_receiver(sender=type(inst), instance=inst)

    mock_seat.objects.filter.assert_called_once()
    kwargs = mock_seat.objects.filter.call_args.kwargs
    assert "billing_team" in kwargs
    assert kwargs["billing_team"] is team_preferred
