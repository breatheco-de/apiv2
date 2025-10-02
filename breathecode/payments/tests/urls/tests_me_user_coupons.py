import pytest
from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status


@pytest.fixture
def utc_now():
    return timezone.now()


def coupon_serializer(coupon, is_valid=False):
    return {
        "slug": coupon.slug,
        "discount_type": coupon.discount_type,
        "discount_value": coupon.discount_value,
        "referral_type": coupon.referral_type,
        "referral_value": coupon.referral_value,
        "auto": coupon.auto,
        "offered_at": coupon.offered_at.isoformat().replace("+00:00", "Z") if coupon.offered_at else None,
        "expires_at": coupon.expires_at.isoformat().replace("+00:00", "Z") if coupon.expires_at else None,
        "is_valid": is_valid,
    }


@pytest.mark.django_db
def test_get__without_coupons(client, bc):
    """Test /v1/payments/me/user/coupons with user that has no coupons"""
    user = bc.database.create(user=1)
    client.force_authenticate(user=user.user)

    url = reverse_lazy("payments:me_user_coupons")
    response = client.get(url)
    json = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert json == []


@pytest.mark.django_db
def test_get__with_valid_coupon(client, bc, utc_now):
    """Test /v1/payments/me/user/coupons with valid user coupon"""
    model = bc.database.create(
        user=1,
        plan={
            "is_renewable": True,
            "trial_duration": 0,
            "trial_duration_unit": "DAY",
            "time_of_life": 30,
            "time_of_life_unit": "DAY",
        },
        coupon={
            "discount_type": "PERCENT_OFF",
            "discount_value": 10,
            "referral_type": "NO_REFERRAL",
            "auto": False,
            "offered_at": utc_now - timezone.timedelta(days=1),
            "expires_at": utc_now + timezone.timedelta(days=1),
            "how_many_offers": 1,
            "allowed_user_id": 1,
        },
    )
    # Manually link coupon to plan
    model.coupon.plans.add(model.plan)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:me_user_coupons")
    response = client.get(url)
    json = response.json()

    expected = [coupon_serializer(model.coupon, is_valid=True)]

    assert response.status_code == status.HTTP_200_OK
    assert json == expected


@pytest.mark.django_db
def test_get__with_invalid_coupon_expired(client, bc, utc_now):
    """Test /v1/payments/me/user/coupons with expired coupon"""
    model = bc.database.create(
        user=1,
        plan={
            "is_renewable": True,
            "trial_duration": 0,
            "trial_duration_unit": "DAY",
            "time_of_life": 30,
            "time_of_life_unit": "DAY",
        },
        coupon={
            "discount_type": "PERCENT_OFF",
            "discount_value": 10,
            "referral_type": "NO_REFERRAL",
            "auto": False,
            "offered_at": utc_now - timezone.timedelta(days=2),
            "expires_at": utc_now - timezone.timedelta(days=1),
            "how_many_offers": 1,
            "allowed_user_id": 1,
        },
    )
    # Manually link coupon to plan
    model.coupon.plans.add(model.plan)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:me_user_coupons")
    response = client.get(url)
    json = response.json()

    # The view filters out expired coupons, so we expect an empty list
    expected = []

    assert response.status_code == status.HTTP_200_OK
    assert json == expected


@pytest.mark.django_db
def test_get__with_multiple_coupons(client, bc, utc_now):
    """Test /v1/payments/me/user/coupons with multiple user coupons"""
    model = bc.database.create(
        user=1,
        plan={
            "is_renewable": True,
            "trial_duration": 0,
            "trial_duration_unit": "DAY",
            "time_of_life": 30,
            "time_of_life_unit": "DAY",
        },
        coupon=[
            {
                "discount_type": "PERCENT_OFF",
                "discount_value": 10,
                "referral_type": "NO_REFERRAL",
                "auto": False,
                "offered_at": utc_now - timezone.timedelta(days=1),
                "expires_at": utc_now + timezone.timedelta(days=1),
                "how_many_offers": 1,
                "allowed_user_id": 1,
            },
            {
                "discount_type": "FIXED_PRICE",
                "discount_value": 50,
                "referral_type": "NO_REFERRAL",
                "auto": True,
                "offered_at": utc_now - timezone.timedelta(days=1),
                "expires_at": utc_now + timezone.timedelta(days=1),
                "how_many_offers": -1,  # Unlimited
                "allowed_user_id": 1,
            },
        ],
    )
    # Manually link coupons to plan
    model.coupon[0].plans.add(model.plan)
    model.coupon[1].plans.add(model.plan)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:me_user_coupons")
    response = client.get(url)
    json = response.json()

    # The view sorts by -id (descending), so coupon[1] (created second, higher ID) comes first
    expected = [
        coupon_serializer(model.coupon[1], is_valid=True),
        coupon_serializer(model.coupon[0], is_valid=True),
    ]

    assert response.status_code == status.HTTP_200_OK
    assert json == expected


@pytest.mark.django_db
def test_put__coupon_not_found(client, bc):
    """Test PUT /v1/payments/me/user/coupons/{slug} with non-existent coupon"""
    user = bc.database.create(user=1)
    client.force_authenticate(user=user.user)

    url = reverse_lazy("payments:me_user_coupons_detail", kwargs={"coupon_slug": "non-existent"})
    response = client.put(url, content_type="application/json")
    json = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert json["detail"] == "coupon-not-found"


@pytest.mark.django_db
def test_put__other_user_coupon(client, bc):
    """Test PUT /v1/payments/me/user/coupons/{slug} with coupon belonging to another user"""
    # Create user 1 and coupon belonging to user 1
    model = bc.database.create(
        user=1,
        coupon={
            "discount_type": "PERCENT_OFF",
            "discount_value": 10,
            "referral_type": "NO_REFERRAL",
            "auto": False,
            "allowed_user_id": 1,  # Belongs to user 1
        },
    )
    # Create user 2
    user2 = bc.database.create(user=1)
    # Authenticate as user 2
    client.force_authenticate(user=user2.user)

    url = reverse_lazy("payments:me_user_coupons_detail", kwargs={"coupon_slug": model.coupon.slug})
    response = client.put(url, content_type="application/json")
    json = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert json["detail"] == "coupon-not-found"
