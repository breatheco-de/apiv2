import pytest
from datetime import timedelta
from unittest.mock import ANY, MagicMock, patch

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from breathecode.admissions.models import Academy, City, Country
from breathecode.payments.models import (
    Currency,
    PlanFinancing,
    PlanFinancingSeat,
    PlanFinancingTeam,
)
from breathecode.payments.views import PlanFinancingSeatView, PlanFinancingTeamView


@pytest.fixture()
def factory():
    return APIRequestFactory()


@pytest.fixture()
def plan_financing_setup(db):
    owner = User.objects.create(username="owner", email="owner@example.com")
    other_user = User.objects.create(username="other", email="other@example.com")

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

    seat = PlanFinancingSeat.objects.create(team=team, user=owner, email=owner.email)

    return {
        "owner": owner,
        "other_user": other_user,
        "financing": financing,
        "team": team,
        "seat": seat,
    }


@pytest.mark.django_db
def test_get_plan_financing_team(factory, plan_financing_setup):
    request = factory.get("/v2/payments/plan-financing/1/team")
    force_authenticate(request, user=plan_financing_setup["owner"])

    response = PlanFinancingTeamView.as_view()(request, plan_financing_id=plan_financing_setup["financing"].id)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == plan_financing_setup["team"].id
    assert response.data["seats_count"] == 1
    assert response.data["plan_financing"] == plan_financing_setup["financing"].id


@pytest.mark.django_db
def test_get_plan_financing_team_not_owner(factory, plan_financing_setup):
    request = factory.get("/v2/payments/plan-financing/1/team")
    force_authenticate(request, user=plan_financing_setup["other_user"])

    response = PlanFinancingTeamView.as_view()(request, plan_financing_id=plan_financing_setup["financing"].id)

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_get_plan_financing_seat_list(factory, plan_financing_setup):
    request = factory.get("/v2/payments/plan-financing/1/team/seat")
    force_authenticate(request, user=plan_financing_setup["owner"])

    response = PlanFinancingSeatView.as_view()(request, plan_financing_id=plan_financing_setup["financing"].id)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["email"] == plan_financing_setup["seat"].email


@pytest.mark.django_db
def test_put_plan_financing_add_seat(factory, plan_financing_setup):
    new_seat = MagicMock()
    new_seat.id = 99
    new_seat.email = "new@example.com"
    new_seat.user_id = None
    new_seat.is_active = True
    new_seat.seat_log = []

    with patch("breathecode.payments.views.actions.create_plan_financing_seat", return_value=new_seat) as mock_create, patch(
        "breathecode.payments.views.actions.validate_seats_limit"
    ) as mock_validate:
        request = factory.put(
            "/v2/payments/plan-financing/1/team/seat",
            {"add_seats": [{"email": "new@example.com"}]},
            format="json",
        )
        force_authenticate(request, user=plan_financing_setup["owner"])

        response = PlanFinancingSeatView.as_view()(request, plan_financing_id=plan_financing_setup["financing"].id)

    assert response.status_code == status.HTTP_207_MULTI_STATUS
    mock_validate.assert_called_once()
    mock_create.assert_called_once_with("new@example.com", None, plan_financing_setup["team"], ANY)
    assert response.data["data"][0]["email"] == "new@example.com"


@pytest.mark.django_db
def test_put_plan_financing_replace_seat(factory, plan_financing_setup):
    replacement = MagicMock()
    replacement.id = 42
    replacement.email = "replacement@example.com"
    replacement.user_id = plan_financing_setup["owner"].id
    replacement.is_active = True
    replacement.seat_log = []

    with patch(
        "breathecode.payments.views.actions.replace_plan_financing_seat",
        return_value=replacement,
    ) as mock_replace, patch(
        "breathecode.payments.views.actions.validate_seats_limit"
    ) as mock_validate:
        request = factory.put(
            "/v2/payments/plan-financing/1/team/seat",
            {
                "replace_seats": [
                    {
                        "from_email": plan_financing_setup["seat"].email,
                        "to_email": "replacement@example.com",
                        "to_user": plan_financing_setup["owner"].id,
                    }
                ]
            },
            format="json",
        )
        force_authenticate(request, user=plan_financing_setup["owner"])

        response = PlanFinancingSeatView.as_view()(request, plan_financing_id=plan_financing_setup["financing"].id)

    assert response.status_code == status.HTTP_207_MULTI_STATUS
    mock_validate.assert_called_once()
    mock_replace.assert_called_once()
    args, kwargs = mock_replace.call_args
    assert args[0] == plan_financing_setup["seat"].email
    assert args[1] == "replacement@example.com"
    assert args[2] == plan_financing_setup["owner"]
    assert isinstance(args[3], PlanFinancingSeat)
    assert isinstance(args[4], str)
    assert response.data["data"][0]["email"] == "replacement@example.com"


@pytest.mark.django_db
def test_delete_plan_financing_seat(factory, plan_financing_setup):
    with patch("breathecode.payments.views.actions.deactivate_plan_financing_seat") as mock_deactivate:
        request = factory.delete("/v2/payments/plan-financing/1/team/seat/1")
        force_authenticate(request, user=plan_financing_setup["owner"])

        response = PlanFinancingSeatView.as_view()(
            request,
            plan_financing_id=plan_financing_setup["financing"].id,
            seat_id=plan_financing_setup["seat"].id,
        )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_deactivate.assert_called_once()

