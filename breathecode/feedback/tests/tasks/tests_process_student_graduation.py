"""
Test /academy/survey
"""

import logging
from unittest.mock import MagicMock, call

import pytest
from django.utils import timezone

from breathecode.feedback.tasks import process_student_graduation
from capyc.rest_framework import pytest as capy

now = timezone.now()


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("logging.Logger.info", MagicMock())
    monkeypatch.setattr("logging.Logger.error", MagicMock())
    yield


def db_item(data={}):
    return {
        "author_id": 0,
        "cohort_id": 0,
        "comments": None,
        "id": 0,
        "is_public": False,
        "lang": None,
        "nps_previous_rating": None,
        "platform_id": "",
        "public_url": None,
        "status": "PENDING",
        "status_text": None,
        "total_rating": None,
        **data,
    }


def test_cohort_not_found(database: capy.Database):
    process_student_graduation.delay(1, 1)

    assert logging.Logger.info.call_args_list == []
    assert logging.Logger.error.call_args_list == [
        call("Invalid cohort id: 1", exc_info=True),
    ]
    assert database.list_of("feedback.Review") == []


def test_user_not_found(database: capy.Database):
    database.create(cohort=1, city=1, country=1)

    process_student_graduation.delay(1, 1)

    assert logging.Logger.info.call_args_list == []
    assert logging.Logger.error.call_args_list == [
        call("Invalid user id: 1", exc_info=True),
    ]
    assert database.list_of("feedback.Review") == []


def test_no_answers(database: capy.Database):
    database.create(cohort=1, city=1, country=1, user=1)

    process_student_graduation.delay(1, 1)

    assert logging.Logger.info.call_args_list == [call("0 will be requested for student 1, avg NPS score of None")]
    assert logging.Logger.error.call_args_list == []
    assert database.list_of("feedback.Review") == []


def test_answers_not_answered(database: capy.Database):
    model = database.create(
        cohort=1,
        city=1,
        country=1,
        user=1,
        feedback__answer=[{"score": 4, "token_id": n + 1} for n in range(2)],
        token=2,
        review_platform=2,
    )

    process_student_graduation.delay(1, 1)

    assert logging.Logger.info.call_args_list == [call("2 will be requested for student 1, avg NPS score of None")]
    assert logging.Logger.error.call_args_list == []
    assert database.list_of("feedback.Review") == [
        db_item(
            {
                "id": n + 1,
                "cohort_id": 1,
                "author_id": 1,
                "platform_id": model.review_platform[n].slug,
                "nps_previous_rating": None,
            }
        )
        for n in range(2)
    ]


def test_answers_answered__low_avg(database: capy.Database):
    model = database.create(
        cohort=1,
        city=1,
        country=1,
        user=1,
        feedback__answer=[
            {
                "score": 4,
                "token_id": n + 1,
                "status": "ANSWERED",
            }
            for n in range(2)
        ],
        token=2,
        review_platform=2,
    )

    process_student_graduation.delay(1, 1)

    assert logging.Logger.info.call_args_list == [
        call("No reviews requested for student 1 because average NPS score is 4.0"),
    ]
    assert logging.Logger.error.call_args_list == []
    assert database.list_of("feedback.Review") == []


def test_answers_answered__good_avg(database: capy.Database):
    model = database.create(
        cohort=1,
        city=1,
        country=1,
        user=1,
        feedback__answer=[
            {
                "score": 8,
                "token_id": n + 1,
                "status": "ANSWERED",
            }
            for n in range(2)
        ],
        token=2,
        review_platform=2,
    )

    process_student_graduation.delay(1, 1)

    assert logging.Logger.info.call_args_list == [
        call("2 will be requested for student 1, avg NPS score of 8.0"),
    ]
    assert logging.Logger.error.call_args_list == []
    assert database.list_of("feedback.Review") == [
        db_item(
            {
                "id": n + 1,
                "cohort_id": 1,
                "author_id": 1,
                "platform_id": model.review_platform[n].slug,
                "nps_previous_rating": 8.0,
            }
        )
        for n in range(2)
    ]
