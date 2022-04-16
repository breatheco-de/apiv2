import re
from importlib import import_module
from typing import Any, Optional
from rest_framework.test import APITestCase
from django.db.models import Model
from ..generate_models_mixin import GenerateModelsMixin
from ..models_mixin import ModelsMixin

__all__ = ['Database']


class Database:
    """Mixin with the purpose of cover all the related with the database"""

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

        Usage:

        ```py
        # get all the Cohort as list of dict
        self.bc.database.get('admissions.Cohort')

        # get all the Cohort as list of instances of model
        self.bc.database.get('admissions.Cohort', dict=False)
        ```

        Keywords arguments:
        - path(`str`): path to a model, for example `admissions.CohortUser`.
        - dict(`bool`): if true return dict of values of model else return model instance.
        """

        model = Database._get_model(path)
        result = model.objects.filter()

        if dict:
            result = [ModelsMixin.remove_dinamics_fields(self, data.__dict__.copy()) for data in result]

        return result

    def delete(self, path: str, pk: Optional[int or str] = None) -> tuple[int, dict[str, int]]:
        """
        This is a wrapper for `Model.objects.filter(pk=pk).delete()`, delete a element if `pk` is provided else
        all the entries.

        Usage:

        ```py
        # create 19110911 cohorts 🦾
        self.bc.database.create(cohort=19110911)

        # exists 19110911 cohorts 🦾
        self.assertEqual(self.bc.database.count('admissions.Cohort'), 19110911)

        # remove all the cohorts
        self.bc.database.delete(10)

        # exists 19110910 cohorts
        self.assertEqual(self.bc.database.count('admissions.Cohort'), 19110910)
        ```

        # remove all the cohorts
        self.bc.database.delete()

        # exists 0 cohorts
        self.assertEqual(self.bc.database.count('admissions.Cohort'), 0)
        ```

        Keywords arguments:
        - path(`str`): path to a model, for example `admissions.CohortUser`.
        - pk(`str | int`): primary key of model.
        """

        lookups = {'pk': pk} if pk else {}

        model = Database._get_model(path)
        return model.objects.filter(**lookups).delete()

    def get(self, path: str, pk: int or str, dict: bool = True) -> Model | dict[str, Any]:
        """
        This is a wrapper for `Model.objects.filter(pk=pk).first()`, get the values of model as `dict` if
        `dict=True` else get the `Model` instance.

        Usage:

        ```py
        # get the Cohort with the pk 1 as dict
        self.bc.database.get('admissions.Cohort', 1)

        # get the Cohort with the pk 1 as instance of model
        self.bc.database.get('admissions.Cohort', 1, dict=False)
        ```

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

    def count(self, path: str) -> int:
        """
        This is a wrapper for `Model.objects.count()`, get how many instances of this `Model` are saved.

        Usage:

        ```py
        self.bc.database.count('admissions.Cohort')
        ```

        Keywords arguments:
        - path(`str`): path to a model, for example `admissions.CohortUser`.
        """
        model = Database._get_model(path)
        return model.objects.count()

    def create(self, *args, **kwargs) -> dict[str, Model | list[Model]]:
        """
        Create one o many instances of models and return it like a dict of models.

        Usage:

        ```py
        # create three users
        self.bc.database.create(user=3)

        # create one user with a specific first name
        user = {'first_name': 'Lacey'}
        self.bc.database.create(user=user)

        # create two users with a specific first name and last name
        users = [
            {'first_name': 'Lacey', 'last_name': 'Sturm'},
            {'first_name': 'The', 'last_name': 'Warning'},
        ]
        self.bc.database.create(user=users)

        # create two users with the same first name
        user = {'first_name': 'Lacey'}
        self.bc.database.create(user=(2, user))

        # setting up manually the relationships
        cohort_user = {'cohort_id': 2}
        self.bc.database.create(cohort=2, cohort_user=cohort_user)
        ```

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
