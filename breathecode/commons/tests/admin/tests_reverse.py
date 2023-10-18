import random
from unittest.mock import MagicMock, call
from logging import Logger
import pytest
from breathecode.commons.admin import reverse
from breathecode.commons import tasks

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

param_names = 'task_module,task_name,get_call_args_list'


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr('breathecode.commons.tasks.mark_task_as_reversed.delay', MagicMock())

    yield


@pytest.fixture
def arrange(bc: Breathecode, fake):

    def _arrange(n):
        model = bc.database.create(task_manager=n)
        return model, bc.database.get_model('commons.TaskManager').objects.filter()

    yield _arrange


# When: 0 TaskManager's
# Then: nothing happens
def test_with_0(bc: Breathecode, arrange):
    _, queryset = arrange(0)

    res = reverse(None, None, queryset)

    assert res == None

    assert bc.database.list_of('commons.TaskManager') == []
    assert tasks.mark_task_as_reversed.delay.call_args_list == []


# When: 2 TaskManager's
# Then: two tasks are scheduled
def test_with_2(bc: Breathecode, arrange):

    model, queryset = arrange(2)

    res = reverse(None, None, queryset)

    assert res == None

    assert bc.database.list_of('commons.TaskManager') == bc.format.to_dict(model.task_manager)
    assert tasks.mark_task_as_reversed.delay.call_args_list == [call(1), call(2)]
