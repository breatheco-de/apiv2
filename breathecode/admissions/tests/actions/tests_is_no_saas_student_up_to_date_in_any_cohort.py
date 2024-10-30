"""
Test mentorhips
"""

import capyc.pytest as capy
import pytest

from ...actions import is_no_saas_student_up_to_date_in_any_cohort


@pytest.fixture(autouse=True)
def setup(db: None):
    yield


@pytest.mark.parametrize("default", [True, False])
def test_default(database: capy.Database, default: bool):
    model = database.create(user=1)
    res = is_no_saas_student_up_to_date_in_any_cohort(model.user, default=default)
    assert res == default


class TestNoSaasStudent:

    @pytest.mark.parametrize("educational_status", ["ACTIVE", "GRADUATED"])
    @pytest.mark.parametrize("finantial_status", ["FULLY_PAID", "UP_TO_DATE"])
    @pytest.mark.parametrize(
        "extra",
        [
            {"cohort": {"available_as_saas": False}, "academy": {"available_as_saas": True}},
            {"cohort": {"available_as_saas": None}, "academy": {"available_as_saas": False}},
        ],
    )
    def test_true(self, database: capy.Database, educational_status: str, finantial_status: str, extra: dict):
        model = database.create(
            user=1,
            city=1,
            country=1,
            cohort_user={"educational_status": educational_status, "finantial_status": finantial_status},
            **extra,
        )
        res = is_no_saas_student_up_to_date_in_any_cohort(model.user, default=False)
        assert res == True

    @pytest.mark.parametrize("educational_status", ["ACTIVE"])
    @pytest.mark.parametrize("finantial_status", ["LATE"])
    @pytest.mark.parametrize(
        "extra",
        [
            {"cohort": {"available_as_saas": False}, "academy": {"available_as_saas": True}},
            {"cohort": {"available_as_saas": None}, "academy": {"available_as_saas": False}},
        ],
    )
    def test_false(self, database: capy.Database, educational_status: str, finantial_status: str, extra: dict):
        model = database.create(
            user=1,
            city=1,
            country=1,
            cohort_user={"educational_status": educational_status, "finantial_status": finantial_status},
            **extra,
        )
        res = is_no_saas_student_up_to_date_in_any_cohort(model.user, default=True)
        assert res == False


@pytest.mark.parametrize("default", [True, False])
def test_default(database: capy.Database, default: bool):
    model = database.create(user=1)
    res = is_no_saas_student_up_to_date_in_any_cohort(model.user, default=default)
    assert res == default


class TestSaasStudent:

    @pytest.mark.parametrize("educational_status", ["ACTIVE", "GRADUATED"])
    @pytest.mark.parametrize("finantial_status", ["FULLY_PAID", "UP_TO_DATE"])
    @pytest.mark.parametrize(
        "extra",
        [
            {"cohort": {"available_as_saas": True}, "academy": {"available_as_saas": False}},
            {"cohort": {"available_as_saas": None}, "academy": {"available_as_saas": True}},
        ],
    )
    def test_default_false(self, database: capy.Database, educational_status: str, finantial_status: str, extra: dict):
        model = database.create(
            user=1,
            city=1,
            country=1,
            cohort_user={"educational_status": educational_status, "finantial_status": finantial_status},
            **extra,
        )
        res = is_no_saas_student_up_to_date_in_any_cohort(model.user, default=False)
        assert res == False

    @pytest.mark.parametrize("educational_status", ["ACTIVE"])
    @pytest.mark.parametrize("finantial_status", ["LATE"])
    @pytest.mark.parametrize(
        "extra",
        [
            {"cohort": {"available_as_saas": True}, "academy": {"available_as_saas": False}},
            {"cohort": {"available_as_saas": None}, "academy": {"available_as_saas": True}},
        ],
    )
    def test_default_true(self, database: capy.Database, educational_status: str, finantial_status: str, extra: dict):
        model = database.create(
            user=1,
            city=1,
            country=1,
            cohort_user={"educational_status": educational_status, "finantial_status": finantial_status},
            **extra,
        )
        res = is_no_saas_student_up_to_date_in_any_cohort(model.user, default=True)
        assert res == True
