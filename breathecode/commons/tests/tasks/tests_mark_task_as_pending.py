from datetime import timedelta
import os
import random
from unittest.mock import MagicMock, call
from logging import Logger
import pytest
from breathecode.commons.tasks import mark_task_as_pending
import breathecode.admissions.tasks as admissions_tasks
import breathecode.payments.tasks as payments_tasks
import breathecode.events.tasks as events_tasks
from django.utils import timezone

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

# this fix a problem caused by the geniuses at pytest-xdist
random.seed(os.getenv('RANDOM'))

# minutes
TOLERANCE = random.randint(3, 10)
TOLERATED_DELTA = [timezone.timedelta(minutes=x) for x in range(0, TOLERANCE)]
NO_TOLERATED_DELTA = [timezone.timedelta(minutes=x) for x in range(TOLERANCE + 1, TOLERANCE + 5)]

params = [
    ('breathecode.admissions.tasks', 'async_test_syllabus',
     lambda: admissions_tasks.async_test_syllabus.delay.call_args_list),
    ('breathecode.admissions.tasks', 'build_profile_academy',
     lambda: admissions_tasks.build_profile_academy.delay.call_args_list),
    ('breathecode.admissions.tasks', 'build_cohort_user',
     lambda: admissions_tasks.build_cohort_user.delay.call_args_list),
    ('breathecode.payments.tasks', 'add_cohort_set_to_subscription',
     lambda: payments_tasks.add_cohort_set_to_subscription.delay.call_args_list),
    ('breathecode.payments.tasks', 'build_consumables_from_bag',
     lambda: payments_tasks.build_consumables_from_bag.delay.call_args_list),
    ('breathecode.payments.tasks', 'build_plan_financing',
     lambda: payments_tasks.build_plan_financing.delay.call_args_list),
    ('breathecode.events.tasks', 'async_eventbrite_webhook',
     lambda: events_tasks.async_eventbrite_webhook.delay.call_args_list),
    ('breathecode.events.tasks', 'async_export_event_to_eventbrite',
     lambda: events_tasks.async_export_event_to_eventbrite.delay.call_args_list),
    ('breathecode.events.tasks', 'fix_live_class_dates',
     lambda: events_tasks.fix_live_class_dates.delay.call_args_list),
]

param_names = 'task_module,task_name,get_call_args_list'


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr('breathecode.commons.tasks.mark_task_as_pending.apply_async', MagicMock())
    monkeypatch.setattr('breathecode.commons.tasks.TOLERANCE', TOLERANCE)
    monkeypatch.setattr('logging.Logger.info', MagicMock())
    monkeypatch.setattr('logging.Logger.warn', MagicMock())
    monkeypatch.setattr('logging.Logger.error', MagicMock())

    yield


def get_args(fake):
    args = []

    for _ in range(random.randint(1, 4)):
        n = random.randint(0, 2)
        if n == 0:
            args.append(fake.slug())
        elif n == 1:
            args.append(random.randint(1, 100))
        elif n == 2:
            args.append(random.randint(1, 10000) / 100)

    return args


def get_kwargs(fake):
    kwargs = {}

    for _ in range(random.randint(1, 4)):
        n = random.randint(0, 2)
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
    res = mark_task_as_pending(1)

    assert res == None

    assert Logger.info.call_args_list == [call('Running mark_task_as_pending for 1')]
    assert Logger.warn.call_args_list == []
    assert Logger.error.call_args_list == [call('TaskManager 1 not found')]

    assert bc.database.list_of('commons.TaskManager') == []
    assert mark_task_as_pending.apply_async.call_args_list == []


# When: TaskManager found
# Then: the task execution is resheduled
@pytest.mark.parametrize(param_names, params)
def test_found(bc: Breathecode, arrange, task_module, task_name, get_call_args_list):

    model = arrange({
        'task_module': task_module,
        'task_name': task_name,
    })

    res = mark_task_as_pending(1)

    assert res == None

    assert Logger.info.call_args_list == [
        call('Running mark_task_as_pending for 1'),
        call('TaskManager 1 is being marked as PENDING'),
    ]

    assert Logger.warn.call_args_list == []
    assert Logger.error.call_args_list == []

    assert bc.database.list_of('commons.TaskManager') == [bc.format.to_dict(model.task_manager)]

    assert get_call_args_list() == [
        call(*model.task_manager.arguments['args'],
             **model.task_manager.arguments['kwargs'],
             page=1,
             total_pages=0,
             task_manager_id=1)
    ]
    assert mark_task_as_pending.apply_async.call_args_list == []


# When: TaskManager found and it's done
# Then: nothing happens
@pytest.mark.parametrize('status', ['DONE', 'CANCELLED', 'REVERSED'])
@pytest.mark.parametrize(param_names, params)
def test_task_is_done(bc: Breathecode, arrange, task_module, task_name, get_call_args_list, status):

    model = arrange({
        'task_module': task_module,
        'task_name': task_name,
        'status': status,
    })

    res = mark_task_as_pending(1)

    assert res == None

    assert Logger.info.call_args_list == [
        call('Running mark_task_as_pending for 1'),
    ]

    assert Logger.warn.call_args_list == [call('TaskManager 1 was already DONE')]
    assert Logger.error.call_args_list == []

    assert bc.database.list_of('commons.TaskManager') == [bc.format.to_dict(model.task_manager)]

    assert get_call_args_list() == []
    assert mark_task_as_pending.apply_async.call_args_list == []


# When: TaskManager found and it's running, so, the last_run changed
# Then: nothing happens
@pytest.mark.parametrize(param_names, params)
def test_task_is_running(bc: Breathecode, arrange, task_module, task_name, get_call_args_list):
    d1 = timezone.now()
    d2 = timezone.now()

    model = arrange({
        'task_module': task_module,
        'task_name': task_name,
        'last_run': d1,
    })

    res = mark_task_as_pending(1, last_run=d2)

    assert res == None

    assert Logger.info.call_args_list == [
        call('Running mark_task_as_pending for 1'),
    ]

    assert Logger.warn.call_args_list == [call('TaskManager 1 is already running')]
    assert Logger.error.call_args_list == []

    assert bc.database.list_of('commons.TaskManager') == [bc.format.to_dict(model.task_manager)]

    assert get_call_args_list() == []
    assert mark_task_as_pending.apply_async.call_args_list == []


# When: TaskManager last_run is less than the tolerance
# Then: mark_task_as_pending is rescheduled
@pytest.mark.parametrize('delta', TOLERATED_DELTA)
@pytest.mark.parametrize(param_names, random.choices(params, k=1))
def test_task_last_run_less_than_the_tolerance(bc: Breathecode, arrange, task_module, task_name,
                                               get_call_args_list, delta, utc_now):
    model = arrange({
        'task_module': task_module,
        'task_name': task_name,
        'last_run': timezone.now() - delta,
    })

    res = mark_task_as_pending(1)

    assert res == None

    assert Logger.info.call_args_list == [
        call('Running mark_task_as_pending for 1'),
    ]

    assert Logger.warn.call_args_list == [call('TaskManager 1 was not killed, scheduling to run it again')]
    assert Logger.error.call_args_list == []

    assert bc.database.list_of('commons.TaskManager') == [bc.format.to_dict(model.task_manager)]

    assert get_call_args_list() == []
    assert mark_task_as_pending.apply_async.call_args_list == [
        call(args=(1, ),
             kwargs={
                 'attempts': 1,
                 'last_run': model.task_manager.last_run,
             },
             eta=utc_now + timedelta(seconds=30))
    ]


# When: TaskManager last_run is less than the tolerance, force is True
# Then: it's rescheduled, the tolerance is ignored
@pytest.mark.parametrize('delta', TOLERATED_DELTA)
@pytest.mark.parametrize(param_names, random.choices(params, k=1))
def test_task_last_run_less_than_the_tolerance__force_true(bc: Breathecode, arrange, task_module, task_name,
                                                           get_call_args_list, delta):
    model = arrange({
        'task_module': task_module,
        'task_name': task_name,
        'last_run': timezone.now() - delta,
    })

    res = mark_task_as_pending(1, force=True)

    assert res == None

    assert Logger.info.call_args_list == [
        call('Running mark_task_as_pending for 1'),
        call('TaskManager 1 is being marked as PENDING'),
    ]

    assert Logger.warn.call_args_list == []
    assert Logger.error.call_args_list == []

    assert bc.database.list_of('commons.TaskManager') == [bc.format.to_dict(model.task_manager)]

    assert get_call_args_list() == [
        call(*model.task_manager.arguments['args'],
             **model.task_manager.arguments['kwargs'],
             page=1,
             total_pages=0,
             task_manager_id=1)
    ]
    assert mark_task_as_pending.apply_async.call_args_list == []


# When: TaskManager last_run is less than the tolerance, attempts is greater than 10
# Then: it's rescheduled because the task was not ended and it's not running
@pytest.mark.parametrize('attempts', [x for x in range(11, 16)])
@pytest.mark.parametrize('delta', TOLERATED_DELTA)
@pytest.mark.parametrize(param_names, random.choices(params, k=1))
def test_task_last_run_less_than_the_tolerance__attempts_gt_10(bc: Breathecode, arrange, task_module,
                                                               task_name, get_call_args_list, delta,
                                                               attempts):
    model = arrange({
        'task_module': task_module,
        'task_name': task_name,
        'last_run': timezone.now() - delta,
    })

    res = mark_task_as_pending(1, attempts=attempts)

    assert res == None

    assert Logger.info.call_args_list == [
        call('Running mark_task_as_pending for 1'),
        call('TaskManager 1 is being marked as PENDING'),
    ]

    assert Logger.warn.call_args_list == []
    assert Logger.error.call_args_list == []

    assert bc.database.list_of('commons.TaskManager') == [bc.format.to_dict(model.task_manager)]

    assert get_call_args_list() == [
        call(*model.task_manager.arguments['args'],
             **model.task_manager.arguments['kwargs'],
             page=1,
             total_pages=0,
             task_manager_id=1)
    ]
    assert mark_task_as_pending.apply_async.call_args_list == []


# When: TaskManager last_run is greater than the tolerance
# Then: mark_task_as_pending is rescheduled
@pytest.mark.parametrize('delta', NO_TOLERATED_DELTA)
@pytest.mark.parametrize(param_names, random.choices(params, k=1))
def test_task_last_run_greater_than_the_tolerance(bc: Breathecode, arrange, task_module, task_name,
                                                  get_call_args_list, delta, utc_now):
    model = arrange({
        'task_module': task_module,
        'task_name': task_name,
        'last_run': timezone.now() - delta,
    })

    res = mark_task_as_pending(1)

    assert res == None

    assert Logger.info.call_args_list == [
        call('Running mark_task_as_pending for 1'),
        call('TaskManager 1 is being marked as PENDING'),
    ]

    assert Logger.warn.call_args_list == []
    assert Logger.error.call_args_list == []

    assert bc.database.list_of('commons.TaskManager') == [bc.format.to_dict(model.task_manager)]

    assert get_call_args_list() == [
        call(*model.task_manager.arguments['args'],
             **model.task_manager.arguments['kwargs'],
             page=1,
             total_pages=0,
             task_manager_id=1)
    ]
    assert mark_task_as_pending.apply_async.call_args_list == []
