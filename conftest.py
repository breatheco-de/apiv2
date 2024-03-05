import importlib
import os
import random
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from django.core.cache import cache
from django.db.models.signals import (
    ModelSignal,
    m2m_changed,
    post_delete,
    post_init,
    post_migrate,
    post_save,
    pre_delete,
    pre_init,
    pre_migrate,
    pre_save,
)
from django.dispatch.dispatcher import Signal
from django.utils import timezone
from faker import Faker
from PIL import Image
from rest_framework.test import APIClient
from urllib3.connectionpool import HTTPConnectionPool

from breathecode.notify.utils.hook_manager import HookManagerClass
from breathecode.utils.exceptions import TestError
from scripts.utils.environment import reset_environment, test_environment

# set ENV as test before run django
os.environ['ENV'] = 'test'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

_fake = Faker()
pytest_plugins = ('celery.contrib.pytest', )
urlopen = HTTPConnectionPool.urlopen

from breathecode.tests.mixins.breathecode_mixin import Breathecode


def pytest_configure():
    os.environ['ENV'] = 'test'
    os.environ['SQLALCHEMY_SILENCE_UBER_WARNING'] = '1'


@pytest.fixture
def get_args(fake):

    def wrapper(num):
        args = []

        for _ in range(0, num):
            n = random.randint(0, 2)
            if n == 0:
                args.append(fake.slug())
            elif n == 1:
                args.append(random.randint(1, 100))
            elif n == 2:
                args.append(random.randint(1, 10000) / 100)

        return tuple(args)

    yield wrapper


@pytest.fixture
def get_int():

    def wrapper(min=0, max=1000):
        return random.randint(min, max)

    yield wrapper


@pytest.fixture
def get_kwargs(fake):

    def wrapper(num):
        kwargs = {}

        for _ in range(0, num):
            n = random.randint(0, 2)
            if n == 0:
                kwargs[fake.slug()] = fake.slug()
            elif n == 1:
                kwargs[fake.slug()] = random.randint(1, 100)
            elif n == 2:
                kwargs[fake.slug()] = random.randint(1, 10000) / 100

        return kwargs

    yield wrapper


# it does not work yet
@pytest.fixture
def bc(request):
    return Breathecode(request.instance)


@pytest.fixture
def set_datetime(monkeypatch):

    def patch(new_datetime):
        monkeypatch.setattr(timezone, 'now', lambda: new_datetime)

    yield patch


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture(autouse=True)
def clear_cache():

    def wrapper():
        cache.clear()

    wrapper()
    yield wrapper


@pytest.fixture(autouse=True)
def enable_cache_logging(monkeypatch):
    """
    Disable all signals by default.

    You can re-enable them within a test by calling the provided wrapper.
    """

    monkeypatch.setattr('breathecode.commons.actions.is_output_enable', lambda: False)

    def wrapper(*args, **kwargs):
        monkeypatch.setattr('breathecode.commons.actions.is_output_enable', lambda: True)

    yield wrapper


@pytest.fixture(autouse=True, scope='module')
def random_seed():
    seed = os.getenv('RANDOM_SEED')
    if seed:
        seed = int(seed)

    random.seed(seed)
    yield seed


@pytest.fixture
def utc_now(set_datetime):
    utc_now = timezone.now()
    set_datetime(utc_now)
    yield utc_now


@pytest.fixture(autouse=True)
def enable_hook_manager(monkeypatch):
    """Disable the HookManagerClass.process_model_event by default.

    You can re-enable it within a test by calling the provided wrapper.
    """

    original_process_model_event = HookManagerClass.process_model_event

    monkeypatch.setattr(HookManagerClass, 'process_model_event', lambda *args, **kwargs: None)

    def enable():
        monkeypatch.setattr(HookManagerClass, 'process_model_event', original_process_model_event)

    yield enable


@pytest.fixture(autouse=True)
def disable_newrelic_prints(monkeypatch):
    """Disable NewRelic prints."""

    monkeypatch.setattr('newrelic.core.agent._logger.info', lambda *args, **kwargs: None)
    monkeypatch.setattr('newrelic.core.agent._logger.warn', lambda *args, **kwargs: None)
    monkeypatch.setattr('newrelic.core.agent._logger.error', lambda *args, **kwargs: None)

    yield


@pytest.fixture(autouse=True)
def dont_wait_for_rescheduling_tasks():
    """
    Don't wait for rescheduling tasks by default.

    You can re-enable it within a test by calling the provided wrapper.
    """

    from task_manager.core.settings import set_settings

    set_settings(RETRIES_LIMIT=2)

    with patch('task_manager.core.decorators.Task.reattempt_settings', lambda *args, **kwargs: dict()):
        with patch('task_manager.core.decorators.Task.circuit_breaker_settings', lambda *args, **kwargs: dict()):
            yield


@pytest.fixture(autouse=True)
def dont_close_the_circuit():
    """Don't allow the circuit be closed."""

    with patch('circuitbreaker.CircuitBreaker._failure_count', 0, create=True):
        with patch('circuitbreaker.CircuitBreaker.FAILURE_THRESHOLD', 10000000, create=True):
            yield


@pytest.fixture(scope='session')
def signals():
    import os

    # Get the current working directory (root directory)
    root_directory = os.getcwd()

    # Initialize a list to store the file paths
    signal_files = []

    # Walk through the current directory and its subdirectories
    for folder, _, files in os.walk(root_directory):
        for file in files:
            if file == 'signals.py':
                signal_files.append(os.path.join(folder, file))

    if '/' in root_directory:
        separator = '/'
    else:
        separator = '\\'

    res = {
        # these signals cannot be mocked by monkeypatch
        'django.db.models.signals.pre_init': pre_init,
        'django.db.models.signals.post_init': post_init,
        'django.db.models.signals.pre_save': pre_save,
        'django.db.models.signals.post_save': post_save,
        'django.db.models.signals.pre_delete': pre_delete,
        'django.db.models.signals.post_delete': post_delete,
        'django.db.models.signals.m2m_changed': m2m_changed,
        'django.db.models.signals.pre_migrate': pre_migrate,
        'django.db.models.signals.post_migrate': post_migrate,
    }

    signal_files = [
        '.'.join(x.replace(root_directory + separator, '').replace('.py', '').split(separator)) for x in signal_files
        if 'breathecode' in x
    ]

    for module_path in signal_files:
        module = importlib.import_module(module_path)
        signals = [
            x for x in dir(module)
            if x[0] != '_' and (isinstance(getattr(module, x), Signal) or isinstance(getattr(module, x), ModelSignal))
        ]

        for signal_path in signals:
            res[f'{module_path}.{signal_path}'] = getattr(module, signal_path)

    yield res


@pytest.fixture(autouse=True)
def enable_signals(monkeypatch, signals):
    """Disable all signals by default. You can re-enable them within a test by calling the provided wrapper."""

    original_signal_send = Signal.send
    original_signal_send_robust = Signal.send_robust

    original_model_signal_send = ModelSignal.send
    original_model_signal_send_robust = ModelSignal.send_robust

    # Mock the functions to disable signals
    monkeypatch.setattr(Signal, 'send', lambda *args, **kwargs: None)
    monkeypatch.setattr(Signal, 'send_robust', lambda *args, **kwargs: None)

    # Mock the functions to disable signals
    monkeypatch.setattr(ModelSignal, 'send', lambda *args, **kwargs: None)
    monkeypatch.setattr(ModelSignal, 'send_robust', lambda *args, **kwargs: None)

    def enable(*to_enable, debug=False):
        monkeypatch.setattr(Signal, 'send', original_signal_send)
        monkeypatch.setattr(Signal, 'send_robust', original_signal_send_robust)

        monkeypatch.setattr(ModelSignal, 'send', original_model_signal_send)
        monkeypatch.setattr(ModelSignal, 'send_robust', original_model_signal_send_robust)

        if to_enable or debug:
            to_disable = [x for x in signals if x not in to_enable]

            for signal in to_disable:

                def apply_mock(module):

                    def send_mock(*args, **kwargs):
                        if debug:
                            print(module)
                            try:
                                print('  args\n    ', args)
                            except Exception:
                                pass

                            try:
                                print('  kwargs\n    ', kwargs)
                            except Exception:
                                pass

                            print('\n')

                    monkeypatch.setattr(module, send_mock)

                apply_mock(f'{signal}.send')
                apply_mock(f'{signal}.send_robust')

    yield enable


@pytest.fixture(autouse=True)
def no_http_requests(monkeypatch):

    def urlopen_mock(self, method, url, *args, **kwargs):
        # this prevent a tester left pass a request to a third party service
        allow = [
            ('0.0.0.0', 9050, None),
        ]

        for host, port, path in allow:
            if host == self.host and port == self.port and (path == url or path == None):
                return urlopen(self, method, url, *args, **kwargs)

        raise TestError(f'Avoid make a real request to {method} {self.scheme}://{self.host}{url}')

    monkeypatch.setattr('urllib3.connectionpool.HTTPConnectionPool.urlopen', urlopen_mock)


@pytest.fixture()
def patch_request(monkeypatch):

    def patcher(conf=None):
        if not conf:
            conf = []

        def wrapper(*args, **kwargs):
            raises = True

            for c in conf:
                if args == c[0].args and kwargs == c[0].kwargs:
                    raises = False
                    break

            if raises:
                raise TestError(f'Avoiding to make a real request to {args} {kwargs}')

            mock = MagicMock()

            if len(c) > 2:
                mock.json.return_value = c[1]
                mock.status_code = c[2]
            elif len(c) > 1:
                mock.json.return_value = c[1]
                mock.status_code = 200
            else:
                mock.json.return_value = None
                mock.status_code = 204

            return mock

        mock = MagicMock()
        monkeypatch.setattr('requests.api.request', wrapper)

        return mock

    yield patcher


@pytest.fixture(autouse=True)
def clean_environment(fake):
    reset_environment()
    test_environment()

    os.environ['APP_URL'] = fake.url()
    os.environ['LOGIN_URL'] = fake.url()


@pytest.fixture(autouse=True)
def disable_new_relic(monkeypatch):
    monkeypatch.setattr('newrelic.core.agent.Agent._atexit_shutdown', lambda *args, **kwargs: None)


@pytest.fixture()
def random_image(fake):

    filename = fake.slug() + '.png'

    def wrapper(size):
        image = Image.new('RGB', size)
        arr = np.random.randint(low=0, high=255, size=(size[1], size[0]))

        image = Image.fromarray(arr.astype('uint8'))
        image.save(filename, 'PNG')

        file = open(filename, 'rb')

        return file, filename

    yield wrapper

    os.remove(filename)


@pytest.fixture(scope='module')
def fake():
    return _fake


@pytest.fixture()
def get_queryset_pks():

    def wrapper(queryset):
        return [x.pk for x in queryset]

    yield wrapper
