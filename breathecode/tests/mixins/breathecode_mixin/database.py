import re
from importlib import import_module
from typing import Any
from rest_framework.test import APITestCase
from channels.db import database_sync_to_async
from django.db.models import Model
from ..generate_models_mixin import GenerateModelsMixin
from ..models_mixin import ModelsMixin

__all__ = ['Database']


class Database:
    """Wrapper of last implementation for generate_queries for testing purposes"""

    _cache: dict[str, Model] = {}
    _parent: APITestCase

    def __init__(self, parent) -> None:
        self._parent = parent

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
        """
        This is a wrapper for `Model.objects.filter()`, get a list of values of models as `list[dict]` if
        `dict=True` else get a list of `Model` instances.

        Keywords arguments:
        - path(`str`): path to a model, for example `admissions.CohortUser`.
        - dict(`bool`): if true return dict of values of model else return model instance.
        """

        model = Database._get_model(path)
        result = model.objects.filter()

        if dict:
            result = [ModelsMixin.remove_dinamics_fields(self, data.__dict__.copy()) for data in result]

        return result

    @database_sync_to_async
    def async_list_of(self, path: str, dict: bool = True) -> list[Model | dict[str, Any]]:
        """
        This is a wrapper for `Model.objects.filter()`, get a list of values of models as `list[dict]` if
        `dict=True` else get a list of `Model` instances.

        Keywords arguments:
        - path(`str`): path to a model, for example `admissions.CohortUser`.
        - dict(`bool`): if true return dict of values of model else return model instance.
        """

        return self.list_of(path, dict)

    def get(self, path: str, pk: int or str, dict: bool = True) -> Model | dict[str, Any]:
        """
        This is a wrapper for `Model.objects.filter(pk=pk).first()`, get the values of model as `dict` if
        `dict=True` else get the `Model` instance.

        Keywords arguments:
        - path(`str`): path to a model, for example `admissions.CohortUser`.
        - pk(`str | int`): primary key of model.
        - dict(`bool`): if true return dict of values of model else return model instance.
        """

        model = Database._get_model(path)
        result = model.objects.filter(pk=pk).first()

        if dict:
            result = ModelsMixin.remove_dinamics_fields(self, result.__dict__.copy())

        return result

    @database_sync_to_async
    def async_get(self, path: str, pk: int or str, dict: bool = True) -> Model | dict[str, Any]:
        """
        This is a wrapper for `Model.objects.filter(pk=pk).first()`, get the values of model as `dict` if
        `dict=True` else get the `Model` instance.

        Keywords arguments:
        - path(`str`): path to a model, for example `admissions.CohortUser`.
        - pk(`str | int`): primary key of model.
        - dict(`bool`): if true return dict of values of model else return model instance.
        """

        return self.get(path, pk, dict)

    def count(self, path: str) -> int:
        """
        This is a wrapper for `Model.objects.count()`, get how many instances of this `Model` are saved.

        Keywords arguments:
        - path(`str`): path to a model, for example `admissions.CohortUser`.
        """

        model = Database._get_model(path)
        return model.objects.count()

    @database_sync_to_async
    def async_count(self, path: str) -> int:
        """
        This is a wrapper for `Model.objects.count()`, get how many instances of this `Model` are saved.

        Keywords arguments:
        - path(`str`): path to a model, for example `admissions.CohortUser`.
        """

        return self.count(path)

    def create(self, *args, **kwargs) -> dict[str, Model | list[Model]]:
        """
        Create one o many instances of models and return it like a dict of models.

        It get the model name as snake case, you can pass a `bool`, `int`, `dict`, `tuple`, `list[dict]` or
        `list[tuple]`.

        Behavior for type of argument:
        - `bool`: if it is true generate a instance of a model.
        - `int`: generate a instance of a model n times, if `n` > 1 this is a list.
        - `dict`: generate a instance of a model, this pass to mixer.blend custom values to the model.
        - `tuple`: one element need to be a int and the other be a dict, generate a instance of a model n times,
        if `n` > 1 this is a list, this pass to mixer.blend custom values to the model.
        - `list[dict]`: generate a instance of a model n times, if `n` > 1 this is a list,
        this pass to mixer.blend custom values to the model.
        - `list[tuple]`: generate a instance of a model n times, if `n` > 1 this is a list for each element,
        this pass to mixer.blend custom values to the model.

        Keywords arguments deprecated:
        - models: this arguments is use to implement inheritance, receive as argument the output of other
        `self.bc.database.create()` execution.
        - authenticate: create a user and use `APITestCase.client.force_authenticate(user=models['user'])` to
        get credentials.
        """

        return GenerateModelsMixin.generate_models(self._parent, _new_implementation=True, *args, **kwargs)

    @database_sync_to_async
    def async_create(self, *args, **kwargs) -> dict[str, Model | list[Model]]:
        """
        This is a wrapper for `Model.objects.count()`, get how many instances of this `Model` are saved.

        Keywords arguments:
        - path(`str`): path to a model, for example `admissions.CohortUser`.
        """

        return self.create(*args, **kwargs)
