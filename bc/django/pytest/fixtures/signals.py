"""
QuerySet fixtures.
"""
# not working yet
import importlib
from typing import Generator, final

import pytest

# from django.db.models.query import QuerySet
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
from django.dispatch import Signal

__all__ = ['signals', 'Signals', 'signals_map']


def check_path(dir: str, pattern: str):
    linux_path = dir.replace('\\', '/')
    windows_path = dir.replace('/', '\\')
    return linux_path not in dir and windows_path not in dir


@pytest.fixture(scope='session')
def signals_map():
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
        if check_path(dir=x, pattern='/bc/django/') and check_path(dir=x, pattern='.venv') and check_path(dir=x, pattern='.env')
    ]

    for module_path in signal_files:
        print(module_path)
        module = importlib.import_module(module_path)
        signals = [
            x for x in dir(module)
            if x[0] != '_' and (isinstance(getattr(module, x), Signal) or isinstance(getattr(module, x), ModelSignal))
        ]

        for signal_path in signals:
            res[f'{module_path}.{signal_path}'] = getattr(module, signal_path)

    yield res


@final
class Signals:
    """
    QuerySet utils.
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch, signals_map: dict[str, Signal | ModelSignal]) -> None:
        self._monkeypatch = monkeypatch
        self._signals_map = signals_map

        self._original_signal_send = Signal.send
        self._original_signal_send_robust = Signal.send_robust

        self._original_model_signal_send = ModelSignal.send
        self._original_model_signal_send_robust = ModelSignal.send_robust

    def disable(self):
        """Disables all signals.

        This function can be used to temporarily disable all signals during a test.
        When signals are disabled, they will not be sent and any code that depends on them will not be executed.
        """

        # Mock the functions to disable signals
        self._monkeypatch.setattr(Signal, 'send', lambda *args, **kwargs: None)
        self._monkeypatch.setattr(Signal, 'send_robust', lambda *args, **kwargs: None)

        # Mock the functions to disable signals
        self._monkeypatch.setattr(ModelSignal, 'send', lambda *args, **kwargs: None)
        self._monkeypatch.setattr(ModelSignal, 'send_robust', lambda *args, **kwargs: None)

    def enable(self, *to_enable, debug=False):
        """
        Enable the specified signals or all signals if no arguments are provided. Right now this method can only be used once per test.

        Parameters:
            *to_enable (list, optional): A list of signals to enable. Defaults to None.
            debug (bool, optional): A boolean flag to enable debugging. Defaults to False.

        Returns:
            None
        """

        self._monkeypatch.setattr(Signal, 'send', self._original_signal_send)
        self._monkeypatch.setattr(Signal, 'send_robust', self._original_signal_send_robust)

        self._monkeypatch.setattr(ModelSignal, 'send', self._original_model_signal_send)
        self._monkeypatch.setattr(ModelSignal, 'send_robust', self._original_model_signal_send_robust)

        if to_enable or debug:
            to_disable = [x for x in self._signals_map if x not in to_enable]

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

                    self._monkeypatch.setattr(module, send_mock)

                apply_mock(f'{signal}.send')
                apply_mock(f'{signal}.send_robust')


@pytest.fixture
def signals(monkeypatch, signals_map: dict[str, Signal | ModelSignal]) -> Generator[Signals, None, None]:
    """
    Signals utils.
    """

    s = Signals(monkeypatch, signals_map)
    s.disable()

    yield s

    s.enable()
