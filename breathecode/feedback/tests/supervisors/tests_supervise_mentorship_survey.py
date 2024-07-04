from datetime import datetime, timedelta
from logging import Logger
from unittest.mock import MagicMock, call

import pytest
from asgiref.sync import sync_to_async

from breathecode.feedback.supervisors import supervise_mentorship_survey
from breathecode.monitoring.models import Supervisor as SupervisorModel
from breathecode.monitoring.models import SupervisorIssue
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from breathecode.utils.decorators import supervisor as supervisor_decorator
from capyc.rest_framework import pytest as capy


class Supervisor:

    def __init__(self, bc: Breathecode):
        self._bc = bc

    def list(self):
        supervisors = SupervisorModel.objects.all()
        return [
            {
                "task_module": supervisor.task_module,
                "task_name": supervisor.task_name,
            }
            for supervisor in supervisors
        ]

    @sync_to_async
    def alist(self):
        return self.list()

    def reset(self):
        SupervisorModel.objects.all().delete()

    @sync_to_async
    def areset(self):
        return self.reset()

    def log(self, module, name):
        issues = SupervisorIssue.objects.filter(supervisor__task_module=module, supervisor__task_name=name)
        return [x.error for x in issues]

    @sync_to_async
    def alog(self, module, name):
        return self.log(module, name)

    def get(self, module, name) -> SupervisorModel | None:
        return SupervisorModel.objects.filter(task_module=module, task_name=name).first()

    @sync_to_async
    def aget(self, module, name) -> SupervisorModel | None:
        return self.get(module, name)


@pytest.fixture
def supervisor(db, bc: Breathecode):
    yield Supervisor(bc)


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    from breathecode.monitoring.models import Supervisor

    monkeypatch.setattr("logging.Logger.error", MagicMock())
    monkeypatch.setattr("breathecode.payments.supervisors.MIN_PENDING_SESSIONS", 2)
    monkeypatch.setattr("breathecode.payments.supervisors.MIN_CANCELLED_SESSIONS", 2)

    fn_module = "breathecode.feedback.supervisors"
    fn_name = "supervise_mentorship_survey"
    Supervisor.objects.get_or_create(
        task_module=fn_module,
        task_name=fn_name,
        defaults={
            "delta": timedelta(seconds=3600),
            "ran_at": None,
        },
    )

    yield


def db(data={}):
    return {
        "delta": timedelta(seconds=3600),
        "id": 0,
        "ran_at": None,
        "task_module": "",
        "task_name": "",
        **data,
    }


def tests_no_sessions(supervisor: Supervisor):
    supervisor.reset()
    supervise_mentorship_survey()

    # assert supervisor.list() == [
    #     {
    #         'task_module': 'breathecode.feedback.supervisors',
    #         'task_name': 'supervise_mentorship_survey',
    #     },
    # ]
    assert supervisor.log("breathecode.feedback.supervisors", "supervise_mentorship_survey") == []

    # sessions = MentorshipSession.objects.filter(status='COMPLETED',
    #                                             started_at__isnull=False,
    #                                             ended_at__isnull=False,
    #                                             mentor__isnull=False,
    #                                             mentee__isnull=False,
    #                                             created_at__lte=utc_now,
    #                                             created_at__gte=utc_now - timedelta(days=5))


@pytest.mark.parametrize(
    "status",
    [
        "PENDING",
        "STARTED",
        "FAILED",
        "IGNORED",
        "CANCELED",
    ],
)
@pytest.mark.parametrize(
    "started_at, ended_at, mentor, mentee",
    [
        (None, None, 0, 0),
        (timedelta(0), None, 0, 0),
        (None, timedelta(0), 0, 0),
        (None, None, 1, 0),
        (None, None, 0, 1),
    ],
)
def tests_invalid_sessions(
    database: capy.Database, supervisor: Supervisor, utc_now: datetime, status, started_at, ended_at, mentor, mentee
):
    mentorship_session = {"status": status, "mentor": mentor, "mentee": mentee}
    if started_at is not None:
        mentorship_session["started_at"] = utc_now + started_at

    if ended_at is not None:
        mentorship_session["ended_at"] = utc_now + ended_at

    database.create(user=1, mentorship_session=(2, mentorship_session))

    supervise_mentorship_survey()

    assert supervisor.log("breathecode.feedback.supervisors", "supervise-mentorshipsurvey") == []


@pytest.mark.parametrize(
    "delta, answer",
    [
        (timedelta(0), False),
        (timedelta(0), True),
        (timedelta(minutes=5, seconds=1), True),
    ],
)
def tests_found_sessions(
    database: capy.Database, supervisor: Supervisor, utc_now: datetime, delta: timedelta, answer: bool
):
    mentorship_session = {
        "status": "COMPLETED",
        "mentor": 1,
        "mentee": 1,
        "started_at": utc_now,
        "ended_at": utc_now + delta,
    }

    if answer:
        answer = [{"mentorship_session_id": n + 1, "token_id": n + 1} for n in range(2)]

    database.create(user=1, mentorship_session=(2, mentorship_session), feedback__answer=answer, token=2)

    supervise_mentorship_survey()

    assert supervisor.log("breathecode.feedback.supervisors", "supervise_mentorship_survey") == []


def tests_sessions_with_no_surveys(database: capy.Database, supervisor: Supervisor, utc_now: datetime):
    delta = timedelta(minutes=5, seconds=1)
    mentorship_session = {
        "status": "COMPLETED",
        "mentor": 1,
        "mentee": 1,
        "started_at": utc_now,
        "ended_at": utc_now + delta,
    }

    database.create(user=1, mentorship_session=(2, mentorship_session))

    supervise_mentorship_survey()

    assert supervisor.log("breathecode.feedback.supervisors", "supervise_mentorship_survey") == [
        "Session 1 hasn't a survey",
        "Session 2 hasn't a survey",
    ]
