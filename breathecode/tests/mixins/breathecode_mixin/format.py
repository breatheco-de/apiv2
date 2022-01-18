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
