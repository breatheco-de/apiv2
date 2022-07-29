import os
from scripts.utils.get_python_path import get_python_path

from shutil import which

__all__ = ['main']
python_path = get_python_path()


def preinstall_hook():
    from scripts.hooks.preinstall import scripts

    for script_name in scripts:
        print('')
        print('--- Running preinstall script ---', os.path.basename(script_name), '---')
        print('')
        os.system(f'{python_path} -m {script_name}')


def install():
    print('')
    print('--- Running pdm install ---')
    print('')

    python_path = which('python')
    os.system(f'pdm install --dev --python "{python_path}"')


def postinstall_hook():
    from scripts.hooks.postinstall import scripts

    for script_name in scripts:
        print('')
        print('--- Running postinstall script ---', os.path.basename(script_name), '---')
        print('')
        os.system(f'{python_path} -m {script_name}')


def main():
    preinstall_hook()
    install()
    postinstall_hook()
