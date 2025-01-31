import random

import pytest

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def arange(db, bc: Breathecode, fake):

    yield


def test_with_one_micro_cohort(enable_signals, bc: Breathecode):
    enable_signals()

    model_micro_cohort = bc.database.create(
        cohort={"available_as_saas": True},
    )

    model_main_cohort = bc.database.create(
        user=1,
        cohort_user={"role": "STUDENT"},
        cohort={"available_as_saas": True, "micro_cohorts": [model_micro_cohort.cohort]},
    )

    assert bc.database.list_of("admissions.CohortUser") == [
        {
            **bc.format.to_dict(model_main_cohort.cohort_user),
        },
        {
            **bc.format.to_dict(model_main_cohort.cohort_user),
            "id": 2,
            "cohort_id": 1,
            "finantial_status": "FULLY_PAID",
        },
    ]


def test_with_many_micro_cohorts(enable_signals, bc: Breathecode):
    enable_signals()

    model_micro_cohort = bc.database.create(
        cohort=[{"available_as_saas": True}, {"available_as_saas": True}],
    )

    model_main_cohort = bc.database.create(
        user=1,
        cohort_user={"role": "STUDENT"},
        cohort={
            "available_as_saas": True,
            "micro_cohorts": [model_micro_cohort.cohort[0], model_micro_cohort.cohort[1]],
        },
    )

    assert bc.database.list_of("admissions.CohortUser") == [
        {
            **bc.format.to_dict(model_main_cohort.cohort_user),
        },
        {
            **bc.format.to_dict(model_main_cohort.cohort_user),
            "id": 2,
            "cohort_id": 1,
            "finantial_status": "FULLY_PAID",
        },
        {
            **bc.format.to_dict(model_main_cohort.cohort_user),
            "id": 3,
            "cohort_id": 2,
            "finantial_status": "FULLY_PAID",
        },
    ]


def test_with_cohort_users_previously_created(enable_signals, bc: Breathecode):
    enable_signals()

    model_micro_cohorts = bc.database.create(
        cohort=[{"available_as_saas": True}, {"available_as_saas": True}],
    )

    model_cohort_users = bc.database.create(
        user=1,
        cohort_user=[
            {"role": "STUDENT", "cohort": model_micro_cohorts.cohort[0]},
            {"role": "STUDENT", "cohort": model_micro_cohorts.cohort[1]},
        ],
    )

    model_main_cohort = bc.database.create(
        cohort_user={"user": model_cohort_users.user, "role": "STUDENT"},
        cohort={"available_as_saas": True, "micro_cohorts": [*model_micro_cohorts.cohort]},
    )

    assert bc.database.list_of("admissions.CohortUser") == [
        {
            **bc.format.to_dict(model_main_cohort.cohort_user),
            "id": 1,
            "cohort_id": 1,
        },
        {
            **bc.format.to_dict(model_main_cohort.cohort_user),
            "id": 2,
            "cohort_id": 2,
        },
        {
            **bc.format.to_dict(model_main_cohort.cohort_user),
        },
    ]
