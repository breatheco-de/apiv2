from __future__ import annotations
import base64
from datetime import timedelta
import random
from faker import Faker
import yaml
import urllib.parse
from typing import Any, Callable
from rest_framework.test import APITestCase
from django.db.models import Model
from django.db.models.query import QuerySet

from . import interfaces

from ..models_mixin import ModelsMixin
import urllib.parse
from django.db.models import Q

from django.utils import timezone

__all__ = ["Format"]

ENCODE = "utf-8"

fake = Faker()


class Field:

    @staticmethod
    def id(mode: str) -> Q:
        return f"{random.randint(0, 100000000000000000)}"

    @staticmethod
    def integer(mode: str) -> Callable[[str, str, str], Q]:
        if mode == "in":
            v = ""
            now_many = random.randint(2, 4)
            for _ in range(now_many):
                v += f"{random.randint(0, 100000000000000000)},"
            return v[:-1]

        if mode == "isnull":
            return "true" if bool(random.randbytes(1)) else "false"

        return f"{random.randint(0, 100000000000000000)}"

    @staticmethod
    def slug(mode: str) -> Q:
        is_int = bool(random.randbytes(1))
        if is_int:
            return f"{random.randint(0, 100000000000000000)}"

        return fake.slug()

    @staticmethod
    def string(mode: str) -> Callable[[str, str, str], Q]:
        if mode == "in":
            v = ""
            now_many = random.randint(2, 4)
            for _ in range(now_many):
                v += f"'{fake.slug()}',"
            return v[:-1]

        if mode == "isnull":
            return "true" if bool(random.randbytes(1)) else "false"

        return fake.slug()

    @staticmethod
    def datetime(mode: str) -> Callable[[str, str, str], Q]:

        def value():
            delta = random.randint(0, 10000000)
            sign = bool(random.randbytes(1))
            date = timezone.now()

            if sign:
                date += timedelta(seconds=delta)

            else:
                date -= timedelta(seconds=delta)

            return date.isoformat()

        if mode == "in":
            v = ""
            now_many = random.randint(2, 4)
            for _ in range(now_many):
                v += value() + ","
            return v[:-1]

        return value()

    @staticmethod
    def bool(mode: str) -> Callable[[str, str, str], Q]:
        return "true" if bool(random.randbytes(1)) else "false"


class Format:
    """Mixin with the purpose of cover all the related with format or parse something"""

    _parent: APITestCase
    _bc: interfaces.BreathecodeInterface
    ENCODE = ENCODE

    def __init__(self, parent, bc: interfaces.BreathecodeInterface) -> None:
        self._parent = parent
        self._bc = bc

    def call(self, *args: Any, **kwargs: Any) -> str:
        """
        Wraps a call into it and return its args and kwargs.

        example:

        ```py
        args, kwargs = self.bc.format.call(2, 3, 4, a=1, b=2, c=3)

        assert args == (2, 3, 4)
        assert kwargs == {'a': 1, 'b': 2, 'c': 3}
        ```
        """

        return args, kwargs

    def querystring(self, query: dict) -> str:
        """
        Build a querystring from a given dict.
        """

        return urllib.parse.urlencode(query)

    def queryset(self, query: dict) -> str:
        """
        Build a QuerySet from a given dict.
        """

        return Q(**query)

    # remove lang from args
    def lookup(self, lang: str, overwrite: dict = dict(), **kwargs: dict | tuple) -> dict[str, Any]:
        """
        Generate from lookups the values in test side to be used in querystring.

        example:

        ```py
        query = self.bc.format.lookup(
            'en',
            strings={
                'exact': [
                    'remote_meeting_url',
                ],
            },
            bools={
                'is_null': ['ended_at'],
            },
            datetimes={
                'gte': ['starting_at'],
                'lte': ['ending_at'],
            },
            slugs=[
                'cohort_time_slot__cohort',
                'cohort_time_slot__cohort__academy',
                'cohort_time_slot__cohort__syllabus_version__syllabus',
            ],
            overwrite={
                'cohort': 'cohort_time_slot__cohort',
                'academy': 'cohort_time_slot__cohort__academy',
                'syllabus': 'cohort_time_slot__cohort__syllabus_version__syllabus',
                'start': 'starting_at',
                'end': 'ending_at',
                'upcoming': 'ended_at',
            },
        )

        url = reverse_lazy('events:me_event_liveclass') + '?' + self.bc.format.querystring(query)

        # this test avoid to pass a invalid param to ORM
        response = self.client.get(url)
        ```
        """

        result = {}

        # foreign
        ids = kwargs.get("ids", tuple())
        slugs = kwargs.get("slugs", tuple())

        # fields
        ints = kwargs.get("ints", dict())
        strings = kwargs.get("strings", dict())
        datetimes = kwargs.get("datetimes", dict())
        bools = kwargs.get("bools", dict())

        # opts
        custom_fields = kwargs.get("custom_fields", dict())

        # serialize foreign
        ids = tuple(ids)
        slugs = tuple(slugs)

        overwrite = dict([(v, k) for k, v in overwrite.items()])

        # foreign

        for field in ids:
            if field == "":
                result["id"] = field.integer("exact")
                continue

            name = overwrite.get(field, field)
            result[name] = Field.id("")

        for field in slugs:
            if field == "":
                result["id"] = Field.integer("exact")
                result["slug"] = Field.string("exact")
                continue

            name = overwrite.get(field, field)
            result[name] = Field.slug("")

        # fields

        for mode in ints:
            for field in ints[mode]:
                name = overwrite.get(field, field)
                result[name] = Field.int(mode)

        for mode in strings:
            for field in strings[mode]:
                name = overwrite.get(field, field)
                result[name] = Field.string(mode)

        for mode in datetimes:
            for field in datetimes[mode]:
                name = overwrite.get(field, field)
                result[name] = Field.datetime(mode)

        for mode in bools:
            for field in bools[mode]:
                name = overwrite.get(field, field)
                result[name] = Field.bool(mode)

        # custom fields

        for field in custom_fields:
            name = overwrite.get(field, field)
            result[name] = custom_fields[field]()

        return result

    def table(self, arg: QuerySet) -> dict[str, Any] | list[dict[str, Any]]:
        """
        Convert a QuerySet in a list.

        Usage:

        ```py
        model = self.bc.database.create(user=1, group=1)

        self.bc.format.model(model.user.groups.all())  # = [{...}]
        ```
        """

        return [ModelsMixin.remove_dinamics_fields(self, data.__dict__.copy()) for data in arg]

    def to_dict(self, arg: Any) -> dict[str, Any] | list[dict[str, Any]]:
        """
        Parse the object to a `dict` or `list[dict]`.

        Usage:

        ```py
        # setup the database, model.user is instance of dict and model.cohort
        # is instance list of dicts
        model = self.bc.database.create(user=1, cohort=2)

        # Parsing one model to a dict
        self.bc.format.to_dict(model.user)  # = {...}

        # Parsing many models to a list of dict (infered from the type of
        # argument)
        self.bc.format.to_dict(model.cohort)  # = [{...}, {...}]
        ```
        """

        if isinstance(arg, list) or isinstance(arg, QuerySet):
            return [self._one_to_dict(x) for x in arg]

        return self._one_to_dict(arg)

    def to_decimal_string(self, decimal: int | float) -> str:
        """
        Parse a number to the django representation of a decimal.

        Usage:

        ```py
        self.bc.format.to_decimal(1)  # returns '1.000000000000000'
        ```
        """
        return "%.15f" % round(decimal, 15)

    def _one_to_dict(self, arg) -> dict[str, Any]:
        """Parse the object to a `dict`"""

        if isinstance(arg, Model):
            return ModelsMixin.remove_dinamics_fields(None, vars(arg)).copy()

        if isinstance(arg, dict):
            return arg.copy()

        raise NotImplementedError(f"{arg.__name__} is not implemented yet")

    def describe_models(self, models: dict[str, Model]) -> str:
        """
        Describe the models.

        Usage:

        ```py
        # setup the database
        model = self.bc.database.create(user=1, cohort=1)

        # print the docstring to the corresponding test
        self.bc.format.describe_models(model)
        ```
        """

        title_spaces = " " * 8
        model_spaces = " " * 10
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

        print(title_spaces + "Descriptions of models are being generated:")

        for line in yaml.dump(result).split("\n"):
            if not line.startswith(" "):
                print()

            print(model_spaces + line)

        # This make sure the element are being printed and prevent `describe_models` are pushed to dev branch
        assert False

    # TODO: this method is buggy in the line `if not hasattr(model, key)`
    def _describe_model(self, model: Model):
        pk_name = self._get_pk_name(model)
        attrs = dir(model)
        result = {}

        for key in attrs:
            if key.startswith("_"):
                continue

            if key == "DoesNotExist":
                continue

            if key == "MultipleObjectsReturned":
                continue

            if key.startswith("get_next_"):
                continue

            if key.startswith("get_previous_"):
                continue

            if key.endswith("_set"):
                continue

            if not hasattr(model, key):
                continue

            attr = getattr(model, key)

            if attr.__class__.__name__ == "method":
                continue

            if isinstance(attr, Model):
                result[key] = f"{attr.__class__.__name__}({self._get_pk_name(attr)}={self._repr_pk(attr.pk)})"

            elif attr.__class__.__name__ == "ManyRelatedManager":
                instances = [
                    f"{attr.model.__name__}({self._get_pk_name(x)}={self._repr_pk(x.pk)})" for x in attr.get_queryset()
                ]
                result[key] = instances

        return (f"{model.__class__.__name__}({pk_name}={self._repr_pk(model.pk)})", result)

    def _repr_pk(self, pk: str | int) -> int | str:
        if isinstance(pk, int):
            return pk

        return f'"{pk}"'

    def _get_pk_name(self, model: Model):
        from django.db.models.fields import Field, SlugField

        attrs = [
            x
            for x in dir(model)
            if hasattr(model.__class__, x)
            and (
                isinstance(getattr(model.__class__, x), SlugField) or isinstance(getattr(model.__class__, x), SlugField)
            )
            and getattr(model.__class__, x).primary_key
        ]

        for key in dir(model):
            if (
                hasattr(model.__class__, key)
                and hasattr(getattr(model.__class__, key), "field")
                and getattr(model.__class__, key).field.primary_key
            ):
                return key

        return "pk"

    def from_base64(self, hash: str | bytes) -> str:
        """
        Transform a base64 hash to string.
        """

        if isinstance(hash, str):
            hash = hash.encode()

        return base64.b64decode(hash).decode(ENCODE)

    def to_base64(self, string: str | bytes) -> str:
        """
        Transform a base64 hash to string.
        """

        if isinstance(string, str):
            string = string.encode()

        return base64.b64encode(string).decode(ENCODE)

    def to_querystring(self, params: dict) -> str:
        """
        Transform dict to querystring
        """

        return urllib.parse.urlencode(params)

    def from_bytes(self, s: bytes, encode: str = ENCODE) -> str:
        """
        Transform bytes to a string.
        """

        return s.decode(encode)
