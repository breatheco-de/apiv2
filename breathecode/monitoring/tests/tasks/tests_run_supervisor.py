from datetime import datetime, timedelta
from logging import Logger
from unittest.mock import MagicMock, call

import pytest
from asgiref.sync import sync_to_async

import capyc.django.pytest.fixtures as dfx
from breathecode.monitoring.models import Supervisor as SupervisorModel
from breathecode.monitoring.models import SupervisorIssue
from breathecode.monitoring.tasks import run_supervisor
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from breathecode.utils.decorators import paths
from breathecode.utils.decorators import supervisor as supervisor_decorator

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
def all_ok_supervisor():
    pass


@supervisor_decorator(delta=timedelta(days=1))
def something_went_wrong_supervisor():
    for n in range(3):
        yield f"Something went wrong {n}"


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


def tests_not_found(database: dfx.Database, supervisor: Supervisor):
    database.create()

    run_supervisor.delay(1)

    assert supervisor.list() == []
    assert database.list_of("monitoring.Supervisor") == []
    assert database.list_of("monitoring.SupervisorIssue") == []
    assert Logger.error.call_args_list == [
        call("Supervisor 1 not found", exc_info=True),
    ]


@pytest.mark.parametrize(
    "task_module, task_name, error",
    [
        ("x", "all_ok_supervisor", "Module x not found"),
        (
            "breathecode.monitoring.tests.tasks.tests_run_supervisor",
            "x",
            "Supervisor breathecode.monitoring.tests.tasks.tests_run_supervisor.x not found",
        ),
    ],
)
def tests_supervisor_handler_not_found(database: dfx.Database, supervisor: Supervisor, task_module, task_name, error):
    database.create(
        supervisor={
            "task_module": task_module,
            "task_name": task_name,
            "delta": timedelta(days=1),
        }
    )

    run_supervisor.delay(1)

    assert supervisor.list() == [
        {
            "task_module": task_module,
            "task_name": task_name,
        },
    ]
    assert supervisor.log(task_module, task_name) == []
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
    assert database.list_of("monitoring.SupervisorIssue") == []
    assert Logger.error.call_args_list == [
        call(error, exc_info=True),
    ]


def tests_supervision_with_not_issues(database: dfx.Database, supervisor: Supervisor, utc_now: datetime):
    database.create(
        supervisor={
            "task_module": "breathecode.monitoring.tests.tasks.tests_run_supervisor",
            "task_name": "all_ok_supervisor",
            "delta": timedelta(days=1),
        }
    )

    run_supervisor.delay(1)

    assert supervisor.list() == [
        {
            "task_module": "breathecode.monitoring.tests.tasks.tests_run_supervisor",
            "task_name": "all_ok_supervisor",
        },
    ]
    assert supervisor.log("breathecode.monitoring.tests.tasks.tests_run_supervisor", "all_ok_supervisor") == []
    assert database.list_of("monitoring.Supervisor") == [
        db(
            {
                "id": 1,
                "task_module": "breathecode.monitoring.tests.tasks.tests_run_supervisor",
                "task_name": "all_ok_supervisor",
                "delta": timedelta(days=1),
                "ran_at": utc_now,
            }
        ),
    ]
    assert database.list_of("monitoring.SupervisorIssue") == []
    assert Logger.error.call_args_list == []


def tests_supervision_with_issues(database: dfx.Database, supervisor: Supervisor, utc_now: datetime):
    database.create(
        supervisor={
            "task_module": "breathecode.monitoring.tests.tasks.tests_run_supervisor",
            "task_name": "something_went_wrong_supervisor",
            "delta": timedelta(days=1),
        }
    )

    run_supervisor.delay(1)

    assert supervisor.list() == [
        {
            "task_module": "breathecode.monitoring.tests.tasks.tests_run_supervisor",
            "task_name": "something_went_wrong_supervisor",
        },
    ]
    assert supervisor.log(
        "breathecode.monitoring.tests.tasks.tests_run_supervisor", "something_went_wrong_supervisor"
    ) == [f"Something went wrong {x}" for x in range(3)]
    assert database.list_of("monitoring.Supervisor") == [
        db(
            {
                "id": 1,
                "task_module": "breathecode.monitoring.tests.tasks.tests_run_supervisor",
                "task_name": "something_went_wrong_supervisor",
                "delta": timedelta(days=1),
                "ran_at": utc_now,
            }
        ),
    ]
    assert database.list_of("monitoring.SupervisorIssue") == [
        {
            "error": "Something went wrong 0",
            "id": 1,
            "occurrences": 1,
            "ran_at": utc_now,
            "supervisor_id": 1,
            "attempts": 0,
            "code": None,
            "fixed": None,
            "params": None,
        },
        {
            "error": "Something went wrong 1",
            "id": 2,
            "occurrences": 1,
            "ran_at": utc_now,
            "supervisor_id": 1,
            "attempts": 0,
            "code": None,
            "fixed": None,
            "params": None,
        },
        {
            "error": "Something went wrong 2",
            "id": 3,
            "occurrences": 1,
            "ran_at": utc_now,
            "supervisor_id": 1,
            "attempts": 0,
            "code": None,
            "fixed": None,
            "params": None,
        },
    ]
    assert Logger.error.call_args_list == []
