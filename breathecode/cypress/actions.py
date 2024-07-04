import importlib
import inspect
import logging

from django.contrib.auth.models import User
from django.db.models import Model
from mixer.backend.django import mixer

from breathecode.authenticate.management.commands.create_academy_roles import Command

logger = logging.getLogger(__name__)

PROJECT = "breathecode"
MODULES = [
    "admissions",
    # 'assessment',
    "assignments",
    "authenticate",
    "certificate",
    "events",
    "feedback",
    "freelance",
    "marketing",
    "media",
    "monitoring",
    "notify",
]


def clean():
    cleaned = ["User"]

    User.objects.all().delete()

    for forder in MODULES:
        path = f"{PROJECT}.{forder}.models"
        module = importlib.import_module(path)
        models = []

        for x in dir(module):
            model_cls = getattr(module, x)
            if not inspect.isclass(model_cls):
                continue

            if not issubclass(model_cls, Model):
                continue

            if hasattr(model_cls, "Meta") and hasattr(model_cls.Meta, "abstract"):
                continue

            models.append(model_cls)

        for model_cls in models:
            model_name = model_cls.__name__

            if model_name in cleaned:
                continue

            logger.info(f"{model_name} was cleaned")
            model_cls.objects.all().delete()
            cleaned.append(model_name)


def load_roles():
    command = Command()
    command.handle()

    logger.info("Roles loaded")


def get_model(model_name):
    modules = MODULES
    found = []

    if "." in model_name:
        parts = model_name.split(".")
        if len(parts) != 2:
            raise Exception("Bad model name format")

        modules = [parts[0]]
        model_name = parts[1]

    if model_name == "User":
        found.append(User)

    for forder in modules:
        path = f"{PROJECT}.{forder}.models"
        module = importlib.import_module(path)

        if not hasattr(module, model_name):
            continue

        model = getattr(module, model_name)

        if not inspect.isclass(model):
            continue

        if not issubclass(model, Model):
            continue

        if hasattr(model, "Meta") and hasattr(model.Meta, "abstract"):
            continue

        found.append(model)

    if not found:
        raise Exception("Model not found")

    if len(found) > 1:
        raise Exception("Exist many app with the same model name, use `app.model` syntax")

    return found[0]


def clean_model(model_name):
    model_cls = get_model(model_name)
    model_cls.objects.all().delete()


def generate_model(data):
    status = "done"
    pk = 0

    try:
        model_name = data.pop("$model")
        model_cls = get_model(model_name)
        element = mixer.blend(model_cls, **data)
        pk = element.pk

    except Exception as e:
        status = str(e)

    result = {
        "model": model_name,
        "status_text": status,
    }

    if pk:
        result["pk"] = pk

    return result


def generate_models(step):
    result = []

    for data in step:
        current_result = generate_model(data)
        result.append(current_result)

    return result
