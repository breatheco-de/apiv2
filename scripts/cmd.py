import os
import subprocess
import sys
import webbrowser
from pathlib import Path


def python_module_to_dir(module: str) -> str:
    parsed_dir = "/".join(module.split("."))
    return Path(f"./{parsed_dir}").resolve()


def get_argument(index: int):
    try:
        return sys.argv[index]
    except IndexError:
        return None


def get_arguments(offset: int = 0):
    return " ".join(sys.argv[1 + offset :])


def dev():
    args = get_arguments()
    if ":" not in args and not any(
        arg.startswith("0.0.0.0") or arg.startswith("127.0.0.1") or arg.startswith("localhost") for arg in args.split()
    ):
        args = f"0.0.0.0:8000 {args}"
    sys.exit(os.system(f"python manage.py runserver {args}"))


def start():
    args = get_arguments()
    if "--bind" not in args:
        args = f"--bind 0.0.0.0:8000 {args}"

    # Add --reload flag for Gunicorn
    # Ensure --reload is not duplicated if already in args by chance, though unlikely for this script
    if "--reload" not in args:
        args = f"--reload {args}"

    sys.exit(os.system(f"gunicorn breathecode.asgi --worker-class uvicorn.workers.UvicornWorker {args}"))


def migrate():
    sys.exit(os.system(f"python manage.py migrate {get_arguments()}"))


def makemigrations():
    sys.exit(os.system(f"python manage.py makemigrations {get_arguments()}"))


def startapp():
    sys.exit(os.system(f"python manage.py startapp {get_arguments()}"))


def createsuperuser():
    sys.exit(os.system(f"python manage.py createsuperuser {get_arguments()}"))


def test():
    sys.exit(os.system(f"pytest --nomigrations --durations=1 {get_arguments()}"))


def test_parallel():
    sys.exit(
        os.system(
            f"pytest --disable-pytest-warnings {get_arguments()} "
            f"--cov-report html -n auto --nomigrations --durations=1"
        )
    )


def test_coverage():
    if (module := get_argument(1)) is None:
        module = "breathecode"

    dir = python_module_to_dir(module)

    command = (
        f"pytest {dir} --disable-pytest-warnings {get_arguments(1)} "
        f"--cov={module} --cov-report html -n auto --nomigrations --durations=1"
    )

    exit_code = subprocess.run(command, shell=True).returncode

    webbrowser.open("file://" + os.path.realpath(os.path.join(os.getcwd(), "htmlcov", "index.html")))

    if exit_code:
        sys.exit(1)


def format():
    sys.exit(os.system(f"pre-commit run --all-files {get_arguments()}"))


def install_precommit():
    sys.exit(os.system(f"pre-commit install {get_arguments()}"))


def celery():
    sys.exit(os.system(f"python -m celery -A breathecode.celery worker --loglevel=INFO {get_arguments()}"))


def docs_serve():
    sys.exit(os.system(f"mkdocs serve --livereload {get_arguments()}"))


def docs_build():
    sys.exit(os.system(f"mkdocs build {get_arguments()}"))


def docs_deploy():
    sys.exit(os.system(f"mkdocs gh-deploy -c {get_arguments()}"))


def lint():
    sys.exit(os.system(f"pre-commit run --all-files {get_arguments()}"))


def flake8():
    sys.exit(os.system(f"flake8 . {get_arguments()}"))


def docker_build():
    sys.exit(os.system(f"docker build . {get_arguments()}"))
