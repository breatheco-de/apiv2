import os
from shutil import which

print('---')
print(which('python'))
p = os.system('python manage.py makemigrations --check --dry-run')

if p:
    exit(1)
