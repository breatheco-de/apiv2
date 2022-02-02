import yaml
from typing import Any
from rest_framework.test import APITestCase
from django.db.models import Model
from ..models_mixin import ModelsMixin

__all__ = ['Format']


class Format:
    """Wrapper of last implementation for request for testing purposes"""

    _parent: APITestCase

    def __init__(self, parent) -> None:
        self._parent = parent

    def to_dict(self, arg: Any) -> dict[str, Any] | list[dict[str, Any]]:
        """Parse the object to a `dict` or `list[dict]`"""

        if isinstance(arg, list):
            return [self._one_to_dict(x) for x in arg]

        return self._one_to_dict(arg)

    def _one_to_dict(self, arg) -> dict[str, Any]:
        """Parse the object to a `dict`"""

        if isinstance(arg, Model):
            return ModelsMixin.remove_dinamics_fields(None, vars(arg))

        if isinstance(arg, dict):
            return arg

        raise NotImplementedError(f'{arg.__name__} is not implemented yet')

    def describe_models(self, models: dict[str, Model]) -> str:
        """Describe the models"""

        title_spaces = ' ' * 8
        model_spaces = ' ' * 10
        result = {}

        for key in models:
            model = models[key]

            if isinstance(model, list):
                for v in model:
                    name, obj = self._describe_model(v)
                    result[name] = obj

            else:
                name, obj = self._describe_model(model)
                result[name] = obj

        print(title_spaces + 'Descriptions of models are being generated:')

        for line in yaml.dump(result).split('\n'):
            if not line.startswith(' '):
                print()

            print(model_spaces + line)

    def _describe_model(self, model: Model):
        pk_name = self._get_pk_name(model)
        attrs = dir(model)
        result = {}

        for key in attrs:
            if key.startswith('_'):
                continue

            if key == 'DoesNotExist':
                continue

            if key == 'MultipleObjectsReturned':
                continue

            if key.startswith('get_next_'):
                continue

            if key.startswith('get_previous_'):
                continue

            if key.endswith('_set'):
                continue

            if not hasattr(model, key):
                continue

            attr = getattr(model, key)

            if attr.__class__.__name__ == 'method':
                continue

            if isinstance(attr, Model):
                result[key] = f'{attr.__class__.__name__}({self._get_pk_name(attr)}={self._repr_pk(attr.pk)})'

            elif attr.__class__.__name__ == 'ManyRelatedManager':
                instances = [
                    f'{attr.model.__name__}({self._get_pk_name(x)}={self._repr_pk(x.pk)})'
                    for x in attr.get_queryset()
                ]
                result[key] = instances

        return (f'{model.__class__.__name__}({pk_name}={self._repr_pk(model.pk)})', result)

    def _repr_pk(self, pk: str | int) -> int | str:
        if isinstance(pk, int):
            return pk

        return f'"{pk}"'

    def _get_pk_name(self, model: Model):
        from django.db.models.fields import Field, SlugField

        # print(dir(model))
        attrs = [
            x for x in dir(model)
            if hasattr(model.__class__, x) and (isinstance(getattr(model.__class__, x), SlugField)
                                                or isinstance(getattr(model.__class__, x), SlugField))
            and getattr(model.__class__, x).primary_key
        ]

        for key in dir(model):
            if (hasattr(model.__class__, key) and hasattr(getattr(model.__class__, key), 'field')
                    and getattr(model.__class__, key).field.primary_key):
                return key

        return 'pk'
