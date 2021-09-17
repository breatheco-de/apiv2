import os

from shutil import which

__all__ = ['main']


def preinstall_hook():
    from scripts.hooks.preinstall import scripts

    for script_name in scripts:
        print('')
        print('--- Running preinstall script ---', os.path.basename(script_name), '---')
        print('')
        os.system(f'python {script_name}')


def install():
    print('')
    print('--- Running pipenv install ---')
    print('')

    python_path = which('python')
    os.system(f'pipenv install --dev --python "{python_path}"')


def postinstall_hook():
    from scripts.hooks.postinstall import scripts

    for script_name in scripts:
        print('')
        print('--- Running postinstall script ---', os.path.basename(script_name), '---')
        print('')
        os.system(f'python {script_name}')


def main():
    preinstall_hook()
    install()
    postinstall_hook()
