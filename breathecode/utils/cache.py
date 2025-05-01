from __future__ import annotations

import functools
import gzip
import json
import os
import sys
import urllib.parse
import zlib
from datetime import datetime, timedelta
from typing import Optional

import brotli
import zstandard
from circuitbreaker import circuit
from django.core.cache import cache
from django.db import models
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ForwardOneToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)

__all__ = ["Cache", "CACHE_DESCRIPTORS", "CACHE_DEPENDENCIES"]
CACHE_DESCRIPTORS: dict[models.Model, Cache] = {}
CACHE_DEPENDENCIES: set[models.Model] = set()

ENABLE_LIST_OPTIONS = ["true", "1", "yes", "y"]
IS_DJANGO_REDIS = hasattr(cache, "fake") is False


@functools.lru_cache(maxsize=1)
def is_compression_enabled():
    return os.getenv("COMPRESSION", "1").lower() in ENABLE_LIST_OPTIONS


@functools.lru_cache(maxsize=1)
def min_compression_size():
    return int(os.getenv("MIN_COMPRESSION_SIZE", "10"))


@functools.lru_cache(maxsize=1)
def use_gzip():
    return os.getenv("USE_GZIP", "0").lower() in ENABLE_LIST_OPTIONS


def must_compress(data):
    size = min_compression_size()
    if size == 0:
        return True

    return sys.getsizeof(data) / 1024 > size


class CacheMeta(type):

    def __init__(cls: Cache, name, bases, clsdict):

        super().__init__(name, bases, clsdict)

        if hasattr(cls, "model"):
            # key = cls.model.__module__ + '.' + cls.model.__name__

            CACHE_DESCRIPTORS[cls.model] = cls
            model = cls.model

            # .related.related_model gets the model where the field is DEFINED (e.g., SimpleModel)
            one_to_one_fwd = {
                getattr(model, x).field.related_model
                for x in dir(model)
                if isinstance(getattr(model, x), ForwardOneToOneDescriptor)
                and getattr(model, x).field.related_model != model  # Exclude self
            }

            # .related.related_model gets the model where the field is DEFINED (e.g., SimpleModel)
            one_to_one_rev = {
                getattr(model, x).related.related_model
                for x in dir(model)
                if isinstance(getattr(model, x), ReverseOneToOneDescriptor)
                and getattr(model, x).related.related_model != model  # Exclude self
            }

            # Finds FKs DEFINED ON 'model' (e.g., OneToOneRelatedModel)
            # .field.related_model gets the model they point TO
            many_to_one_forward = {
                getattr(model, x).field.related_model
                for x in dir(model)
                if isinstance(getattr(model, x), ForwardManyToOneDescriptor)
                and not isinstance(getattr(model, x), ForwardOneToOneDescriptor)  # Exclude O2O
                and getattr(model, x).field.related_model != model  # Exclude self
            }

            # Finds FKs in OTHER models pointing TO 'model' (e.g., OneToOneRelatedModel)
            # .field.model gets the model where the FK is defined
            reverse_many_to_one = {
                getattr(model, x).field.model
                for x in dir(model)
                if isinstance(getattr(model, x), ReverseManyToOneDescriptor)
                and getattr(model, x).field.model != model  # Exclude self
            }

            # Finds M2M fields defined ON 'model' (e.g., ManyToManyRelatedModel)
            # .field.related_model gets the model they point TO
            many_to_many = {
                getattr(model, x).field.related_model
                for x in dir(model)
                # Ensure it's an M2M descriptor AND the field is defined on this model (forward relationship)
                if isinstance(getattr(model, x), ManyToManyDescriptor)
                and getattr(model, x).field.model == model
                and getattr(model, x).field.related_model != model  # Exclude self
            }

            cls.one_to_one = one_to_one_fwd | one_to_one_rev
            cls.many_to_one = many_to_one_forward | reverse_many_to_one
            cls.many_to_many = many_to_many

            # CACHE_DEPENDENCIES = (CACHE_DEPENDENCIES | one_to_one | reverse_one_to_one | many_to_one |
            #                       reverse_many_to_one | many_to_many)

            if not cls.is_dependency:
                CACHE_DEPENDENCIES.update(cls.one_to_one | cls.many_to_one | cls.many_to_many)


def serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat().replace("+00:00", "Z")

    if isinstance(obj, timedelta):
        return str(obj.total_seconds())

    raise TypeError("Type not serializable")


class Cache(metaclass=CacheMeta):
    _version_prefix: str = ""
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
        return f"{cls._version_prefix}{key}__{qs}"

    @classmethod
    def _generate_keys_key(cls):
        return f"{cls._version_prefix}{cls.model.__name__}__keys"

    @classmethod
    @circuit
    def clear(cls, deep=0, max_deep=None) -> set | None:
        if max_deep is None:
            max_deep = cls.max_deep

        resolved = set()
        resolved.add(cls)

        # Always attempt to delete keys for the current level
        keys_to_delete = set()
        # Use the base key generated by _generate_key and append __keys
        cls_keys_key = cls._generate_keys_key()
        keys_to_delete.add(cls_keys_key)
        if existing_keys := cache.get(cls_keys_key):
            keys_to_delete.update(existing_keys)

        # Only recurse if max_deep has not been reached
        if deep < max_deep:
            for x in cls.one_to_one | cls.many_to_one | cls.many_to_many:
                # lazy load the dependency to can clean it
                if x not in CACHE_DESCRIPTORS and x in CACHE_DEPENDENCIES:

                    class DepCache(Cache):
                        model = x
                        is_dependency = True

                    # Add the dynamically created descriptor to resolved
                    # so its keys '__keys' entry gets deleted later.
                    # Also, ensures the dynamic cache is cleared recursively.
                    resolved.add(DepCache)
                    # Reinstate dynamic dependency registration
                    if x not in CACHE_DESCRIPTORS:
                        CACHE_DESCRIPTORS[x] = DepCache

                # Check if the dependency (static or dynamic) is already resolved
                dep_cache_cls = CACHE_DESCRIPTORS.get(x)
                if dep_cache_cls and dep_cache_cls not in resolved:
                    children = dep_cache_cls.clear(deep=deep + 1, max_deep=max_deep)
                    if children:
                        resolved = resolved.union(children)

        # Collect all keys to delete from resolved dependencies (including dynamic ones)
        for dep_cls in resolved:
            # Use the base key generated by _generate_key and append __keys
            dep_keys_key = dep_cls._generate_keys_key()
            keys_to_delete.add(dep_keys_key)
            if existing_dep_keys := cache.get(dep_keys_key):
                keys_to_delete.update(existing_dep_keys)

        if keys_to_delete:
            cache.delete_many(keys_to_delete)

        # Return the set of resolved cache classes for potential use by callers
        # Only return dependencies resolved *within this call frame* if deep > 0
        # The top-level call (deep=0) returns all resolved classes.
        return resolved if deep == 0 else (resolved - {cls})

    @classmethod
    @circuit
    def keys(cls):
        return cache.get(cls._generate_keys_key()) or set()

    @classmethod
    @circuit
    def get(cls, data, encoding: Optional[str] = None) -> dict:
        key = cls._generate_key(**data)
        data = cache.get(key)

        if data is None or hasattr(data, "get") is False:
            return None

        # Assume new format: dictionary with 'headers' and 'content'
        headers = data.get("headers", {})
        content = data.get("content", None)

        return content, headers

    @classmethod
    @circuit
    def set(
        cls,
        data: str | dict | list[dict],
        format: str = "application/json",
        timeout: int = -1,
        encoding: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> str:
        """Set a key value pair on the cache in bytes, it reminds the format and compress the data if needed."""

        if params is None:
            params = {}

        key = cls._generate_key(**params)
        res = {
            "headers": {
                "Content-Type": format,
            },
            "content": None,
        }

        # serialize the data to avoid serialization on get requests
        if format == "application/json":
            data = json.dumps(data, default=serializer).encode("utf-8")

        elif isinstance(data, str):
            data = data.encode("utf-8")

        else:
            data = data

        # in kilobytes
        if (compress := (must_compress(data) and is_compression_enabled())) and use_gzip():
            res["content"] = gzip.compress(data)
            res["headers"]["Content-Encoding"] = "gzip"

        elif compress and encoding == "br":
            res["content"] = brotli.compress(data)
            res["headers"]["Content-Encoding"] = "br"

        # faster option, it should be the standard in the future
        elif compress and encoding == "zstd":
            res["content"] = zstandard.compress(data)
            res["headers"]["Content-Encoding"] = "zstd"

        elif compress and encoding == "deflate":
            res["content"] = zlib.compress(data)
            res["headers"]["Content-Encoding"] = "deflate"

        elif compress and encoding == "gzip":
            res["content"] = gzip.compress(data)
            res["headers"]["Content-Encoding"] = "gzip"

        else:
            res["content"] = data

        # encode the response to avoid serialization on get requests
        if timeout == -1:
            cache.set(key, res)

        # encode the response to avoid serialization on get requests
        else:
            cache.set(key, res, timeout)

        cls_keys_key = cls._generate_keys_key()
        keys = cache.get(cls_keys_key) or set()
        keys.add(key)

        cache.set(cls_keys_key, keys)
        return res
