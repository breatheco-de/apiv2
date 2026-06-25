"""Tests for billing team fields on GetAbstractIOweYouSerializer."""

import pytest
from datetime import timedelta
from django.contrib.auth.models import User
from django.utils import timezone

from breathecode.admissions.models import Academy, City, Country
from breathecode.payments.models import (
    Currency,
    PlanFinancing,
    PlanFinancingSeat,
    PlanFinancingTeam,
    Subscription,
    SubscriptionBillingTeam,
    SubscriptionSeat,
)
from breathecode.payments.serializers import GetPlanFinancingSerializer, GetSubscriptionSerializer


@pytest.mark.django_db
def test_subscription_serializer_billing_team_fields():
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
    owner = User.objects.create(username="owner", email="owner@example.com")
    subscription = Subscription.objects.create(
        user=owner,
        academy=academy,
        paid_at=timezone.now(),
        next_payment_at=timezone.now(),
    )
    team = SubscriptionBillingTeam.objects.create(subscription=subscription, name="Team", additional_seats=4)
    SubscriptionSeat.objects.create(billing_team=team, email="member@example.com", user=None, is_active=True)
    SubscriptionSeat.objects.create(billing_team=team, email="inactive@example.com", user=None, is_active=False)

    data = GetSubscriptionSerializer(subscription).data

    assert data["has_billing_team"] is True
    assert data["seats_count"] == 1
    assert data["seats_limit"] == 5


@pytest.mark.django_db
def test_plan_financing_serializer_billing_team_fields():
    owner = User.objects.create(username="owner", email="owner@example.com")
    currency = Currency.objects.create(code="USD", name="US Dollar", decimals=2)
    country = Country.objects.create(code="US", name="United States")
    city = City.objects.create(name="Miami", country=country)
    academy = Academy.objects.create(
        slug="test-academy",
        name="Test Academy",
        logo_url="https://example.com/logo.png",
        street_address="123 Main St",
        marketing_email="marketing@example.com",
        feedback_email="feedback@example.com",
        country=country,
        city=city,
    )
    academy.main_currency = currency
    academy.save(update_fields=["main_currency"])

    financing = PlanFinancing.objects.create(
        user=owner,
        academy=academy,
        next_payment_at=timezone.now() + timedelta(days=30),
        valid_until=timezone.now() + timedelta(days=60),
        plan_expires_at=timezone.now() + timedelta(days=90),
        monthly_price=100,
        currency=currency,
        how_many_installments=1,
    )
    team = PlanFinancingTeam.objects.create(
        financing=financing,
        name="Financing Team",
        additional_seats=2,
    )
    PlanFinancingSeat.objects.create(team=team, user=owner, email=owner.email, is_active=True)
    PlanFinancingSeat.objects.create(team=team, user=None, email="guest@example.com", is_active=True)

    data = GetPlanFinancingSerializer(financing).data

    assert data["has_billing_team"] is True
    assert data["seats_count"] == 2
    assert data["seats_limit"] == 3
