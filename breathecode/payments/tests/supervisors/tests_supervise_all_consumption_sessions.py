from datetime import datetime, timedelta
from logging import Logger
from unittest.mock import MagicMock, call

import pytest
from asgiref.sync import sync_to_async

import capyc.core.pytest.fixtures as cfx
import capyc.django.pytest.fixtures as dfx
from breathecode.monitoring.models import Supervisor as SupervisorModel
from breathecode.monitoring.models import SupervisorIssue
from breathecode.payments.supervisors import supervise_all_consumption_sessions
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from breathecode.utils.decorators import supervisor as supervisor_decorator


class Supervisor:

    def __init__(self, bc: Breathecode):
        self._bc = bc

    def list(self):
        supervisors = SupervisorModel.objects.all()
        return [{
            'task_module': supervisor.task_module,
            'task_name': supervisor.task_name,
        } for supervisor in supervisors]

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


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    from breathecode.monitoring.models import Supervisor

    monkeypatch.setattr('logging.Logger.error', MagicMock())
    monkeypatch.setattr('breathecode.payments.supervisors.MIN_PENDING_SESSIONS', 2)
    monkeypatch.setattr('breathecode.payments.supervisors.MIN_CANCELLED_SESSIONS', 2)

    fn_module = 'breathecode.payments.supervisors'
    fn_name = 'supervise_all_consumption_sessions'
    Supervisor.objects.get_or_create(task_module=fn_module,
                                     task_name=fn_name,
                                     defaults={
                                         'delta': timedelta(seconds=3600),
                                         'ran_at': None,
                                     })

    yield


def db(data={}):
    return {
        'delta': timedelta(seconds=3600),
        'id': 0,
        'ran_at': None,
        'task_module': '',
        'task_name': '',
        **data,
    }


def tests_no_sessions(supervisor: Supervisor):
    supervise_all_consumption_sessions()

    assert supervisor.list() == [
        {
            'task_module': 'breathecode.payments.supervisors',
            'task_name': 'supervise_all_consumption_sessions',
        },
    ]
    assert supervisor.log('breathecode.payments.supervisors', 'supervise_all_consumption_sessions') == []


def tests_so_much_pending_sessions(database: dfx.Database, supervisor: Supervisor, utc_now: datetime,
                                   random: cfx.Random):
    eta = utc_now - timedelta(seconds=(3600 * random.int(1, 24)) - 1)
    x = {'eta': eta}
    consumption_sessions = [{'status': 'PENDING', **x} for _ in range(3)] + [{'status': 'DONE', **x} for _ in range(7)]
    database.create(consumption_session=consumption_sessions)

    supervise_all_consumption_sessions()

    # run_supervisor.delay(1)

    assert supervisor.list() == [
        {
            'task_module': 'breathecode.payments.supervisors',
            'task_name': 'supervise_all_consumption_sessions',
        },
    ]
    assert supervisor.log('breathecode.payments.supervisors', 'supervise_all_consumption_sessions') == [
        'There has so much pending consumption sessions, 3 pending and rate 42.86%',
    ]


def tests_so_much_cancelled_sessions__no_unsafe_sessions(database: dfx.Database, supervisor: Supervisor,
                                                         utc_now: datetime, random: cfx.Random):
    eta = utc_now - timedelta(seconds=(3600 * random.int(1, 24)) - 1)
    x = {'eta': eta}
    consumption_sessions = [{
        'status': 'CANCELLED',
        **x
    } for _ in range(2)] + [{
        'status': 'DONE',
        **x
    } for _ in range(8)]
    database.create(consumption_session=consumption_sessions, service_set=1)

    supervise_all_consumption_sessions()

    # run_supervisor.delay(1)

    assert supervisor.list() == [
        {
            'task_module': 'breathecode.payments.supervisors',
            'task_name': 'supervise_all_consumption_sessions',
        },
    ]
    assert supervisor.log('breathecode.payments.supervisors', 'supervise_all_consumption_sessions') == []


def tests_so_much_cancelled_sessions__unsafe_sessions(database: dfx.Database, supervisor: Supervisor, utc_now: datetime,
                                                      random: cfx.Random):
    eta = utc_now - timedelta(seconds=(3600 * random.int(1, 24)) - 1)
    x = {'eta': eta, 'operation_code': 'unsafe-consume-service-set'}
    consumption_sessions = [{
        'status': 'CANCELLED',
        **x
    } for _ in range(4)] + [{
        'status': 'DONE',
        **x
    } for _ in range(6)]
    model = database.create(consumption_session=consumption_sessions, service_set=1)

    supervise_all_consumption_sessions()

    # run_supervisor.delay(1)

    assert supervisor.list() == [
        {
            'task_module': 'breathecode.payments.supervisors',
            'task_name': 'supervise_all_consumption_sessions',
        },
    ]
    assert supervisor.log('breathecode.payments.supervisors', 'supervise_all_consumption_sessions') == [
        f'There has 66.67% cancelled consumption sessions, due to a bug or a cheater, user {model.user.email}',
    ]
