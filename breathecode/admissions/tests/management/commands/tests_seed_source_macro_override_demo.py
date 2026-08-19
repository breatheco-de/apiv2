import pytest

from breathecode.admissions.management.commands.seed_source_macro_override_demo import Command, PREFIX
from breathecode.admissions.models import Cohort, CohortUser
from breathecode.admissions.services.completion import evaluate_cohort_user_completion
from breathecode.assignments.models import Task
from breathecode.authenticate.models import Token
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db):
    yield


def test_command_requires_existing_user():
    with pytest.raises(Exception):
        Command().handle(user="missing-user-xyz", academy=1, clear=False, hours_length=24)


def test_seeds_override_demo_and_token(bc: Breathecode):
    model = bc.database.create(user=1, academy=1, city=1, country=1)
    Command().handle(user=str(model.user.id), academy=model.academy.id, clear=False, hours_length=24)

    micro = Cohort.objects.get(slug=f"{PREFIX}-micro")
    macro = Cohort.objects.get(slug=f"{PREFIX}-macro")
    micro_cu = CohortUser.objects.get(user=model.user, cohort=micro, role="STUDENT")
    token = Token.objects.filter(user=model.user, token_type="temporal").first()

    assert macro.micro_cohorts.filter(id=micro.id).exists()
    assert micro_cu.source_macro_cohort_id == macro.id
    assert micro_cu.educational_status == "ACTIVE"
    assert token is not None
    assert Task.objects.filter(user=model.user, cohort=micro, task_type="PROJECT").count() == 2

    result = evaluate_cohort_user_completion(micro_cu)
    assert result["is_complete"] is False
    assert result["used_macro_override"] is True
    assert result["pending_required_count"] == 1
