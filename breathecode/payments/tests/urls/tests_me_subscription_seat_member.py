import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.admissions.models import Academy, Cohort, CohortUser, Country, City
from breathecode.authenticate.models import User
from breathecode.payments.models import (
    CohortSet,
    Plan,
    Subscription,
    SubscriptionBillingTeam,
    SubscriptionSeat,
)


@pytest.mark.django_db
def test_me_subscription_includes_owner_subscription_for_active_seat_member():
    country = Country.objects.create(code="US", name="United States")
    city = City.objects.create(name="Miami", country=country)
    academy = Academy.objects.create(
        slug="academy",
        name="Academy",
        logo_url="https://example.com/logo.png",
        street_address="123 Main St",
        city=city,
        country=country,
        available_as_saas=True,
    )

    owner = User.objects.create(username="owner", email="owner@example.com")
    member = User.objects.create(username="member", email="member@example.com")

    cohort_set = CohortSet.objects.create(slug="ai-set", academy=academy)
    cohort = Cohort.objects.create(
        slug="ai-intro",
        name="AI Intro",
        academy=academy,
        available_as_saas=True,
        stage="STARTED",
    )
    cohort_set.cohorts.add(cohort)

    plan = Plan.objects.create(slug="ai-plan", title="AI Plan", academy=academy, cohort_set=cohort_set)

    subscription = Subscription.objects.create(
        user=owner,
        academy=academy,
        status="ACTIVE",
        paid_at=timezone.now(),
        next_payment_at=timezone.now(),
        selected_cohort_set=cohort_set,
    )
    subscription.plans.add(plan)

    team = SubscriptionBillingTeam.objects.create(subscription=subscription, name="Team", seats_limit=5)
    SubscriptionSeat.objects.create(
        billing_team=team,
        user=member,
        email=member.email,
        is_active=True,
    )

    CohortUser.objects.create(user=member, cohort=cohort, role="STUDENT", educational_status="ACTIVE")

    client = APIClient()
    client.force_authenticate(user=member)

    response = client.get(reverse("payments:me_subscription"))

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["subscriptions"]) == 1
    assert data["subscriptions"][0]["id"] == subscription.id
    assert data["plan_financings"] == []


@pytest.mark.django_db
def test_me_subscription_does_not_include_inactive_seat():
    country = Country.objects.create(code="US", name="United States")
    city = City.objects.create(name="Miami", country=country)
    academy = Academy.objects.create(
        slug="academy",
        name="Academy",
        logo_url="https://example.com/logo.png",
        street_address="123 Main St",
        city=city,
        country=country,
        available_as_saas=True,
    )

    owner = User.objects.create(username="owner", email="owner@example.com")
    member = User.objects.create(username="member", email="member@example.com")

    subscription = Subscription.objects.create(
        user=owner,
        academy=academy,
        status="ACTIVE",
        paid_at=timezone.now(),
        next_payment_at=timezone.now(),
    )
    team = SubscriptionBillingTeam.objects.create(subscription=subscription, name="Team", seats_limit=5)
    SubscriptionSeat.objects.create(
        billing_team=team,
        user=member,
        email=member.email,
        is_active=False,
    )

    client = APIClient()
    client.force_authenticate(user=member)

    response = client.get(reverse("payments:me_subscription"))

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["subscriptions"] == []
    assert data["plan_financings"] == []
