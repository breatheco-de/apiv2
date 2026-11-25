import pytest
from capyc.rest_framework.exceptions import ValidationException
from django.contrib.auth.models import User

from breathecode.admissions.models import Academy
from breathecode.registry.actions import assert_user_can_claim_asset
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

pytestmark = pytest.mark.django_db


def test_claim_blocked_when_no_owner_or_author(bc: Breathecode):
    model = bc.database.create(user=1, asset=1)
    model.asset.owner = None
    model.asset.author = None
    model.asset.academy = None
    model.asset.save()

    with pytest.raises(ValidationException) as exc:
        assert_user_can_claim_asset(model.asset, model.user)

    assert exc.value.slug == "asset-claim-requires-owner-or-author"


def test_claim_forbidden_when_user_is_neither_owner_nor_author(bc: Breathecode):
    model = bc.database.create(user=2, academy=1, asset=1)
    owner, claimant = model.user
    model.asset.owner = owner
    model.asset.author = None
    model.asset.academy = None
    model.asset.save()
    Academy.objects.filter(id=model.academy.id).update(owner=None)

    with pytest.raises(ValidationException) as exc:
        assert_user_can_claim_asset(model.asset, claimant, academy_id=model.academy.id)

    assert exc.value.slug == "asset-claim-forbidden"


def test_claim_allowed_for_owner(bc: Breathecode):
    model = bc.database.create(user=1, asset=1)
    model.asset.owner = model.user
    model.asset.author = None
    model.asset.academy = None
    model.asset.save()

    assert_user_can_claim_asset(model.asset, model.user)


def test_claim_allowed_for_author(bc: Breathecode):
    model = bc.database.create(user=1, asset=1)
    model.asset.owner = None
    model.asset.author = model.user
    model.asset.academy = None
    model.asset.save()

    assert_user_can_claim_asset(model.asset, model.user)


def test_claim_allowed_when_pending_owner_in_validated_data(bc: Breathecode):
    model = bc.database.create(user=1, asset=1)
    model.asset.owner = None
    model.asset.author = None
    model.asset.academy = None
    model.asset.save()

    assert_user_can_claim_asset(model.asset, model.user, validated_data={"owner": model.user})


def test_claim_allowed_when_asset_owner_matches_academy_owner(bc: Breathecode):
    model = bc.database.create(user=2, academy=1, asset=1)
    academy_owner, staff = model.user
    model.asset.owner = academy_owner
    model.asset.author = None
    model.asset.academy = None
    model.asset.save()
    Academy.objects.filter(id=model.academy.id).update(owner=academy_owner.id)

    assert_user_can_claim_asset(model.asset, staff, academy_id=model.academy.id)


def test_claim_forbidden_when_academy_owner_does_not_match_asset_owner(bc: Breathecode):
    model = bc.database.create(user=2, academy=1, asset=1)
    asset_owner, staff = model.user
    other_academy_owner = User.objects.create(username="academy-owner", email="academy-owner@example.com")
    model.asset.owner = asset_owner
    model.asset.author = None
    model.asset.academy = None
    model.asset.save()
    Academy.objects.filter(id=model.academy.id).update(owner=other_academy_owner.id)

    with pytest.raises(ValidationException) as exc:
        assert_user_can_claim_asset(model.asset, staff, academy_id=model.academy.id)

    assert exc.value.slug == "asset-claim-forbidden"
