"""Tests for SubscriptionBillingTeamView (v2).

Covers the real ORM and view path with a single DB-backed integration test
to ensure correct team payload and aggregated seats_count.
"""

import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status

from breathecode.admissions.models import Country, City, Academy
from breathecode.payments.models import Subscription, SubscriptionBillingTeam, SubscriptionSeat


@pytest.mark.django_db
def test_get_ok_integration_db(client):
    """Integration: GET returns billing team details with aggregated seats_count."""
    # Arrange minimal valid data
    country = Country.objects.create(code="US", name="United States")
    city = City.objects.create(name="Miami", country=country)
    academy = Academy.objects.create(
        slug="academy",
        name="Academy",
        logo_url="https://example.com/logo.png",
        street_address="123 Main St",
        city=city,
        country=country,
    )

    from django.utils import timezone

    owner = User.objects.create(username="owner", email="owner@example.com")
    subscription = Subscription.objects.create(
        user=owner,
        academy=academy,
        paid_at=timezone.now(),
        next_payment_at=timezone.now(),
    )

    team = SubscriptionBillingTeam.objects.create(subscription=subscription, name="Team", seats_limit=10, seats_log=[])

    # Active seat counts; inactive does not
    SubscriptionSeat.objects.create(billing_team=team, email="a@b.com", user=None, is_active=True)
    SubscriptionSeat.objects.create(billing_team=team, email="c@d.com", user=None, is_active=False)

    # Act (patch methods at class level so fetched instance uses them)
    client.force_authenticate(user=owner)
    url = f"/v2/payments/subscription/{subscription.id}/billing-team"
    with (
        patch.object(SubscriptionBillingTeam, "get_current_monthly_period_dates", return_value=(None, None)),
        patch.object(SubscriptionBillingTeam, "get_current_period_spend", return_value=0.0),
    ):
        resp = client.get(url)

    # Assert
    assert resp.status_code == 200
    assert resp.json() == {
        "id": team.id,
        "subscription": subscription.id,
        "name": "Team",
        "seats_limit": 10,
        "seats_count": 1,  # only active seats counted
        "seats_log": [],
        # Auto-recharge settings
        "auto_recharge_enabled": False,
        "recharge_threshold_amount": "10.00",
        "recharge_amount": "10.00",
        "max_period_spend": None,
        # Current spending (calculated from invoices)
        "current_period_spend": 0.0,
        # Virtual attributes for current period
        "period_start": None,
        "period_end": None,
        # Subscription currency
        "currency": None,
    }


# ------------------------------
# Unit tests (mocked DB)
# ------------------------------


@pytest.fixture()
def factory():
    return APIRequestFactory()


@patch("breathecode.payments.views.get_user_language", return_value="en")
@patch("breathecode.payments.views.Subscription.objects")
def test_get_subscription_not_found_returns_404(mock_sub_objects, mock_lang, factory):
    """When subscription does not exist, return 404 with proper slug."""
    from breathecode.payments.views import SubscriptionBillingTeamView

    mock_qs = MagicMock()
    mock_qs.filter.return_value = MagicMock(first=lambda: None)
    mock_sub_objects.filter.return_value = mock_qs.filter()

    request = factory.get("/v2/payments/subscription/999/billing-team")
    force_authenticate(request, user=MagicMock(id=1))

    resp = SubscriptionBillingTeamView.as_view()(request, subscription_id=999)
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert resp.data == {"detail": "subscription-not-found", "status_code": 404}


@patch("breathecode.payments.views.get_user_language", return_value="en")
@patch("breathecode.payments.views.Subscription.objects")
def test_get_not_owner_returns_403(mock_sub_objects, mock_lang, factory):
    """When the requester is not the subscription owner, return 403."""
    from breathecode.payments.views import SubscriptionBillingTeamView

    subscription = MagicMock(id=1, user_id=2)
    mock_sub_objects.filter.return_value = MagicMock(first=lambda: subscription)

    request = factory.get("/v2/payments/subscription/1/billing-team")
    force_authenticate(request, user=MagicMock(id=1))

    resp = SubscriptionBillingTeamView.as_view()(request, subscription_id=1)
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert resp.data == {"detail": "only-owner-allowed", "status_code": 403}


@patch("breathecode.payments.views.get_user_language", return_value="en")
@patch("breathecode.payments.views.SubscriptionBillingTeam.objects")
@patch("breathecode.payments.views.Subscription.objects")
def test_get_team_not_found_returns_404(mock_sub_objects, mock_team_objects, mock_lang, factory):
    """When the team is missing, return 404 with billing-team-not-found."""
    from breathecode.payments.views import SubscriptionBillingTeamView

    subscription = MagicMock(id=1, user_id=1)
    mock_sub_objects.filter.return_value = MagicMock(first=lambda: subscription)
    mock_team_objects.filter.return_value = MagicMock(first=lambda: None)

    request = factory.get("/v2/payments/subscription/1/billing-team")
    force_authenticate(request, user=MagicMock(id=1))

    resp = SubscriptionBillingTeamView.as_view()(request, subscription_id=1)
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert resp.data == {"detail": "billing-team-not-found", "status_code": 404}


@patch("breathecode.payments.views.get_user_language", return_value="en")
@patch("breathecode.payments.views.SubscriptionBillingTeam.objects")
@patch("breathecode.payments.views.Subscription.objects")
def test_get_ok_mocked_returns_payload(mock_sub_objects, mock_team_objects, mock_lang, factory):
    """Happy path: returns payload with aggregated seats_count using mocked seats."""
    from breathecode.payments.views import SubscriptionBillingTeamView

    subscription = MagicMock(id=1, user_id=7)
    subscription.currency = None
    mock_sub_objects.filter.return_value = MagicMock(first=lambda: subscription)

    # Provide a manager-like object with filter().count()
    seats_qs = MagicMock()
    seats_qs.count.return_value = 2
    seats_manager = MagicMock()
    seats_manager.filter.return_value = seats_qs
    team = MagicMock(id=99, seats_limit=10, seats_log=[], seats=seats_manager)
    team.name = "Team"
    team.subscription = subscription
    team.get_current_monthly_period_dates.return_value = (None, None)
    team.get_current_period_spend.return_value = 0.0
    team.auto_recharge_enabled = False
    team.recharge_threshold_amount = "10.00"
    team.recharge_amount = "10.00"
    team.max_period_spend = None
    mock_team_objects.filter.return_value = MagicMock(first=lambda: team)

    request = factory.get("/v2/payments/subscription/1/billing-team")
    force_authenticate(request, user=MagicMock(id=7))

    resp = SubscriptionBillingTeamView.as_view()(request, subscription_id=1)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data == {
        "id": 99,
        "subscription": 1,
        "name": "Team",
        "seats_limit": 10,
        "seats_count": 2,
        "seats_log": [],
        # Auto-recharge settings
        "auto_recharge_enabled": False,
        "recharge_threshold_amount": "10.00",
        "recharge_amount": "10.00",
        "max_period_spend": None,
        # Current spending (calculated from invoices)
        "current_period_spend": 0.0,
        # Virtual attributes for current period
        "period_start": None,
        "period_end": None,
        # Subscription currency
        "currency": None,
    }
