"""
Test cases for /discord (get_discord_token)
"""

import os
import urllib.parse
from datetime import timedelta

import pytest
from django.urls.base import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db):
    pass


# When: User tries to get Discord token without url parameter
# Then: Return 400 with no-callback-url error
def test_discord_without_url_authenticated(bc: Breathecode, client: APIClient):
    """Test /discord without url parameter when user is authenticated"""
    model = bc.database.create(user=1, subscription=1)
    client.force_authenticate(model.user)
    url = reverse_lazy("authenticate:discord")
    response = client.get(url)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    response_data = str(response.data).lower()
    assert "no-callback-url" in response_data


# When: User tries to get Discord token without cohort_slug
# Then: Return 400 error for missing cohort_slug
def test_discord_without_cohort_slug_authenticated(bc: Breathecode, client: APIClient):
    """Test /discord without cohort_slug parameter when user is authenticated"""
    model = bc.database.create(user=1, subscription=1)
    client.force_authenticate(model.user)

    url = reverse_lazy("authenticate:discord")
    params = {"url": "https://google.co.ve"}
    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    response_data = str(response.data).lower()
    assert "no cohort slug specified" in response_data


# When: User is not authenticated
# Then: Return 401 unauthorized error
def test_discord_without_auth(client: APIClient):
    """Test /discord without authentication"""
    url = reverse_lazy("authenticate:discord")
    params = {"url": "https://google.co.ve", "cohort_slug": "test-cohort"}
    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# Given: User is authenticated but has no active subscription
# When: User tries to get Discord token
# Then: Return 403 error for missing subscription
def test_discord_without_subscription(bc: Breathecode, client: APIClient):
    """Test /discord with user without active subscription"""
    model = bc.database.create(user=1)
    client.force_authenticate(model.user)
    url = reverse_lazy("authenticate:discord")
    params = {"url": "https://google.co.ve", "cohort_slug": "test-cohort"}
    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    assert response.status_code == status.HTTP_403_FORBIDDEN


# Given: User is authenticated but has no active plan financing
# When: User tries to get Discord token
# Then: Return 403 error for missing plan financing
def test_discord_without_plan_financing(bc: Breathecode, client: APIClient):
    """Test /discord with user without active plan financing"""
    model = bc.database.create(user=1)
    client.force_authenticate(model.user)
    url = reverse_lazy("authenticate:discord")
    params = {"url": "https://google.co.ve", "cohort_slug": "test-cohort"}
    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    assert response.status_code == status.HTTP_403_FORBIDDEN


# When: User requests Discord token with valid parameters and an active subscription
# Then: Return 200 with authorization_url containing Discord OAuth parameters
def test_discord_with_subscription(bc: Breathecode, client: APIClient):
    """Test /discord with user having active subscription"""
    plan = bc.database.create(
        plan={
            "slug": "4geeks-plus-subscription",
            "is_renewable": False,
        }
    )
    academy = bc.database.create(academy=1)
    cohort = bc.database.create(cohort={"academy": academy.academy, "slug": "test-cohort"})
    academy_auth_settings = bc.database.create(
        academy_auth_settings={"academy": academy.academy, "discord_settings": {"discord_client_id": "test-client-id"}}
    )
    model = bc.database.create(user=1, subscription={"plans": [plan.plan.id]})
    client.force_authenticate(model.user)

    url = reverse_lazy("authenticate:discord")
    params = {"url": "https://google.co.ve", "cohort_slug": "test-cohort"}
    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.data
    assert "authorization_url" in response_data

    # Verify the authorization URL contains correct Discord OAuth parameters
    auth_url = response_data["authorization_url"]
    assert "https://discord.com/oauth2/authorize" in auth_url
    assert "client_id" in auth_url
    assert "response_type=code" in auth_url
    assert "scope=" in auth_url


# When: User requests Discord token with valid parameters and an active plan financing
# Then: Return 200 with authorization_url containing Discord OAuth parameters
def test_discord_with_plan_financing(bc: Breathecode, client: APIClient):
    """Test /discord with user having active plan financing"""
    plan = bc.database.create(
        plan={
            "slug": "4geeks-plus-planfinancing",
            "is_renewable": False,
        }
    )
    academy = bc.database.create(academy=1)
    cohort = bc.database.create(cohort={"academy": academy.academy, "slug": "test-cohort"})
    academy_auth_settings = bc.database.create(
        academy_auth_settings={"academy": academy.academy, "discord_settings": {"discord_client_id": "test-client-id"}}
    )
    model = bc.database.create(
        user=1,
        plan_financing={
            "plans": [plan.plan.id],
            "monthly_price": 100,
            "plan_expires_at": bc.datetime.now() + timedelta(days=30),
        },
    )
    client.force_authenticate(model.user)

    url = reverse_lazy("authenticate:discord")
    params = {"url": "https://google.co.ve", "cohort_slug": "test-cohort"}
    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.data
    assert "authorization_url" in response_data

    # Verify the authorization URL contains correct Discord OAuth parameters
    auth_url = response_data["authorization_url"]
    assert "https://discord.com/oauth2/authorize" in auth_url
    assert "client_id" in auth_url
    assert "response_type=code" in auth_url
    assert "scope=" in auth_url


# When: User requests Discord token
# Then: Verify that a temporal token is created for the user
def test_discord_creates_temporal_token(bc: Breathecode, client: APIClient):
    """Test /discord creates a temporal token for authenticated requests"""
    from breathecode.authenticate.models import Token

    plan = bc.database.create(
        plan={
            "slug": "4geeks-plus-subscription",
            "is_renewable": False,
        }
    )
    academy = bc.database.create(academy=1)
    cohort = bc.database.create(cohort={"academy": academy.academy, "slug": "test-cohort"})
    academy_auth_settings = bc.database.create(
        academy_auth_settings={"academy": academy.academy, "discord_settings": {"discord_client_id": "test-client-id"}}
    )
    model = bc.database.create(user=1, subscription={"plans": [plan.plan.id]})
    client.force_authenticate(model.user)

    # Count tokens before the request
    initial_token_count = Token.objects.filter(user=model.user, token_type="temporal").count()

    url = reverse_lazy("authenticate:discord")
    params = {"url": "https://google.co.ve", "cohort_slug": "test-cohort"}
    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    assert response.status_code == status.HTTP_200_OK

    # Verify that a new temporal token was created
    final_token_count = Token.objects.filter(user=model.user, token_type="temporal").count()
    assert final_token_count == initial_token_count + 1

    # Verify the token is properly configured
    latest_token = Token.objects.filter(user=model.user, token_type="temporal").order_by("-created").first()
    assert latest_token is not None
    assert latest_token.token_type == "temporal"
    assert latest_token.expires_at is not None
