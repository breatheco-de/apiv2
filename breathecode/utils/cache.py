from django.core.cache import cache

class Cache():
    name: str

    def __init__(self, name: str):
        self.name = name

    def clear(self):
        cache.delete_pattern(f'{self.name}_*')

    def keys(self, all=False):
        if hasattr(cache, 'keys'):
            query = f'{self.name}_*' if not all else '*'
            return cache.keys(query)
        return []