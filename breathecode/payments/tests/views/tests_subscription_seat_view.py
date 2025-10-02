import pytest
from unittest.mock import MagicMock, patch, ANY

from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status
from django.contrib.auth.models import User
from django.utils import timezone
from breathecode.admissions.models import Country, City, Academy
from breathecode.payments.models import Subscription, SubscriptionBillingTeam, SubscriptionSeat


@pytest.fixture()
def factory():
    return APIRequestFactory()


def build_seat(id=1, email="a@b.com", user_id=None, seat_multiplier=1, is_active=True, seat_log=None):
    """Build a fake seat object for view tests."""
    seat = MagicMock()
    seat.id = id
    seat.email = email
    seat.user_id = user_id
    seat.seat_multiplier = seat_multiplier
    seat.is_active = is_active
    seat.seat_log = seat_log or []
    return seat


def build_team(id=10, name="Team", seats_limit=5):
    """Build a fake billing team object for view tests."""
    team = MagicMock()
    team.id = id
    team.name = name
    team.seats_limit = seats_limit
    team.seats = MagicMock(filter=lambda is_active=True: [])
    return team


def build_subscription(id=99, user_id=7):
    """Build a fake subscription object for view tests."""
    sub = MagicMock()
    sub.id = id
    sub.user_id = user_id
    sub.plans = MagicMock(first=lambda: MagicMock(seat_service_price=MagicMock()))
    return sub


@patch("breathecode.payments.views.get_user_language", return_value="en")
@patch("breathecode.payments.views.SubscriptionSeatView._get_seats")
@patch("breathecode.payments.views.SubscriptionSeatView._get_team")
@patch("breathecode.payments.views.SubscriptionSeatView._get_subscription")
def test_get_list_ok(mock_get_subscription, mock_get_team, mock_get_seats, mock_lang, factory):
    """List seats returns expected payload (mocked dependencies)."""
    from breathecode.payments.views import SubscriptionSeatView

    mock_get_subscription.return_value = build_subscription()
    mock_get_team.return_value = build_team()

    seat1 = build_seat(id=1, email="x@y.com", user_id=1, seat_multiplier=2)
    seat2 = build_seat(id=2, email="y@z.com", user_id=None, seat_multiplier=1)
    mock_get_seats.return_value = [seat1, seat2]

    request = factory.get("/v2/payments/subscriptions/99/seats")
    force_authenticate(request, user=MagicMock(id=7))

    resp = SubscriptionSeatView.as_view()(request, subscription_id=99)

    assert resp.status_code == status.HTTP_200_OK
    assert isinstance(resp.data, list)
    assert resp.data == [
        {
            "id": 1,
            "email": "x@y.com",
            "user": 1,
            "seat_multiplier": 2,
            "is_active": True,
            "seat_log": [],
        },
        {
            "id": 2,
            "email": "y@z.com",
            "user": None,
            "seat_multiplier": 1,
            "is_active": True,
            "seat_log": [],
        },
    ]


@patch("breathecode.payments.views.get_user_language", return_value="en")
@patch("breathecode.payments.views.SubscriptionSeatView._get_seats")
@patch("breathecode.payments.views.SubscriptionSeatView._get_team")
@patch("breathecode.payments.views.SubscriptionSeatView._get_subscription")
def test_get_detail_not_found_raises(mock_get_subscription, mock_get_team, mock_get_seats, mock_lang, factory):
    """Get detail with non-existing seat returns 404 (mocked)."""
    from breathecode.payments.views import SubscriptionSeatView

    mock_get_subscription.return_value = build_subscription()
    mock_get_team.return_value = build_team()
    mock_qs = MagicMock()
    mock_qs.filter.return_value = MagicMock(first=lambda: None)
    mock_get_seats.return_value = mock_qs

    request = factory.get("/v2/payments/subscriptions/99/seats/999")
    force_authenticate(request, user=MagicMock(id=7))

    resp = SubscriptionSeatView.as_view()(request, subscription_id=99, seat_id=999)
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert resp.data == {"detail": "seat-not-found", "status_code": 404}


# Integration test (DB): ensure real view + ORM path works and catches issues mocks might miss
@pytest.mark.django_db
def test_get_list_ok_integration_db(client):
    """Integration: real ORM + endpoint GET list returns seats."""
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
    sub = Subscription.objects.create(
        user=owner,
        academy=academy,
        paid_at=timezone.now(),
        next_payment_at=timezone.now(),
    )
    team = SubscriptionBillingTeam.objects.create(subscription=sub, name="Team", seats_limit=10)

    u1 = User.objects.create(username="u1", email="x@y.com")
    SubscriptionSeat.objects.create(billing_team=team, email="x@y.com", user=u1, seat_multiplier=2)
    SubscriptionSeat.objects.create(billing_team=team, email="y@z.com", user=None, seat_multiplier=1)

    # Act: call real endpoint
    client.force_authenticate(user=owner)
    url = f"/v2/payments/subscription/{sub.id}/billing-team/seat"
    resp = client.get(url)

    # Assert
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert isinstance(data, list)
    # sort by email for deterministic checks
    data = sorted(data, key=lambda x: x["email"])  # unique per team

    assert data[0]["email"] == "x@y.com"
    assert data[0]["user"] == u1.id
    assert data[0]["seat_multiplier"] == 2
    assert data[0]["is_active"] is True

    assert data[1]["email"] == "y@z.com"
    assert data[1]["user"] is None
    assert data[1]["seat_multiplier"] == 1
    assert data[1]["is_active"] is True


@patch("breathecode.payments.views.get_user_language", return_value="en")
@patch("breathecode.payments.views.actions.normalize_replace_seat", return_value=[])
@patch("breathecode.payments.views.actions.normalize_add_seats", return_value=[])
@patch("breathecode.payments.views.SubscriptionSeatView._get_team")
@patch("breathecode.payments.views.SubscriptionSeatView._get_subscription")
def test_put_missing_add_and_replace_raise(
    mock_get_subscription, mock_get_team, mock_norm_add, mock_norm_replace, mock_lang, factory
):
    """PUT without add/replace raises 400 with guidance (mocked)."""
    from breathecode.payments.views import SubscriptionSeatView

    mock_get_subscription.return_value = build_subscription(user_id=1)
    mock_get_team.return_value = build_team()

    request = factory.put("/v2/payments/subscriptions/99/seats", data={}, format="json")
    force_authenticate(request, user=MagicMock(id=1))

    resp = SubscriptionSeatView.as_view()(request, subscription_id=99)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.data == {"detail": "add-or-replace-seats-required", "status_code": 400}


@patch("breathecode.payments.views.get_user_language", return_value="en")
@patch("breathecode.payments.views.SubscriptionSeatView._get_subscription")
def test_put_permission_denied_when_not_owner(mock_get_subscription, mock_lang, factory):
    """PUT by non-owner returns 403 forbidden (mocked)."""
    from breathecode.payments.views import SubscriptionSeatView

    mock_get_subscription.return_value = build_subscription(user_id=2)

    request = factory.put("/v2/payments/subscriptions/99/seats", data={}, format="json")
    force_authenticate(request, user=MagicMock(id=1))

    resp = SubscriptionSeatView.as_view()(request, subscription_id=99)
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert resp.data == {"detail": "only-owner-allowed", "status_code": 403}


@patch("breathecode.payments.views.get_user_language", return_value="en")
@patch("breathecode.payments.views.actions.create_seat")
@patch("breathecode.payments.views.actions.validate_seats_limit")
@patch("breathecode.payments.views.actions.normalize_replace_seat", return_value=[])
@patch("breathecode.payments.views.actions.normalize_add_seats")
@patch("breathecode.payments.views.SubscriptionSeatView._get_team")
@patch("breathecode.payments.views.SubscriptionSeatView._get_subscription")
def test_put_add_seats_happy_path(
    mock_get_subscription,
    mock_get_team,
    mock_norm_add,
    mock_norm_replace,
    mock_validate_limit,
    mock_create_seat,
    mock_lang,
    factory,
):
    """PUT add_seats returns 207 and creates seats (mocked)."""
    from breathecode.payments.views import SubscriptionSeatView

    mock_get_subscription.return_value = build_subscription(user_id=1)
    team = build_team()
    mock_get_team.return_value = team

    mock_norm_add.return_value = [
        MagicMock(email="a@b.com", user=10, seat_multiplier=2, first_name="A", last_name="B"),
        MagicMock(email="c@d.com", user=None, seat_multiplier=1, first_name="C", last_name="D"),
    ]

    seat1 = build_seat(id=1, email="a@b.com", user_id=10, seat_multiplier=2)
    seat2 = build_seat(id=2, email="c@d.com", user_id=None, seat_multiplier=1)
    mock_create_seat.side_effect = [seat1, seat2]

    request = factory.put(
        "/v2/payments/subscriptions/99/seats",
        data={
            "add_seats": [
                {"email": "a@b.com", "seat_multiplier": 2, "first_name": "A", "last_name": "B"},
                {"email": "c@d.com", "seat_multiplier": 1, "first_name": "C", "last_name": "D"},
            ]
        },
        format="json",
    )
    force_authenticate(request, user=MagicMock(id=1))

    resp = SubscriptionSeatView.as_view()(request, subscription_id=99)

    assert resp.status_code == status.HTTP_207_MULTI_STATUS
    # verify calls
    mock_validate_limit.assert_called_once_with(team, ANY, [], ANY)
    assert mock_create_seat.call_count == 2
    # payload validation
    assert resp.data["errors"] == []
    assert resp.data["data"] == [
        {
            "id": 1,
            "email": "a@b.com",
            "user": 10,
            "seat_multiplier": 2,
            "is_active": True,
            "seat_log": [],
        },
        {
            "id": 2,
            "email": "c@d.com",
            "user": None,
            "seat_multiplier": 1,
            "is_active": True,
            "seat_log": [],
        },
    ]


@patch("breathecode.payments.views.get_user_language", return_value="en")
@patch("breathecode.payments.views.actions.create_seat")
@patch("breathecode.payments.views.actions.validate_seats_limit")
@patch("breathecode.payments.views.actions.normalize_replace_seat", return_value=[])
@patch("breathecode.payments.views.actions.normalize_add_seats")
@patch("breathecode.payments.views.SubscriptionSeatView._get_team")
@patch("breathecode.payments.views.SubscriptionSeatView._get_subscription")
def test_put_add_seats_with_errors(
    mock_get_subscription,
    mock_get_team,
    mock_norm_add,
    mock_norm_replace,
    mock_validate_limit,
    mock_create_seat,
    mock_lang,
    factory,
):
    """PUT add_seats returns 207 and includes errors when a seat fails to be created (mocked)."""
    from breathecode.payments.views import SubscriptionSeatView
    from capyc.rest_framework.exceptions import ValidationException

    mock_get_subscription.return_value = build_subscription(user_id=1)
    team = build_team()
    mock_get_team.return_value = team

    mock_norm_add.return_value = [
        MagicMock(email="a@b.com", user=10, seat_multiplier=2, first_name="A", last_name="B"),
        MagicMock(email="bad", user=None, seat_multiplier=1, first_name="C", last_name="D"),
    ]

    seat1 = build_seat(id=1, email="a@b.com", user_id=10, seat_multiplier=2)
    # first succeeds, second raises validation error
    mock_create_seat.side_effect = [seat1, ValidationException("invalid-email", code=400)]

    request = factory.put(
        "/v2/payments/subscriptions/99/seats",
        data={
            "add_seats": [
                {"email": "a@b.com", "seat_multiplier": 2, "first_name": "A", "last_name": "B"},
                {"email": "bad", "seat_multiplier": 1, "first_name": "C", "last_name": "D"},
            ]
        },
        format="json",
    )
    force_authenticate(request, user=MagicMock(id=1))

    resp = SubscriptionSeatView.as_view()(request, subscription_id=99)

    assert resp.status_code == status.HTTP_207_MULTI_STATUS
    # one success, one error
    assert len(resp.data["data"]) == 1
    assert len(resp.data["errors"]) == 1
    assert resp.data["data"][0]["email"] == "a@b.com"
    assert resp.data["errors"] == [{"message": "invalid-email", "code": 400}]


@pytest.mark.django_db
@patch("breathecode.payments.views.get_user_language", return_value="en")
@patch("breathecode.payments.views.SubscriptionSeat.objects")
@patch("breathecode.payments.views.SubscriptionSeatView._get_subscription")
def test_delete_happy_path(mock_get_subscription, mock_seat_objects, mock_lang, factory):
    """DELETE deactivates an existing seat (mocked)."""
    from breathecode.payments.views import SubscriptionSeatView

    subscription = build_subscription(user_id=5)
    mock_get_subscription.return_value = subscription

    seat = build_seat(id=77, email="bye@x.com", is_active=True)
    # configure manager chain .filter(...).first() -> seat
    mock_qs = MagicMock()
    mock_qs.first.return_value = seat
    mock_seat_objects.filter.return_value = mock_qs

    request = factory.delete("/v2/payments/subscriptions/99/seats/77")
    force_authenticate(request, user=MagicMock(id=5))

    resp = SubscriptionSeatView.as_view()(request, subscription_id=99, seat_id=77)

    assert resp.status_code == status.HTTP_204_NO_CONTENT
    assert seat.is_active is False
    assert seat.user is None
    seat.save.assert_called_once_with(update_fields=["is_active", "user"])


@patch("breathecode.payments.views.get_user_language", return_value="en")
@patch("breathecode.payments.views.SubscriptionSeat.objects")
@patch("breathecode.payments.views.SubscriptionSeatView._get_subscription")
def test_delete_not_found_raises(mock_get_subscription, mock_seat_objects, mock_lang, factory):
    """DELETE with non-existing seat returns 404 (mocked)."""
    from breathecode.payments.views import SubscriptionSeatView

    subscription = build_subscription(user_id=5)
    mock_get_subscription.return_value = subscription

    mock_qs = MagicMock()
    mock_qs.first.return_value = None
    mock_seat_objects.filter.return_value = mock_qs

    request = factory.delete("/v2/payments/subscriptions/99/seats/77")
    force_authenticate(request, user=MagicMock(id=5))

    resp = SubscriptionSeatView.as_view()(request, subscription_id=99, seat_id=77)
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert resp.data == {"detail": "seat-not-found", "status_code": 404}


# Integration tests (DB)


@pytest.mark.django_db
def test_put_add_seats_integration_db(client):
    """Integration: PUT add_seats creates seats and returns 207 with data and no errors."""
    # Arrange DB
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
    sub = Subscription.objects.create(
        user=owner,
        academy=academy,
        paid_at=timezone.now(),
        next_payment_at=timezone.now(),
    )
    team = SubscriptionBillingTeam.objects.create(subscription=sub, name="Team", seats_limit=10)

    u1 = User.objects.create(username="u1", email="a@b.com")
    u2 = User.objects.create(username="u2", email="c@d.com")

    payload = {
        "add_seats": [
            {"email": "a@b.com", "seat_multiplier": 2, "first_name": "A", "last_name": "B"},
            {"email": "c@d.com", "seat_multiplier": 1, "first_name": "C", "last_name": "D"},
        ]
    }

    # Patch only normalizers and validator; create_seat will persist real records
    with (
        patch("breathecode.payments.views.actions.normalize_add_seats") as mock_norm,
        patch("breathecode.payments.views.actions.normalize_replace_seat", return_value=[]),
        patch("breathecode.payments.views.actions.validate_seats_limit"),
    ):
        # return dicts as normalize_add_seats would in production
        mock_norm.return_value = [
            {"email": "a@b.com", "user": u1, "seat_multiplier": 2},
            {"email": "c@d.com", "user": u2, "seat_multiplier": 1},
        ]

        # create_seat to persist into DB
        def create_seat_side_effect(email, user, seat_multiplier, billing_team, lang):
            return SubscriptionSeat.objects.create(
                billing_team=team,
                user=user,
                email=email,
                seat_multiplier=seat_multiplier,
            )

        with patch("breathecode.payments.views.actions.create_seat", side_effect=create_seat_side_effect):
            client.force_authenticate(user=owner)
            url = f"/v2/payments/subscription/{sub.id}/billing-team/seat"
            resp = client.put(url, data=payload, content_type="application/json")

    # Assert
    assert resp.status_code == status.HTTP_207_MULTI_STATUS
    data = resp.json()
    assert data["errors"] == []
    emails = sorted([x["email"] for x in data["data"]])
    assert emails == ["a@b.com", "c@d.com"]
    assert SubscriptionSeat.objects.filter(billing_team=team, is_active=True).count() == 2


@pytest.mark.django_db
def test_delete_happy_path_integration_db(client):
    """Integration: DELETE deactivates an existing seat in DB."""
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
    sub = Subscription.objects.create(
        user=owner,
        academy=academy,
        paid_at=timezone.now(),
        next_payment_at=timezone.now(),
    )
    team = SubscriptionBillingTeam.objects.create(subscription=sub, name="Team", seats_limit=10)
    seat = SubscriptionSeat.objects.create(billing_team=team, email="bye@x.com", user=None, seat_multiplier=1)

    client.force_authenticate(user=owner)
    url = f"/v2/payments/subscription/{sub.id}/billing-team/seat/{seat.id}"
    resp = client.delete(url)

    assert resp.status_code == status.HTTP_204_NO_CONTENT
    seat.refresh_from_db()
    assert seat.is_active is False
    assert seat.user is None
