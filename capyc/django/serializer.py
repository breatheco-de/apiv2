import base64
from collections.abc import Iterable, Mapping
from copy import copy
from datetime import datetime, timedelta
from typing import Any, Optional, overload

from adrf.requests import AsyncRequest
from asgiref.sync import sync_to_async
from django.db import models
from django.db.models import QuerySet
from django.db.models.fields import BinaryField, CommaSeparatedIntegerField, DateTimeField, DurationField, TimeField
from django.db.models.fields.related_descriptors import (
    ForeignKeyDeferredAttribute,
    ForwardManyToOneDescriptor,
    ForwardOneToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.query_utils import DeferredAttribute
from django.http import HttpRequest


def binary_serializer(field: bytes) -> str:
    return base64.b64encode(field).decode("utf-8")


def comma_separated_integer_serializer(field: str) -> list[int]:
    return [int(x) for x in field.split(",") if x]


def time_serializer(field: datetime) -> str:
    return field.isoformat().replace("+00:00", "Z")


def duration_serializer(field: timedelta) -> str:
    total_seconds = int(field.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


CUSTOM_SERIALIZERS = {
    BinaryField: binary_serializer,
    CommaSeparatedIntegerField: comma_separated_integer_serializer,
    DateTimeField: time_serializer,
    TimeField: time_serializer,
    DurationField: duration_serializer,
}


class FieldRelatedDescriptor:
    path: str
    field_name: str
    field_alias: str
    nullable: bool
    related_model: models.Model

    def __init__(self, path: str, field_name: str, field_alias: str, nullable: bool, related_model: models.Model):
        self.path = path
        self.field_name = field_name
        self.field_alias = field_alias
        self.nullable = nullable
        self.related_model = related_model

    def __repr__(self) -> str:
        return (
            f'<Descriptor path="{self.path}", field_name="{self.field_name}", '
            f'field_alias="{self.field_alias}", nullable={self.nullable}, related_model={self.related_model}>'
        )


class Choice:
    display_name: Any
    value: Any

    def __init__(self, display_name: Any, value: Any):
        self.display_name = display_name
        self.value = value


class FieldDescriptor:
    primary_key: bool
    max_length: int
    field_name: str
    is_relation: int
    editable: bool
    help_text: str
    # auto_created: bool
    # field_alias: str
    null: bool
    blank: bool
    choices: Optional[list[Choice]]
    # related_model: models.Model
    serializer: Optional[callable]

    def __init__(
        self,
        primary_key: bool,
        max_length: int,
        field_name,
        is_relation: int,
        editable: bool,
        help_text: str,
        null: bool,
        blank: bool,
        choices: list[Choice],
        # related_model: models.Model,
        serializer: Optional[callable] = None,
    ):
        self.primary_key = primary_key
        self.max_length = max_length
        self.field_name = field_name
        self.is_relation = is_relation
        self.editable = editable
        self.help_text = help_text
        # self.auto_created = auto_created
        # self.field_alias = field_alias
        self.null = null
        self.blank = blank
        self.choices = choices
        # self.related_model = related_model
        self.serializer = serializer

    def __repr__(self) -> str:
        return (
            f"<FieldDescriptor primary_key={self.primary_key}, max_length={self.max_length}, "
            f'field_name="{self.field_name}", is_relation={self.is_relation}, editable={self.editable}, '
            f'help_text="{self.help_text}", null={self.null}, blank={self.blank}, choices={self.choices}>'
        )


class ModelCached:
    reverse_one_to_one_list: list[FieldRelatedDescriptor] = []
    reverse_many_to_one_list: list[FieldRelatedDescriptor] = []
    forward_one_to_one_list: list[FieldRelatedDescriptor] = []
    forward_many_to_one_list: list[FieldRelatedDescriptor] = []
    many_to_many_list: list[FieldRelatedDescriptor] = []
    id_list: list[FieldDescriptor] = []
    field_list: list[FieldDescriptor] = []


CACHE: dict[str, ModelCached] = {}


@overload
def get_cache(key: str) -> ModelCached:
    pass


@overload
def get_cache() -> dict[str, ModelCached]:
    pass


def get_cache(key: Optional[str] = None) -> dict[str, ModelCached] | ModelCached:
    cache: dict[str, ModelCached] = {}

    if key is None:
        return copy(CACHE[key])

    for key in CACHE:
        cache[key] = copy(CACHE[key])

    return cache


class ModelFieldMixin:
    depth = 1

    @classmethod
    def _get_related_fields(cls, key: str):
        model = cls.model
        cache = CACHE.get(key)
        if cache is None:
            cache = ModelCached()
            CACHE[key] = cache

        cls.cache = CACHE[key]

        def get_related_attrs(field, name):
            if hasattr(field, "field"):
                field = field.field

            else:
                field = field.related

            obj = FieldRelatedDescriptor(
                path=field.related_model._meta.app_label + "." + field.related_model.__name__,
                field_name=name,
                field_alias=field.name,
                nullable=field.null,
                related_model=field.related_model,
            )

            return obj

        def get_attrs(field, name):
            field = field.field
            if x := getattr(field, "_choices", None):
                choices = [Choice(display_name=display_name, value=value) for display_name, value in x]
            else:
                choices = None

            serializer = CUSTOM_SERIALIZERS.get(type(field), None)

            obj = FieldDescriptor(
                primary_key=field.primary_key,
                max_length=field.max_length,
                field_name=name,
                is_relation=field.is_relation,
                editable=field.editable,
                help_text=field.help_text,
                null=field.null,
                blank=field.blank,
                choices=choices,
                serializer=serializer,
            )

            return obj

        for x in vars(model):
            if type(getattr(model, x)) is ForwardOneToOneDescriptor:
                cache.forward_one_to_one_list.append(get_related_attrs(getattr(model, x), x))

            elif type(getattr(model, x)) is ForwardManyToOneDescriptor:
                cache.forward_many_to_one_list.append(get_related_attrs(getattr(model, x), x))

            elif type(getattr(model, x)) is ManyToManyDescriptor:
                cache.many_to_many_list.append(get_related_attrs(getattr(model, x), x))

            elif type(getattr(model, x)) is ReverseManyToOneDescriptor:
                cache.reverse_many_to_one_list.append(get_related_attrs(getattr(model, x), x))

            elif type(getattr(model, x)) is ReverseOneToOneDescriptor:
                cache.reverse_one_to_one_list.append(get_related_attrs(getattr(model, x), x))

            elif type(getattr(model, x)) is ForeignKeyDeferredAttribute:
                cache.id_list.append(get_attrs(getattr(model, x), x))

            elif type(getattr(model, x)) is DeferredAttribute:
                cache.field_list.append(get_attrs(getattr(model, x), x))

    @classmethod
    def _get_field_names(cls, l: list[FieldDescriptor | FieldRelatedDescriptor]) -> list[str]:
        return [x.field_name for x in l]

    @classmethod
    def _get_field_serializers(cls, l: list[FieldDescriptor]) -> dict[str, callable]:
        return dict([(x.field_name, x.serializer) for x in l if x.serializer is not None])

    @classmethod
    def _check_settings(cls):
        assert cls.depth > 0, "Depth must be greater than 0"
        assert (len(cls.fields) > 0 and len(cls.exclude) == 0) or (
            len(cls.fields) == 0 and len(cls.exclude) > 0
        ), "Fields and exclude must be mutually exclusive"
        assert all(isinstance(x, str) for x in cls.fields), "Fields must be an array of strings"
        assert all(isinstance(x, str) for x in cls.exclude), "Exclude must be an array of strings"

        field_list = cls._get_field_names(cls.cache.field_list)
        id_list = cls._get_field_names(cls.cache.id_list)

        for field in cls.fields:
            if field in field_list or field in id_list:
                continue

            assert 0, f"Field '{field}' not found in model '{cls.model.__name__}'"

        cls._serializers = {
            **cls._get_field_serializers(cls.cache.id_list),
            **cls._get_field_serializers(cls.cache.field_list),
        }

    @classmethod
    def _prepare_fields(cls, key: str):
        cls._get_related_fields(key)
        cls._check_settings()


class Serializer(ModelFieldMixin):
    model: Optional[models.Model] = None
    fields = ()
    exclude = ()

    def _serialize(self, instance: models.Model) -> dict:
        data = {}
        self.fields

        for field in self.fields:
            data[field] = getattr(instance, field, None)

            serializer = self._serializers.get(field, None)
            if serializer:
                data[field] = serializer(data[field])

        return data

    @property
    def data(self) -> dict | list:
        if isinstance(self._data, QuerySet):
            self._data.only(*self.fields)

        if issubclass(type(self._data), models.Model) or isinstance(self._data, Mapping):
            return self._serialize(self._data)

        return [self._serialize(x) for x in self._data]

    @property
    @sync_to_async
    def adata(self) -> dict | list:
        return self.data

    def __init_subclass__(cls):
        key = cls.__module__ + "." + cls.__name__
        cls._prepare_fields(key)
        super().__init_subclass__()

    def __init__(
        self,
        instance: Optional[QuerySet | models.Model] = None,
        many: bool = False,
        data: Optional[Iterable | Mapping | QuerySet | models.Model] = None,
        context: Optional[Mapping] = None,
        required: bool = True,
        request: Optional[HttpRequest | AsyncRequest] = None,
        **kwargs,
    ):
        self.instance = instance
        self.many = many
        self._data = data
        self.context = context or {}
        self.required = required
        self.request = request

        super().__init__(**kwargs)
