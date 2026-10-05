import random

import pytest

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def arange(db, bc: Breathecode, fake):

    def wrapper(task=1, cohort_user=1, syllabus_version={}, cohort=1):
        return bc.database.create(
            task=task,
            cohort_user=cohort_user,
            cohort=cohort,
        )

    yield wrapper


def test_no_graduated_status(enable_signals, bc: Breathecode):
    enable_signals()

    model_micro_cohort = bc.database.create(
        user=1,
        cohort_user={"role": "STUDENT"},
        cohort={"available_as_saas": True},
    )

    model_main_cohort = bc.database.create(
        cohort_user={"user": model_micro_cohort.user, "role": "STUDENT"},
        cohort={"available_as_saas": True, "micro_cohorts": [model_micro_cohort.cohort]},
    )

    model_micro_cohort.cohort_user.educational_status = "POSTPONED"
    model_micro_cohort.cohort_user.save()

    assert bc.database.list_of("admissions.CohortUser") == [
        {
            **bc.format.to_dict(model_micro_cohort.cohort_user),
            "educational_status": "POSTPONED",
        },
        {
            **bc.format.to_dict(model_main_cohort.cohort_user),
        },
    ]


def test_with_one_micro_cohort(enable_signals, bc: Breathecode):
    enable_signals()

    model_micro_cohort = bc.database.create(
        user=1,
        cohort_user={"role": "STUDENT"},
        cohort={"available_as_saas": True},
    )

    model_main_cohort = bc.database.create(
        cohort_user={"user": model_micro_cohort.user, "role": "STUDENT"},
        cohort={"available_as_saas": True, "micro_cohorts": [model_micro_cohort.cohort]},
    )

    model_micro_cohort.cohort_user.educational_status = "GRADUATED"
    model_micro_cohort.cohort_user.save()

    assert bc.database.list_of("admissions.CohortUser") == [
        {
            **bc.format.to_dict(model_micro_cohort.cohort_user),
            "educational_status": "GRADUATED",
        },
        {
            **bc.format.to_dict(model_main_cohort.cohort_user),
            "educational_status": "GRADUATED",
        },
    ]


def test_with_many_micro_cohorts_one_graduated(enable_signals, bc: Breathecode):
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

    model_cohort_users.cohort_user[0].educational_status = "GRADUATED"
    model_cohort_users.cohort_user[0].save()

    assert bc.database.list_of("admissions.CohortUser") == [
        {
            **bc.format.to_dict(model_cohort_users.cohort_user[0]),
            "educational_status": "GRADUATED",
        },
        {
            **bc.format.to_dict(model_cohort_users.cohort_user[1]),
        },
        {
            **bc.format.to_dict(model_main_cohort.cohort_user),
        },
    ]


def test_with_many_micro_cohorts_many_graduated(enable_signals, bc: Breathecode):
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

    model_cohort_users.cohort_user[0].educational_status = "GRADUATED"
    model_cohort_users.cohort_user[0].save()

    model_cohort_users.cohort_user[1].educational_status = "GRADUATED"
    model_cohort_users.cohort_user[1].save()

    assert bc.database.list_of("admissions.CohortUser") == [
        {
            **bc.format.to_dict(model_cohort_users.cohort_user[0]),
            "educational_status": "GRADUATED",
        },
        {
            **bc.format.to_dict(model_cohort_users.cohort_user[1]),
            "educational_status": "GRADUATED",
        },
        {
            **bc.format.to_dict(model_main_cohort.cohort_user),
            "educational_status": "GRADUATED",
        },
    ]
