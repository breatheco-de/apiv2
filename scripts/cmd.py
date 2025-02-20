import os
import sys


def get_arguments():
    return " ".join(sys.argv[1:])


def dev():
    os.system(f"python manage.py runserver {get_arguments()}")


def start():
    os.system(f"gunicorn breathecode.asgi --worker-class uvicorn.workers.UvicornWorker {get_arguments()}")


def migrate():
    os.system(f"python manage.py migrate {get_arguments()}")


def makemigrations():
    os.system(f"python manage.py makemigrations {get_arguments()}")


def startapp():
    os.system(f"python manage.py startapp {get_arguments()}")


def createsuperuser():
    os.system(f"python manage.py createsuperuser {get_arguments()}")


def test():
    os.system(f"pytest --nomigrations --durations=1 {get_arguments()}")


def format():
    os.system(f"pre-commit run --all-files {get_arguments()}")


def install_precommit():
    os.system(f"pre-commit install {get_arguments()}")


def celery():
    os.system(f"python -m celery -A breathecode.celery worker --loglevel=INFO {get_arguments()}")


def docs_serve():
    os.system(f"mkdocs serve --livereload {get_arguments()}")


def docs_build():
    os.system(f"mkdocs build {get_arguments()}")


def docs_deploy():
    os.system(f"mkdocs gh-deploy -c {get_arguments()}")


def lint():
    os.system(f"pre-commit run --all-files {get_arguments()}")


def flake8():
    os.system(f"flake8 . {get_arguments()}")


def docker_build():
    os.system(f"docker build . {get_arguments()}")
