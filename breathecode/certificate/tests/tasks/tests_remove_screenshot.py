from unittest.mock import MagicMock, call

import pytest

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from ...tasks import remove_screenshot


@pytest.fixture(autouse=True)
def get_patch(db, monkeypatch):

    def wrapper(key, value):
        if isinstance(value, Exception):
            m4 = MagicMock(side_effect=value)

        else:
            m4 = MagicMock(side_effect=lambda x: value if key == x else 1000)

        monkeypatch.setattr("breathecode.certificate.actions.remove_certificate_screenshot", m4)

        return m1, m2, m3, m4

    m1 = MagicMock()
    m2 = MagicMock()
    m3 = MagicMock()
    monkeypatch.setattr("logging.Logger.info", m1)
    monkeypatch.setattr("logging.Logger.warning", m2)
    monkeypatch.setattr("logging.Logger.error", m3)

    yield wrapper


def test_returns_true(bc: Breathecode, get_patch, get_int):
    """remove_screenshot don't call open in development environment"""

    key = get_int()
    info_mock, warn_mock, error_mock, action_mock = get_patch(key, True)

    remove_screenshot(key)

    assert info_mock.call_args_list == [call("Starting remove_screenshot")]
    assert warn_mock.call_args_list == []
    assert error_mock.call_args_list == []
    assert action_mock.call_args_list == [call(key)]


def test_returns_false(bc: Breathecode, get_patch, get_int):
    """remove_screenshot don't call open in development environment"""

    key = get_int()
    info_mock, warn_mock, error_mock, action_mock = get_patch(key, False)

    remove_screenshot(key)

    assert info_mock.call_args_list == [call("Starting remove_screenshot")]
    assert warn_mock.call_args_list == []
    assert error_mock.call_args_list == [
        call("UserSpecialty does not have any screenshot, it is skipped", exc_info=True)
    ]
    assert action_mock.call_args_list == [call(key)]


def test_returns_an_exception(bc: Breathecode, get_patch, get_int, fake):
    """remove_screenshot don't call open in development environment"""

    key = get_int()
    exc = fake.pystr()
    info_mock, warn_mock, error_mock, action_mock = get_patch(key, Exception(exc))

    remove_screenshot(key)

    assert info_mock.call_args_list == [call("Starting remove_screenshot")]
    assert warn_mock.call_args_list == []
    assert error_mock.call_args_list == [call(exc, exc_info=True)]
    assert action_mock.call_args_list == [call(key)]
