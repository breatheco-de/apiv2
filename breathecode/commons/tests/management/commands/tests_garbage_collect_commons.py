from datetime import timedelta
import random
from unittest.mock import MagicMock, call
from logging import Logger
import pytest
from django.utils import timezone
from breathecode.commons.admin import cancel
from breathecode.commons import tasks

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from breathecode.commons.management.commands.garbage_collect_commons import Command

param_names = 'task_module,task_name,get_call_args_list'

short_delta_list = [timedelta(hours=n * 2) for n in range(1, 23)]
long_delta_list = [timedelta(hours=n * 2) for n in range(25, 48)]


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr('breathecode.commons.tasks.mark_task_as_cancelled.delay', MagicMock())

    yield


@pytest.fixture
def arrange(bc: Breathecode, fake):

    def _arrange(n, data={}):
        model = bc.database.create(task_manager=(n, data))
        return model

    yield _arrange


# When: 0 TaskManager's
# Then: nothing happens
def test_with_0(bc: Breathecode):

    command = Command()
    res = command.handle()

    assert res == None
    assert bc.database.list_of('commons.TaskManager') == []


# When: 2 TaskManager's, one of them is not old enough
# Then: nothing happens
def test_with_2(bc: Breathecode, arrange, set_datetime):
    utc_now = timezone.now()
    set_datetime(utc_now)

    model = arrange(2)

    command = Command()
    res = command.handle()

    assert res == None
    assert bc.database.list_of('commons.TaskManager') == bc.format.to_dict(model.task_manager)


# When: 2 TaskManager's, one of them is not old enough yet
# Then: nothing happens
@pytest.mark.parametrize('delta', short_delta_list)
def test_with_2__is_not_so_old_yet(bc: Breathecode, arrange, set_datetime, delta):
    utc_now = timezone.now()

    model = arrange(2)

    set_datetime(utc_now + delta)

    command = Command()
    res = command.handle()

    assert res == None
    assert bc.database.list_of('commons.TaskManager') == bc.format.to_dict(model.task_manager)


# When: 2 TaskManager's, all tasks is old
# Then: remove all tasks
@pytest.mark.parametrize('delta', long_delta_list)
def test_with_2__all_tasks_is_old(bc: Breathecode, arrange, set_datetime, delta):
    utc_now = timezone.now()

    _ = arrange(2)

    set_datetime(utc_now + delta)

    command = Command()
    res = command.handle()

    assert res == None
    assert bc.database.list_of('commons.TaskManager') == []
