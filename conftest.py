from datetime import datetime
import os
import random
from unittest.mock import patch
import pytest
from scripts.utils.environment import reset_environment, test_environment
from breathecode.utils.exceptions import TestError
import numpy as np
from PIL import Image
from faker import Faker
from urllib3.connectionpool import HTTPConnectionPool
from django.db.models.signals import ModelSignal
from breathecode.notify.utils.hook_manager import HookManagerClass
from django.utils import timezone
from django.core.cache import cache
from rest_framework.test import APIClient

# set ENV as test before run django
os.environ['ENV'] = 'test'

FAKE = Faker()
pytest_plugins = ('celery.contrib.pytest', )
urlopen = HTTPConnectionPool.urlopen

from breathecode.tests.mixins.breathecode_mixin import Breathecode


def pytest_configure():
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


@pytest.fixture
def utc_now(set_datetime):
    utc_now = timezone.now()
    set_datetime(utc_now)
    yield utc_now


@pytest.fixture(autouse=True)
def enable_hook_manager(monkeypatch):
    """
    Disable the HookManagerClass.process_model_event by default. You can re-enable it within a test by calling the provided wrapper.
    """

    original_process_model_event = HookManagerClass.process_model_event

    monkeypatch.setattr(HookManagerClass, 'process_model_event', lambda *args, **kwargs: None)

    def enable():
        monkeypatch.setattr(HookManagerClass, 'process_model_event', original_process_model_event)

    yield enable


@pytest.fixture(autouse=True)
def dont_wait_for_rescheduling_tasks(monkeypatch):
    """
    Don't wait for rescheduling tasks by default. You can re-enable it within a test by calling the provided wrapper.
    """

    with patch('breathecode.utils.decorators.task.RETRIES_LIMIT', 2):
        with patch('breathecode.utils.decorators.task.Task.reattemp_settings',
                   lambda *args, **kwargs: dict()):
            yield


from django.dispatch.dispatcher import Signal


@pytest.fixture(autouse=True)
def enable_signals(monkeypatch):
    """
    Disable all signals by default. You can re-enable them within a test by calling the provided wrapper.
    """
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

    #TODO: get a list of signals that will be enabled
    def enable():
        monkeypatch.setattr(Signal, 'send', original_signal_send)
        monkeypatch.setattr(Signal, 'send_robust', original_signal_send_robust)

        monkeypatch.setattr(ModelSignal, 'send', original_model_signal_send)
        monkeypatch.setattr(ModelSignal, 'send_robust', original_model_signal_send_robust)

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


@pytest.fixture(autouse=True)
def clean_environment():
    reset_environment()
    test_environment()


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


@pytest.fixture(scope='session')
def fake():
    return FAKE
