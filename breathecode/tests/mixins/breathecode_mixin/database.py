import re
from importlib import import_module
from typing import Any
from django.db.models import Model
from ..generate_models_mixin import GenerateModelsMixin
from ..models_mixin import ModelsMixin

ModelsMixin

__all__ = ['Database']


class Database:
    """Wrapper of last implementation for generate_queries for testing purposes"""
    _cache = {}

    @classmethod
    def _get_model(cls, path: str) -> Model:
        """Get model class"""

        if path in cls._cache:
            return cls._cache[path]

        app, model_name = path.split('.')

        module_path = f'breathecode.{app}.models'
        module = import_module(module_path)

        cls._cache[path] = getattr(module, model_name)

        return cls._cache[path]

    def list_of(self, path: str, dict: bool = True) -> list[Model | dict[str, Any]]:
        model = Database._get_model(path)
        result = model.objects.filter()

        if dict:
            result = [ModelsMixin.remove_dinamics_fields(self, data.__dict__.copy()) for data in result]

        return result

    def get(self, path: str, pk: int or str, dict: bool = True) -> Model | dict[str, Any]:
        model = Database._get_model(path)
        result = model.objects.filter(pk=pk).first()

        if dict:
            result = [ModelsMixin.remove_dinamics_fields(self, data.__dict__.copy()) for data in result]

        return result

    def count(self, path: str) -> int:
        model = Database._get_model(path)
        return model.objects.count()

    def create(self, *args, **kwargs) -> dict[str, Model | list[Model]]:
        return GenerateModelsMixin.generate_models(self, *args, **kwargs)
