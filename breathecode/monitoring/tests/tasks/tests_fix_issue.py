import datetime
from datetime import timedelta
from logging import Logger
from unittest.mock import MagicMock, call

import pytest
from asgiref.sync import sync_to_async

from breathecode.monitoring.models import Supervisor as SupervisorModel
from breathecode.monitoring.models import SupervisorIssue
from breathecode.monitoring.tasks import fix_issue
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from breathecode.utils.decorators import issue as issue_decorator
from breathecode.utils.decorators import paths
from breathecode.utils.decorators import supervisor as supervisor_decorator
from capyc.rest_framework import pytest as capy

PATHS = paths.copy()


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


@pytest.fixture
def supervisor(db, bc: Breathecode):
    yield Supervisor(bc)


@supervisor_decorator(delta=timedelta(days=1))
def my_supervisor():
    pass


@issue_decorator(my_supervisor)
def issue_returns_none():
    return None


@issue_decorator(my_supervisor)
def issue_returns_false():
    return False


@issue_decorator(my_supervisor)
def issue_returns_true():
    return True


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("logging.Logger.error", MagicMock())

    yield


@pytest.fixture(autouse=True, scope="module")
def setup_module():
    yield

    keys = paths.copy()
    for x in keys:
        if x not in PATHS:
            paths.remove(x)


def db(data={}):
    return {
        "delta": timedelta(seconds=3600),
        "id": 0,
        "ran_at": None,
        "task_module": "",
        "task_name": "",
        **data,
    }


def tests_not_found(database: capy.Database):
    database.create()

    fix_issue.delay(1)

    assert database.list_of("monitoring.Supervisor") == []
    assert database.list_of("monitoring.SupervisorIssue") == []
    assert Logger.error.call_args_list == [
        call("Issue 1 not found", exc_info=True),
    ]


def tests_issue_with_no_code(database: capy.Database, format: capy.Format):
    task_module = "breathecode.monitoring.tests.tasks.tests_fix_issue"
    task_name = "my_supervisor"
    model = database.create(
        supervisor={
            "task_module": "breathecode.monitoring.tests.tasks.tests_fix_issue",
            "task_name": "my_supervisor",
            "delta": timedelta(days=1),
        },
        supervisor_issue=1,
    )

    fix_issue.delay(1)

    assert database.list_of("monitoring.Supervisor") == [
        db(
            {
                "id": 1,
                "task_module": task_module,
                "task_name": task_name,
                "delta": timedelta(days=1),
            }
        ),
    ]
    assert database.list_of("monitoring.SupervisorIssue") == [format.to_obj_repr(model.supervisor_issue)]
    assert Logger.error.call_args_list == [
        call("Issue 1 has no code", exc_info=True),
    ]


@pytest.mark.parametrize(
    "task_module, code, error",
    [
        ("x", "all_ok_supervisor", "Module x not found"),
        (
            "breathecode.monitoring.tests.tasks.tests_fix_issue",
            "x",
            "Supervisor breathecode.monitoring.tests.tasks.tests_fix_issue.x not found",
        ),
    ],
)
def tests_supervisor_handler_not_found(
    database: capy.Database, format: capy.Format, error: str, task_module: str, code: str
):
    task_name = "my_supervisor"
    model = database.create(
        supervisor={
            "task_module": task_module,
            "task_name": task_name,
            "delta": timedelta(days=1),
        },
        supervisor_issue={"code": code},
    )

    fix_issue.delay(1)

    assert database.list_of("monitoring.Supervisor") == [
        db(
            {
                "id": 1,
                "task_module": task_module,
                "task_name": task_name,
                "delta": timedelta(days=1),
            }
        ),
    ]
    assert database.list_of("monitoring.SupervisorIssue") == [format.to_obj_repr(model.supervisor_issue)]
    assert Logger.error.call_args_list == [
        call(error, exc_info=True),
    ]


@pytest.mark.parametrize("res", [None, False, True])
def tests_issue_returns_x(database: capy.Database, format: capy.Format, res: str, utc_now: datetime):
    model = database.create(
        supervisor={
            "task_module": "breathecode.monitoring.tests.tasks.tests_fix_issue",
            "task_name": "my_supervisor",
            "delta": timedelta(days=1),
        },
        supervisor_issue={"code": f"issue-returns-{str(res).lower()}"},
    )

    fix_issue.delay(1)

    assert database.list_of("monitoring.Supervisor") == [
        db(
            {
                "id": 1,
                "task_module": "breathecode.monitoring.tests.tasks.tests_fix_issue",
                "task_name": "my_supervisor",
                "delta": timedelta(days=1),
                "ran_at": None,
            }
        ),
    ]
    assert database.list_of("monitoring.SupervisorIssue") == [
        {
            **format.to_obj_repr(model.supervisor_issue),
            "attempts": 1,
            "fixed": res,
            "ran_at": utc_now,
        }
    ]
    assert Logger.error.call_args_list == []


def tests_issue_with_3_attempts(database: capy.Database, format: capy.Format):
    code = "issue-returns-true"
    task_module = "breathecode.monitoring.tests.tasks.tests_fix_issue"
    model = database.create(
        supervisor={
            "task_module": task_module,
            "task_name": "my_supervisor",
            "delta": timedelta(days=1),
        },
        supervisor_issue={
            "code": code,
            "attempts": 3,
        },
    )

    fix_issue.delay(1)

    assert database.list_of("monitoring.Supervisor") == [
        db(
            {
                "id": 1,
                "task_module": task_module,
                "task_name": "my_supervisor",
                "delta": timedelta(days=1),
                "ran_at": None,
            }
        ),
    ]
    assert database.list_of("monitoring.SupervisorIssue") == [
        {
            **format.to_obj_repr(model.supervisor_issue),
            "attempts": 3,
            "fixed": None,
        }
    ]
    assert Logger.error.call_args_list == [
        call(f"Supervisor {task_module}.{code.replace('-', '_')} has reached max attempts", exc_info=True),
    ]
