import random
import sys
from unittest.mock import MagicMock, call, patch

import pytest

from breathecode.feedback.management.commands.garbagecollect_answers import Command
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from breathecode.tests.mixins.legacy import LegacyAPITestCase

from ...mixins import FeedbackTestCase


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("breathecode.feedback.signals.survey_answered.send_robust", MagicMock())


@patch("sys.stdout.write", MagicMock())
def test_run_handler(db, bc: Breathecode):
    surveys = [{"cohort_id": n} for n in range(1, 4)]
    cohort_users = [
        {"cohort_id": n, "user_id": n, "educational_status": random.choice(["POSTPONED", "SUSPENDED", "DROPPED"])}
        for n in range(1, 4)
    ]
    answers = (
        [
            {
                "survey_id": n,
                "cohort_id": n,
                "user_id": n,
                "status": random.choice(["ANSWERED", "OPENED"]),
                "score": random.randint(1, 10),
            }
            for n in range(1, 4)
        ]
        + [
            {
                "survey_id": n,
                "cohort_id": n,
                "user_id": n,
                "status": random.choice(["PENDING", "SENT", "EXPIRED"]),
                "score": None,
            }
            for n in range(1, 4)
        ]
        + [
            {
                "survey_id": n,
                "cohort_id": n,
                "user_id": n,
                "status": random.choice(["ANSWERED", "OPENED"]),
                "score": None,
            }
            for n in range(1, 4)
        ]
        + [
            {
                "survey_id": n,
                "cohort_id": n,
                "user_id": n,
                "status": random.choice(["ANSWERED", "OPENED"]),
                "score": random.randint(1, 10),
            }
            for n in range(1, 4)
        ]
        + [
            {
                "survey_id": n,
                "cohort_id": n,
                "user_id": n,
                "status": random.choice(["PENDING", "SENT", "EXPIRED"]),
                "score": None,
            }
            for n in range(1, 4)
        ]
        + [
            {
                "survey_id": n,
                "cohort_id": n,
                "user_id": n,
                "status": random.choice(["ANSWERED", "OPENED"]),
                "score": None,
            }
            for n in range(1, 4)
        ]
    )

    with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):

        model = bc.database.create(user=3, survey=surveys, answer=answers, cohort=3, cohort_user=cohort_users)

    answer_db = bc.format.to_dict(model.answer)

    # reset in this line because some people left print in some places
    sys.stdout.write.call_args_list = []

    with patch("sys.stderr.write", MagicMock()):
        command = Command()
        command.handle()

        assert sys.stderr.write.call_args_list == []

    assert bc.database.list_of("feedback.Survey") == bc.format.to_dict(model.survey)

    # this ignore the answers is not answered or opened
    assert bc.database.list_of("feedback.Answer") == [
        bc.format.to_dict(answer_db[0]),
        bc.format.to_dict(answer_db[1]),
        bc.format.to_dict(answer_db[2]),
        bc.format.to_dict(answer_db[6]),
        bc.format.to_dict(answer_db[7]),
        bc.format.to_dict(answer_db[8]),
        bc.format.to_dict(answer_db[9]),
        bc.format.to_dict(answer_db[10]),
        bc.format.to_dict(answer_db[11]),
        bc.format.to_dict(answer_db[15]),
        bc.format.to_dict(answer_db[16]),
        bc.format.to_dict(answer_db[17]),
    ]

    assert sys.stdout.write.call_args_list == [
        call("Successfully removed invalid survey answers\n"),
        call("Successfully removed 0 old survey answers\n"),
        call("Successfully completed garbage collection\n"),
    ]
