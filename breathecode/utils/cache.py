from __future__ import annotations
from typing import Optional
import urllib.parse, json
from django.core.cache import cache
from datetime import datetime, timedelta
from django.db import models
import brotli
import sys

from django.db.models.fields.related_descriptors import (ReverseManyToOneDescriptor, ManyToManyDescriptor,
                                                         ForwardManyToOneDescriptor,
                                                         ReverseOneToOneDescriptor, ForwardOneToOneDescriptor)

__all__ = ['Cache', 'CACHE_DESCRIPTORS', 'CACHE_DEPENDENCIES']
CACHE_DESCRIPTORS: dict[models.Model, Cache] = {}
CACHE_DEPENDENCIES: set[models.Model] = set()


class CacheMeta(type):

    def __init__(cls: Cache, name, bases, clsdict):
        global CACHE_DEPENDENCIES

        super().__init__(name, bases, clsdict)

        if hasattr(cls, 'model'):
            # key = cls.model.__module__ + '.' + cls.model.__name__

            CACHE_DESCRIPTORS[cls.model] = cls
            model = cls.model

            one_to_one = {
                getattr(model, x).field.model
                for x in dir(model) if isinstance(getattr(model, x), ForwardOneToOneDescriptor)
            }

            reverse_one_to_one = {
                getattr(model, x).related.related_model
                for x in dir(model) if isinstance(getattr(model, x), ReverseOneToOneDescriptor)
            }

            many_to_one = {
                getattr(model, x).field.related_model
                for x in dir(model) if isinstance(getattr(model, x), ForwardManyToOneDescriptor)
            }

            reverse_many_to_one = {
                getattr(model, x).field.model
                for x in dir(model) if isinstance(getattr(model, x), ReverseManyToOneDescriptor)
            }

            many_to_many = {
                getattr(model, x).field.model
                for x in dir(model) if isinstance(getattr(model, x), ManyToManyDescriptor)
            }

            cls.one_to_one = one_to_one | reverse_one_to_one
            cls.many_to_one = many_to_one | reverse_many_to_one
            cls.many_to_many = many_to_many

            # CACHE_DEPENDENCIES = (CACHE_DEPENDENCIES | one_to_one | reverse_one_to_one | many_to_one |
            #                       reverse_many_to_one | many_to_many)

            if not cls.is_dependency:
                CACHE_DEPENDENCIES.update(cls.one_to_one | cls.many_to_one | cls.many_to_many)


def serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()

    if isinstance(obj, timedelta):
        return str(obj.total_seconds())

    raise TypeError('Type not serializable')


class Cache(metaclass=CacheMeta):
    version_prefix: str = ''
    model: models.Model

    one_to_one: list[models.Model]
    many_to_one: list[models.Model]
    many_to_many: list[models.Model]

    max_deep: int = 2
    is_dependency: bool = False

    @classmethod
    def _generate_key(cls, **kwargs):
        key = cls.model.__name__

        sorted_kwargs = sorted(kwargs.items())

        qs = urllib.parse.urlencode(sorted_kwargs)
        return f'{cls.version_prefix}{key}__{qs}'

    @classmethod
    def clear(cls, cleaned: Optional[set] = None, deep=0):
        if cleaned is None:
            cleaned = set()

        model_name = cls.model.__name__
        cleaned.add(cls.model)

        cache.delete_pattern(f'{cls.version_prefix}{model_name}*')

        if deep >= cls.max_deep:
            return

        for x in cls.one_to_one | cls.many_to_one | cls.many_to_many:
            if x.__name__ not in cleaned and x in CACHE_DESCRIPTORS:
                CACHE_DESCRIPTORS[x].clear(cleaned, deep + 1)

    @classmethod
    def keys(cls):
        key = cls.model.__name__
        return cache.keys(f'{cls.version_prefix}{key}__*')

    @classmethod
    def get(cls, data) -> dict:
        key = cls._generate_key(**data)
        data = cache.get(key)

        if data is None:
            return None

        spaces = 0
        starts = 0
        mime = 'application/json'
        headers = {}

        for s in data[:30].decode('utf-8'):
            if s in ['{', '[']:
                break

            if s == ' ':
                spaces += 1
            else:
                spaces = 0

            starts += 1

            if spaces == 4:
                mime = data[:starts - 4]
                break

        if isinstance(mime, bytes):
            unpack = mime.decode('utf-8').split(':')
            mime = unpack[0]
            if unpack == 2:
                headers['Content-Encoding'] = unpack[1]

        return data[starts:], mime, headers

    @classmethod
    def set(cls, data: str | dict | list[dict], format='application/json', timeout=-1, **kwargs) -> str:
        key = cls._generate_key(**kwargs)
        res = {
            'headers': {
                'Content-Type': format,
            },
        }

        # serialize the data to avoid serialization on get requests
        if format == 'application/json':
            data = json.dumps(data, default=serializer).encode('utf-8')

            # 10KB
            if sys.getsizeof(data) / 1024 > 10:
                data = brotli.compress(data)
                res['data'] = data
                res['headers']['Content-Encoding'] = 'br'

                data = b'application/json:br    ' + data

            else:
                res['data'] = data

                data = b'application/json    ' + data

        elif format == 'text/html':
            data = data.encode('utf-8')

            # 10KB
            if sys.getsizeof(data) / 1024 > 10:
                data = brotli.compress(data)
                res['data'] = data
                res['headers']['Content-Encoding'] = 'br'

                data = b'text/html:br    ' + data

            else:
                res['data'] = data

                data = b'text/html    ' + data

        elif format == 'text/plain':
            data = data.encode('utf-8')

            # 10KB
            if sys.getsizeof(data) / 1024 > 10:
                data = brotli.compress(data)
                res['data'] = data
                res['headers']['Content-Encoding'] = 'br'

                data = b'text/plain:br    ' + data

            else:
                res['data'] = data

                data = b'text/plain    ' + data

        # encode the response to avoid serialization on get requests
        if timeout == -1:
            cache.set(key, data)

        # encode the response to avoid serialization on get requests
        else:
            cache.set(key, data, timeout)

        return res
