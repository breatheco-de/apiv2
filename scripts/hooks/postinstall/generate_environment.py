import json
import os
from pathlib import Path

from shutil import which, copyfile

__all__ = ['main']

api_path = os.getcwd()
env_path = Path(f'{api_path}/.env').resolve()
env_example_path = Path(f'{api_path}/.env.example').resolve()

if which('gp'):
    copyfile(env_example_path, env_path)
    exit()

content = ''
with open(env_example_path, 'r') as file:
    lines = file.read().split('\n')

for line in lines:
    try:
        key, value = line.split('=')

        if key == 'DATABASE_URL':
            content += f'{key}=postgres://user:pass@localhost:5432/breathecode\n'

        elif key == 'REDIS_URL':
            content += f'{key}=redis://localhost:6379\n'

        elif key == 'API_URL':
            content += f'{key}=http://localhost:8000\n'

        else:
            content += f'{key}={value}\n'

    except:
        content += '\n'

with open(env_path, 'w') as file:
    file.write(content)
