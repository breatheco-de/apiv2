from breathecode.utils import Cache
from .models import Event, LiveClass


class EventCache(Cache):
    model = Event


class LiveClassCache(Cache):
    model = LiveClass
