import pytest
from django.utils import timezone

from breathecode.payments.management.commands.fix_plan_financings_how_many_installments import Command
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

UTC_NOW = timezone.now()


@pytest.fixture(autouse=True)
def setup(db):
    yield


def test_with_one_plan_financing(bc: Breathecode):

    how_many_installments = 3
    model = bc.database.create(bag={"how_many_installments": how_many_installments}, invoice=1)
    plan_financing = {
        "invoices": [model.invoice],
        "plan_expires_at": UTC_NOW,
        "monthly_price": 5,
    }
    plan_financing_models = bc.database.create(plan_financing=plan_financing)

    command = Command()
    result = command.handle()

    expected = {
        **bc.format.to_dict(plan_financing_models.plan_financing),
        "how_many_installments": how_many_installments,
    }

    assert result == None
    assert bc.database.list_of("payments.PlanFinancing") == [expected]
