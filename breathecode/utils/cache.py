import urllib.parse, json, re
from django.core.cache import cache, caches
from datetime import datetime
from breathecode.tests.mixins import DatetimeMixin

class Cache(DatetimeMixin):
    app: str
    name: str

    def __init__(self, app: str, name: str):
        self.app = app
        self.name = name

    def clear(self):
        pass
        # cache.clear()
        # cache.delete_pattern(f'{self.app}_{self.name}_*')

    def keys(self, all=False):
        if hasattr(cache, 'keys'):
            query = f'{self.app}_{self.name}_*' if not all else '*'
            return cache.keys(query)
        return []

    def __generate_key__(self, resource=0, **kwargs):
        credentials = urllib.parse.urlencode(kwargs)
        return f'{self.app}_{self.name}_{credentials}_{resource}'

    def get(self, resource=0, **kwargs) -> dict:
        key = self.__generate_key__(resource, **kwargs)
        json_data = cache.get(key)
        return json.loads(json_data) if json_data else None


    def __fix_fields__(self, data):
        for key in data.keys():
            if isinstance(data[key], datetime):
                data[key] = self.datetime_to_iso(data[key])

        return data

    def set(self, data, resource=0, **kwargs):
        key = self.__generate_key__(resource, **kwargs)

        if isinstance(data, dict):
            data = self.__fix_fields__(data)
        else:
            data = [self.__fix_fields__(x) for x in data]

        json_data = json.dumps(data)
        cache.set(key, json_data)
