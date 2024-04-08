import os
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache
from django.utils import timezone

from bc.core.pytest.fixtures import Random
from bc.django.pytest.fixtures.signals import Signals
from breathecode.notify.utils.hook_manager import HookManagerClass
from breathecode.utils.exceptions import TestError

# set ENV as test before run django
os.environ['ENV'] = 'test'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

pytest_plugins = (
    'celery.contrib.pytest',
    'bc.newrelic.pytest',
    'bc.django.pytest',
    'bc.rest_framework.pytest',
    'bc.circuitbreaker.pytest',
)

from breathecode.tests.mixins.breathecode_mixin import Breathecode


def pytest_configure():
    os.environ['ENV'] = 'test'
    os.environ['SQLALCHEMY_SILENCE_UBER_WARNING'] = '1'


@pytest.fixture
def get_args(random: Random) -> Generator[callable, None, None]:
    yield random.args


@pytest.fixture
def get_int(random: Random) -> Generator[callable, None, None]:
    yield random.int


@pytest.fixture
def get_kwargs(random: Random) -> Generator[callable, None, None]:
    yield random.kwargs


@pytest.fixture
def bc():
    return Breathecode(None)


@pytest.fixture
def set_datetime(monkeypatch):

    def patch(new_datetime):
        monkeypatch.setattr(timezone, 'now', lambda: new_datetime)

    yield patch


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
def enable_signals(signals: Signals):
    """Disable all signals by default. You can re-enable them within a test by calling the provided wrapper."""

    signals.disable()

    yield signals.enable

    signals.enable()


@pytest.fixture
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
def default_environment(clean_environment, fake, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv('APP_URL', fake.url().replace('http://', 'https://'))
    monkeypatch.setenv('LOGIN_URL', fake.url().replace('http://', 'https://'))
    monkeypatch.setenv('ENV', 'test')

    yield
