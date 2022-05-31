from __future__ import annotations
import urllib.parse, json
from django.core.cache import cache
from datetime import datetime
from breathecode.tests.mixins import DatetimeMixin

__all__ = ['Cache', 'CACHE_DESCRIPTORS']
CACHE_DESCRIPTORS: dict[int, Cache] = {}


class Cache(DatetimeMixin):
    model: str
    parents: list[str]

    def __init__(self):
        CACHE_DESCRIPTORS[hash(self.model)] = self

    def __generate_key__(self, storage_key=False, parent='', **kwargs):
        key = self.model.__name__ if not parent else parent

        if storage_key:
            return f'{key}__keys'

        credentials = urllib.parse.urlencode(kwargs)
        return f'{key}__{credentials}'

    def __add_key_to_storage__(self, key: str):
        storage_key = self.__generate_key__(storage_key=True)

        json_data = cache.get(storage_key)
        keys = json.loads(json_data) if json_data else []

        keys.append(key)

        json_data = json.dumps(keys)
        cache.set(storage_key, json_data)

    def keys(self):
        # we get key from cache to support multiprocess
        key = self.__generate_key__(storage_key=True)
        json_data = cache.get(key)
        return json.loads(json_data) if json_data else []

    def __clear_one__(self, parent=''):
        # we get key from cache to support multiprocess
        storage_key = self.__generate_key__(storage_key=True, parent=parent)
        keys = self.keys()

        for key in keys:
            cache.set(key, None)

        cache.set(storage_key, None)

    def clear(self):
        # we get key from cache to support multiprocess
        for parent in self.parents:
            self.__clear_one__(parent)

        self.__clear_one__()

    def get(self, **kwargs) -> dict:
        key = self.__generate_key__(**kwargs)
        json_data = cache.get(key)
        return json.loads(json_data) if json_data else None

    def __fix_fields__(self, data):
        for key in data.keys():
            if isinstance(data[key], datetime):
                data[key] = self.datetime_to_iso(data[key])

            if isinstance(data[key], dict):
                data[key] = self.__fix_fields__(data[key])

            if isinstance(data[key], list):
                if data[key] and isinstance(data[key][0], dict):
                    data[key] = [self.__fix_fields__(item) for item in data[key]]

                if data[key] and isinstance(data[key][0], datetime):
                    data[key] = [self.datetime_to_iso(item) for item in data[key]]

        return data

    def __fix_fields_in_array__(self, data):
        check_data = data
        if 'results' in data:
            check_data = data['results']

        if isinstance(check_data, dict):
            check_data = self.__fix_fields__(check_data)
        else:
            check_data = [self.__fix_fields__(x) for x in check_data]

        if 'results' in data:
            return {**data, 'results': check_data}

        return check_data

    def set(self, data, **kwargs):
        key = self.__generate_key__(**kwargs)
        data = self.__fix_fields_in_array__(data)

        json_data = json.dumps(data)
        cache.set(key, json_data)

        self.__add_key_to_storage__(key)
