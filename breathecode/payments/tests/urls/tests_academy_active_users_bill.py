from datetime import date
from decimal import Decimal

from rest_framework import status

from breathecode.authenticate.models import Capability, ProfileAcademy, Role
from breathecode.payments.models import ActiveUsersBill, ActiveUsersBillItem


def _setup_capability_and_role(database):
    database.create(capability={"slug": "read_active_users_bill"})
    database.create(role={"slug": "test_role", "name": "Test Role"})
    role = Role.objects.get(slug="test_role")
    capability = Capability.objects.get(slug="read_active_users_bill")
    role.capabilities.set([capability])
    return role


def test_list_no_auth(client):
    url = "/v1/payments/academy/active-users-bill"
    response = client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_no_capability(database, client):
    model = database.create(user=1, academy=1, city=1, country=1, profile_academy=1)
    client.force_authenticate(model.user)
    url = "/v1/payments/academy/active-users-bill"
    response = client.get(url, headers={"academy": model.academy.id})
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_list_and_detail_and_month(database, client):
    role = _setup_capability_and_role(database)
    model = database.create(user=1, academy=1, city=1, country=1, cohort={"stage": "STARTED"})
    ProfileAcademy.objects.create(
        user=model.user, academy=model.academy, role=role, email=model.user.email, status="ACTIVE"
    )
    client.force_authenticate(model.user)

    peak = ActiveUsersBill.objects.create(
        academy=model.academy,
        billing_date=date(2026, 8, 14),
        unique_user_count=5,
        price_per_user=Decimal("10.00"),
        total_amount=Decimal("50.00"),
        currency_code="USD",
        title="peak",
    )
    ActiveUsersBill.objects.create(
        academy=model.academy,
        billing_date=date(2026, 8, 1),
        unique_user_count=2,
        price_per_user=Decimal("10.00"),
        total_amount=Decimal("20.00"),
        currency_code="USD",
        title="low",
    )
    item = ActiveUsersBillItem.objects.create(
        bill=peak,
        cohort=model.cohort,
        user_count=5,
        amount=Decimal("50.00"),
        user_ids=[1],
        notes="",
    )

    list_res = client.get(
        "/v1/payments/academy/active-users-bill?year=2026&month=8",
        headers={"academy": model.academy.id},
    )
    assert list_res.status_code == status.HTTP_200_OK
    assert len(list_res.json()) == 2

    detail_res = client.get(
        f"/v1/payments/academy/active-users-bill/{peak.id}",
        headers={"academy": model.academy.id},
    )
    assert detail_res.status_code == status.HTTP_200_OK
    detail = detail_res.json()
    assert detail["id"] == peak.id
    assert len(detail["items"]) == 1
    assert detail["items"][0]["id"] == item.id

    month_res = client.get(
        "/v1/payments/academy/active-users-bill/month?year=2026&month=8",
        headers={"academy": model.academy.id},
    )
    assert month_res.status_code == status.HTTP_200_OK
    month = month_res.json()
    assert month["peak_bill_id"] == peak.id
    assert month["unique_user_count"] == 5
    assert month["amount"] == "50.00"
    assert len(month["items"]) == 1
    assert month["items"][0]["id"] == item.id
    assert month["items"][0]["cohort"]["id"] == model.cohort.id


def test_detail_other_academy_404(database, client):
    role = _setup_capability_and_role(database)
    model = database.create(user=1, academy=2, city=1, country=1)
    academy_a, academy_b = model.academy
    ProfileAcademy.objects.create(
        user=model.user, academy=academy_b, role=role, email=model.user.email, status="ACTIVE"
    )

    bill = ActiveUsersBill.objects.create(
        academy=academy_a,
        billing_date=date(2026, 8, 14),
        unique_user_count=1,
        price_per_user=Decimal("10.00"),
        total_amount=Decimal("10.00"),
    )

    client.force_authenticate(model.user)
    response = client.get(
        f"/v1/payments/academy/active-users-bill/{bill.id}",
        headers={"academy": academy_b.id},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
