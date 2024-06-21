"""
QuerySet fixtures.
"""
import importlib
import os
import site
from typing import Generator, final
from unittest.mock import MagicMock

import pytest
from django.db.models.signals import ModelSignal
from django.dispatch import Signal

__all__ = ['signals', 'Signals', 'signals_map']


def get_signal_files(path: str) -> list[str]:
    signal_files = []

    # Walk through the current directory and its subdirectories
    for folder, _, files in os.walk(path):
        for file in files:
            if file == 'signals.py':
                signal_files.append(os.path.join(folder, file))

    return signal_files


def get_signals(path: str, includes_root_folder=True) -> list[Signal]:

    # Get the current working directory (root directory)
    root_directory = path

    # Initialize a list to store the file paths
    signal_files = get_signal_files(root_directory)

    if '/' in root_directory:
        separator = '/'
    else:
        separator = '\\'

    res = {}

    if includes_root_folder:
        prefix = root_directory

        if prefix.endswith(separator):
            prefix = prefix[:-1]

        prefix = prefix.split(separator)[-1] + '.'

    else:
        prefix = ''

    signal_files = [
        prefix + '.'.join(x.replace(root_directory + separator, '').replace('.py', '').split(separator))
        for x in signal_files
    ]

    signal_files = [x for x in signal_files if '-' not in x]

    for module_path in signal_files:
        module = importlib.import_module(module_path)
        signals = [
            x for x in dir(module)
            if x[0] != '_' and (isinstance(getattr(module, x), Signal) or isinstance(getattr(module, x), ModelSignal))
        ]

        for signal_path in signals:
            res[f'{module_path}.{signal_path}'] = getattr(module, signal_path)

    return res


def get_dependencies() -> list[str]:
    site_packages_dirs = site.getsitepackages()

    # Collect all dependency folders
    dependency_folders = []
    for dir in site_packages_dirs:
        if os.path.exists(dir):
            for folder in os.listdir(dir):
                folder_path = os.path.join(dir, folder)
                if os.path.isdir(folder_path) and folder_path.endswith('.dist-info') is False:
                    dependency_folders.append(folder_path)

    return dependency_folders


def check_path(dir: str, pattern: str):
    linux_path = dir.replace('\\', '/')
    windows_path = dir.replace('/', '\\')
    return linux_path not in dir and windows_path not in dir


@pytest.fixture(scope='session')
def signals_map():
    # Get the current working directory (root directory)
    root_directory = os.getcwd()

    signals = {}

    for dependency_folder in get_dependencies():
        signals.update(get_signals(dependency_folder))

    signals.update(get_signals(root_directory, includes_root_folder=False))

    yield signals


@final
class Signals:
    """Signal utils."""

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

        self._disabled = True

        # Mock the functions to disable signals

        def mock(original):

            def wrapper(x, *args, **kwargs):
                if self._disabled:
                    return

                return original(x, *args, **kwargs)

            return wrapper

        # MagicMock(wraps=mock(original))
        self._monkeypatch.setattr('django.dispatch.dispatcher.Signal.send', mock(self._original_signal_send))
        self._monkeypatch.setattr('django.dispatch.dispatcher.Signal.send_robust',
                                  mock(self._original_signal_send_robust))

        # Mock the functions to disable signals
        self._monkeypatch.setattr('django.db.models.signals.ModelSignal.send', mock(self._original_model_signal_send))
        self._monkeypatch.setattr('django.db.models.signals.ModelSignal.send_robust',
                                  mock(self._original_model_signal_send_robust))

    def enable(self, *to_enable, debug=False):
        """
        Enable the specified signals or all signals if no arguments are provided. Right now this method can only be used once per test.

        Parameters:
            *to_enable (list, optional): A list of signals to enable. Defaults to None.
            debug (bool, optional): A boolean flag to enable debugging. Defaults to False.

        Returns:
            None
        """

        self._disabled = False

        self._monkeypatch.setattr('django.dispatch.dispatcher.Signal.send', self._original_signal_send)
        self._monkeypatch.setattr('django.dispatch.dispatcher.Signal.send_robust', self._original_signal_send_robust)

        self._monkeypatch.setattr('django.db.models.signals.ModelSignal.send', self._original_model_signal_send)
        self._monkeypatch.setattr('django.db.models.signals.ModelSignal.send_robust',
                                  self._original_model_signal_send_robust)

        if to_enable or debug:
            to_disable = [x for x in self._signals_map if x not in to_enable]

            for signal in to_disable:

                def apply_mock(module):

                    def send_mock(*args, **kwargs):
                        if debug:
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
    """Signals utils."""

    s = Signals(monkeypatch, signals_map)
    s.disable()

    yield s

    s.enable()
