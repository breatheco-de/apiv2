from datetime import timedelta
import random
from unittest.mock import MagicMock, call
from logging import Logger
import pytest
from django.utils import timezone
from breathecode.commons.admin import cancel
from breathecode.commons import tasks

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from breathecode.commons.management.commands.rerun_pending_tasks import Command

param_names = 'task_module,task_name,get_call_args_list'

short_delta_list = [timedelta(minutes=n * 2) for n in range(1, 14)]
long_delta_list = [timedelta(minutes=n * 2) for n in range(16, 30)]


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr('breathecode.commons.tasks.mark_task_as_pending.delay', MagicMock())

    yield


@pytest.fixture
def arrange(bc: Breathecode, fake):

    def _arrange(n, data={}):
        model = bc.database.create(task_manager=(n, data))
        return model

    yield _arrange


# When: 0 TaskManager's
# Then: nothing happens
def test_with_0(bc: Breathecode, capsys):

    command = Command()
    res = command.handle()

    assert res == None
    assert bc.database.list_of('commons.TaskManager') == []
    assert tasks.mark_task_as_pending.delay.call_args_list == []

    captured = capsys.readouterr()
    assert captured.out == 'No TaskManager\'s available to re-run\n'
    assert captured.err == ''


# When: 2 TaskManager's, one of them is not old enough
# Then: nothing happens
def test_with_2(bc: Breathecode, arrange, set_datetime, capsys):
    utc_now = timezone.now()
    set_datetime(utc_now)

    model = arrange(2, {'last_run': utc_now})

    command = Command()
    res = command.handle()

    assert res == None
    assert bc.database.list_of('commons.TaskManager') == bc.format.to_dict(model.task_manager)
    assert tasks.mark_task_as_pending.delay.call_args_list == []

    captured = capsys.readouterr()
    assert captured.out == 'No TaskManager\'s available to re-run\n'
    assert captured.err == ''


# When: 2 TaskManager's, one of them is not old enough yet
# Then: nothing happens
@pytest.mark.parametrize('delta', short_delta_list)
def test_with_2__is_not_so_old_yet(bc: Breathecode, arrange, set_datetime, delta, capsys):
    utc_now = timezone.now()
    set_datetime(utc_now)

    model = arrange(2, {'last_run': utc_now - delta})

    command = Command()
    res = command.handle()

    assert res == None
    assert bc.database.list_of('commons.TaskManager') == bc.format.to_dict(model.task_manager)
    assert tasks.mark_task_as_pending.delay.call_args_list == []

    captured = capsys.readouterr()
    assert captured.out == 'No TaskManager\'s available to re-run\n'
    assert captured.err == ''


# When: 2 TaskManager's, all tasks is old
# Then: remove all tasks
@pytest.mark.parametrize('delta', long_delta_list)
def test_with_2__all_tasks_is_old(bc: Breathecode, arrange, set_datetime, delta, capsys):
    utc_now = timezone.now()
    set_datetime(utc_now)

    model = arrange(2, {'last_run': utc_now - delta})

    command = Command()
    res = command.handle()

    assert res == None
    assert bc.database.list_of('commons.TaskManager') == bc.format.to_dict(model.task_manager)
    assert tasks.mark_task_as_pending.delay.call_args_list == [call(1, force=True), call(2, force=True)]

    captured = capsys.readouterr()
    assert captured.out == 'Rerunning TaskManager\'s 1, 2\n'
    assert captured.err == ''
