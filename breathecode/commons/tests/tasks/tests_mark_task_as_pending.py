import random
import json
from unittest.mock import MagicMock, call
from logging import Logger
import pytest
from breathecode.commons.tasks import mark_task_as_pending
import breathecode.admissions.tasks as admissions_tasks
import breathecode.payments.tasks as payments_tasks
import breathecode.events.tasks as events_tasks

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

params = [
    ('breathecode.admissions.tasks', 'async_test_syllabus',
     lambda: admissions_tasks.async_test_syllabus.call_args_list),
    ('breathecode.admissions.tasks', 'build_profile_academy',
     lambda: admissions_tasks.build_profile_academy.call_args_list),
    ('breathecode.admissions.tasks', 'build_cohort_user',
     lambda: admissions_tasks.build_cohort_user.call_args_list),
    ('breathecode.payments.tasks', 'add_cohort_set_to_subscription',
     lambda: payments_tasks.add_cohort_set_to_subscription.call_args_list),
    ('breathecode.payments.tasks', 'build_consumables_from_bag',
     lambda: payments_tasks.build_consumables_from_bag.call_args_list),
    ('breathecode.payments.tasks', 'build_plan_financing',
     lambda: payments_tasks.build_plan_financing.call_args_list),
    ('breathecode.events.tasks', 'async_eventbrite_webhook',
     lambda: events_tasks.async_eventbrite_webhook.call_args_list),
    ('breathecode.events.tasks', 'async_export_event_to_eventbrite',
     lambda: events_tasks.async_export_event_to_eventbrite.call_args_list),
    ('breathecode.events.tasks', 'fix_live_class_dates',
     lambda: events_tasks.fix_live_class_dates.call_args_list),
]

param_names = 'task_module,task_name,get_call_args_list'


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr('breathecode.commons.tasks.mark_task_as_pending.apply_async', MagicMock())
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

    return tuple(args)


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
def arrange(monkeypatch, bc: Breathecode, fake):

    def _arrange(data={}):
        task_module = data.get('task_module')
        task_name = data.get('task_name')

        if task_module and task_name:
            monkeypatch.setattr(f'{task_module}.{task_name}.delay', MagicMock())

        task_manager = {
            'args': get_args(fake),
            'kwargs': get_kwargs(fake),
            **data,
        }

        return bc.database.create(task_manager=task_manager)

    yield _arrange


# When: TaskManager is not found
# Then: nothing happens
def test_not_found(bc: Breathecode):
    res = mark_task_as_pending(1)

    assert res == None

    assert Logger.info.call_args_list == [call('Running mark_task_as_pending for 1')]
    assert Logger.warn.call_args_list == []
    assert Logger.error.call_args_list == [call('TaskManager 1 not found')]

    assert bc.database.list_of('commons.TaskManager') == []


# When: TaskManager is not found
# Then: nothing happens
@pytest.mark.parametrize(param_names, params)
def test_found_(bc: Breathecode, arrange, task_module, task_name, get_call_args_list):

    model = arrange({
        'task_module': task_module,
        'task_name': task_name,
    })

    res = mark_task_as_pending(1)

    assert res == None

    assert Logger.info.call_args_list == [call('Running mark_task_as_pending for 1')]
    assert Logger.warn.call_args_list == []
    assert Logger.error.call_args_list == [call('TaskManager 1 not found')]

    assert bc.database.list_of('commons.TaskManager') == []

    assert get_call_args_list() == []
    assert 0
