import os
from typing import Generator, Optional
from unittest.mock import MagicMock, patch

import jwt
import pytest
from capyc.pytest.core.fixtures import Random
from capyc.pytest.django.fixtures.signals import Signals
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from breathecode.notify.utils.hook_manager import HookManagerClass
from breathecode.utils.exceptions import TestError

# set ENV as test before run django
os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

pytest_plugins = (
    "staging.pytest.core",
    "capyc.pytest.core",
    "capyc.pytest.newrelic",
    "capyc.pytest.django",
    "capyc.pytest.rest_framework",
    "capyc.pytest.circuitbreaker",
)

from breathecode.tests.mixins.breathecode_mixin import Breathecode


def pytest_configure():
    os.environ["ENV"] = "test"
    os.environ["SQLALCHEMY_SILENCE_UBER_WARNING"] = "1"


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
def bc(seed):
    return Breathecode(None)


@pytest.fixture
def set_datetime(monkeypatch):

    def patch(new_datetime):
        monkeypatch.setattr(timezone, "now", lambda: new_datetime)

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

    monkeypatch.setattr("breathecode.commons.actions.is_output_enable", lambda: False)

    def wrapper(*args, **kwargs):
        monkeypatch.setattr("breathecode.commons.actions.is_output_enable", lambda: True)

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

    monkeypatch.setattr(HookManagerClass, "process_model_event", lambda *args, **kwargs: None)

    def enable():
        monkeypatch.setattr(HookManagerClass, "process_model_event", original_process_model_event)

    yield enable


@pytest.fixture(autouse=True)
def dont_wait_for_rescheduling_tasks():
    """
    Don't wait for rescheduling tasks by default.

    You can re-enable it within a test by calling the provided wrapper.
    """

    from task_manager.core.settings import set_settings

    set_settings(RETRIES_LIMIT=2)

    with patch("task_manager.core.decorators.Task.reattempt_settings", lambda *args, **kwargs: dict()):
        with patch("task_manager.core.decorators.Task.circuit_breaker_settings", lambda *args, **kwargs: dict()):
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
                raise TestError(f"Avoiding to make a real request to {args} {kwargs}")

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
        monkeypatch.setattr("requests.api.request", wrapper)

        return mock

    yield patcher


@pytest.fixture(autouse=True)
def default_environment(clean_environment, fake, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("APP_URL", fake.url().replace("http://", "https://"))
    monkeypatch.setenv("LOGIN_URL", fake.url().replace("http://", "https://"))
    monkeypatch.setenv("ENV", "test")

    yield


@pytest.fixture
def partial_equality():
    """
    Fail if the two objects are partially unequal as determined by the '==' operator.

    Usage:

    ```py
    obj1 = {'key1': 1, 'key2': 2}
    obj2 = {'key2': 2, 'key3': 1}
    obj3 = {'key2': 2}

    # it's fail because the key3 is not in the obj1
    self.bc.check.partial_equality(obj1, obj2)  # 🔴

    # it's fail because the key1 is not in the obj2
    self.bc.check.partial_equality(obj2, obj1)  # 🔴

    # it's pass because the key2 exists in the obj1
    self.bc.check.partial_equality(obj1, obj3)  # 🟢

    # it's pass because the key2 exists in the obj2
    self.bc.check.partial_equality(obj2, obj3)  # 🟢

    # it's fail because the key1 is not in the obj3
    self.bc.check.partial_equality(obj3, obj1)  # 🔴

    # it's fail because the key3 is not in the obj3
    self.bc.check.partial_equality(obj3, obj2)  # 🔴
    ```
    """

    def _fill_partial_equality(first: dict, second: dict) -> dict:
        original = {}

        for key in second.keys():
            original[key] = second[key]

        return original

    def wrapper(first: dict | list[dict], second: dict | list[dict]) -> None:
        assert type(first) == type(second)

        if isinstance(first, list):
            assert len(first) == len(second)

            original = []

            for i in range(0, len(first)):
                original.append(_fill_partial_equality(first[i], second[i]))

        else:
            original = _fill_partial_equality(first, second)

        assert original == second

    yield wrapper


@pytest.fixture
def sign_jwt_link():

    def wrapper(
        client: APIClient,
        app,
        user_id: Optional[int] = None,
        reverse: bool = False,
    ):
        """
        Set Json Web Token in the request.

        Usage:

        ```py
        # setup the database
        model = self.bc.database.create(app=1, user=1)

        # that setup the request to use the credential of user passed
        self.bc.request.authenticate(model.app, model.user.id)
        ```

        Keywords arguments:

        - user: a instance of user model `breathecode.authenticate.models.User`
        """
        from datetime import datetime, timedelta

        from django.utils import timezone

        now = timezone.now()

        # https://datatracker.ietf.org/doc/html/rfc7519#section-4
        payload = {
            "sub": str(user_id or ""),
            "iss": os.getenv("API_URL", "http://localhost:8000"),
            "app": app.slug,
            "aud": "breathecode",
            "exp": datetime.timestamp(now + timedelta(minutes=2)),
            "iat": datetime.timestamp(now) - 1,
            "typ": "JWT",
        }

        if reverse:
            payload["aud"] = app.slug
            payload["app"] = "breathecode"

        if app.algorithm == "HMAC_SHA256":

            token = jwt.encode(payload, bytes.fromhex(app.private_key), algorithm="HS256")

        elif app.algorithm == "HMAC_SHA512":
            token = jwt.encode(payload, bytes.fromhex(app.private_key), algorithm="HS512")

        elif app.algorithm == "ED25519":
            token = jwt.encode(payload, bytes.fromhex(app.private_key), algorithm="EdDSA")

        else:
            raise Exception("Algorithm not implemented")

        client.credentials(HTTP_AUTHORIZATION=f"Link App={app.slug},Token={token}")

    yield wrapper
