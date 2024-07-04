import inspect
import os
import json
import importlib
import traceback

from breathecode.tests.mixins import DatetimeMixin
from datetime import datetime, timedelta
from django.db.models import Model
from django.core.management.base import BaseCommand
from breathecode.settings import INSTALLED_APPS
from pathlib import Path
from decimal import Decimal

PROJECT = "breathecode"
MODULES = [
    x.replace("breathecode.", "")
    for x in INSTALLED_APPS
    if x.startswith("breathecode.") and x != "breathecode.admin_styles"
]


def db_backup_bucket():
    return os.getenv("DB_BACKUP_BUCKET")


class Command(BaseCommand, DatetimeMixin):
    help = "Backup models"

    def add_arguments(self, parser):
        parser.add_argument("mode", type=str, choices=["storage", "console", "bucket"])
        parser.add_argument("module", nargs="?", type=str, default="")
        parser.add_argument("model", nargs="?", type=str, default="")

    def handle(self, *args, **options):
        self.all_model_names = []

        if not "mode" in options:
            return self.stderr.write(self.style.ERROR("missing mode arguments"))

        module_name = options["module"]
        model_name = options["model"]
        self.mode = options["mode"]

        if module_name and model_name:
            self.backup(module_name, model_name)

        elif module_name:
            for model_name in self.find_modules(module_name):
                self.backup(module_name, model_name)

        else:
            for module_name in MODULES:
                for model_name in self.find_modules(module_name):
                    self.backup(module_name, model_name)

    def find_modules(self, module_name):
        path = f"breathecode.{module_name}.models"
        module = importlib.import_module(path)
        models = []

        for x in dir(module):
            model_cls = getattr(module, x)
            if not inspect.isclass(model_cls):
                continue

            if not issubclass(model_cls, Model):
                continue

            if hasattr(model_cls, "Meta") and hasattr(model_cls.Meta, "abstract") and model_cls.__name__ != "User":
                continue

            if hasattr(model_cls, "Meta") and hasattr(model_cls.Meta, "proxy") and model_cls.__name__ != "User":
                continue

            if model_cls.__name__ in self.all_model_names:
                continue

            self.all_model_names.append(model_cls.__name__)
            models.append(model_cls.__name__)

        return models

    def backup(self, module_name, model_name):
        self.module_name = module_name
        self.model_name = model_name
        path = f"breathecode.{self.module_name}.models"

        try:
            module = importlib.import_module(path)
        except ModuleNotFoundError:
            return self.stderr.write(
                self.style.ERROR(f"module `{self.module_name}` not found or it not have models too")
            )

        if not hasattr(module, self.model_name):
            return self.stderr.write(
                self.style.ERROR(f"module `{self.module_name}` not have a model called `{self.model_name}`")
            )

        model_cls = getattr(module, self.model_name)
        results = model_cls.objects.all()
        dicts = [self.prepare_data(x) for x in results]

        try:
            if self.mode == "storage":
                self.backup_in_storage(json.dumps(dicts))

            elif self.mode == "console":
                self.backup_in_console(json.dumps(dicts))

            elif self.mode == "bucket":
                self.backup_in_bucket(json.dumps(dicts))

        except Exception as e:
            print(dicts)
            traceback.print_exc()
            raise Exception(str(e))

    def prepare_data(self, model):
        data = vars(model)
        private_attrs = [x for x in data if x.startswith("_")]
        datetime_attrs = [x for x in data if isinstance(data[x], datetime)]
        decimal_attrs = [x for x in data if isinstance(data[x], Decimal)]
        timedelta_attrs = [x for x in data if isinstance(data[x], timedelta)]

        for key in private_attrs:
            del data[key]

        for key in datetime_attrs:
            data[key] = self.datetime_to_iso(data[key])

        for key in decimal_attrs:
            data[key] = float(data[key])

        for key in timedelta_attrs:
            data[key] = str(data[key])

        return data

    def backup_in_storage(self, data):
        current_path = Path(os.getcwd())
        backup_path = current_path / "backup"
        file_path = current_path / "backup" / f"{self.module_name}.{self.model_name.lower()}.json"

        if not os.path.exists(current_path / "backup"):
            os.mkdir(backup_path)

        with open(file_path, "w") as file:
            file.write(data)

    def backup_in_console(self, data):
        print(data)

    def backup_in_bucket(self, data):
        from ....services.google_cloud import Storage

        storage = Storage()
        name = f"{self.module_name}.{self.model_name.lower()}.json"

        cloud_file = storage.file(db_backup_bucket(), name)
        cloud_file.upload(data)
