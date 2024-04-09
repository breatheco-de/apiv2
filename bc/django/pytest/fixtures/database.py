from __future__ import annotations

import functools
import random
import re
from typing import Any, Generator, Type, final

import pytest
from asgiref.sync import sync_to_async
from django.apps import apps
from django.conf import settings
from django.db import models
from django.db.models import Model

# from django.db.models.query_utils import DeferredAttribute
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ForwardOneToOneDescriptor,
    ManyToManyDescriptor,
)
from django.db.models.query_utils import DeferredAttribute
from faker import Faker

from breathecode.tests.mixins.generate_models_mixin.utils import argument_parser
from breathecode.utils.attr_dict import AttrDict

__all__ = ['database', 'Database']

_fake = Faker()


def _remove_dinamics_fields(dict, fields=['_state', 'created_at', 'updated_at', '_password']):
    """Remove dinamics fields from django models as dict"""
    if not dict:
        return None

    result = dict.copy()
    for field in fields:
        if field in result:
            del result[field]

    # remove any field starting with __ (double underscore) because it is considered private
    without_private_keys = result.copy()
    for key in result:
        if '__' in key or key.startswith('_'):
            del without_private_keys[key]

    return without_private_keys


@final
class Database:
    _cache = {}

    @classmethod
    def get_model(cls, path: str) -> Model:
        """
        Return the model matching the given app_label and model_name.

        As a shortcut, app_label may be in the form <app_label>.<model_name>.

        model_name is case-insensitive.

        Raise LookupError if no application exists with this label, or no
        model exists with this name in the application. Raise ValueError if
        called with a single argument that doesn't contain exactly one dot.

        Usage:

        ```py
        # class breathecode.admissions.models.Cohort
        Cohort = self.bc.database.get_model('admissions.Cohort')
        ```

        Keywords arguments:
        - path(`str`): path to a model, for example `admissions.CohortUser`.
        """

        if path in cls._cache:
            return cls._cache[path]

        app_label, model_name = path.split('.')
        cls._cache[path] = apps.get_model(app_label, model_name)

        return cls._cache[path]

    @classmethod
    def list_of(cls, path: str, dict: bool = True) -> list[Model | dict[str, Any]]:
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

        model = Database.get_model(path)
        result = model.objects.filter()

        if dict:
            result = [_remove_dinamics_fields(data.__dict__) for data in result]

        return result

    @classmethod
    @sync_to_async
    def alist_of(cls, path: str, dict: bool = True) -> list[Model | dict[str, Any]]:
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

        return cls.list_of(path, dict)

    @classmethod
    def _get_random_attrs(cls, model):
        props = {}

        model_fields = [(
            x,
            type(getattr(model, x).field),
            {
                'choices': getattr(getattr(model, x).field, 'choices', None),
                'default': getattr(getattr(model, x).field, 'default', models.NOT_PROVIDED),
                'null': getattr(getattr(model, x).field, 'null', False),
                'blank': getattr(getattr(model, x).field, 'blank', False),
            },
        ) for x in vars(model) if type(getattr(model, x)) is DeferredAttribute]

        for field_name, field_type, field_attrs in model_fields:

            if field_attrs['default'] is not models.NOT_PROVIDED:
                if callable(field_attrs['default']):
                    props[field_name] = field_attrs['default']()

                else:

                    props[field_name] = field_attrs['default']

            elif field_attrs['blank'] is True and field_attrs['null'] is True:
                props[field_name] = None

            elif field_attrs['choices'] is not None:
                props[field_name] = random.choice(field_attrs['choices'])[0]

            elif field_type is models.EmailField:
                props[field_name] = _fake.email()

            elif field_type is models.CharField:
                props[field_name] = _fake.name()

            elif field_type is models.TextField:
                props[field_name] = _fake.text()

            elif field_type is models.BooleanField:
                props[field_name] = _fake.boolean()

            elif field_type is models.UUIDField:
                props[field_name] = _fake.uuid4()

            elif field_type is models.SlugField:
                props[field_name] = _fake.slug()

            elif field_type is models.URLField:
                props[field_name] = _fake.url()

            elif field_type is models.DateField:
                props[field_name] = _fake.date()

            elif field_type is models.TimeField:
                props[field_name] = _fake.time()

            elif field_type is models.DurationField:
                props[field_name] = _fake.date_time() - _fake.date_time()

            elif field_type is models.DecimalField:
                props[field_name] = _fake.random_number()

            elif field_type in [models.PositiveSmallIntegerField, models.SmallIntegerField]:
                props[field_name] = _fake.random_digit()

                if field_type is models.PositiveSmallIntegerField and props[field_name] < 0:
                    props[field_name] *= -1

            elif field_type in [models.IntegerField, models.PositiveIntegerField]:
                props[field_name] = _fake.random_int()

                if field_type is models.PositiveIntegerField and props[field_name] < 0:
                    props[field_name] *= -1

            elif field_type in [models.BigIntegerField, models.PositiveBigIntegerField]:
                props[field_name] = _fake.random_number()

                if field_type is models.PositiveBigIntegerField and props[field_name] < 0:
                    props[field_name] *= -1

            elif field_type in [models.FloatField, models.DecimalField]:
                props[field_name] = _fake.random_number() / 1000

            elif field_type is models.DateTimeField:
                from datetime import timezone

                props[field_name] = _fake.date_time().replace(tzinfo=timezone.utc)

            elif field_type is models.FileField:
                props[field_name] = _fake.file_name()

            elif field_type is models.ImageField:
                props[field_name] = _fake.image_url()

            elif field_type is models.JSONField:
                import json

                props[field_name] = _fake.pydict()
                is_dict = _fake.boolean()
                while True:
                    try:
                        if is_dict:
                            props[field_name] = _fake.pydict()

                        else:
                            props[field_name] = _fake.pylist()

                        json.dumps(props[field_name])
                        break

                    except Exception:
                        continue

            elif field_type is models.BinaryField:
                props[field_name] = _fake.binary(length=12)

            elif field_type in [models.IPAddressField, models.GenericIPAddressField]:
                props[field_name] = _fake.ipv4()

            elif field_type is models.FilePathField:
                props[field_name] = _fake.file_path()

        return props

    @classmethod
    def _get_related_fields(cls, model):

        def get_attrs(field):
            cls_type = type(field)
            field = field.field
            obj = {
                'cls': cls_type,
                'path': field.related_model._meta.app_label + '.' + field.related_model.__name__,
                'name': field.name,
                'blank': field.blank,
                'null': field.null,
                'default': field.default,
                'choices': field.choices,
                'related_model': field.related_model,
            }

            return obj

        for x in vars(model):
            if type(getattr(model, x)) in [
                    ForwardOneToOneDescriptor,
                    ForwardManyToOneDescriptor,
                    ManyToManyDescriptor,
            ]:
                yield (
                    x,
                    type(getattr(model, x)),
                    get_attrs(getattr(model, x)),
                )

    @classmethod
    def _build_descriptors(cls):
        app_map = {}
        model_map = {}
        model_alias_map = {}
        name_map = {}
        ban_list = set()

        for app in settings.INSTALLED_APPS:
            app_label = app.split('.')[-1]
            all_models = apps.get_app_config(app_label).get_models()
            app_cache = {}

            for model in all_models:
                model_name = model.__name__
                model_descriptor = {
                    'cls': model,
                    'path': app_label + '.' + model_name,
                    'related_fields': [*cls._get_related_fields(model)],
                    'get_values': functools.partial(cls._get_random_attrs, model),
                }
                app_cache[model_name] = model_descriptor
                name_map[app_label + '__' + cls.to_snake_case(model_name)] = (app_label, model_name)

                if model_name in ban_list:
                    continue

                snake_model_name = cls.to_snake_case(model_name)
                if model_name in model_map:
                    ban_list.add(model_name)
                    del model_map[model_name]
                    del name_map[snake_model_name]
                    del model_alias_map[snake_model_name]
                    continue

                model_map[model_name] = model_descriptor
                name_map[snake_model_name] = model_name
                model_alias_map[snake_model_name] = app_label + '.' + model_name

            app_map[app_label] = app_cache

        return app_map, model_map, name_map, model_alias_map

    @classmethod
    def to_snake_case(cls, class_name):
        snake_case = re.sub('([a-z0-9])([A-Z])', r'\1_\2', class_name).lower()
        return snake_case

    @classmethod
    def create(cls, **models):
        res = {}
        app_map, model_map, name_map, model_alias_map = cls._build_descriptors()

        pending = {}

        # get descriptors
        for model_alias, value in models.items():
            try:
                path = name_map[model_alias]

            except KeyError:
                if '__' in model_alias:
                    app_label, model_name = model_alias.split('__')
                    raise ValueError(f'Model {model_name} not found in {app_label}')

                raise ValueError(f'Model {model_alias} not found or two models have the same name, '
                                 'use the app_label.model_name format')

            if isinstance(path, tuple):
                app_label, model_name = path
                model_descriptor = app_map[app_label][model_name]

            else:
                model_descriptor = model_map[path]

            pending[model_alias] = model_descriptor

        cache = {}
        exec_order = []

        # fill cache
        for model_alias, model_descriptor in pending.items():
            x = model_descriptor['path']

            cache[x] = (model_descriptor, models.get(model_alias))
            exec_order.append(x)

        # get dependencies
        processed = set()
        while True:
            cache_to_add = {}
            exec_order_to_add = []
            for key in exec_order:
                item = cache.get(key, None)
                if item is None:
                    app_label, model_name = key.split('.')
                    x = app_map[app_label][model_name]
                    item = (x, 1)
                    cache[key] = item

                model_descriptor, value = item

                if model_descriptor['path'] in cache_to_add:
                    continue

                if model_descriptor['path'] in processed:
                    continue

                processed.add(model_descriptor['path'])

                for related_field, field_type, field_attrs in model_descriptor['related_fields']:

                    if field_attrs['path'] in processed:
                        continue

                    if (field_attrs['path'] not in exec_order and field_attrs['path'] not in cache_to_add
                            and (field_attrs['null'] is False or field_attrs['cls'] is ForwardOneToOneDescriptor)):
                        app_label, model_name = field_attrs['path'].split('.')
                        cache_to_add[field_attrs['path']] = (app_map[app_label][model_name], 1)

                        # disable m2m temporally
                        if field_attrs['cls'] is not ManyToManyDescriptor:
                            exec_order_to_add.append(field_attrs['path'])

            exec_order += exec_order_to_add
            cache.update(cache_to_add)

            if len(cache_to_add) == 0:
                break

        # sort dependencies
        for model_path, (model_descriptor, value) in cache.items():

            for related_field, field_type, field_attrs in model_descriptor['related_fields']:
                dep_path = field_attrs['path']
                to_reevaluate = []

                # dep not found, maybe it is a m2m, that was temporally disabled
                print(exec_order)
                try:
                    dep_index = exec_order.index(dep_path)
                except ValueError:
                    continue

                # check this
                try:
                    model_index = exec_order.index(model_path)
                except ValueError:
                    continue

                if dep_index > model_index:
                    exec_order.pop(dep_index)
                    exec_order.insert(model_index, dep_path)
                    to_reevaluate.append(dep_path)

                while len(to_reevaluate) > 0:
                    to_re_reevaluate = []

                    for x in to_reevaluate:
                        for related_field, field_type, field_attrs in cache[x][0]['related_fields']:

                            dep_path = field_attrs['path']

                            # dep not found, maybe it is a m2m, that was temporally disabled
                            try:
                                dep_index = exec_order.index(dep_path)

                            except ValueError:
                                continue

                            model_index = exec_order.index(x)

                            if dep_index > model_index:
                                exec_order.pop(dep_index)
                                exec_order.insert(model_index, dep_path)

                                # disable m2m temporally
                                if field_attrs['cls'] is not ManyToManyDescriptor:
                                    to_re_reevaluate.append(dep_path)

                    to_reevaluate = to_re_reevaluate

        generated = {}

        # build instances
        for model_path in exec_order:
            model_descriptor, value = cache[model_path]

            how_many, arguments = argument_parser(value)[0]

            for related_field, field_type, field_attrs in model_descriptor['related_fields']:
                if field_attrs['path'] in generated:

                    # no implemented yet
                    if field_type is ManyToManyDescriptor:
                        continue
                        # arguments[field_attrs["name"]] = [generated[field_attrs["path"]]]

                    # else:

                    arguments[field_attrs['name']] = generated[field_attrs['path']]

            result = [
                model_descriptor['cls'].objects.create(**{
                    **model_descriptor['get_values'](),
                    **arguments
                }) for _ in range(how_many)
            ]

            if len(result) == 1:
                result = result[0]

            app_label, model_name = model_descriptor['path'].split('.')
            model_alias = cls.to_snake_case(model_name)

            if model_alias not in name_map:
                model_alias = app_label + '__' + model_alias

            res[model_alias] = result
            generated[model_descriptor['path']] = result

        return AttrDict(**res)


@pytest.fixture
def database(db) -> Generator[Database, None, None]:
    yield Database()
