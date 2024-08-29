from typing import Generator, final

import pytest
from faker import Faker

__all__ = ["Format", "format"]


def _remove_dinamics_fields(dict, fields=None):
    """Remove dinamics fields from django models as dict"""
    if fields is None:
        fields = ["_state", "created_at", "updated_at", "_password"]

    if not dict:
        return None

    result = dict.copy()
    for field in fields:
        if field in result:
            del result[field]

    # remove any field starting with __ (double underscore) because it is considered private
    without_private_keys = result.copy()
    for key in result:
        if "__" in key or key.startswith("_"):
            del without_private_keys[key]

    return without_private_keys


@final
class Format:
    """
    Random utils.
    """

    def __init__(self, fake: Faker) -> None:
        self._fake = fake

    def _single_obj_repr(self, object: object) -> str:
        try:
            from django.db import models

            if isinstance(object, models.Model):
                return _remove_dinamics_fields(object.__dict__)

        except ImportError:
            pass

        raise NotImplementedError(f"Not implemented for {type(object)}")

    def to_obj_repr(self, object: object) -> str:
        """
        Format an object as dict, and an array of dicts if the object is a list.
        """

        if isinstance(object, list):
            return [self._single_obj_repr(o) for o in object]

        return self._single_obj_repr(object)


@pytest.fixture()
def format(fake) -> Generator[Format, None, None]:
    """Image fixtures."""

    x = Format(fake)

    yield x
