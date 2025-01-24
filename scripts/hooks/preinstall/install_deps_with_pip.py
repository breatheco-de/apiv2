#!/bin/env python

import os
import sys

from scripts.utils.get_pip_path import get_pip_path

# fedora silverblue, some package are not compatible with python 3.12 yet
# sudo dnf install boost-devel python3.12-devel

pip_path = get_pip_path()
commands = ";\n".join(
    [
        f"{pip_path} install pipx || {pip_path} install --upgrade pipx",
        f"{pip_path} install --upgrade pip",
        f"{pip_path} install --upgrade yapf poetry toml",
        "pipx install poetry || pipx install poetry",
        "",
    ]
)

exit_code = os.system(commands)

# python don't return 256
if exit_code:
    sys.exit(1)
