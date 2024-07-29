from datetime import timedelta
from unittest.mock import MagicMock, call

import pytest
from asgiref.sync import sync_to_async

import capyc.core.pytest.fixtures as cfx
import capyc.django.pytest.fixtures as dfx
from breathecode.monitoring.models import Supervisor as SupervisorModel
from breathecode.monitoring.models import SupervisorIssue
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from breathecode.utils.decorators import paths

from ....management.commands.supervisor import Command

PATHS = paths.copy()


class Supervisor(Command):

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

    def id(self, module, name):
        s = SupervisorModel.objects.filter(task_module=module, task_name=name).first()
        return s.id

    @sync_to_async
    def aid(self, module, name):
        return self.id(module, name)


@pytest.fixture
def supervisor(db, bc: Breathecode):
    yield Supervisor(bc)


@pytest.fixture(autouse=True)
def patch(monkeypatch: pytest.MonkeyPatch):
    m1 = MagicMock()
    m2 = MagicMock()
    monkeypatch.setattr("breathecode.monitoring.tasks.run_supervisor.delay", m1)
    monkeypatch.setattr("breathecode.monitoring.tasks.fix_issue.delay", m2)

    keys = paths.copy()
    for x in keys:
        if ".tests." in x[0]:
            paths.remove(x)

    yield m1, m2


@pytest.fixture(autouse=True, scope="module")
def setup():
    yield

    for x in paths:
        if x not in PATHS:
            paths.remove(x)


def db(data={}):
    return {
        "delta": timedelta(seconds=3600),
        "ran_at": None,
        "task_module": "",
        "task_name": "",
        **data,
    }


def remove_ids(dbs):
    return [x for x in dbs if x.pop("id")]


class TestIssue:

    @pytest.mark.parametrize(
        "with_supervisor, with_issues",
        [
            (False, False),
            (True, False),
            (True, True),
        ],
    )
    def tests_older_issues_are_removed(
        self, database: dfx.Database, supervisor: Supervisor, patch, with_supervisor, with_issues, utc_now
    ):
        extra = {}
        if with_supervisor:
            extra["supervisor"] = {
                "delta": timedelta(seconds=3600),
                "ran_at": None,
                "task_module": "breathecode.payments.supervisors",
                "task_name": "supervise_all_consumption_sessions",
            }

        if with_issues:
            extra["supervisor_issue"] = (2, {"ran_at": utc_now - timedelta(days=7, seconds=1)})

        model = database.create(**extra)

        run_supervisor_mock, fix_issue_mock = patch
        run_supervisor_mock.call_args_list = []
        fix_issue_mock.call_args_list = []
        command = Command()

        assert command.handle() == None
        assert {
            "task_module": "breathecode.payments.supervisors",
            "task_name": "supervise_all_consumption_sessions",
        } in supervisor.list()
        assert supervisor.log("breathecode.payments.supervisors", "supervise_all_consumption_sessions") == []
        assert db(
            {
                "task_module": "breathecode.payments.supervisors",
                "task_name": "supervise_all_consumption_sessions",
            }
        ) in remove_ids(database.list_of("monitoring.Supervisor"))
        assert database.list_of("monitoring.SupervisorIssue") == []
        assert (
            call(supervisor.id("breathecode.payments.supervisors", "supervise_all_consumption_sessions"))
            in run_supervisor_mock.call_args_list
        )
        assert fix_issue_mock.call_args_list == []

    def tests_recent_issues_keeps__available_attempts(
        self, bc: Breathecode, database: dfx.Database, supervisor: Supervisor, patch, utc_now, random: cfx.Random
    ):
        model = database.create(
            supervisor={
                "delta": timedelta(seconds=3600),
                "ran_at": None,
                "task_module": "breathecode.payments.supervisors",
                "task_name": "supervise_all_consumption_sessions",
            },
            supervisor_issue=(
                2,
                {
                    "ran_at": utc_now - timedelta(days=random.int(0, 6)),
                    "attempts": 0,
                },
            ),
        )

        run_supervisor_mock, fix_issue_mock = patch
        run_supervisor_mock.call_args_list = []
        fix_issue_mock.call_args_list = []
        command = Command()

        assert command.handle() == None
        assert {
            "task_module": "breathecode.payments.supervisors",
            "task_name": "supervise_all_consumption_sessions",
        } in supervisor.list()
        assert supervisor.log("breathecode.payments.supervisors", "supervise_all_consumption_sessions") == [
            x.error for x in model.supervisor_issue
        ]
        assert db(
            {
                "task_module": "breathecode.payments.supervisors",
                "task_name": "supervise_all_consumption_sessions",
            }
        ) in remove_ids(database.list_of("monitoring.Supervisor"))
        assert database.list_of("monitoring.SupervisorIssue") == bc.format.to_dict(model.supervisor_issue)
        assert (
            call(supervisor.id("breathecode.payments.supervisors", "supervise_all_consumption_sessions"))
            in run_supervisor_mock.call_args_list
        )
        assert fix_issue_mock.call_args_list == [call(1), call(2)]

    def tests_recent_issues_keeps__no_available_attempts(
        self, bc: Breathecode, database: dfx.Database, supervisor: Supervisor, patch, utc_now, random: cfx.Random
    ):
        model = database.create(
            supervisor={
                "delta": timedelta(seconds=3600),
                "ran_at": None,
                "task_module": "breathecode.payments.supervisors",
                "task_name": "supervise_all_consumption_sessions",
            },
            supervisor_issue=(
                2,
                {
                    "ran_at": utc_now - timedelta(days=random.int(0, 6)),
                    "attempts": 3,
                },
            ),
        )

        run_supervisor_mock, fix_issue_mock = patch
        run_supervisor_mock.call_args_list = []
        fix_issue_mock.call_args_list = []
        command = Command()

        assert command.handle() == None
        assert {
            "task_module": "breathecode.payments.supervisors",
            "task_name": "supervise_all_consumption_sessions",
        } in supervisor.list()
        assert supervisor.log("breathecode.payments.supervisors", "supervise_all_consumption_sessions") == [
            x.error for x in model.supervisor_issue
        ]
        assert db(
            {
                "task_module": "breathecode.payments.supervisors",
                "task_name": "supervise_all_consumption_sessions",
            }
        ) in remove_ids(database.list_of("monitoring.Supervisor"))
        assert database.list_of("monitoring.SupervisorIssue") == bc.format.to_dict(model.supervisor_issue)
        assert (
            call(supervisor.id("breathecode.payments.supervisors", "supervise_all_consumption_sessions"))
            in run_supervisor_mock.call_args_list
        )
        assert fix_issue_mock.call_args_list == []


class TestSupervision:

    @pytest.mark.parametrize(
        "supervised_at",
        [
            None,
            timedelta(days=2, seconds=1),
        ],
    )
    def tests_pending_to_be_scheduled(
        self, database: dfx.Database, supervisor: Supervisor, patch, supervised_at, utc_now
    ):

        delta = timedelta(days=2)
        ran_at = utc_now - supervised_at if supervised_at else None
        s = {
            "delta": delta,
            "ran_at": ran_at,
            "task_module": "breathecode.payments.supervisors",
            "task_name": "supervise_all_consumption_sessions",
        }

        supervisor_issues = (2, {"ran_at": utc_now - timedelta(days=7, seconds=1)})

        model = database.create(supervisor=s, supervisor_issue=supervisor_issues)

        run_supervisor_mock, fix_issue_mock = patch
        run_supervisor_mock.call_args_list = []
        fix_issue_mock.call_args_list = []
        command = Command()

        assert command.handle() == None
        assert {
            "task_module": "breathecode.payments.supervisors",
            "task_name": "supervise_all_consumption_sessions",
        } in supervisor.list()
        assert supervisor.log("breathecode.payments.supervisors", "supervise_all_consumption_sessions") == []
        assert db(
            {
                "delta": delta,
                "ran_at": ran_at,
                "task_module": "breathecode.payments.supervisors",
                "task_name": "supervise_all_consumption_sessions",
            }
        ) in remove_ids(database.list_of("monitoring.Supervisor"))
        assert database.list_of("monitoring.SupervisorIssue") == []
        assert (
            call(supervisor.id("breathecode.payments.supervisors", "supervise_all_consumption_sessions"))
            in run_supervisor_mock.call_args_list
        )
        assert fix_issue_mock.call_args_list == []

    def tests_in_cooldown(self, database: dfx.Database, supervisor: Supervisor, patch, utc_now):

        delta = timedelta(days=2)
        ran_at = utc_now - timedelta(days=1)
        s = {
            "delta": delta,
            "ran_at": ran_at,
            "task_module": "breathecode.payments.supervisors",
            "task_name": "supervise_all_consumption_sessions",
        }

        supervisor_issues = (2, {"ran_at": utc_now - timedelta(days=7, seconds=1)})

        model = database.create(supervisor=s, supervisor_issue=supervisor_issues)

        run_supervisor_mock, fix_issue_mock = patch
        run_supervisor_mock.call_args_list = []
        fix_issue_mock.call_args_list = []
        command = Command()

        assert command.handle() == None
        assert {
            "task_module": "breathecode.payments.supervisors",
            "task_name": "supervise_all_consumption_sessions",
        } in supervisor.list()
        assert supervisor.log("breathecode.payments.supervisors", "supervise_all_consumption_sessions") == []
        assert db(
            {
                "delta": delta,
                "ran_at": ran_at,
                "task_module": "breathecode.payments.supervisors",
                "task_name": "supervise_all_consumption_sessions",
            }
        ) in remove_ids(database.list_of("monitoring.Supervisor"))
        assert database.list_of("monitoring.SupervisorIssue") == []
        assert (
            call(supervisor.id("breathecode.payments.supervisors", "supervise_all_consumption_sessions"))
            not in run_supervisor_mock.call_args_list
        )
        assert fix_issue_mock.call_args_list == []
