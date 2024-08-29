import os
from typing import Generator

import pytest

__all__ = ["clean_environment"]

WHITELIST = [
    "RANDOM_SEED",
    "SQLALCHEMY_SILENCE_UBER_WARNING",
    "SHELL",
    "HOME",
    "VSCODE_GIT_ASKPASS_EXTRA_ARGS",
    "HOSTTYPE",
    "WSL_INTEROP",
    "XDG_RUNTIME_DIR",
    "COLORTERM",
    "WSL_DISTRO_NAME",
    "TERM",
    "PATH",
    "TERM_PROGRAM",
    "VSCODE_GIT_ASKPASS_NODE",
    "PULSE_SERVER",
    "VSCODE_GIT_IPC_HANDLE",
    "_OLD_FISH_PROMPT_OVERRIDE",
    "_OLD_VIRTUAL_PATH",
    "DISPLAY",
    "LOGNAME",
    "VIRTUAL_ENV",
    "WSLENV",
    "WAYLAND_DISPLAY",
    "SHLVL",
    "PWD",
    "TERM_PROGRAM_VERSION",
    "USER",
    "GIT_ASKPASS",
    "VSCODE_GIT_ASKPASS_MAIN",
    "NAME",
    "VSCODE_IPC_HOOK_CLI",
    "LANG",
]


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    keys = os.environ.keys()

    for key in keys:
        if key not in WHITELIST:
            monkeypatch.delenv(key)

    yield
