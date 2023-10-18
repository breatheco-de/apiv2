import random
from unittest.mock import MagicMock, call
from logging import Logger
import pytest
from breathecode.commons.tasks import mark_task_as_cancelled

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

param_names = 'task_module,task_name,get_call_args_list'


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr('logging.Logger.info', MagicMock())
    monkeypatch.setattr('logging.Logger.warn', MagicMock())
    monkeypatch.setattr('logging.Logger.error', MagicMock())

    yield


def get_args(fake):
    args = []

    for _ in range(random.randint(0, 4)):
        n = range(random.randint(0, 2))
        if n == 0:
            args.append(fake.slug())
        elif n == 1:
            args.append(random.randint(1, 100))
        elif n == 2:
            args.append(random.randint(1, 10000) / 100)

    return args


def get_kwargs(fake):
    kwargs = {}

    for _ in range(random.randint(0, 4)):
        n = range(random.randint(0, 2))
        if n == 0:
            kwargs[fake.slug()] = fake.slug()
        elif n == 1:
            kwargs[fake.slug()] = random.randint(1, 100)
        elif n == 2:
            kwargs[fake.slug()] = random.randint(1, 10000) / 100

    return kwargs


@pytest.fixture
def arrange(bc: Breathecode, fake):

    def _arrange(data={}):

        task_manager = {
            'arguments': {
                'args': get_args(fake),
                'kwargs': get_kwargs(fake),
            },
            **data,
        }

        model = bc.database.create(task_manager=task_manager)

        Logger.info.call_args_list = []
        Logger.warn.call_args_list = []
        Logger.error.call_args_list = []

        return model

    yield _arrange


# When: TaskManager is not found
# Then: nothing happens
def test_not_found(bc: Breathecode):
    res = mark_task_as_cancelled(1)

    assert res == None

    assert Logger.info.call_args_list == [call('Running mark_task_as_cancelled for 1')]
    assert Logger.warn.call_args_list == []
    assert Logger.error.call_args_list == [call('TaskManager 1 not found')]

    assert bc.database.list_of('commons.TaskManager') == []


# When: TaskManager found
# Then: the task is paused
def test_found(bc: Breathecode, arrange):

    model = arrange({})

    res = mark_task_as_cancelled(1)

    assert res == None

    assert Logger.info.call_args_list == [
        call('Running mark_task_as_cancelled for 1'),
        call('TaskManager 1 is being marked as CANCELLED'),
    ]

    assert Logger.warn.call_args_list == []
    assert Logger.error.call_args_list == []

    assert bc.database.list_of('commons.TaskManager') == [
        {
            **bc.format.to_dict(model.task_manager),
            'status': 'CANCELLED',
        },
    ]


# When: TaskManager is not running, it means it's not pending
# Then: nothing happens
@pytest.mark.parametrize('status', ['DONE', 'CANCELLED', 'REVERSED', 'ABORTED', 'ERROR'])
def test_its_not_running(bc: Breathecode, arrange, status):

    model = arrange({'status': status})

    res = mark_task_as_cancelled(1)

    assert res == None

    assert Logger.info.call_args_list == [
        call('Running mark_task_as_cancelled for 1'),
    ]

    assert Logger.warn.call_args_list == [call('TaskManager 1 was already DONE')]
    assert Logger.error.call_args_list == []

    assert bc.database.list_of('commons.TaskManager') == [bc.format.to_dict(model.task_manager)]
