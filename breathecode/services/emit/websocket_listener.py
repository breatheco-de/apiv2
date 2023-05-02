from typing import Callable
from warnings import warn

__all__ = ['WebsocketListener']

cache: dict[str, list[Callable]] = {}


class WebsocketListener:
    """This class is used to send data to Django Channels"""

    def __init__(self, name):
        warn('Deprecated in favor of Microservice implementation, remove it as soon as possible',
             DeprecationWarning,
             stacklevel=2)

        self.name = name

        if not name in cache:
            cache[self.name] = []

    def add_listener(self, handler):
        if handler in cache[self.name]:
            cache[self.name].append(handler)

    def remove_listener(self, handler):
        if handler in cache[self.name]:
            cache[self.name].remove(handler)

    def emit(self, data):
        for handler in cache[self.name]:
            handler(data)
