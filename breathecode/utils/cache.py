import urllib.parse, json, re, os
from django.core.cache import cache, caches
from datetime import datetime
from breathecode.tests.mixins import DatetimeMixin


class Cache(DatetimeMixin):
    app: str
    name: str

    def __init__(self, app: str, name: str):
        self.app = app
        self.name = name

    def __generate_key__(self, resource=0, storage_key=False, **kwargs):
        key = f'{self.app}__{self.name}'
        if storage_key:
            return f'{key}__keys'

        credentials = urllib.parse.urlencode(kwargs)
        return f'{key}__{credentials}__{resource}'

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

    def clear(self):
        # we get key from cache to support multiprocess
        storage_key = self.__generate_key__(storage_key=True)
        keys = self.keys()

        for key in keys:
            cache.set(key, None)

        cache.set(storage_key, None)

    def get(self, resource=0, **kwargs) -> dict:
        key = self.__generate_key__(resource, **kwargs)
        json_data = cache.get(key)
        return json.loads(json_data) if json_data else None


    def __fix_fields__(self, data):
        for key in data.keys():
            if isinstance(data[key], datetime):
                data[key] = self.datetime_to_iso(data[key])

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

    def set(self, data, resource=0, **kwargs):
        key = self.__generate_key__(resource, **kwargs)
        data = self.__fix_fields_in_array__(data)

        json_data = json.dumps(data)
        cache.set(key, json_data)

        self.__add_key_to_storage__(key)
