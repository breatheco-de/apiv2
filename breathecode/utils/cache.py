from __future__ import annotations
import brotli
import sys
import functools
import os
from typing import Optional
import urllib.parse, json
from django.core.cache import cache
from datetime import datetime, timedelta
from django.db import models
from circuitbreaker import circuit

from django.db.models.fields.related_descriptors import (ReverseManyToOneDescriptor, ManyToManyDescriptor,
                                                         ForwardManyToOneDescriptor,
                                                         ReverseOneToOneDescriptor, ForwardOneToOneDescriptor)

__all__ = ['Cache', 'CACHE_DESCRIPTORS', 'CACHE_DEPENDENCIES']
CACHE_DESCRIPTORS: dict[models.Model, Cache] = {}
CACHE_DEPENDENCIES: set[models.Model] = set()

ENABLE_LIST_OPTIONS = ['true', '1', 'yes', 'y']
IS_DJANGO_REDIS = hasattr(cache, 'delete_pattern')


@functools.lru_cache(maxsize=1)
def is_compression_enabled():
    return os.getenv('COMPRESSION', '1').lower() in ENABLE_LIST_OPTIONS


@functools.lru_cache(maxsize=1)
def min_compression_size():
    return int(os.getenv('MIN_COMPRESSION_SIZE', '10'))


def must_compress(data):
    size = min_compression_size()
    if size == 0:
        return True

    return sys.getsizeof(data) / 1024 > size


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
        return obj.isoformat().replace('+00:00', 'Z')

    if isinstance(obj, timedelta):
        return str(obj.total_seconds())

    raise TypeError('Type not serializable')


class Cache(metaclass=CacheMeta):
    _version_prefix: str = ''
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
        return f'{cls._version_prefix}{key}__{qs}'

    @classmethod
    @circuit
    def clear(cls, deep=0, max_deep=None) -> set | None:
        if max_deep is None:
            max_deep = cls.max_deep

        resolved = set()
        resolved.add(cls)

        if deep >= max_deep:
            return set()

        for x in cls.one_to_one | cls.many_to_one | cls.many_to_many:
            # lazy load the dependency to can clean it
            if x not in CACHE_DESCRIPTORS and x in CACHE_DEPENDENCIES:

                class DepCache(Cache):
                    model = x
                    is_dependency = True

            if x in CACHE_DESCRIPTORS:
                resolved |= CACHE_DESCRIPTORS[x].clear(deep + 1, max_deep)

        if deep != 0:
            return resolved

        keys = {f'{cls._version_prefix}{descriptor.model.__name__}__keys' for descriptor in resolved}
        sets = [x or set() for x in cache.get_many(keys).values()]

        to_delete = set()
        for key in sets:
            if not key:
                continue

            to_delete |= key

        to_delete |= keys

        cache.delete_many(to_delete)

    @classmethod
    @circuit
    def keys(cls):
        return cache.get(f'{cls._version_prefix}{cls.model.__name__}__keys') or set()

    @classmethod
    @circuit
    def get(cls, data) -> dict:
        key = cls._generate_key(**data)
        data = cache.get(key)

        if data is None:
            return None

        spaces = 0
        starts = 0
        mime = 'application/json'
        headers = {}

        # parse a fixed amount of bytes to get the mime type
        try:
            head = data[:30].decode('utf-8')

        # if the data cannot be decoded as utf-8, it means that a section was compressed
        except Exception as e:
            try:
                head = data[:e.start].decode('utf-8')

            # if the data cannot be decoded as utf-8, it means that it does not have a header
            except Exception:
                head = ''

            headers['Content-Encoding'] = 'br'

        for s in head:
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
            if len(unpack) == 2:
                headers['Content-Encoding'] = unpack[1]

        return data[starts:], mime, headers

    @classmethod
    @circuit
    def set(cls,
            data: str | dict | list[dict],
            format: str = 'application/json',
            timeout: int = -1,
            params: Optional[dict] = None) -> str:
        """Set a key value pair on the cache in bytes, it reminds the format and compress the data if needed."""

        if params is None:
            params = {}

        key = cls._generate_key(**params)
        res = {
            'headers': {
                'Content-Type': format,
            },
        }

        # serialize the data to avoid serialization on get requests
        if format == 'application/json':
            data = json.dumps(data, default=serializer).encode('utf-8')

            # in kilobytes
            if must_compress(data) and is_compression_enabled():
                data = brotli.compress(data)
                res['data'] = data
                res['headers']['Content-Encoding'] = 'br'

                data = b'application/json:br    ' + data

            else:
                res['data'] = data

                data = b'application/json    ' + data

        elif format == 'text/html':
            data = data.encode('utf-8')

            # in kilobytes
            if must_compress(data) and is_compression_enabled():
                data = brotli.compress(data)
                res['data'] = data
                res['headers']['Content-Encoding'] = 'br'

                data = b'text/html:br    ' + data

            else:
                res['data'] = data

                data = b'text/html    ' + data

        elif format == 'text/plain':
            data = data.encode('utf-8')

            # in kilobytes
            if must_compress(data) and is_compression_enabled():
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

        keys = cache.get(f'{cls._version_prefix}{cls.model.__name__}__keys') or set()
        keys.add(key)

        cache.set(f'{cls._version_prefix}{cls.model.__name__}__keys', keys)
        return res
