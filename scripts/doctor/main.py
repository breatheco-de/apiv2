import json
import os
from pathlib import Path

from shutil import which
import socket

__all__ = ['main']

api_path = os.getcwd()
dependencies_path = Path(
    f'{api_path}/scripts/doctor/dependencies.json').resolve()


def check_dependencies(dependencies):
    print('--- Check installation status ---\n')

    for dependency in dependencies:
        result = 'installed' if which(dependency) else 'not installed'
        print(f'{dependency} =>', result)


def port_is_open(host, port=80):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex(('localhost', 6379))
        if result == 0:
            return True
        else:
            return False


def isOpen(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((ip, int(port)))
        s.shutdown(2)
        return True
    except:
        return False


def main():
    with open(dependencies_path, 'r') as file:
        dependencies = json.load(file)

    check_dependencies(dependencies)

    print('\n--- Check conection status ---\n')

    import subprocess
    result = subprocess.run(['docker', 'image', 'ls'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    print(f'docker =>', 'up' if not result.stderr else 'down')
    print(f'postgres =>', 'up' if port_is_open('localhost', 5432) else 'down')
    print(f'redis =>', 'up' if port_is_open('localhost', 6379) else 'down')
