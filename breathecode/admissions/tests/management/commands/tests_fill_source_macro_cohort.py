import pytest

from breathecode.admissions.management.commands.fill_source_macro_cohort import Command, fill_source_macro_cohort
from breathecode.admissions.models import CohortUser
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db):
    yield


def test_dry_run_does_not_write(bc: Breathecode):
    micro = bc.database.create(cohort=1)
    macro = bc.database.create(
        user=1,
        cohort={"micro_cohorts": [micro.cohort]},
        cohort_user=1,
    )
    micro_cu = CohortUser.objects.create(user=macro.user, cohort=micro.cohort, role="STUDENT")

    stats = fill_source_macro_cohort(commit=False)

    assert stats["filled"] == 1
    micro_cu.refresh_from_db()
    assert micro_cu.source_macro_cohort_id is None


def test_one_macro_fills_its_micros(bc: Breathecode):
    micro = bc.database.create(cohort=1)
    macro = bc.database.create(
        user=1,
        cohort={"micro_cohorts": [micro.cohort]},
        cohort_user=1,
    )
    micro_cu = CohortUser.objects.create(user=macro.user, cohort=micro.cohort, role="STUDENT")

    stats = fill_source_macro_cohort(commit=True)

    micro_cu.refresh_from_db()
    assert stats["filled"] == 1
    assert micro_cu.source_macro_cohort_id == macro.cohort.id


def test_two_disjoint_macros_fill_both(bc: Breathecode):
    micros = bc.database.create(cohort=2)
    user = bc.database.create(user=1).user
    macro_a = bc.database.create(
        user=user,
        cohort={"micro_cohorts": [micros.cohort[0]]},
        cohort_user={"role": "STUDENT"},
    )
    macro_b = bc.database.create(
        user=user,
        cohort={"micro_cohorts": [micros.cohort[1]]},
        cohort_user={"role": "STUDENT"},
    )
    cu_a = CohortUser.objects.create(user=user, cohort=micros.cohort[0], role="STUDENT")
    cu_b = CohortUser.objects.create(user=user, cohort=micros.cohort[1], role="STUDENT")

    fill_source_macro_cohort(commit=True)

    cu_a.refresh_from_db()
    cu_b.refresh_from_db()
    assert cu_a.source_macro_cohort_id == macro_a.cohort.id
    assert cu_b.source_macro_cohort_id == macro_b.cohort.id


def test_three_macros_only_disjoint_macro_fills(bc: Breathecode):
    micros = bc.database.create(cohort=4)
    shared_a, shared_b, unique_c, unique_d = micros.cohort
    user = bc.database.create(user=1).user
    overlapping_a = bc.database.create(
        user=user,
        cohort={"micro_cohorts": [shared_a, shared_b]},
        cohort_user={"role": "STUDENT"},
    )
    overlapping_b = bc.database.create(
        user=user,
        cohort={"micro_cohorts": [shared_a, unique_c]},
        cohort_user={"role": "STUDENT"},
    )
    disjoint = bc.database.create(
        user=user,
        cohort={"micro_cohorts": [unique_d]},
        cohort_user={"role": "STUDENT"},
    )
    cu_shared_a = CohortUser.objects.create(user=user, cohort=shared_a, role="STUDENT")
    cu_shared_b = CohortUser.objects.create(user=user, cohort=shared_b, role="STUDENT")
    cu_unique_c = CohortUser.objects.create(user=user, cohort=unique_c, role="STUDENT")
    cu_unique_d = CohortUser.objects.create(user=user, cohort=unique_d, role="STUDENT")

    fill_source_macro_cohort(commit=True)

    cu_shared_a.refresh_from_db()
    cu_shared_b.refresh_from_db()
    cu_unique_c.refresh_from_db()
    cu_unique_d.refresh_from_db()
    assert cu_shared_a.source_macro_cohort_id is None
    assert cu_shared_b.source_macro_cohort_id is None
    assert cu_unique_c.source_macro_cohort_id is None
    assert cu_unique_d.source_macro_cohort_id == disjoint.cohort.id
    assert overlapping_a.cohort.id != disjoint.cohort.id
    assert overlapping_b.cohort.id != disjoint.cohort.id


def test_does_not_overwrite_existing_fk(bc: Breathecode):
    micros = bc.database.create(cohort=2)
    user = bc.database.create(user=1).user
    other_macro = bc.database.create(cohort=1).cohort
    bc.database.create(
        user=user,
        cohort={"micro_cohorts": [micros.cohort[0]]},
        cohort_user={"role": "STUDENT"},
    )
    cu = CohortUser.objects.create(
        user=user,
        cohort=micros.cohort[0],
        role="STUDENT",
        source_macro_cohort=other_macro,
    )

    stats = fill_source_macro_cohort(commit=True)

    cu.refresh_from_db()
    assert stats["skipped_existing"] == 1
    assert cu.source_macro_cohort_id == other_macro.id


def test_command_commit_flag(bc: Breathecode):
    micro = bc.database.create(cohort=1)
    macro = bc.database.create(
        user=1,
        cohort={"micro_cohorts": [micro.cohort]},
        cohort_user=1,
    )
    micro_cu = CohortUser.objects.create(user=macro.user, cohort=micro.cohort, role="STUDENT")

    Command().handle(commit=False)
    micro_cu.refresh_from_db()
    assert micro_cu.source_macro_cohort_id is None

    Command().handle(commit=True)
    micro_cu.refresh_from_db()
    assert micro_cu.source_macro_cohort_id == macro.cohort.id
