import pytest
from django.utils import timezone

from breathecode.payments.actions import get_available_coupons
from breathecode.payments.models import Coupon, Seller


def _now():
    return timezone.now()


@pytest.mark.django_db
def test_includes_general_coupon(bc):
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
            "discount_type": Coupon.Discount.PERCENT_OFF,
            "discount_value": 10,
            "referral_type": Coupon.Referral.NO_REFERRAL,
            "auto": True,
            "offered_at": _now() - timezone.timedelta(days=1),
            "expires_at": _now() + timezone.timedelta(days=1),
            "how_many_offers": -1,
            "allowed_user_id": None,
        },
    )
    model.coupon.plans.add(model.plan)

    result = get_available_coupons(model.plan, coupons=[], user=model.user)
    assert [x.id for x in result] == [model.coupon.id]
    assert len(result) == 1
    assert result[0].slug == model.coupon.slug
    assert result[0].discount_type == Coupon.Discount.PERCENT_OFF


@pytest.mark.django_db
def test_excludes_user_restricted_coupon_mismatch_user(bc):
    model = bc.database.create(
        user=2,
        plan={
            "is_renewable": True,
            "trial_duration": 0,
            "trial_duration_unit": "DAY",
            "time_of_life": 30,
            "time_of_life_unit": "DAY",
        },
        coupon={
            "discount_type": Coupon.Discount.PERCENT_OFF,
            "discount_value": 10,
            "referral_type": Coupon.Referral.NO_REFERRAL,
            "auto": True,
            "offered_at": _now() - timezone.timedelta(days=1),
            "expires_at": _now() + timezone.timedelta(days=1),
            "how_many_offers": -1,
            "allowed_user_id": 1,
        },
    )
    model.coupon.plans.add(model.plan)

    result = get_available_coupons(model.plan, coupons=[], user=model.user[1])
    assert result == []
    assert len(result) == 0


@pytest.mark.django_db
def test_includes_user_restricted_coupon_matching_user(bc):
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
            "discount_type": Coupon.Discount.PERCENT_OFF,
            "discount_value": 10,
            "referral_type": Coupon.Referral.NO_REFERRAL,
            "auto": True,
            "offered_at": _now() - timezone.timedelta(days=1),
            "expires_at": _now() + timezone.timedelta(days=1),
            "how_many_offers": -1,
            "allowed_user_id": 1,
        },
    )
    model.coupon.plans.add(model.plan)

    result = get_available_coupons(model.plan, coupons=[], user=model.user)
    assert [x.id for x in result] == [model.coupon.id]
    assert len(result) == 1
    assert result[0].allowed_user_id == model.user.id


@pytest.mark.django_db
def test_excludes_referral_coupon_when_plan_excludes(bc):
    model = bc.database.create(
        user=1,
        plan={
            "is_renewable": True,
            "trial_duration": 0,
            "trial_duration_unit": "DAY",
            "time_of_life": 30,
            "time_of_life_unit": "DAY",
            "exclude_from_referral_program": True,
        },
        coupon={
            "discount_type": Coupon.Discount.PERCENT_OFF,
            "discount_value": 10,
            "referral_type": Coupon.Referral.PERCENTAGE,
            "auto": True,
            "offered_at": _now() - timezone.timedelta(days=1),
            "expires_at": _now() + timezone.timedelta(days=1),
            "how_many_offers": -1,
        },
    )
    model.coupon.plans.add(model.plan)

    result = get_available_coupons(model.plan, coupons=[], user=model.user)
    assert result == []
    assert len(result) == 0


@pytest.mark.django_db
def test_includes_only_requested_codes_for_manual_coupons(bc):
    model = bc.database.create(
        user=1,
        plan={
            "is_renewable": True,
            "trial_duration": 0,
            "trial_duration_unit": "DAY",
            "time_of_life": 30,
            "time_of_life_unit": "DAY",
        },
    )
    c1 = bc.database.create(
        coupon={
            "slug": "CODE1",
            "auto": False,
            "discount_type": Coupon.Discount.PERCENT_OFF,
            "discount_value": 0.1,
            "referral_type": Coupon.Referral.NO_REFERRAL,
            "offered_at": _now() - timezone.timedelta(days=1),
            "expires_at": _now() + timezone.timedelta(days=1),
            "how_many_offers": -1,
        }
    ).coupon
    c2 = bc.database.create(
        coupon={
            "slug": "CODE2",
            "auto": False,
            "discount_type": Coupon.Discount.PERCENT_OFF,
            "discount_value": 0.1,
            "referral_type": Coupon.Referral.NO_REFERRAL,
            "offered_at": _now() - timezone.timedelta(days=1),
            "expires_at": _now() + timezone.timedelta(days=1),
            "how_many_offers": -1,
        }
    ).coupon
    c1.plans.add(model.plan)
    c2.plans.add(model.plan)

    result = get_available_coupons(model.plan, coupons=["CODE2"], user=model.user)
    assert [x.slug for x in result] == ["CODE2"]
    assert len(result) == 1
    assert result[0].auto is False
    assert result[0].slug != "CODE1"


@pytest.mark.django_db
def test_excludes_coupon_when_seller_is_the_user(bc):
    model = bc.database.create(
        user=1,
        plan={
            "is_renewable": True,
            "trial_duration": 0,
            "trial_duration_unit": "DAY",
            "time_of_life": 30,
            "time_of_life_unit": "DAY",
        },
    )
    seller = Seller.objects.create(user=model.user, name="Seller")
    coupon = bc.database.create(
        coupon={
            "auto": True,
            "discount_type": Coupon.Discount.PERCENT_OFF,
            "discount_value": 0.1,
            "referral_type": Coupon.Referral.NO_REFERRAL,
            "offered_at": _now() - timezone.timedelta(days=1),
            "expires_at": _now() + timezone.timedelta(days=1),
            "how_many_offers": -1,
        }
    ).coupon
    coupon.seller = seller
    coupon.save()
    coupon.plans.add(model.plan)

    result = get_available_coupons(model.plan, coupons=[], user=model.user)
    assert result == []
    assert len(result) == 0


@pytest.mark.django_db
def test_only_sent_coupons_returns_only_requested_valid(bc):
    model = bc.database.create(
        user=1,
        plan={
            "is_renewable": True,
            "trial_duration": 0,
            "trial_duration_unit": "DAY",
            "time_of_life": 30,
            "time_of_life_unit": "DAY",
        },
    )

    # Two valid manual coupons
    c1 = bc.database.create(
        coupon={
            "slug": "CODE1",
            "auto": False,
            "discount_type": Coupon.Discount.PERCENT_OFF,
            "discount_value": 0.15,
            "referral_type": Coupon.Referral.NO_REFERRAL,
            "offered_at": _now() - timezone.timedelta(days=1),
            "expires_at": _now() + timezone.timedelta(days=1),
            "how_many_offers": -1,
        }
    ).coupon
    c2 = bc.database.create(
        coupon={
            "slug": "CODE2",
            "auto": False,
            "discount_type": Coupon.Discount.PERCENT_OFF,
            "discount_value": 0.2,
            "referral_type": Coupon.Referral.NO_REFERRAL,
            "offered_at": _now() - timezone.timedelta(days=1),
            "expires_at": _now() + timezone.timedelta(days=1),
            "how_many_offers": -1,
        }
    ).coupon

    # One invalid (expired) coupon also sent
    c3 = bc.database.create(
        coupon={
            "slug": "CODE3",
            "auto": False,
            "discount_type": Coupon.Discount.PERCENT_OFF,
            "discount_value": 0.3,
            "referral_type": Coupon.Referral.NO_REFERRAL,
            "offered_at": _now() - timezone.timedelta(days=3),
            "expires_at": _now() - timezone.timedelta(days=1),
            "how_many_offers": -1,
        }
    ).coupon

    # Associate coupons to plan
    for c in (c1, c2, c3):
        c.plans.add(model.plan)

    result = get_available_coupons(
        model.plan, coupons=["CODE1", "CODE2", "CODE3"], user=model.user, only_sent_coupons=True
    )

    assert sorted([x.slug for x in result]) == ["CODE1", "CODE2"]
    assert len(result) == 2
    slugs = {x.slug for x in result}
    assert "CODE3" not in slugs


@pytest.mark.django_db
def test_only_sent_coupons_empty_returns_empty_even_with_auto(bc):
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
            # create an auto coupon that would otherwise be valid
            "auto": True,
            "discount_type": Coupon.Discount.PERCENT_OFF,
            "discount_value": 0.1,
            "referral_type": Coupon.Referral.NO_REFERRAL,
            "offered_at": _now() - timezone.timedelta(days=1),
            "expires_at": _now() + timezone.timedelta(days=1),
            "how_many_offers": -1,
        },
    )
    model.coupon.plans.add(model.plan)

    result = get_available_coupons(model.plan, coupons=[], user=model.user, only_sent_coupons=True)
    assert result == []
    assert len(result) == 0
