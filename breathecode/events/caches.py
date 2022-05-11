from breathecode.utils import Cache
from .models import Event


class EventCache(Cache):
    model = Event
    depends = ['User', 'Academy', 'Organization', 'Venue', 'EventType']
    parents = ['EventCheckin']
