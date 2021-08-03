import os
# import sys

__all__ = ['main']


def preinstall_hook():
    from scripts.hooks.preinstall import scripts

    for script_name in scripts:
        print('')
        print('--- Running preinstall script ---',
              os.path.basename(script_name), '---')
        print('')
        os.system(f'python {script_name}')


def install():
    print('')
    print('--- Running pipenv install ---')
    print('')
    os.system(f'pipenv install --dev')


def postinstall_hook():
    from scripts.hooks.postinstall import scripts

    for script_name in scripts:
        print('')
        print('--- Running postinstall script ---',
              os.path.basename(script_name), '---')
        print('')
        os.system(f'python {script_name}')


def main():
    preinstall_hook()
    install()
    postinstall_hook()
