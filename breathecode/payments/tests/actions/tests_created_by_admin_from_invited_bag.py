import pytest

from breathecode.payments.actions import created_by_admin_from_invited_bag
from breathecode.payments.models import Bag
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

pytestmark = pytest.mark.django_db


def test_returns_false_when_bag_is_not_invited(bc: Breathecode):
    model = bc.database.create(bag={"type": "BAG", "status": "PAID", "how_many_installments": 2})
    assert created_by_admin_from_invited_bag(model.bag) is False


def test_returns_false_when_no_matching_invite(bc: Breathecode):
    model = bc.database.create(
        bag={"type": "INVITED", "status": "PAID", "how_many_installments": 2},
    )
    assert created_by_admin_from_invited_bag(model.bag) is False


def test_returns_true_when_invite_is_admin_managed(bc: Breathecode):
    model = bc.database.create(
        bag={"type": "INVITED", "status": "PAID", "how_many_installments": 2},
        user_invite={"created_by_admin": True},
    )
    invite = model.user_invite
    invite.user = model.user
    invite.academy = model.academy
    invite.email = model.user.email
    invite.save()
    assert created_by_admin_from_invited_bag(model.bag) is True


def test_prefers_invite_linked_to_bag_plan(bc: Breathecode):
    model = bc.database.create(
        bag={"type": "INVITED", "status": "PAID", "how_many_installments": 2},
        plan=2,
        user_invite=[
            {"created_by_admin": False},
            {"created_by_admin": True},
        ],
    )
    bag = Bag.objects.get(id=model.bag.id)
    bag.plans.set([model.plan[1]])
    for invite in model.user_invite:
        invite.user = model.user
        invite.academy = model.academy
        invite.email = model.user.email
        invite.save()
    model.plan[0].invites.add(model.user_invite[0])
    model.plan[1].invites.add(model.user_invite[1])

    assert created_by_admin_from_invited_bag(bag) is True
