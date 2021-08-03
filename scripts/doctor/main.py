import json
import os
from pathlib import Path

from shutil import which

__all__ = ['main']

api_path = os.getcwd()
dependencies_path = Path(
    f'{api_path}/scripts/doctor/dependencies.json').resolve()


def main():
    with open(dependencies_path, 'r') as file:
        dependencies = json.load(file)

        print('--- Check installation status ---\n')

        for dependency in dependencies:
            result = 'installed' if which(dependency) else 'not installed'
            print(f'{dependency} =>', result)
