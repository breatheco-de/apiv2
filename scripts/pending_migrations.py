import os

p = os.system("python manage.py makemigrations --check --dry-run")

if p:
    exit(1)
