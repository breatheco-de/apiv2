import pytest

from breathecode.payments.models import CohortSetCohort
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db):
    yield


def test_adds_new_micro_to_cohort_sets_containing_macro(enable_signals, bc: Breathecode):
    enable_signals()

    model = bc.database.create(
        academy={"available_as_saas": True},
        cohort=[{"available_as_saas": True}, {"available_as_saas": True}],
        cohort_set=1,
        cohort_set_cohort={"cohort_id": 1, "cohort_set_id": 1},
    )
    macro, micro = model.cohort

    macro.micro_cohorts.add(micro)

    assert CohortSetCohort.objects.filter(cohort_set=model.cohort_set, cohort=micro).exists()
    assert set(model.cohort_set.cohorts.values_list("id", flat=True)) == {macro.id, micro.id}


def test_adds_new_micro_via_set_like_api(enable_signals, bc: Breathecode):
    enable_signals()

    model = bc.database.create(
        academy={"available_as_saas": True},
        cohort=[
            {"available_as_saas": True},
            {"available_as_saas": True},
            {"available_as_saas": True},
        ],
        cohort_set=1,
        cohort_set_cohort={"cohort_id": 1, "cohort_set_id": 1},
    )
    macro, micro_a, micro_b = model.cohort
    macro.micro_cohorts.add(micro_a)

    macro.micro_cohorts.set([micro_a, micro_b])

    assert set(model.cohort_set.cohorts.values_list("id", flat=True)) == {macro.id, micro_a.id, micro_b.id}


def test_adds_new_micro_to_all_cohort_sets_containing_macro(enable_signals, bc: Breathecode):
    enable_signals()

    model = bc.database.create(
        academy={"available_as_saas": True},
        cohort=[{"available_as_saas": True}, {"available_as_saas": True}],
        cohort_set=2,
        cohort_set_cohort=[
            {"cohort_id": 1, "cohort_set_id": 1},
            {"cohort_id": 1, "cohort_set_id": 2},
        ],
    )
    macro, micro = model.cohort

    macro.micro_cohorts.add(micro)

    for cohort_set in model.cohort_set:
        assert CohortSetCohort.objects.filter(cohort_set=cohort_set, cohort=micro).exists()
        assert set(cohort_set.cohorts.values_list("id", flat=True)) == {macro.id, micro.id}


def test_idempotent_when_micro_already_in_cohort_set(enable_signals, bc: Breathecode):
    enable_signals()

    model = bc.database.create(
        academy={"available_as_saas": True},
        cohort=[{"available_as_saas": True}, {"available_as_saas": True}],
        cohort_set=1,
        cohort_set_cohort=[
            {"cohort_id": 1, "cohort_set_id": 1},
            {"cohort_id": 2, "cohort_set_id": 1},
        ],
    )
    macro, micro = model.cohort

    macro.micro_cohorts.add(micro)

    assert CohortSetCohort.objects.filter(cohort_set=model.cohort_set, cohort=micro).count() == 1
    assert set(model.cohort_set.cohorts.values_list("id", flat=True)) == {macro.id, micro.id}


def test_skips_micro_not_available_as_saas(enable_signals, bc: Breathecode):
    enable_signals()

    model = bc.database.create(
        academy={"available_as_saas": True},
        cohort=[{"available_as_saas": True}, {"available_as_saas": False}],
        cohort_set=1,
        cohort_set_cohort={"cohort_id": 1, "cohort_set_id": 1},
    )
    macro, micro = model.cohort

    macro.micro_cohorts.add(micro)

    assert list(macro.micro_cohorts.all()) == [micro]
    assert not CohortSetCohort.objects.filter(cohort_set=model.cohort_set, cohort=micro).exists()
    assert set(model.cohort_set.cohorts.values_list("id", flat=True)) == {macro.id}


def test_does_not_remove_micro_from_cohort_set_when_unlinked(enable_signals, bc: Breathecode):
    enable_signals()

    model = bc.database.create(
        academy={"available_as_saas": True},
        cohort=[{"available_as_saas": True}, {"available_as_saas": True}],
        cohort_set=1,
        cohort_set_cohort=[
            {"cohort_id": 1, "cohort_set_id": 1},
            {"cohort_id": 2, "cohort_set_id": 1},
        ],
    )
    macro, micro = model.cohort
    macro.micro_cohorts.add(micro)

    macro.micro_cohorts.remove(micro)

    assert not macro.micro_cohorts.filter(id=micro.id).exists()
    assert CohortSetCohort.objects.filter(cohort_set=model.cohort_set, cohort=micro).exists()
