#!/bin/env python

import os
import sys
import shutil
import webbrowser
from pathlib import Path
from .utils.environment import test_environment, reset_environment


def python_module_to_dir(module: str) -> str:
    parsed_dir = "/".join(module.split("."))
    return Path(f"./{parsed_dir}").resolve()


def help_command():
    print("Usage:")
    print(
        "   `pipenv run cov breathecode.events` where events is the name of module and accept "
        "add submodules using the dot(.) character as delimiter."
    )
    print("")
    print("commands:")
    print("   --help see this help message.")
    exit()


if __name__ == "__main__":
    module = "breathecode"

    if len(sys.argv) > 3:
        module = sys.argv[3]

        if module == "--help" or module == "-h":
            help_command()

    dir = python_module_to_dir(module)

    reset_environment()
    test_environment()
    htmlcov_path = os.path.join(os.getcwd(), "htmlcov")

    if os.path.exists(htmlcov_path):
        shutil.rmtree(htmlcov_path)

    exit_code = os.system(
        f"pytest {dir} --disable-pytest-warnings {sys.argv[1]} {sys.argv[2]} "
        f"--cov={module} --cov-report html --nomigrations --durations=1"
    )

    webbrowser.open("file://" + os.path.realpath(os.path.join(os.getcwd(), "htmlcov", "index.html")))

    # python don't return 256
    if exit_code:
        sys.exit(1)
