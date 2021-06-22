import importlib
import inspect
import logging
import os

from django.contrib.auth.models import User
from django.db.models import Model

from breathecode.authenticate.management.commands.create_roles import Command

logger = logging.getLogger(__name__)

PROJECT = 'breathecode'
MODULES = [
    'admissions',
    # 'assessment',
    'assignments',
    'authenticate',
    'certificate',
    'events',
    'feedback',
    'freelance',
    'marketing',
    'media',
    'monitoring',
    'notify',
]


def clean():
    cleaned = ['User']

    User.objects.all().delete()

    for forder in MODULES:
        path = f'{PROJECT}.{forder}.models'
        module = importlib.import_module(path)
        models = []

        for x in dir(module):
            CurrentModel = getattr(module, x)
            if not inspect.isclass(CurrentModel):
                continue

            if not issubclass(CurrentModel, Model):
                continue

            if (hasattr(CurrentModel, 'Meta') and
                    hasattr(CurrentModel.Meta, 'abstract')):
                continue

            models.append(CurrentModel)

        for CurrentModel in models:
            model_name = CurrentModel.__name__

            if model_name in cleaned:
                continue

            logger.info(f'{model_name} was cleaned')
            CurrentModel.objects.all().delete()
            cleaned.append(model_name)


def load_fixtures():
    for forder in MODULES:
        path = f'{PROJECT}/{forder}/fixtures'

        for root, dirs, files in os.walk(path):
            for name in files:
                if name.startswith('dev_') and name.endswith('.json'):
                    logger.info(f'Load {path}/{name}')
                    os.system(  # noqa: S605
                        f'python manage.py loaddata {path}/{name}')


def extend(roles, slugs):
    caps_groups = [item["caps"] for item in roles if item["slug"] in slugs]
    inhered_caps = []
    for roles in caps_groups:
        inhered_caps = inhered_caps + roles
    return list(dict.fromkeys(inhered_caps))


def load_roles():
    command = Command()
    command.handle()

    logger.info('Roles loaded')


def reset():
    clean()
    load_fixtures()
