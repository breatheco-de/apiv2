from datetime import datetime, timedelta
from logging import Logger
from unittest.mock import MagicMock, call

import pytest
from asgiref.sync import sync_to_async

from breathecode.feedback.supervisors import no_survey_for_session
from breathecode.feedback.tasks import send_mentorship_session_survey
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
    monkeypatch.setattr("breathecode.feedback.tasks.send_mentorship_session_survey.delay", MagicMock())
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


def tests_issue_not_found(database: capy.Database):
    res = no_survey_for_session(1)

    assert res is None
    assert database.list_of("mentorship.MentorshipSession") == []
    assert send_mentorship_session_survey.delay.call_args_list == []


def tests_mentorship_session_not_found(database: capy.Database, format: capy.Format):
    fn_module = "breathecode.feedback.supervisors"
    fn_name = "supervise_mentorship_survey"
    database.create(
        supervisor={
            "task_module": fn_module,
            "task_name": fn_name,
        },
        supervisor_issue={
            "code": "no-survey-for-session",
            "fixed": None,
            "params": {
                "session_id": 1,
            },
        },
    )

    res = no_survey_for_session(1)

    assert res is None
    assert database.list_of("mentorship.MentorshipSession") == []
    assert send_mentorship_session_survey.delay.call_args_list == []


def tests_no_answer(database: capy.Database, format: capy.Format):
    fn_module = "breathecode.feedback.supervisors"
    fn_name = "supervise_mentorship_survey"
    model = database.create(
        mentorship_session=1,
        supervisor={
            "task_module": fn_module,
            "task_name": fn_name,
        },
        supervisor_issue={
            "code": "no-survey-for-session",
            "fixed": None,
            "params": {
                "session_id": 1,
            },
        },
    )

    res = no_survey_for_session(1)

    assert res is None
    assert database.list_of("mentorship.MentorshipSession") == [
        format.to_obj_repr(model.mentorship_session),
    ]

    assert send_mentorship_session_survey.delay.call_args_list == [call(1)]


def tests_answer(database: capy.Database, format: capy.Format):
    fn_module = "breathecode.feedback.supervisors"
    fn_name = "supervise_mentorship_survey"
    model = database.create(
        mentorship_session=1,
        supervisor={
            "task_module": fn_module,
            "task_name": fn_name,
        },
        supervisor_issue={
            "code": "no-survey-for-session",
            "fixed": None,
            "params": {
                "session_id": 1,
            },
        },
        feedback__answer=1,
        city=1,
        country=1,
    )

    res = no_survey_for_session(1)

    assert res is True
    assert database.list_of("mentorship.MentorshipSession") == [
        format.to_obj_repr(model.mentorship_session),
    ]

    assert send_mentorship_session_survey.delay.call_args_list == []
