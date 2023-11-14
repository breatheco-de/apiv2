from unittest.mock import MagicMock
import pytest
from breathecode.admissions.models import Country
import breathecode.utils.decorators as decorators
from breathecode.utils.decorators import AbortTask
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

# enable this file to use the database
pytestmark = pytest.mark.usefixtures('db')


def inner_fn(*args, **kwargs):
    key = next(iter(kwargs.keys()))

    # this is used for testing the rollback
    Country.objects.create(code=key[:3], name=kwargs[key])

    if 'MUST_BE_ABORTED' in kwargs and kwargs['MUST_BE_ABORTED'] is True:
        raise AbortTask('It was aborted')

    if 'MUST_RAISE_EXCEPTION' in kwargs and kwargs['MUST_RAISE_EXCEPTION'] is True:
        raise Exception('Unexpected error')

    if len(args) == 5:
        kwargs['WITH_SELF'] = True

    return args, kwargs


# it's to can reverse a task through the task manager
def reverse(*args, **kwargs):
    return args, kwargs


def fallback(*args, exception=None, **kwargs):
    kwargs['exception'] = f'{type(exception)}: {str(exception)}'

    Country.objects.create(code='fll', name='fallback city')

    return 1, args, kwargs, 2


@pytest.fixture
def setup(bc: Breathecode, fake, monkeypatch, get_args, get_kwargs):

    def _arrange(*, task_manager, transaction=None, bind=False, with_fallback=False, with_reverse=False):
        c = MagicMock()
        name = fake.slug().replace('-', '_')

        inner_fn.__name__ = name
        inner_fn.__module__ = 'breathecode.commons.tasks'

        reverse.__module__ = 'breathecode.commons.tasks'

        params = {
            'bind': bind,
            'transaction': transaction,
        }

        if with_fallback:
            params['fallback'] = fallback

        if with_reverse:
            params['reverse'] = reverse

        task = decorators.task(**params)(inner_fn)

        setattr(c, name, MagicMock(side_effect=task))

        monkeypatch.setattr('breathecode.commons.tasks', c)
        model = bc.database.create(task_manager=task_manager)

        args = get_args(4)
        kwargs = get_kwargs(4)

        # return model, task, name, args, kwargs, lambda: getattr(c, name).call_args_list
        city_code = next(iter(kwargs.keys()))
        return model, task, name, args, kwargs, city_code

    yield _arrange


def db_item(data={}):
    return {
        'arguments': {
            'args': ['resource-reflect', 25, 38.21, 49.74],
            'kwargs': {
                'minute-agree-spring': 'range-so-power-drop',
                'public-western': 15.88,
                'something-along': 47,
                'street-book': 20.36,
                'task_manager_id': 1
            }
        },
        'attempts': 1,
        'current_page': 1,
        'id': 1,
        'killed': False,
        'last_run': ...,
        'reverse_module': None,
        'reverse_name': None,
        'status': 'DONE',
        'status_message': None,
        'task_module': 'breathecode.commons.tasks',
        'task_name': '',
        'total_pages': 1,
        **data,
    }


# When: 0 TaskManager's
# Then: it should create a new TaskManager and call the task
def test_no_task_manager(bc: Breathecode, setup, utc_now):
    _, task, task_name, args, kwargs, city_code = setup(task_manager=0,
                                                        bind=False,
                                                        with_fallback=False,
                                                        with_reverse=False,
                                                        transaction=False)

    res = task(*args, **kwargs)

    assert res == (args, {**kwargs, 'task_manager_id': 1})

    assert bc.database.list_of('commons.TaskManager') == [
        db_item({
            'arguments': {
                'args': list(args),
                'kwargs': {
                    **kwargs,
                    'task_manager_id': 1,
                },
            },
            'status': 'DONE',
            'last_run': utc_now,
            'task_name': task_name,
            'current_page': 1,
            'total_pages': 1,
        }),
    ]

    # this is used for testing the rollback
    assert bc.database.list_of('admissions.Country') == [
        {
            'code': city_code[:3],
            'name': str(kwargs[city_code]),
        },
    ]


# Given: 0 TaskManager's
# When: it's aborted
# Then: it should create a new TaskManager and call the task,
#    -> and save it as aborted even if transaction=True
@pytest.mark.parametrize('transaction', [True, False, None])
def test_no_task_manager__it_was_aborted(bc: Breathecode, setup, utc_now, transaction):
    _, task, task_name, args, kwargs, city_code = setup(task_manager=0,
                                                        bind=False,
                                                        with_fallback=False,
                                                        with_reverse=False,
                                                        transaction=transaction)

    kwargs['MUST_BE_ABORTED'] = True

    res = task(*args, **kwargs)

    assert res == None

    assert bc.database.list_of('commons.TaskManager') == [
        db_item({
            'arguments': {
                'args': list(args),
                'kwargs': {
                    **kwargs,
                    'task_manager_id': 1,
                },
            },
            'status': 'ABORTED',
            'last_run': utc_now,
            'task_name': task_name,
            'current_page': 1,
            'total_pages': 1,
            'status_message': 'It was aborted',
        }),
    ]

    # this is used for testing the rollback
    assert bc.database.list_of('admissions.Country') == [
        {
            'code': city_code[:3],
            'name': str(kwargs[city_code]),
        },
    ]


# Given: 0 TaskManager's
# When: it had an exception, no fallback
# Then: it should create a new TaskManager and call the task,
#    -> and save it as error even if transaction=True
@pytest.mark.parametrize('with_fallback', [False, None])
@pytest.mark.parametrize('transaction', [False, None])
def test_no_task_manager__it_got_an_exception__no_transaction__no_fallback(bc: Breathecode, setup, utc_now,
                                                                           transaction, with_fallback):
    _, task, task_name, args, kwargs, city_code = setup(task_manager=0,
                                                        bind=False,
                                                        with_fallback=with_fallback,
                                                        with_reverse=False,
                                                        transaction=transaction)

    kwargs['MUST_RAISE_EXCEPTION'] = True

    task.delay(*args, **kwargs)

    assert bc.database.list_of('commons.TaskManager') == [
        db_item({
            'arguments': {
                'args': list(args),
                'kwargs': {
                    **kwargs,
                    'task_manager_id': 1,
                },
            },
            'status': 'ERROR',
            'last_run': utc_now,
            'task_name': task_name,
            'current_page': 1,
            'total_pages': 1,
            'status_message': 'Unexpected error',
        }),
    ]

    # this is used for testing the rollback
    assert bc.database.list_of('admissions.Country') == [
        {
            'code': city_code[:3],
            'name': str(kwargs[city_code]),
        },
    ]


# Given: 0 TaskManager's
# When: it had an exception, with fallback
# Then: it should create a new TaskManager and call the task,
#    -> save it as error even if transaction=True
#    -> and call the fallback
@pytest.mark.parametrize('transaction', [False, None])
def test_no_task_manager__it_got_an_exception__no_transaction__with_fallback(bc: Breathecode, setup, utc_now,
                                                                             transaction):
    _, task, task_name, args, kwargs, city_code = setup(task_manager=0,
                                                        bind=False,
                                                        with_fallback=True,
                                                        with_reverse=False,
                                                        transaction=transaction)

    kwargs['MUST_RAISE_EXCEPTION'] = True

    res = task(*args, **kwargs)

    assert res == (1, args, {
        **kwargs,
        'task_manager_id': 1,
        'exception': "<class 'Exception'>: Unexpected error",
    }, 2)

    assert bc.database.list_of('commons.TaskManager') == [
        db_item({
            'arguments': {
                'args': list(args),
                'kwargs': {
                    **kwargs,
                    'task_manager_id': 1,
                },
            },
            'status': 'ERROR',
            'last_run': utc_now,
            'task_name': task_name,
            'current_page': 1,
            'total_pages': 1,
            'status_message': 'Unexpected error',
        }),
    ]

    # this is used for testing the rollback
    assert bc.database.list_of('admissions.Country') == [
        {
            'code': city_code[:3],
            'name': str(kwargs[city_code]),
        },
        {
            'code': 'fll',
            'name': 'fallback city',
        },
    ]


# Given: 0 TaskManager's
# When: it had an exception, with transaction and no fallback
# Then: it should create a new TaskManager and call the task,
#    -> it reverse the database (City)
def test_no_task_manager__it_got_an_exception__with_transaction__no_fallback(bc: Breathecode, setup, utc_now):
    _, task, task_name, args, kwargs, _ = setup(task_manager=0,
                                                bind=False,
                                                with_fallback=False,
                                                with_reverse=False,
                                                transaction=True)

    kwargs['MUST_RAISE_EXCEPTION'] = True

    task.delay(*args, **kwargs)

    assert bc.database.list_of('commons.TaskManager') == [
        db_item({
            'arguments': {
                'args': list(args),
                'kwargs': {
                    **kwargs,
                    'task_manager_id': 1,
                },
            },
            'status': 'ERROR',
            'last_run': utc_now,
            'task_name': task_name,
            'current_page': 1,
            'total_pages': 1,
            'status_message': 'Unexpected error',
        }),
    ]

    # this is used for testing the rollback
    assert bc.database.list_of('admissions.Country') == []


# Given: 0 TaskManager's
# When: it had an exception, with transaction and fallback
# Then: it should create a new TaskManager and call the task,
#    -> it reverse the database (City) and save elements from the fallback (City)
def test_no_task_manager__it_got_an_exception__with_transaction__with_fallback(
        bc: Breathecode, setup, utc_now):
    _, task, task_name, args, kwargs, _ = setup(task_manager=0,
                                                bind=False,
                                                with_fallback=True,
                                                with_reverse=False,
                                                transaction=True)

    kwargs['MUST_RAISE_EXCEPTION'] = True

    res = task(*args, **kwargs)

    assert res == (1, args, {
        **kwargs,
        'task_manager_id': 1,
        'exception': "<class 'Exception'>: Unexpected error",
    }, 2)

    assert bc.database.list_of('commons.TaskManager') == [
        db_item({
            'arguments': {
                'args': list(args),
                'kwargs': {
                    **kwargs,
                    'task_manager_id': 1,
                },
            },
            'status': 'ERROR',
            'last_run': utc_now,
            'task_name': task_name,
            'current_page': 1,
            'total_pages': 1,
            'status_message': 'Unexpected error',
        }),
    ]

    # this is used for testing the rollback
    assert bc.database.list_of('admissions.Country') == [
        {
            'code': 'fll',
            'name': 'fallback city',
        },
    ]


# When: 2 TaskManager's
# Then: it should update the first TaskManager and call the task
def test_two_task_managers(bc: Breathecode, setup, utc_now):
    task_manager = {'total_pages': 2}
    model, task, _, args, kwargs, city_code = setup(task_manager=(2, task_manager),
                                                    bind=False,
                                                    with_fallback=False,
                                                    with_reverse=False,
                                                    transaction=False)

    res = task(*args, **kwargs, task_manager_id=1)

    assert res == (args, {**kwargs, 'task_manager_id': 1})

    assert bc.database.list_of('commons.TaskManager') == [
        {
            **bc.format.to_dict(model.task_manager[0]),
            'status': 'PENDING',
            'last_run': utc_now,
            'current_page': 1,
            'total_pages': 2,
        },
        bc.format.to_dict(model.task_manager[1]),
    ]

    # this is used for testing the rollback
    assert bc.database.list_of('admissions.Country') == [
        {
            'code': city_code[:3],
            'name': str(kwargs[city_code]),
        },
    ]


# When: 2 TaskManager's
# Then: it should update the first TaskManager and mark it as killed
@pytest.mark.parametrize('status', ['CANCELLED', 'REVERSED', 'PAUSED', 'ABORTED', 'DONE'])
def test_two_task_managers__it_must_be_killed(bc: Breathecode, setup, utc_now, status):
    task_manager = {
        'total_pages': 2,
        'status': status,
        'killed': False,
    }
    model, task, _, args, kwargs, _ = setup(task_manager=(2, task_manager),
                                            bind=False,
                                            with_fallback=False,
                                            with_reverse=False,
                                            transaction=False)

    res = task(*args, **kwargs, task_manager_id=1)

    assert res == None
    assert bc.database.list_of('commons.TaskManager') == [
        {
            **bc.format.to_dict(model.task_manager[0]),
            'status': status,
            'last_run': utc_now,
            'current_page': 1,
            'total_pages': 2,
            'killed': True,
        },
        bc.format.to_dict(model.task_manager[1]),
    ]

    # this is used for testing the rollback
    assert bc.database.list_of('admissions.Country') == []
