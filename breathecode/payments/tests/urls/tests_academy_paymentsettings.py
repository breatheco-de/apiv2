"""
Tests for /academy/paymentsettings endpoint
"""

from rest_framework import status

from breathecode.authenticate.models import Capability, ProfileAcademy, Role
from breathecode.payments.models import AcademyPaymentSettings


def setup_capability_and_role(database):
    """Helper to setup capability and role correctly"""
    database.create(capability={"slug": "crud_academy_payment_settings"})
    database.create(role={"slug": "test_role", "name": "Test Role"})

    role = Role.objects.get(slug="test_role")
    capability = Capability.objects.get(slug="crud_academy_payment_settings")
    role.capabilities.set([capability])

    return role


def test_no_auth(client):
    """Test that accessing without authentication returns 401"""
    url = "/v1/payments/academy/paymentsettings"
    response = client.put(url)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "Authentication credentials were not provided.",
        "status_code": 401,
    }


def test_no_capability(database, client):
    """Test that accessing without crud_academy_payment_settings capability returns 403"""
    model = database.create(user=1, academy=1, city=1, country=1)
    client.force_authenticate(model.user)

    url = "/v1/payments/academy/paymentsettings"
    response = client.put(url, HTTP_ACADEMY=model.academy.id)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    json_response = response.json()
    assert json_response["status_code"] == 403
    assert "don't have this capability" in json_response["detail"]


def test_no_academy_header(database, client):
    """Test that accessing without Academy header returns 403"""
    role = setup_capability_and_role(database)
    model = database.create(user=1, city=1, country=1, academy=1)
    ProfileAcademy.objects.create(user=model.user, academy=model.academy, role=role, email=model.user.email)

    client.force_authenticate(model.user)

    url = "/v1/payments/academy/paymentsettings"
    response = client.put(url)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
        "status_code": 403,
    }


def test_payment_settings_not_found(database, client):
    """Test that returns 404 when payment settings don't exist for academy"""
    role = setup_capability_and_role(database)
    model = database.create(user=1, city=1, country=1, academy=1)
    ProfileAcademy.objects.create(user=model.user, academy=model.academy, role=role, email=model.user.email)

    client.force_authenticate(model.user)

    url = "/v1/payments/academy/paymentsettings"
    data = {"stripe_api_key": "sk_test_new"}
    response = client.put(url, data, format="json", HTTP_ACADEMY=model.academy.id)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    json = response.json()
    assert json["status_code"] == 404
    assert "payment-settings-not-found" in json["detail"] or "not found" in json["detail"].lower()


def test_update_all_fields(database, client):
    """Test updating all fields successfully"""
    role = setup_capability_and_role(database)
    model = database.create(user=1, city=1, country=1, academy=1, academy_payment_settings=1)
    ProfileAcademy.objects.create(user=model.user, academy=model.academy, role=role, email=model.user.email)

    client.force_authenticate(model.user)

    url = "/v1/payments/academy/paymentsettings"
    data = {
        "stripe_api_key": "sk_test_new_key",
        "stripe_webhook_secret": "whsec_new_secret",
        "stripe_publishable_key": "pk_test_new_key",
        "coinbase_api_key": "new_coinbase_key",
        "coinbase_webhook_secret": "new_coinbase_secret",
    }
    response = client.put(url, data, format="json", HTTP_ACADEMY=model.academy.id)

    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert json["stripe_api_key"] == "sk_test_new_key"
    assert json["stripe_webhook_secret"] == "whsec_new_secret"
    assert json["stripe_publishable_key"] == "pk_test_new_key"
    assert json["coinbase_api_key"] == "new_coinbase_key"
    assert json["coinbase_webhook_secret"] == "new_coinbase_secret"

    # Verify in database
    settings = AcademyPaymentSettings.objects.get(academy=model.academy)
    assert settings.stripe_api_key == "sk_test_new_key"
    assert settings.stripe_webhook_secret == "whsec_new_secret"
    assert settings.stripe_publishable_key == "pk_test_new_key"
    assert settings.coinbase_api_key == "new_coinbase_key"
    assert settings.coinbase_webhook_secret == "new_coinbase_secret"


def test_update_partial_only_stripe_key(database, client):
    """Test updating only one field (partial update)"""
    role = setup_capability_and_role(database)
    model = database.create(
        user=1,
        city=1,
        country=1,
        academy=1,
        academy_payment_settings={
            "stripe_api_key": "sk_test_old",
            "stripe_webhook_secret": "whsec_old",
            "coinbase_api_key": "coinbase_old",
        },
    )
    ProfileAcademy.objects.create(user=model.user, academy=model.academy, role=role, email=model.user.email)

    client.force_authenticate(model.user)

    url = "/v1/payments/academy/paymentsettings"
    data = {"stripe_api_key": "sk_test_updated"}
    response = client.put(url, data, format="json", HTTP_ACADEMY=model.academy.id)

    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert json["stripe_api_key"] == "sk_test_updated"
    # Other fields should remain unchanged
    assert json["stripe_webhook_secret"] == "whsec_old"
    assert json["coinbase_api_key"] == "coinbase_old"

    # Verify in database
    settings = AcademyPaymentSettings.objects.get(academy=model.academy)
    assert settings.stripe_api_key == "sk_test_updated"
    assert settings.stripe_webhook_secret == "whsec_old"
    assert settings.coinbase_api_key == "coinbase_old"
